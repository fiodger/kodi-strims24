# Strims24 dla Kodi

Nieoficjalny, eksperymentalny dodatek do Kodi 19+ (Python 3), przeznaczony
również na Android TV. Wersja **0.1.3**.

Od wersji 0.1.3 dodatek obsługuje **https://capitanstrims.st/** (dawniej Strims24)
oraz odtwarzacze **https://iplayer24.me/**. Identyfikator dodatku pozostał ten sam.

## Instalacja

Dodaj w menedżerze plików Kodi źródło **https://fiodger.github.io/kodi-strims24/**. Następnie wybierz **Dodatki → Zainstaluj z pliku ZIP**, otwórz źródło i zainstaluj `repository.fiodger.strims24-1.0.0.zip`. Dalej: **Zainstaluj z repozytorium → Fiodger - Strims24 → Dodatki wideo → Strims24 — transmisje**. Repozytorium umożliwia pobieranie przyszłych opublikowanych aktualizacji.

Możesz też pobrać `dist/plugin.video.strims24-0.1.3.zip`, a w Kodi wybrać
**Dodatki → Zainstaluj z pliku ZIP**. Ten sam ZIP służy do aktualizacji.

## Obsługa

- **Obecnie live** zbiera trwające wydarzenia ze wszystkich obsługiwanych dyscyplin.
- Pozostałe kategorie: dyscyplina → dzisiaj/jutro → wydarzenie → źródło.
- Godzina startu po lewej jest zielona dla live i niebieska dla nadchodzących wydarzeń.
- Godziny są wyświetlane w strefie czasowej urządzenia z Kodi.

Dodatek działa na urządzeniu z Kodi bez pomocnika na komputerze. Wbudowany
adapter HLS usuwa rozpoznane nagłówki PNG poprzedzające pakiety MPEG-TS.
Adapter działa w pamięci, wyłącznie na lokalnym interfejsie, i kończy pracę
po zakończeniu odtwarzania.

## Ograniczenia

Obsługiwane są bezpośrednie HLS oraz jawne adresy HLS w HTML/iframe.
Wbudowany klient WSS odbiera playlisty nowego odtwarzacza echo, a lokalny adapter
podaje je do Kodi. Nie wykonuje zewnętrznych skryptów. Brak obsługi DRM, CAPTCHA
i innych odtwarzaczy wymagających wykonywania JavaScript.
Zewnętrzne źródła mogą być niedostępne lub zmieniać format. Status live pochodzi
z terminarza i nie stanowi potwierdzenia dostępności transmisji.

Nowa strona wyłączyła globalny katalog kanałów. Dodatek korzysta ze źródeł
przypisanych do poszczególnych wydarzeń, bez wywołań nieistniejącego `/channels`.
Błędy są wyświetlane w Kodi, a ostatni komunikat można odczytać w **Diagnostyce**.

## Testy

```sh
python -m unittest discover -s tests -v
```

21 testów obejmuje terminarz, nowe domeny i format odtwarzacza, składanie ramek
WebSocket, ping/pong, limit rozmiaru i ważności playlisty, wirtualny manifest
przez lokalny HTTP oraz wcześniejszy adapter HLS.

18.10.2026 sprawdzono działającą listę live (31 wydarzeń, bez ostrzeżeń),
subskrypcję WSS, zmieniającą się playlistę HLS i pobranie fragmentu z poprawnymi
pakietami MPEG-TS. To test sieci i adaptera; odtwarzanie wersji 0.1.3 na Android TV
wymaga potwierdzenia na urządzeniu. Wersja 0.1.1 była wcześniej sprawdzona w Kodi
na Windows. Wersja 0.1.2 dodała kategorię live i kolorowe godziny.

Repozytorium zawiera kod, ZIP dodatku i publiczne źródło aktualizacji Kodi. Projekt nie jest powiązany z administracją Strims24.

## Publikowanie aktualizacji
Po zmianie wersji w addon.xml uruchom `python build_repository.py` i opublikuj zaktualizowane katalogi docs oraz dist. GitHub Pages serwuje katalog docs z gałęzi main. Format repozytorium: https://kodi.wiki/view/Add-on_repositories
