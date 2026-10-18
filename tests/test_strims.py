import sys
from pathlib import Path
import unittest
import struct
from unittest.mock import patch
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'plugin.video.strims24'))
from client import feed_events, resolve, SiteError, Client, player_url
from hls_proxy import unwrap_ts, Proxy
from live_playlist import PlaylistFeed, LIMIT


class ProxyTests(unittest.TestCase):
    def test_only_verified_transport_stream_is_unwrapped(self):
        png = b'\x89PNG\r\n\x1a\n' + b'\x00\x00\x00\x00IEND' + b'\x00'*4
        ts = (b'G' + b'\x00'*187)*4
        self.assertEqual(unwrap_ts(png+ts), ts)
        self.assertEqual(unwrap_ts(ts), ts)
        with self.assertRaises(ValueError): unwrap_ts(png+b'not video')
        with self.assertRaises(ValueError): unwrap_ts(png[:12])

    def test_playlist_rewrites_segments_and_keys(self):
        proxy = Proxy('https://cdn.example/live.m3u8','https://iplayer24.me/')
        try:
            body=proxy.playlist('#EXTM3U\n#EXT-X-KEY:METHOD=AES-128,URI="key"\npart.ts\n','https://cdn.example/live.m3u8')
            self.assertNotIn('URI="key"',body)
            self.assertIn('https://cdn.example/part.ts',proxy.urls.values())
            self.assertIn('https://cdn.example/key',proxy.urls.values())
            self.assertIn(proxy.base,body)
        finally:proxy.server.server_close()

    def test_live_playlist_survives_cache_eviction(self):
        proxy=Proxy('https://cdn.example/live.m3u8','https://iplayer24.me/')
        try:
            key=proxy.url.rsplit('/',1)[-1]
            proxy.playlists.add(key)
            for i in range(1010):proxy.register('https://cdn.example/%s.ts'%i)
            self.assertIn(key,proxy.urls)
            self.assertLessEqual(len(proxy.urls),1000)
        finally:proxy.server.server_close()

class Tests(unittest.TestCase):
    def test_channels_catalog_is_no_longer_requested(self):
        with patch('client.get_json') as get:
            c = Client()
            c.load_channels()
            c.load_channels()
        get.assert_not_called()
        self.assertEqual(c.warnings, [])

    @patch('client.request')
    def test_new_echo_websocket_manifest(self, request):
        token = 'c077690fade9109b989ab8b5f94995a1'
        request.return_value = ('var TOKEN = "%s"; var WS_BASE = "wss://l1.strims24.st/ws"; var MANIFEST = "/bloop/" + TOKEN + ".m3u8";' % token,
                                'text/html', 'https://iplayer24.me/echo/' + token)
        self.assertEqual(resolve('https://iplayer.is/echo/' + token),
                         ('wss://l1.strims24.st/ws#' + token, 'https://iplayer24.me/echo/' + token))
        self.assertEqual(request.call_args.args[0], 'https://iplayer24.me/echo/' + token)

    def test_new_sports_and_nfl_api_slug(self):
        from client import SPORTS
        self.assertTrue({'winter-sports', 'motorsport', 'waterpolo'} <= set(SPORTS))
        with patch('client.get_json', return_value={'items': []}) as get, patch('client.request', return_value=('', '', '')):
            self.assertEqual(Client().events('nfl', tomorrow=True), [])
        self.assertTrue(get.call_args.args[0].startswith('/api/v1/american-football/'))

    def test_sport_without_feed_uses_custom_events(self):
        import time
        event = {'match_id':'CUST:water', 'name':'Water', 'start_ts':int(time.time()) + 100}
        with patch('client.get_json', return_value={'items':[event]}), patch('client.request') as request:
            result = Client().events('waterpolo', tomorrow=True)
        request.assert_not_called()
        self.assertEqual(result[0]['name'], 'Water')

    @patch('client.get_json', return_value=[])
    def test_live_category_filters_merges_and_keeps_partial_results(self, get_json):
        def events(child, sport, tomorrow=False):
            if sport == 'tennis': raise SiteError('Niedostępne')
            if sport == 'football':
                return [{'match_id':'FS:one','name':'Mecz','live':True,'start_ts':200},
                        {'match_id':'FS:future','name':'Jutro','live':False,'start_ts':300}]
            return [{'match_id':'CUST:race','name':'Wyścig','live':True,'start_ts':100}]
        with patch('client.SPORTS', {'football':('Piłka nożna',1),'tennis':('Tenis',2),'cycling':('Kolarstwo',34)}), patch.object(Client,'events',events):
            client=Client()
            result=client.live_events()
        self.assertEqual([e['name'] for e in result],['Wyścig','Mecz'])
        self.assertEqual(result[0]['sport'],'cycling')
        self.assertIn('Tenis',client.warnings[0])
        get_json.assert_not_called()

    @patch('client.get_json', return_value=[])
    @patch.object(Client,'events',side_effect=SiteError('Offline'))
    def test_live_category_does_not_hide_total_failure(self, events, get_json):
        with self.assertRaises(SiteError): Client().live_events()

    def test_custom_token_route(self):
        token = '60a95dce5bbaf5cb6ae395717f84e898'
        self.assertEqual(player_url(token), 'https://iplayer24.me/echo/' + token)
        self.assertEqual(player_url('/player/lean/2'), 'https://iplayer24.me/player/lean/2')
        self.assertEqual(player_url('https://example.com/live'), 'https://example.com/live')

    @patch('client.request')
    def test_old_history_link_and_escaped_jwplayer_url(self, request):
        token = '60a95dce5bbaf5cb6ae395717f84e898'
        request.side_effect = [(r'var STREAM_URL = "https:\/\/cdn.example\/index.m3u8";', 'text/html', 'https://iplayer24.me/echo/' + token),
            ('#EXTM3U\n', 'application/vnd.apple.mpegurl', 'https://cdn.example/index.m3u8')]
        self.assertEqual(resolve('https://iplayer.is/' + token)[0], 'https://cdn.example/index.m3u8')
        self.assertEqual(request.call_args_list[0].args[0], 'https://iplayer24.me/echo/' + token)

    def test_real_feed(self):
        data = feed_events((root/'tests/fixtures/schedule.txt').read_text(encoding='utf-8'))
        self.assertIn('FS:MP8ki7KE', data)
        self.assertIn('Gibraltar', data['FS:MP8ki7KE']['name'])

    @patch('client.request')
    def test_nested_hls(self, request):
        request.side_effect = [('<iframe src="/embed"></iframe>', 'text/html', 'https://example.com/player'),
            ('<video src="https://cdn.example/live.m3u8?x=1&amp;y=2">', 'text/html', 'https://example.com/embed'),
            ('#EXTM3U\n#EXT-X-TARGETDURATION:6', 'application/vnd.apple.mpegurl', 'https://cdn.example/live.m3u8?x=1&y=2')]
        url, referer = resolve('https://example.com/player')
        self.assertEqual(url,'https://cdn.example/live.m3u8?x=1&y=2')
        self.assertEqual(referer,'https://example.com/embed')

    @patch('client.request')
    def test_script_only_player_is_not_playable(self, request):
        request.return_value=('<script>fetch("/secret")</script>','text/html','https://example.com')
        with self.assertRaises(SiteError): resolve('https://example.com')

    @patch('client.request')
    def test_drm_rejected(self, request):
        request.return_value=('#EXTM3U\n#EXT-X-KEY:METHOD=SAMPLE-AES,KEYFORMAT="com.apple.streamingkeydelivery"','', 'https://example.com')
        with self.assertRaisesRegex(SiteError,'DRM'): resolve('https://example.com')

    @patch('client.get_json')
    def test_disabled_sources_and_missing_channels(self, get):
        get.side_effect=[{'custom_urls':[{'name':'no','url':'/no','enabled':False},{'name':'yes','url':'/yes'}]},SiteError('404')]
        c=Client()
        self.assertEqual(c.sources('CUST:test'),[{'name':'yes','url':'https://iplayer24.me/yes'}])

    @patch('client.request')
    def test_loop_stops(self, request):
        request.return_value=('<iframe src="https://example.com"></iframe>','text/html','https://example.com')
        with self.assertRaises(SiteError): resolve('https://example.com')
        self.assertEqual(request.call_count,1)

