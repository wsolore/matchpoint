/* ============================================================
   Cloudflare Web Analytics
   ------------------------------------------------------------
   Licznik odwiedzin bez cookies, wiec nie wymaga bannera zgody.
   Token wklejasz RAZ w config.js, w pole cfBeaconToken.
   Dopoki jest puste, nic sie nie wczytuje i strona dziala bez zmian.
   Instrukcja: docs/analytics.md
   ============================================================ */

(function () {
  if (typeof MATCHPOINT === 'undefined') return;

  var token = (MATCHPOINT.cfBeaconToken || '').trim();
  if (!token) return;

  var s = document.createElement('script');
  s.defer = true;
  s.src = 'https://static.cloudflareinsights.com/beacon.min.js';
  s.setAttribute('data-cf-beacon', JSON.stringify({ token: token }));
  document.head.appendChild(s);
})();
