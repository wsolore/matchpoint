# MatchPoint Wydarzenia — instrukcja

Aplikacja dodaje nowe wydarzenia na stronę **matchpointdate.pl**, zmienia
istniejące (ceny, liczbę miejsc, zamknięcie zapisów) i przenosi zakończone
do archiwum. Nie trzeba niczego programować ani instalować — to jeden plik
`MatchPointWydarzenia.exe`.

Każda publikacja od razu trafia na prawdziwą stronę (po około minucie).
Dlatego przed opublikowaniem zawsze obejrzyj **Podgląd**.

---

## 1. Pierwsze uruchomienie (raz)

### Token — robi go osoba, która prowadzi stronę

Token to „klucz”, który pozwala aplikacji zapisywać zmiany na stronie.

1. Zaloguj się na GitHub na konto właściciela repozytorium (`wsolore`).
2. Wejdź na https://github.com/settings/personal-access-tokens/new
3. Wypełnij:
   - **Token name:** `MatchPoint Wydarzenia — <imię osoby>`
   - **Expiration:** 1 rok (w kalendarzu zapisz datę odnowienia)
   - **Repository access:** *Only select repositories* → `wsolore/matchpoint`
   - **Permissions → Repository permissions → Contents:** *Read and write*
     (reszty nie ruszaj)
4. **Generate token**, skopiuj go (zaczyna się od `github_pat_`) i przekaż
   osobie bezpiecznie, np. osobno od tej instrukcji. Token daje prawo do
   zmiany strony, więc nie wklejaj go w publiczne miejsca.

Gdy ktoś przestaje dodawać wydarzenia, usuń jego token na tej samej stronie
GitHuba — aplikacja przestanie działać tylko u niego.

### Uruchomienie aplikacji

1. Kliknij dwa razy `MatchPointWydarzenia.exe`.
2. Windows może pokazać niebieskie okno „System Windows ochronił ten
   komputer”. Kliknij **Więcej informacji → Uruchom mimo to**. To normalne
   dla programów spoza sklepu.
3. Otworzy się okno **Ustawienia**. Wklej token w pole *Token GitHub*,
   repozytorium zostaw `wsolore/matchpoint`, kliknij **Zapisz**.
4. Po chwili na liście „W sprzedaży” pojawią się wydarzenia ze strony.

Token zapisuje się na tym komputerze i przy następnych uruchomieniach nie
trzeba go wpisywać.

---

## 2. Najpierw zakładka w arkuszu

Każde wydarzenie ma **własną zakładkę** w arkuszu zapisów. Bez niej
formularz na stronie nie przyjmie zapisu.

1. Otwórz arkusz zapisów w Google Sheets.
2. **Plik → Importuj → Prześlij** i wybierz `szablon-zakladki.csv`
   (leży obok aplikacji).
3. Przy „Miejsce importu” wybierz **Wstaw nowe arkusze** → **Importuj dane**.
4. Kliknij prawym przyciskiem nową zakładkę → **Zmień nazwę** i nadaj jej
   nazwę wydarzenia, najprościej datę: `25.10`. Gdy tego dnia są dwa
   terminy, dopisz godzinę: `25.10 15:00`.

Nazwa zakładki musi być **dokładnie** taka, jaką wpiszesz w aplikacji
w polu *Zakładka w arkuszu*.

Nie zmieniaj nagłówków tabelek (Kobiety, Mężczyźni, Lista rezerwowa,
Zgłoszone wpłaty) ani nazw kolumn — po nich skrypt znajduje ludzi.

---

## 3. Nowe wydarzenie

1. Kliknij **+ Nowe wydarzenie**.
2. W polu **Dyscyplina** wybierz *Tenis* albo *Padel*. Aplikacja wpisze
   gotowe teksty dla tej dyscypliny — potem poprawisz je pod konkretne
   wydarzenie.
3. Zakładka **1. Termin, miejsce, ceny**:
   - **Data**: `25.10.2026` (kropki, pełny rok). Dzień tygodnia dopisze
     się sam.
   - **Godziny**: `17:00-19:30`.
   - **Miejsce**: nazwa obiektu, np. `WTS Orzeł`.
   - **Adres**: `ulica numer, miasto`, np. `Podskarbińska 14, Warszawa`.
   - **Wiek od / do**: formularz nie przyjmie nikogo spoza tych granic.
   - **Ceny**: gdy obie są równe, na stronie pokaże się jedna pozycja „Cena”.
   - **Miejsca**: ile osób każdej płci. Liczą się **opłacone** — ktoś, kto
     się zapisał, ale nie zapłacił, nie zajmuje miejsca.
   - **Zakładka w arkuszu**: nazwa zakładki z rozdziału 2. Puste pole =
     sama data, np. `25.10`.
4. Zakładka **2. Mail do uczestnika**: teksty z maila, który uczestnik
   dostaje po Twoim `TAK` w arkuszu (nawierzchnia, co zabrać, co jest
   w cenie). **Puste pole usuwa linię z maila**, więc jeśli nie ma nic do
   napisania o dojeździe, zostaw je puste.
