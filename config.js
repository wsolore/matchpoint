/* ============================================================
   MATCH POINT — jedyny plik do edycji
   ------------------------------------------------------------
   1) PO KAZDEJ ZAKSIEGOWANEJ WPLACIE zmien paidWomen / paidMen.
      Licznik na stronie pokazuje OPLACONE miejsca, nie zgloszenia.
   2) sheetEndpoint wklejasz raz, po wdrozeniu skryptu Google
      (instrukcja: docs/apps-script.md). Dopoki jest puste,
      formularz na stronie pokazuje przycisk do Google Forms.
   ============================================================ */

const MATCHPOINT = {

  /* adres skryptu Google Apps Script, ktory dopisuje zgloszenia
     do arkusza. Wyglada tak:
     https://script.google.com/macros/s/AKfy.../exec            */
  sheetEndpoint: 'https://script.google.com/macros/s/AKfycbxHiSMEiB8geAq8-VjcQl7IBm7bf51cIs0aPKPMzSSBKMot_BZZ7wFtDK5AXcAxIul4UQ/exec',

  /* Czy licznik ma czytac liczbe oplaconych z arkusza.
     false = liczby ponizej (paidWomen / paidMen) sa zrodlem prawdy.
     Wlaczyc dopiero, gdy uklad blokow w arkuszu jest potwierdzony.  */
  useSheetCounter: true,

  /* --- najblizsze wydarzenie, w sprzedazy --- */
  next: {
    id:      'TSD-2009',
    name:    'Tennis Speed Dating',
    date:    '20.09.2026',
    weekday: 'Niedziela',
    time:    '17:00–19:00',
    venue:   'Korty Wolica SGGW',
    address: 'Nowoursynowska 92, Warszawa',
    age:     '25–40',
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
    limitMen:   6,

    /* ↓↓↓ TYLKO TE DWIE LICZBY ZMIENIASZ NA BIEZACO ↓↓↓
       Liczba osob z "TAK" w kolumnie "Oplacone" w arkuszu.         */
    paidWomen: 3,
    paidMen:   0
  },

  /* --- archiwum --- */
  past: [
    {
      name:  'Tennis Speed Dating',
      date:  '12.09.2026',
      venue: 'WTS Orzeł, Warszawa',
      page:  'tennis-speed-dating-12-09.html'
    }
  ]

};
