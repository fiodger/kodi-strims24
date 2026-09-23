import datetime
import os
import sys
import time
import urllib.parse
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs
from client import Client, SPORTS, SiteError, UA, resolve

ADDON = xbmcaddon.Addon()
HANDLE = int(sys.argv[1])
LOG = os.path.join(xbmcvfs.translatePath(ADDON.getAddonInfo('profile')), 'diagnostyka.txt')

def log(text):
    xbmc.log('[Strims24] ' + text, xbmc.LOGINFO)
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, 'w', encoding='utf-8') as f: f.write(text)
    except OSError: pass

def item(label, action, folder=True, **params):
    params['action'] = action
    li = xbmcgui.ListItem(label=label)
    if action == 'play': li.setProperty('IsPlayable', 'true')
    xbmcplugin.addDirectoryItem(HANDLE, sys.argv[0] + '?' + urllib.parse.urlencode(params), li, isFolder=folder)


def event_label(event, show_sport=False):
    start = event.get('start_ts')
    clock = datetime.datetime.fromtimestamp(start).strftime('%H:%M') if start else '--:--'
    color = 'FF66DD99' if event['live'] else 'FF69BFFF'
    label = '[COLOR %s]%s[/COLOR]  %s' % (color, clock, event['name'])
    if show_sport:
        label += ' · ' + SPORTS[event['sport']][0]
    if event['live']:
        label += '  [COLOR FF66DD99]LIVE[/COLOR]'
    return label

def main():
    p = dict(urllib.parse.parse_qsl(sys.argv[2].lstrip('?') if len(sys.argv) > 2 else ''))
    action = p.get('action', '')
    try:
        if not action:
            item('[COLOR FF66DD99]Obecnie live[/COLOR]', 'live')
            for sport, (name, _) in SPORTS.items(): item(name, 'days', sport=sport)
            item('Diagnostyka / ograniczenia wersji', 'logs', folder=False)
        elif action == 'days':
            item('Na żywo i dzisiaj', 'events', sport=p['sport'], day='0')
            item('Jutro', 'events', sport=p['sport'], day='1')
        elif action in ('events', 'live'):
            client = Client()
            events = client.live_events() if action == 'live' else client.events(p['sport'], p.get('day') == '1')
            log('\n'.join(client.warnings) or 'Lista pobrana poprawnie: %s wydarzeń.' % len(events))
            if client.warnings:
                xbmcgui.Dialog().notification('Strims24', 'Część danych niedostępna — szczegóły w Diagnostyce.', time=5000)
            for e in events:
                item(event_label(e, show_sport=action == 'live'), 'sources', id=e['match_id'])
            if not events: item('Brak aktualnych wydarzeń — diagnostyka', 'logs', folder=False)
        elif action == 'sources':
            sources = Client().sources(p['id'])
            for source in sources: item(source['name'], 'play', folder=False, url=source['url'])
            if not sources: item('Serwis nie udostępnił źródeł — diagnostyka', 'logs', folder=False)
        elif action == 'play':
            url, referer = resolve(p['url'])
            from hls_proxy import Proxy
            proxy = Proxy(url, referer)
            try:
                li = xbmcgui.ListItem(path=proxy.start())
                li.setMimeType('application/vnd.apple.mpegurl')
                li.setContentLookup(False)
                xbmcplugin.setResolvedUrl(HANDLE, True, li)
                monitor, player = xbmc.Monitor(), xbmc.Player()
                deadline = time.monotonic() + 40
                started = False
                while not monitor.waitForAbort(1):
                    try:
                        playing = player.isPlaying() and player.getPlayingFile().startswith(proxy.base)
                    except RuntimeError:
                        playing = False
                    if playing:
                        started = True
                        deadline = time.monotonic() + 5
                    elif started or time.monotonic() > deadline:
                        break
            finally:
                proxy.close()
            return
        elif action == 'logs':
            text = 'Wersja testowa: odtwarza bezpośredni HLS. Brak obsługi JavaScript, CAPTCHA i DRM.\n\n'
            if os.path.exists(LOG):
                with open(LOG, encoding='utf-8') as f: text += f.read()[-8000:]
            xbmcgui.Dialog().textviewer('Strims24 — diagnostyka', text)
            return
        xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)
    except Exception as exc:
        message = str(exc) if isinstance(exc, SiteError) else 'Błąd dodatku: ' + type(exc).__name__
        log(message)
        xbmcgui.Dialog().ok('Strims24', message)
        if action == 'play': xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        else: xbmcplugin.endOfDirectory(HANDLE, succeeded=False)

if __name__ == '__main__': main()
