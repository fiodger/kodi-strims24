# Strims24 dla Kodi

Nieoficjalny, eksperymentalny dodatek do Kodi 19+ (Python 3), przeznaczony
również na Android TV. Wersja **0.1.2**.

## Instalacja

Pobierz `dist/plugin.video.strims24-0.1.2.zip`, a w Kodi wybierz
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

Repozytorium zawiera kod i ZIP dodatku. Nie jest automatycznym repozytorium
aktualizacji Kodi. Projekt nie jest powiązany z administracją Strims24.