class WebSocketTests(unittest.TestCase):
    def feed(self, payload):
        import io
        feed = PlaylistFeed('wss://example.com/ws#token', 'https://player.example/echo/token')
        reader = io.BytesIO(payload)
        class Sock:
            def recv(self, size): return reader.read(size)
            def sendall(self, data): self.sent = data
        feed.sock = Sock()
        return feed

    def test_fragmented_playlist_and_ping(self):
        text = b'#EXTM3U\n#EXTINF:6,\nhttps://cdn.example/1.ts\n'
        first, last = text[:15], text[15:]
        feed = self.feed(bytes((1,len(first))) + first + b'\x89\x01x' + bytes((0x80,len(last))) + last + b'\x88\x00')
        with self.assertRaises(OSError): feed._receive()
        self.assertEqual(feed.snapshot(), text.decode())
        self.assertTrue(feed.ready.is_set())
        # Client pong frames must be masked and carry the same ping payload.
        self.assertEqual(feed.sock.sent[0], 0x8A)
        self.assertEqual(feed.sock.sent[-1] ^ feed.sock.sent[2], ord('x'))

    def test_oversized_frame_is_rejected_before_reading_body(self):
        feed = self.feed(b'\x81\x7f' + struct.pack('!Q', LIMIT + 1))
        with self.assertRaisesRegex(ValueError, 'size'): feed._receive()

    def test_stale_playlist_is_not_served(self):
        import time
        feed = self.feed(b'')
        feed.text, feed.updated = '#EXTM3U', time.monotonic() - 46
        with self.assertRaisesRegex(ValueError, 'stale'): feed.snapshot()

    def test_proxy_does_not_fetch_virtual_manifest_over_http(self):
        import urllib.request
        p = Proxy('wss://example.com/ws#token', 'https://player.example/echo/token')
        with patch.object(p.feed, 'start'), patch.object(p.feed, 'close'), patch.object(p.feed, 'snapshot', return_value='#EXTM3U\n#EXTINF:6,\nhttps://cdn.example/1.ts\n'):
            try:
                url = p.start()
                with urllib.request.urlopen(url) as response:
                    data = response.read().decode()
                self.assertIn(p.base, data)
                self.assertNotIn('https://cdn.example/1.ts', data)
            finally:
                p.close()

if __name__=='__main__':unittest.main()
