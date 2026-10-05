/* ============================================================
   MATCH POINT — jedyny plik do edycji
   ------------------------------------------------------------
   1) Licznik oplaconych miejsc czyta arkusz sam, wiec nie ma tu
      zadnych liczb do utrzymywania. Gdy arkusz nie odpowie, strona
      nie pokazuje zadnej liczby zamiast pokazywac nieaktualna.
   2) sheetEndpoint wklejasz raz, po wdrozeniu skryptu Google
      (instrukcja: docs/apps-script.md). Dopoki jest puste,
      formularz na stronie pokazuje przycisk do Google Forms.
   3) Wydarzenia w sprzedazy siedza w upcoming[], od najblizszego.
      Kazda strona wydarzenia siega po swoje przez MATCHPOINT.byId(),
      a strona glowna po cala liste.
   4) Od 29.09 listy wydarzen pisze aplikacja "MatchPoint Wydarzenia"
      (katalog aplikacja/). Blok ponizej to czysty JSON, bo aplikacja
      go czyta i przepisuje w calosci — komentarze w nim by przepadly.
      Recznie tez mozna go edytowac, byle zostal poprawnym JSON-em
      (cudzyslowy, bez przecinka po ostatnim elemencie).
   ============================================================ */

/* >>> WYDARZENIA — blok pisany przez aplikacje, czysty JSON.
   Pola, o ktorych trzeba pamietac:
   - sheetTab: nazwa zakladki w arkuszu. Skrypt od 2026-09-22.a
     dopasowuje ja mimo zer wiodacych ("3.10" = "03.10"), ale reszta
     nazwy musi sie zgadzac, inaczej licznik milknie i zapisy padaja.
   - limitWomen / limitMen: ile miejsc na sprzedaz, liczone po OPLACONYCH.
   - soldOutWomen / soldOutMen: reczne zamkniecie puli, wygrywa z arkuszem.
     Flaga nie otwiera sie sama: gdy ktos zrezygnuje, trzeba ja zdjac
     recznie (tak bylo z pula kobiet na 3.10 17:00 — 30.09 dwie osoby
     sie wypisaly, a zapisy staly zamkniete, bo flaga wygrywala).
   - transport, bringExtra: puste pole KASUJE linie w mailu, a nie
     wraca do domyslnej tresci.
   - cardNote: dopisek na karcie na stronie glownej (wiek dochodzi sam).
   - past[].note: dopisek w sekcji "Za nami".                        */
const MATCHPOINT_WYDARZENIA = {
  "upcoming": [
    {
      "id": "TSD-1810",
      "name": "Tennis Speed Dating",
      "sport": "Tenis",
      "city": "Warszawa",
      "date": "18.10.2026",
      "weekday": "Niedziela",
      "time": "17:00–19:30",
      "venue": "WTS Orzeł",
      "address": "Podskarbińska 14, Warszawa",
      "age": "30–45",
      "ageMin": 30,
      "ageMax": 45,
      "level": "Początkujący+",
      "surface": "mączka",
      "shoes": "obuwie na mączkę",
      "transport": "",
      "bring": "Rakietę, obuwie na mączkę i strój sportowy.",
      "bringExtra": "Nie masz rakiety? Daj nam znać - można ją wypożyczyć za dodatkową opłatą.",
      "included": "Kort i piłki.",
      "cardNote": "Kort ziemny, poziom początkujący+.",
      "priceW": 130,
      "priceM": 130,
      "page": "tennis-speed-dating-18-10.html",
      "sheetTab": "18.10",
      "formUrl": "",
      "blik": "731 210 703",
      "limitWomen": 6,
      "limitMen": 6,
      "soldOutWomen": false,
      "soldOutMen": false
    }
  ],
  "past": [
    {
      "name": "Padel Speed Dating",
      "sport": "Padel",
      "date": "03.10.2026",
      "weekday": "Sobota",
      "venue": "Warsaw Padel Club, Warszawa",
      "note": "",
      "page": "padel-speed-dating-03-10-1500.html"
    },
    {
      "name": "Padel Speed Dating",
      "sport": "Padel",
      "date": "03.10.2026",
      "weekday": "Sobota",
      "venue": "Warsaw Padel Club, Warszawa",
      "note": "",
      "page": "padel-speed-dating-03-10.html"
    },
    {
      "name": "Tennis Speed Dating",
      "sport": "Tenis",
      "date": "20.09.2026",
      "weekday": "Niedziela",
      "venue": "Korty Wolica SGGW, Warszawa",
      "note": "Komplet: 6 par.",
      "page": "tennis-speed-dating-20-09.html"
    },
    {
      "name": "Tennis Speed Dating",
      "sport": "Tenis",
      "date": "12.09.2026",
      "weekday": "Sobota",
      "venue": "WTS Orzeł, Warszawa",
      "note": "Pierwsza edycja.",
      "page": "tennis-speed-dating-12-09.html"
    }
  ]
};
/* <<< WYDARZENIA */

const MATCHPOINT = {

  /* adres skryptu Google Apps Script, ktory dopisuje zgloszenia
     do arkusza. Wyglada tak:
     https://script.google.com/macros/s/AKfy.../exec            */
  sheetEndpoint: 'https://script.google.com/macros/s/AKfycbxHiSMEiB8geAq8-VjcQl7IBm7bf51cIs0aPKPMzSSBKMot_BZZ7wFtDK5AXcAxIul4UQ/exec',

  /* Token Cloudflare Web Analytics. Wklejasz raz, instrukcja
     w docs/analytics.md. Puste = licznik odwiedzin wylaczony.     */
  cfBeaconToken: '',

  /* Czy licznik ma czytac liczbe oplaconych z arkusza.
     Przy false liczniki zostaja puste, bo nie ma zapasowego zrodla.
     Blokada zapisow NIE zalezy od tej flagi: przy false strona nadal
     pyta arkusz o miejsca i nie wpuszcza nikogo do pelnej puli,
     tylko nie pokazuje liczb.                                      */
  useSheetCounter: true,

  /* wydarzenia w sprzedazy (od najblizszego) i archiwum — z bloku wyzej */
  upcoming: MATCHPOINT_WYDARZENIA.upcoming,
  past:     MATCHPOINT_WYDARZENIA.past

};

/* Najblizsze wydarzenie to pierwsze z listy. Zostaje pod nazwa
   MATCHPOINT.next, bo tak siega po nie strona glowna i tak nazywa
   je skrypt maila — zmiana nazwy zerwalaby oba miejsca naraz.   */
MATCHPOINT.next = MATCHPOINT.upcoming[0];

/* Strona wydarzenia podaje swoje id i dostaje swoj wpis. Gdy id
   nie pasuje do niczego, wraca najblizsze wydarzenie — strona
   pokaze wtedy zle dane, ale sie nie wysypie.                   */
MATCHPOINT.byId = function (id) {
  return MATCHPOINT.upcoming.filter(function (e) { return e.id === id; })[0]
      || MATCHPOINT.next;
};
