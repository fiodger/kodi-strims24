STRIMS24 0.1.2 — WERSJA TESTOWA

NOWOŚCI 0.1.2:
Pierwsza kategoria „Obecnie live” zbiera trwające wydarzenia ze wszystkich
obsługiwanych dyscyplin. Obok nazwy widać również dyscyplinę.
Godzina startu znajduje się po lewej stronie każdej nazwy: zielona dla live,
niebieska dla nadchodzących wydarzeń. Czas odpowiada strefie urządzenia Kodi.
Status live pochodzi z terminarza; nie jest testem dostępności każdego źródła.

POPRAWKI 0.1.1:
Identyfikatory źródeł są kierowane do /echo/, zgodnie z odtwarzaczem strony.
Naprawiono też adresy pozostawione w historii Kodi przez wersję 0.1.0.
Wbudowany adapter HLS usuwa nagłówek PNG wyłącznie po potwierdzeniu pakietów
MPEG-TS. Działa w pamięci na urządzeniu z Kodi, na lokalnym porcie losowym;
nie wymaga żadnego programu na komputerze i kończy pracę po odtwarzaniu.

Kodi 19 lub nowsze, także na Android TV. Instalacja z ZIP-a dodatku,
bez komputera, rozszerzenia Chrome, hasła i programu pomocniczego.

Menu: dyscyplina → dzisiaj/jutro → wydarzenie → źródło.
Lista łączy dane serwisu i jego zewnętrzny terminarz. Nie otwiera reklam ani czatu.
Odtwarzanie: bezpośredni HLS oraz odtwarzacze udostępniające dosłowny adres HLS
w HTML lub zagnieżdżonym iframe (maksymalnie trzy strony). Nie wykonuje skryptów.
Brak obsługi odtwarzaczy wymagających JavaScript, CAPTCHA, logowania i DRM.

STAN TESTU 23.09.2026:
Lista wydarzeń działa. Katalog /channels zwracał 404, dlatego część wydarzeń
może być pominięta. Dla CRO Race — Stage 2 potwierdzono poprawny adres odtwarzacza,
pobranie HLS oraz odczyt pakietów MPEG-TS z fragmentu dostawcy. Testy kodu: 11.
Krótki test adaptera w Kodi na Windows potwierdził dekodowanie obrazu i dźwięku
oraz postęp odtwarzania. Nie przeprowadzono jeszcze testu na Android TV.
Serwer źródłowy okresowo zwracał 504; dodatek nie naprawia awarii dostawcy.
Błąd pojawia się bezpośrednio na ekranie; ostatni komunikat jest w Diagnostyce.

Wykonano testy parsera rzeczywistego terminarza, odczytu HLS z iframe,
odrzucania DRM i odtwarzaczy wymagających JavaScript oraz filtrowania źródeł.
Godziny są pokazywane w strefie czasowej urządzenia z Kodi.
Nie publikuj całego logu Kodi: sam odtwarzacz może zapisać adresy transmisji.
