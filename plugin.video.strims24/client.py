import datetime
import html
from html.parser import HTMLParser
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = 'https://capitanstrims.st'
PLAYER = 'https://iplayer24.me'
FEED = 'https://1.newsoccers.one/2/x/feed'
UA = 'Mozilla/5.0 (Kodi; Strims24/0.1.3)'
SPORTS = {'football': ('Piłka nożna', 1), 'tennis': ('Tenis', 2),
          'basketball': ('Koszykówka', 3), 'hockey': ('Hokej', 4),
          'volleyball': ('Siatkówka', 12), 'handball': ('Piłka ręczna', 7),
          'mma': ('MMA', 28), 'boxing': ('Boks', 16), 'nfl': ('NFL', 5),
          'snooker': ('Snooker', 15), 'darts': ('Dart', 14), 'futsal': ('Futsal', 11),
          'cycling': ('Kolarstwo', 34), 'baseball': ('Baseball', 6),
          'cricket': ('Krykiet', 13), 'golf': ('Golf', 23),
          'winter-sports': ('Sporty zimowe', 37),
          'motorsport': ('Sporty motorowe', 31), 'waterpolo': ('Piłka wodna', 0)}


class SiteError(Exception):
    pass


def safe_url(url):
    p = urllib.parse.urlsplit(url)
    if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password or any(c in url for c in '\r\n|'):
        raise SiteError('Nieprawidłowy adres źródła.')
    return url


def request(url, referer=BASE + '/', feed=False):
    safe_url(url)
    headers = {'User-Agent': UA, 'Referer': referer, 'Accept-Encoding': 'identity'}
    if feed:
        headers['x-fsign'] = 'SW9D1eZo'
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=15) as r:
            body = r.read(4 * 1024 * 1024 + 1)
            if len(body) > 4 * 1024 * 1024:
                raise SiteError('Odpowiedź źródła jest zbyt duża.')
            return body.decode('utf-8-sig', 'replace'), r.headers.get('Content-Type', ''), r.url
    except urllib.error.HTTPError as e:
        if e.code == 403:
            raise SiteError('%s: HTTP 403. Serwis odrzucił połączenie; może wymagać weryfikacji przeglądarki.' % urllib.parse.urlsplit(url).hostname)
        raise SiteError('%s: HTTP %s. Źródło jest niedostępne.' % (urllib.parse.urlsplit(url).hostname, e.code))
    except (urllib.error.URLError, OSError):
        raise SiteError('Nie udało się połączyć z %s.' % urllib.parse.urlsplit(url).hostname)


def get_json(path):
    body, _, _ = request(BASE + path)
    try:
        return json.loads(body)
    except ValueError:
        raise SiteError('Serwis zwrócił stronę zamiast danych. Spróbuj później.')


def player_url(value):
    # Bare custom source IDs use /echo/, as observed in the live site iframe.
    # Explicit URLs and paths must keep their provider-specific routing.
    if re.fullmatch(r'[a-fA-F0-9]{32}', value):
        return PLAYER + '/echo/' + value
    return urllib.parse.urljoin(PLAYER + '/', value)


def feed_events(text):
    result = {}
    league = ''
    for row in text.split('~'):
        values = dict(c.split('÷', 1) for c in row.split('¬') if '÷' in c)
        if values.get('ZA'):
            league = values['ZA']
        if not values.get('AA'):
            continue
        name = ' — '.join(filter(None, (values.get('CX') or values.get('AE'), values.get('AF'))))
        if not name:
            continue
        try:
            start = int(values.get('AD', 0))
            channels = json.loads(values.get('AL') or '{}').get('1', [])
        except (ValueError, AttributeError):
            start, channels = 0, []
        key = 'FS:' + values['AA']
        result[key] = {'match_id': key, 'name': name, 'start_ts': start,
                       'status': values.get('AB'), 'league': league,
                       'tvi': [str(c['TVI']).lstrip('0') for c in channels if isinstance(c, dict) and c.get('TVI')]}
    return result


