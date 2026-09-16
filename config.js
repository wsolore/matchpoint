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
      a strona glowna po cala liste. Dodanie kolejnej dyscypliny to
      nowy wpis tutaj plus nowa zakladka w arkuszu.
   ============================================================ */

const MATCHPOINT = {

  /* adres skryptu Google Apps Script, ktory dopisuje zgloszenia
     do arkusza. Wyglada tak:
     https://script.google.com/macros/s/AKfy.../exec            */
  sheetEndpoint: 'https://script.google.com/macros/s/AKfycbxHiSMEiB8geAq8-VjcQl7IBm7bf51cIs0aPKPMzSSBKMot_BZZ7wFtDK5AXcAxIul4UQ/exec',

  /* Token Cloudflare Web Analytics. Wklejasz raz, instrukcja
     w docs/analytics.md. Puste = licznik odwiedzin wylaczony.     */
  cfBeaconToken: '',

  /* Czy licznik ma czytac liczbe oplaconych z arkusza.
     Przy false liczniki zostaja puste, bo nie ma zapasowego zrodla. */
  useSheetCounter: true,

  /* --- wydarzenia w sprzedazy, od najblizszego --- */
  upcoming: [

    {
      id:      'TSD-2009',
      name:    'Tennis Speed Dating',
      sport:   'Tenis',
      date:    '20.09.2026',
      weekday: 'Niedziela',
      time:    '17:00–19:00',
      venue:   'Korty Wolica SGGW',
      address: 'Nowoursynowska 92, Warszawa',
      age:     '25–40',
      level:   'Każdy poziom',
      /* dane wykorzystywane w mailu z potwierdzeniem */
      surface:   'ziemny (mączka)',
      shoes:     'obuwie na mączkę',
      transport: 'Metro Ursynów → Nowoursynowska 92 → kampus SGGW',
      priceW:  90,
      priceM:  100,
      page:    'tennis-speed-dating-20-09.html',
      /* nazwa ZAKLADKI w arkuszu. Kazde wydarzenie ma swoja.   */
      sheetTab: '20.09',
      formUrl: 'https://docs.google.com/forms/d/e/1FAIpQLSfqkm4kn6giUD2qxViy0b4kboN1vJ-utRemI2BE3KOZ9FuCQA/viewform',
      blik:    '731 210 703',

      limitWomen: 6,
      limitMen:   6
    },

    {
      id:      'PSD-0310',
      name:    'Padel Speed Dating',
      sport:   'Padel',
      date:    '03.10.2026',
      weekday: 'Sobota',
      time:    '17:00–18:30',
      venue:   'Warsaw Padel Club',
      address: 'Annopol 3, Warszawa',
      age:     '25–35',
      level:   'Początkujący+',
      surface:   'sztuczna trawa',
      shoes:     'obuwie sportowe na płaskiej podeszwie',
      transport: 'Annopol 3, Warszawa — szczegóły dojazdu wysyłamy w mailu z potwierdzeniem',
      priceW:  140,
      priceM:  150,
      page:    'padel-speed-dating-03-10.html',
      sheetTab: '03.10',
      formUrl: '',
      blik:    '731 210 703',

      limitWomen: 6,
      limitMen:   6
    }

  ],

  /* --- archiwum --- */
  past: [
    {
      name:  'Tennis Speed Dating',
      sport: 'Tenis',
      date:  '12.09.2026',
      venue: 'WTS Orzeł, Warszawa',
      page:  'tennis-speed-dating-12-09.html'
    }
  ]

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