5. Zakładka **3. Teksty na stronie**: to, co widać na stronie wydarzenia.
   - W polach z listą każda pozycja to osobna linia.
   - W polach „Tytuł | tekst” części oddziela pionowa kreska `|`
     (na klawiaturze: Shift + klawisz nad Enterem).
   - `**słowa w gwiazdkach**` będą pogrubione.
   - Adres e-mail sam zamieni się w link.
   - Pytania o płatność, rezygnację, kontakt i dane osobowe są na każdej
     stronie zawsze — nie dopisuj ich.
6. Kliknij **Podgląd w przeglądarce** i przejrzyj całą stronę. Na podglądzie
   działa też licznik miejsc, jeśli zakładka w arkuszu już jest.
7. Kliknij **Opublikuj**. Aplikacja:
   - sprawdzi, czy arkusz widzi zakładkę (jeśli nie — ostrzeże),
   - pokaże podsumowanie do potwierdzenia,
   - wyśle zmiany. Po około minucie wydarzenie jest na stronie głównej
     i pod własnym adresem, który aplikacja poda na koniec.

Po publikacji zrób próbny zapis na stronie (np. z własnym mailem) i sprawdź,
czy trafił do zakładki na listę rezerwową. Potem usuń ten wiersz.

---

## 4. Zmiana wydarzenia

Zaznacz wydarzenie na liście i kliknij **Zmień zaznaczone** (albo kliknij
je dwa razy). Popraw, co trzeba, i **Opublikuj**.

Najczęstsze zmiany:

| Chcę… | Pole |
|---|---|
| zamknąć zapisy kobiet/mężczyzn, choć arkusz ich nie zamknął (np. komplet zebrał się poza stroną) | **Zamknij pulę kobiet / mężczyzn** |
| otworzyć je z powrotem, bo ktoś zrezygnował | odznacz to samo pole |
| dodać miejsca | **Miejsca — kobiety / mężczyźni** |
| zmienić cenę | **Cena** |

Dyscypliny i adresu strony nie da się zmienić — link do strony mógł już pójść
do ludzi. Jeśli pomyliła się dyscyplina, przenieś wydarzenie do archiwum
i dodaj nowe.

**Strony zrobione przed aplikacją** (padel 3.10) mają teksty wpisane ręcznie.
Przy nich zakładka 3 jest nieaktywna. Ceny, liczby miejsc i zamknięcie puli
działają normalnie, ale w tabelce „Szczegóły” na tej stronie zostanie stara
cena — przy zmianie ceny daj znać osobie, która prowadzi stronę.

---

## 5. Po wydarzeniu: archiwum

Po wydarzeniu zaznacz je i kliknij **Przenieś do archiwum**. Karta zniknie
z „Najbliższych terminów” i pojawi się w „Za nami”, a strona wydarzenia
dostanie baner „To wydarzenie już się odbyło” i straci formularz.

Nie rób tego przed wydarzeniem — tego nie da się cofnąć z poziomu aplikacji.
Zakładki w arkuszu nie usuwaj: to lista uczestników.

---

## 6. Czego aplikacja nie robi

- **nie zakłada zakładki w arkuszu** — rozdział 2;
- **nie wpisuje `TAK` przy wpłatach** — to nadal robisz w arkuszu, jak dotąd;
- **nie zmienia treści maili** (poza danymi wydarzenia). Szablon maili siedzi
  w skrypcie arkusza;
- **nie usuwa wydarzeń** — tylko przenosi do archiwum;
- nie zmienia strony głównej poza kartami wydarzeń i archiwum.

---

## 7. Gdy coś nie działa

| Komunikat | Co zrobić |
|---|---|
| „GitHub nie przyjął tokenu” | token wygasł albo został usunięty. Poproś o nowy (rozdział 1) i wklej w **Ustawienia**. |
| „Token nie ma uprawnień do zapisu” | przy tworzeniu tokenu zabrakło *Contents: Read and write* albo wybrano inne repozytorium. |
| „Brak połączenia z GitHubem” | sprawdź internet. |
| „Ktoś w tym samym czasie zmieniał stronę” | kliknij **Odśwież** i powtórz. Nic się nie zepsuło. |
| „Arkusz nie widzi zakładki” | nazwa zakładki w arkuszu różni się od tej w aplikacji albo zakładki jeszcze nie ma. Przycisk **Sprawdź zakładkę w arkuszu** pokaże, co widzi arkusz. |
| „W pliku … nie ma znaczników” | ktoś zmienił stronę ręcznie w nieoczekiwany sposób. Nic nie zapisuj i daj znać osobie, która prowadzi stronę. |
| „Popraw, proszę: …” | lista pól do poprawy — nic nie zostało wysłane. |

Każda zmiana z aplikacji zostaje zapisana w historii strony na GitHubie
(z dopiskiem „(aplikacja)”), więc każdą da się cofnąć — ale robi to już
osoba, która prowadzi stronę.
