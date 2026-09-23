"""In-memory HLS adapter for image-prefixed MPEG-TS segments."""
import re
import secrets
import threading
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from client import UA, safe_url


def unwrap_ts(data):
    if not data.startswith(b'\x89PNG\r\n\x1a\n'):
        return data
    offset = 8
    while offset + 12 <= len(data) and offset < 65536:
        length = int.from_bytes(data[offset:offset+4], 'big')
        kind = data[offset+4:offset+8]
        end = offset + length + 12
        if end > len(data):
            break
        offset = end
        if kind == b'IEND':
            payload = data[offset:]
            if len(payload) >= 188 * 3 and all(payload[i*188] == 0x47 for i in range(3)):
                return payload
            break
    raise ValueError('PNG without verified MPEG-TS payload')


class Proxy:
    def __init__(self, url, referer):
        self.referer = referer
        self.key = secrets.token_urlsafe(24)
        self.urls = {}
        self.playlists = set()
        self.lock = threading.Lock()
        self.closed = False
        proxy = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass

            def do_HEAD(self):
                self.do_GET(head=True)

            def do_GET(self, head=False):
                if self.headers.get('Host') != '127.0.0.1:%s' % self.server.server_port:
                    self.send_error(403); return
                if not self.path.startswith('/' + proxy.key + '/'):
                    self.send_error(403); return
                with proxy.lock:
                    upstream = proxy.urls.get(self.path.rsplit('/', 1)[-1])
                if upstream is None:
                    self.send_error(404); return
                try:
                    req = urllib.request.Request(upstream, headers={
                        'User-Agent': UA, 'Referer': proxy.referer, 'Accept-Encoding': 'identity'})
                    with urllib.request.urlopen(req, timeout=15) as response:
                        data = response.read(16 * 1024 * 1024 + 1)
                        final = response.url
                        kind = response.headers.get('Content-Type', 'application/octet-stream')
                    if len(data) > 16 * 1024 * 1024:
                        raise ValueError('Oversized media response')
                    if data.lstrip().startswith(b'#EXTM3U'):
                        with proxy.lock:
                            proxy.playlists.add(self.path.rsplit('/', 1)[-1])
                        data = proxy.playlist(data.decode('utf-8-sig'), final).encode('utf-8')
                        kind = 'application/vnd.apple.mpegurl'
                    elif data.startswith(b'\x89PNG\r\n\x1a\n'):
                        data = unwrap_ts(data)
                        kind = 'video/mp2t'
                    self.send_response(200)
                    self.send_header('Content-Type', kind)
                    self.send_header('Content-Length', str(len(data)))
                    self.send_header('Cache-Control', 'no-store')
                    self.end_headers()
                    if not head:
                        self.wfile.write(data)
                except (OSError, ValueError):
                    if not proxy.closed:
                        try: self.send_error(502, 'Upstream media unavailable')
                        except OSError: pass

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.daemon_threads = True
        self.base = 'http://127.0.0.1:%s/%s/' % (self.server.server_port, self.key)
        self.url = self.register(url)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def register(self, url):
        safe_url(url)
        with self.lock:
            for key, existing in self.urls.items():
                if existing == url: return self.base + key
            key = secrets.token_hex(12)
            self.urls[key] = url
            while len(self.urls) > 1000:
                victim = next((k for k in self.urls if k not in self.playlists), None)
                if victim is None:
                    break
                del self.urls[victim]
        return self.base + key

    def playlist(self, text, base):
        lines = []
        for line in text.splitlines():
            if re.search(r'KEYFORMAT\s*=\s*"(?!identity")', line, re.I):
                raise ValueError('Unsupported DRM')
            if line.startswith('#'):
                line = re.sub(r'URI="([^"]+)"', lambda m: 'URI="' + self.register(urllib.parse.urljoin(base, m[1])) + '"', line)
            elif line.strip():
                line = self.register(urllib.parse.urljoin(base, line.strip()))
            lines.append(line)
        return '\n'.join(lines) + '\n'

    def start(self):
        self.thread.start()
        return self.url

    def close(self):
        self.closed = True
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
