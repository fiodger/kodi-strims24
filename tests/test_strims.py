import sys
from pathlib import Path
import unittest
from unittest.mock import patch
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'plugin.video.strims24'))
from client import feed_events, resolve, SiteError, Client, player_url
from hls_proxy import unwrap_ts, Proxy


class ProxyTests(unittest.TestCase):
    def test_only_verified_transport_stream_is_unwrapped(self):
        png = b'\x89PNG\r\n\x1a\n' + b'\x00\x00\x00\x00IEND' + b'\x00'*4
        ts = (b'G' + b'\x00'*187)*4
        self.assertEqual(unwrap_ts(png+ts), ts)
        self.assertEqual(unwrap_ts(ts), ts)
        with self.assertRaises(ValueError): unwrap_ts(png+b'not video')
        with self.assertRaises(ValueError): unwrap_ts(png[:12])

    def test_playlist_rewrites_segments_and_keys(self):
        proxy = Proxy('https://cdn.example/live.m3u8','https://iplayer.is/')
        try:
            body=proxy.playlist('#EXTM3U\n#EXT-X-KEY:METHOD=AES-128,URI="key"\npart.ts\n','https://cdn.example/live.m3u8')
            self.assertNotIn('URI="key"',body)
            self.assertIn('https://cdn.example/part.ts',proxy.urls.values())
            self.assertIn('https://cdn.example/key',proxy.urls.values())
            self.assertIn(proxy.base,body)
        finally:proxy.server.server_close()

    def test_live_playlist_survives_cache_eviction(self):
        proxy=Proxy('https://cdn.example/live.m3u8','https://iplayer.is/')
        try:
            key=proxy.url.rsplit('/',1)[-1]
            proxy.playlists.add(key)
            for i in range(1010):proxy.register('https://cdn.example/%s.ts'%i)
            self.assertIn(key,proxy.urls)
            self.assertLessEqual(len(proxy.urls),1000)
        finally:proxy.server.server_close()

class Tests(unittest.TestCase):
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
        get_json.assert_called_once_with('/channels')

    @patch('client.get_json', return_value=[])
    @patch.object(Client,'events',side_effect=SiteError('Offline'))
    def test_live_category_does_not_hide_total_failure(self, events, get_json):
        with self.assertRaises(SiteError): Client().live_events()

    def test_custom_token_route(self):
        token = '60a95dce5bbaf5cb6ae395717f84e898'
        self.assertEqual(player_url(token), 'https://iplayer.is/echo/' + token)
        self.assertEqual(player_url('/player/lean/2'), 'https://iplayer.is/player/lean/2')
        self.assertEqual(player_url('https://example.com/live'), 'https://example.com/live')

    @patch('client.request')
    def test_old_history_link_and_escaped_jwplayer_url(self, request):
        token = '60a95dce5bbaf5cb6ae395717f84e898'
        request.side_effect = [(r'var STREAM_URL = "https:\/\/cdn.example\/index.m3u8";', 'text/html', 'https://iplayer.is/echo/' + token),
            ('#EXTM3U\n', 'application/vnd.apple.mpegurl', 'https://cdn.example/index.m3u8')]
        self.assertEqual(resolve('https://iplayer.is/' + token)[0], 'https://cdn.example/index.m3u8')
        self.assertEqual(request.call_args_list[0].args[0], 'https://iplayer.is/echo/' + token)

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
        self.assertEqual(c.sources('CUST:test'),[{'name':'yes','url':'https://iplayer.is/yes'}])

    @patch('client.request')
    def test_loop_stops(self, request):
        request.return_value=('<iframe src="https://example.com"></iframe>','text/html','https://example.com')
        with self.assertRaises(SiteError): resolve('https://example.com')
        self.assertEqual(request.call_count,1)

if __name__=='__main__':unittest.main()
