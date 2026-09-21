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
     Przy false liczniki zostaja puste, bo nie ma zapasowego zrodla.
     Blokada zapisow NIE zalezy od tej flagi: przy false strona nadal
     pyta arkusz o miejsca i nie wpuszcza nikogo do pelnej puli,
     tylko nie pokazuje liczb.                                      */
  useSheetCounter: true,

  /* --- wydarzenia w sprzedazy, od najblizszego --- */
  upcoming: [

    {
      id:      'PSD-0310-15',
      name:    'Padel Speed Dating',
      sport:   'Padel',
      date:    '03.10.2026',
      weekday: 'Sobota',
      time:    '15:00–16:30',
      venue:   'Warsaw Padel Club',
      address: 'Annopol 3, Warszawa',
      age:     '25–35',
      ageMin:  25,
      ageMax:  35,
      level:   'Początkujący+',
      surface:   'sztuczna trawa',
      shoes:     'obuwie sportowe na płaskiej podeszwie',
      transport: '',
      bring:      'Obuwie sportowe na płaskiej podeszwie i strój sportowy.',
      bringExtra: 'Rakiety nie potrzebujesz — jest w pakiecie i czeka na miejscu.',
      included:   'Kort, rakiety i piłki, voucher na shake proteinowy.',
      priceW:  140,
      priceM:  150,
      page:    'padel-speed-dating-03-10-1500.html',
      /* Dwa sloty tego samego dnia, wiec i dwie zakladki w arkuszu.
         Nazwa musi zgadzac sie z ta w arkuszu. Skrypt od wersji
         2026-09-21.f dopasowuje ja tez mimo zer wiodacych i spacji
         ("3.10 15:00" = "03.10 15:00"), ale trzymajmy tu dokladnie
         to, co widac na zakladce.                                 */
      sheetTab: '03.10 15:00',
      formUrl: '',
      blik:    '731 210 703',

      limitWomen: 6,
      limitMen:   6,
      soldOutWomen: false,
      soldOutMen:   false
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
      ageMin:  25,
      ageMax:  35,
      level:   'Początkujący+',
      surface:   'sztuczna trawa',
      shoes:     'obuwie sportowe na płaskiej podeszwie',
      /* Puste — w mailu z potwierdzeniem linia "Dojazd" wtedy nie
         wychodzi. Wczesniej bylo tu "szczegoly wysylamy w mailu",
         co w tym wlasnie mailu brzmialo absurdalnie. Adres i tak
         jest wyzej. Wypelnij, gdy bedzie co napisac o dojezdzie. */
      transport: '',
      bring:      'Obuwie sportowe na płaskiej podeszwie i strój sportowy.',
      bringExtra: 'Rakiety nie potrzebujesz — jest w pakiecie i czeka na miejscu.',
      included:   'Kort, rakiety i piłki, voucher na shake proteinowy.',
      priceW:  140,
      priceM:  150,
      page:    'padel-speed-dating-03-10.html',
      /* Od 21.09 zakladka ma w nazwie godzine, bo tego dnia sa dwa
         sloty. Nazwa musi zgadzac sie CO DO ZNAKU z ta w arkuszu. */
      sheetTab: '03.10 17:00',
      formUrl: '',
      blik:    '731 210 703',

      limitWomen: 6,
      limitMen:   6,

      /* Pula kobiet zamknięta 20.09: komplet zebrał się poza arkuszem,
         więc same liczby z arkusza jeszcze o tym nie wiedzą.
         Wpisz false, gdy zwolni się miejsce.                      */
      soldOutWomen: true,
      soldOutMen:   false
    }

  ],

  /* --- archiwum --- */
  past: [
    {
      name:  'Tennis Speed Dating',
      sport: 'Tenis',
      date:  '20.09.2026',
      venue: 'Korty Wolica SGGW, Warszawa',
      page:  'tennis-speed-dating-20-09.html'
    },
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