class Client:
    def __init__(self):
        self.warnings = []
        self.channels = []
        self.channels_loaded = False

    def load_channels(self):
        # Capitan's current frontend disables this catalog. Sources are listed
        # in each match's custom_urls, so /channels must no longer be requested.
        self.channels_loaded = True

    def live_events(self):
        self.load_channels()

        def load(sport):
            child = Client()
            child.channels = self.channels
            child.channels_loaded = True
            try:
                events = child.events(sport)
                return [dict(e, sport=sport) for e in events if e['live']], child.warnings, True
            except SiteError as exc:
                return [], [SPORTS[sport][0] + ': ' + str(exc)], False

        result = {}
        successes = 0
        with ThreadPoolExecutor(max_workers=4) as pool:
            for events, warnings, success in pool.map(load, SPORTS):
                successes += int(success)
                self.warnings.extend(warnings)
                for event in events:
                    result[(event['sport'], event['match_id'])] = event
        if not successes:
            raise SiteError('Nie udało się pobrać wydarzeń z żadnej dyscypliny. Sprawdź połączenie i spróbuj ponownie.')
        self.warnings = list(dict.fromkeys(self.warnings))
        return sorted(result.values(), key=lambda e: (e.get('start_ts', 0), e['name']))

    def events(self, sport, tomorrow=False):
        if sport not in SPORTS:
            raise SiteError('Nieznana dyscyplina.')
        self.load_channels()
        today = datetime.date.today()
        offsets = [1] if tomorrow else [-1, 0]
        def load(offset):
            day = today + datetime.timedelta(days=offset)
            slug = 'american-football' if sport == 'nfl' else sport
            backend = get_json('/api/v1/%s/%s' % (slug, day.isoformat())).get('items', [])
            if not SPORTS[sport][1]:
                return backend, {}, None
            try:
                raw, _, _ = request('%s/f_%s_%s_2_en_1' % (FEED, SPORTS[sport][1], offset), feed=True)
                return backend, feed_events(raw), None
            except SiteError as e:
                return backend, {}, str(e)
        with ThreadPoolExecutor(max_workers=2) as pool:
            batches = list(pool.map(load, offsets))
        backend, feed = {}, {}
        for items, events, warning in batches:
            backend.update({x['match_id']: x for x in items if isinstance(x, dict) and x.get('match_id')})
            feed.update(events)
            if warning:
                self.warnings.append(warning)
        tvi = {re.sub(r'^TVI0*', '', str(c.get('FS', ''))) for c in self.channels}
        selected = {k: v for k, v in feed.items() if k in backend or tvi.intersection(v['tvi'])}
        selected.update({k: v for k, v in backend.items() if v.get('name')})
        now = time.time()
        output = []
        for event in selected.values():
            start = event.get('start_ts') or 0
            end = event.get('end_ts') or start + 6 * 3600
            if event.get('status') == '3' or (end and end < now and event.get('status') != '2'):
                continue
            event['live'] = event.get('status') == '2' or start <= now < end
            output.append(event)
        return sorted(output, key=lambda e: (not e['live'], e.get('start_ts', 0), e['name']))

    def sources(self, match_id):
        detail = get_json('/api/v1/match/' + urllib.parse.quote(match_id, safe=''))
        self.load_channels()
        by_id = {str(c.get('id')): c for c in self.channels}
        by_tvi = {re.sub(r'^TVI0*', '', str(c.get('FS', ''))): c for c in self.channels}
        sources = []
        disabled = set()
        for c in detail.get('channels', []):
            key = str(c.get('id', ''))
            mapped = by_id.get(key) or by_tvi.get(re.sub(r'^TVI0*', '', key))
            if c.get('enabled') is False:
                if mapped: disabled.add(str(mapped['id']))
                continue
            if mapped:
                sources.append({'name': mapped.get('name', 'Kanał'), 'url': PLAYER + '/player/lean/' + str(mapped['id'])})
        if match_id.startswith('FS:') and self.channels:
            try:
                raw, _, _ = request(FEED + '/df_dos_1_' + urllib.parse.quote(match_id[3:], safe='') + '_', feed=True)
                for key in re.findall(r'TVI÷(\d+)', raw):
                    c = by_tvi.get(key.lstrip('0'))
                    if c and str(c['id']) not in disabled:
                        sources.append({'name': c.get('name', 'Kanał'), 'url': PLAYER + '/player/lean/' + str(c['id'])})
            except SiteError:
                pass
        for c in detail.get('custom_urls', []):
            if c.get('enabled') is not False and c.get('url'):
                sources.append({'name': c.get('name', 'Źródło'), 'url': player_url(c['url'])})
        return list({s['url']: s for s in sources}.values())


class PlayerHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.media, self.frames = [], []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get('src'):
            if tag in ('video', 'source'): self.media.append(values['src'])
            if tag == 'iframe': self.frames.append(values['src'])


def resolve(url, referer=BASE + '/', seen=None):
    parsed = urllib.parse.urlsplit(url)
    # Existing Kodi favourites/history may still point to the former player.
    if parsed.hostname == 'iplayer.is':
        url = urllib.parse.urlunsplit(('https', 'iplayer24.me', parsed.path, parsed.query, ''))
        parsed = urllib.parse.urlsplit(url)
    # Repair playback items left in Kodi history from version 0.1.0.
    if parsed.hostname == 'iplayer24.me' and re.fullmatch(r'/[a-fA-F0-9]{32}', parsed.path):
        url = player_url(parsed.path[1:])
    seen = set() if seen is None else seen
    safe_url(url)
    if url in seen or len(seen) >= 3:
        raise SiteError('Zbyt wiele zagnieżdżonych odtwarzaczy. To źródło nie jest obsługiwane.')
    seen.add(url)
    text, kind, final_url = request(url, referer)
    if text.lstrip().startswith('#EXTM3U'):
        if re.search(r'KEYFORMAT\s*=\s*"(?!identity")', text, re.I):
            raise SiteError('Źródło używa DRM, którego ten dodatek nie obsługuje.')
        return final_url, referer
    if 'dash+xml' in kind or '<MPD' in text:
        raise SiteError('Źródło DASH nie jest obsługiwane w tej wersji.')
    # The new echo player receives HLS text over WSS and exposes a virtual
    # /bloop/ manifest through a service worker. Kodi uses our local adapter.
    ws = re.search(r'''\bvar\s+WS_BASE\s*=\s*["'](wss://[^"']+)["']''', text)
    token = re.search(r'''\bvar\s+TOKEN\s*=\s*["']([a-fA-F0-9]{32})["']''', text)
    if ws and token and '/bloop/' in text:
        return ws[1] + '#' + token[1], final_url
    parser = PlayerHTML()
    parser.feed(text)
    # Read literal media URLs only; never execute scripts from external hosts.
    literals = re.findall(r'''["']([^"'<>\s]+\.m3u8(?:\?[^"'<>\s]*)?)["']''', text.replace('\\/', '/'))
    candidates = parser.media + literals + parser.frames
    for candidate in candidates:
        candidate = urllib.parse.urljoin(final_url, html.unescape(candidate))
        if candidate.startswith(('https://', 'http://')) and candidate not in seen:
            return resolve(candidate, final_url, seen)
    raise SiteError('Brak bezpośredniego HLS. Odtwarzacz może wymagać JavaScript, weryfikacji lub używać nieobsługiwanego formatu. Nie da się odtworzyć samej strony HTML w Kodi.')
