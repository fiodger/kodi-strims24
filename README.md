# Strims24 dla Kodi

Nieoficjalny, eksperymentalny dodatek do Kodi 19+ (Python 3), przeznaczony
również na Android TV. Wersja **0.1.2**.

## Instalacja

Dodaj w menedżerze plików Kodi źródło **https://fiodger.github.io/kodi-strims24/**. Następnie wybierz **Dodatki → Zainstaluj z pliku ZIP**, otwórz źródło i zainstaluj `repository.fiodger.strims24-1.0.0.zip`. Dalej: **Zainstaluj z repozytorium → Fiodger - Strims24 → Dodatki wideo → Strims24 — transmisje**. Repozytorium umożliwia pobieranie przyszłych opublikowanych aktualizacji.

Możesz też pobrać `dist/plugin.video.strims24-0.1.2.zip`, a w Kodi wybrać
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
Brak obsługi DRM, CAPTCHA i odtwarzaczy wymagających wykonywania JavaScript.
Zewnętrzne źródła mogą być niedostępne lub zmieniać format. Status live pochodzi
z terminarza i nie stanowi potwierdzenia dostępności transmisji.

Na dzień 23.09.2026 katalog kanałów serwisu zwracał 404; dodatek korzysta wtedy
z wydarzeń dodanych bezpośrednio przez serwis. Błędy są wyświetlane w Kodi,
a ostatni komunikat można odczytać w **Diagnostyce**.

## Testy

```sh
python -m unittest discover -s tests -v
```

13 testów obejmuje parsowanie terminarza, rozwiązywanie adresów HLS,
adapter fragmentów oraz zbiorczą kategorię live. Krótki test rzeczywistej
transmisji kolarskiej wykonano w Kodi na Windows; użytkownik potwierdził
działanie wersji 0.1.1. Wersja 0.1.2 dodaje listę live i kolorowe godziny.

Repozytorium zawiera kod, ZIP dodatku i publiczne źródło aktualizacji Kodi. Projekt nie jest powiązany z administracją Strims24.

## Publikowanie aktualizacji
Po zmianie wersji w addon.xml uruchom `python build_repository.py` i opublikuj zaktualizowane katalogi docs oraz dist. GitHub Pages serwuje katalog docs z gałęzi main. Format repozytorium: https://kodi.wiki/view/Add-on_repositories
