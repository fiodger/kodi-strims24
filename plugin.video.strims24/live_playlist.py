"""Small RFC 6455 client for Capitan's public live HLS playlist feed."""
import base64
import hashlib
import json
import os
import socket
import ssl
import struct
import threading
import time
import urllib.parse

from client import SiteError, UA

LIMIT = 1024 * 1024


class PlaylistFeed:
    def __init__(self, url, referer):
        parts = urllib.parse.urlsplit(url)
        if (parts.scheme != 'wss' or not parts.hostname or parts.username or parts.password
                or not parts.fragment or any(c in url + referer for c in '\r\n')):
            raise SiteError('Nieprawidłowy adres playlisty live.')
        self.parts = parts
        self.referer = referer
        self.sock = None
        self.text = ''
        self.updated = 0
        self.lock = threading.Lock()
        self.ready = threading.Event()
        self.stopped = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _read(self, length):
        data = bytearray()
        while len(data) < length:
            chunk = self.sock.recv(length - len(data))
            if not chunk:
                raise OSError('WebSocket closed')
            data.extend(chunk)
        return bytes(data)

    def _send(self, opcode, payload):
        mask = os.urandom(4)
        size = len(payload)
        if size < 126:
            header = bytes((0x80 | opcode, 0x80 | size))
        elif size < 65536:
            header = bytes((0x80 | opcode, 0xFE)) + struct.pack('!H', size)
        else:
            header = bytes((0x80 | opcode, 0xFF)) + struct.pack('!Q', size)
        self.sock.sendall(header + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))

    def _connect(self):
        p = self.parts
        raw = socket.create_connection((p.hostname, p.port or 443), timeout=12)
        try:
            self.sock = ssl.create_default_context().wrap_socket(raw, server_hostname=p.hostname)
        except Exception:
            raw.close()
            raise
        key = base64.b64encode(os.urandom(16)).decode('ascii')
        origin = urllib.parse.urlsplit(self.referer)
        path = p.path or '/'
        if p.query:
            path += '?' + p.query
        request = ('GET %s HTTP/1.1\r\nHost: %s\r\nUpgrade: websocket\r\n'
                   'Connection: Upgrade\r\nSec-WebSocket-Key: %s\r\n'
                   'Sec-WebSocket-Version: 13\r\nOrigin: %s://%s\r\n'
                   'User-Agent: %s\r\n\r\n') % (path, p.netloc, key, origin.scheme, origin.netloc, UA)
        self.sock.sendall(request.encode('ascii'))
        response = bytearray()
        while not response.endswith(b'\r\n\r\n'):
            response.extend(self._read(1))
            if len(response) > 16384:
                raise ValueError('Oversized WebSocket handshake')
        lines = response.decode('iso-8859-1').split('\r\n')
        headers = dict((k.lower().strip(), v.strip()) for k, v in
                       (line.split(':', 1) for line in lines[1:] if ':' in line))
        accept = base64.b64encode(hashlib.sha1((key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode('ascii')).digest()).decode('ascii')
        if (lines[0].split()[1] != '101' or headers.get('sec-websocket-accept') != accept
                or headers.get('upgrade', '').lower() != 'websocket'
                or 'sec-websocket-extensions' in headers):
            raise ValueError('Invalid WebSocket handshake')
        self._send(1, json.dumps({'subscribe': p.fragment}).encode('utf-8'))

    def _receive(self):
        fragments = bytearray()
        message_type = None
        while not self.stopped.is_set():
            first, second = self._read(2)
            final, opcode = bool(first & 0x80), first & 15
            if first & 0x70 or second & 0x80:
                raise ValueError('Unsupported WebSocket frame')
            length = second & 127
            if length == 126:
                length = struct.unpack('!H', self._read(2))[0]
            elif length == 127:
                length = struct.unpack('!Q', self._read(8))[0]
            if length > LIMIT or (opcode >= 8 and (length > 125 or not final)):
                raise ValueError('Invalid WebSocket frame size')
            payload = self._read(length)
            if opcode == 8:
                raise OSError('WebSocket closed')
            if opcode == 9:
                self._send(10, payload)
                continue
            if opcode == 10:
                continue
            if opcode in (1, 2):
                if message_type is not None:
                    raise ValueError('Unexpected fragmented message')
                message_type = opcode
            elif opcode != 0 or message_type is None:
                raise ValueError('Unexpected WebSocket opcode')
            fragments.extend(payload)
            if len(fragments) > LIMIT:
                raise ValueError('Oversized playlist')
            if final:
                text = fragments.decode('utf-8')
                if text.lstrip().startswith('#EXTM3U') and '#EXTINF' in text:
                    with self.lock:
                        self.text, self.updated = text, time.monotonic()
                    self.ready.set()
                fragments.clear()
                message_type = None

    def _disconnect(self):
        sock, self.sock = self.sock, None
        if sock:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock.close()

    def _run(self):
        while not self.stopped.is_set():
            try:
                self._connect()
                self._receive()
            except (OSError, ValueError, AttributeError):
                pass
            finally:
                self._disconnect()
            self.stopped.wait(2)

    def start(self):
        self.thread.start()
        if not self.ready.wait(20):
            self.close()
            raise SiteError('Brak playlisty live z serwera transmisji. Spróbuj innego źródła.')

    def snapshot(self):
        with self.lock:
            if not self.text or time.monotonic() - self.updated > 45:
                raise ValueError('Live playlist unavailable or stale')
            return self.text

    def close(self):
        self.stopped.set()
        self._disconnect()
        if self.thread.ident is not None:
            self.thread.join(timeout=2)
