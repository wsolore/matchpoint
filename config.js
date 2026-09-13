/* ============================================================
   MATCH POINT — jedyny plik do edycji
   ------------------------------------------------------------
   PO KAZDYM ZAPISIE zmien takenWomen / takenMen w "next".
   Liczniki i paski postepu przelicza sie same na obu stronach.
   ============================================================ */

const MATCHPOINT = {

  /* --- najblizsze wydarzenie, w sprzedazy --- */
  next: {
    name:    'Tennis Speed Dating',
    date:    '20.09.2026',
    weekday: 'Niedziela',
    time:    '17:00–19:00',
    venue:   'Korty Wolica SGGW',
    address: 'Nowoursynowska 92, Warszawa',
    age:     '25–40',
    priceW:  90,
    priceM:  100,
    page:    'tennis-speed-dating-20-09.html',
    formUrl: 'https://docs.google.com/forms/d/e/1FAIpQLSfqkm4kn6giUD2qxViy0b4kboN1vJ-utRemI2BE3KOZ9FuCQA/viewform',
    blik:    '731 210 703',

    limitWomen: 6,
    limitMen:   6,

    /* ↓↓↓ TYLKO TE DWIE LICZBY ZMIENIASZ NA BIEZACO ↓↓↓ */
    takenWomen: 0,
    takenMen:   0
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
