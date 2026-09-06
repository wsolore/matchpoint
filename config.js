/* ============================================================
   MATCH POINT — jedyny plik do edycji przy aktualizacji miejsc
   ------------------------------------------------------------
   Po każdej zaksięgowanej płatności zmień takenWomen / takenMen.
   Liczniki, statusy i podsumowania na obu stronach przeliczą się same.
   ============================================================ */

const MATCHPOINT = {

  nextEvent: {
    name:    'Tennis Speed Dating',
    date:    '12.09.2026',
    time:    '17:00–18:00',
    venue:   'WTS Orzeł, Warszawa',
    page:    'tennis-speed-dating-12-09.html',

    formUrl: 'https://docs.google.com/forms/d/e/1FAIpQLSeC0FvaZTJQAU0aM4oVA3MpNW3gUBf-sFr1DIvdtv1CYtpSBg/viewform',

    limitWomen: 6,
    limitMen:   6,

    /* ↓↓↓ TYLKO TE DWIE LICZBY ZMIENIASZ NA BIEŻĄCO ↓↓↓ */
    takenWomen: 0,
    takenMen:   0
  }

};
