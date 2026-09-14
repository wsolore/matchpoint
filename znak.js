/* Start animacji znaku marki (strzaly w hero).
 *
 * Animacja nie jest przypisana do wczytania strony. Klase `mp-lot`
 * dodajemy na <html> dopiero po pierwszym wymalowaniu (`load` plus dwie
 * klatki requestAnimationFrame), a to ona wlacza lot w CSS.
 *
 * Po co: lot trwa 0,37 s razem z opoznieniem. Animacja przypisana
 * wprost do wczytania strony moze sie w calosci zmiescic przed
 * pierwsza klatka, ktora zobaczy uzytkownik, i wtedy nikt jej nie
 * zobaczy. Start po pierwszym wymalowaniu to wyklucza.
 *
 * Uwaga na historie: ten mechanizm powstal jako poprawka zgloszenia
 * „animacja nie dziala na iPhonie". Prawdziwa przyczyna byla inna —
 * w telefonie wlaczone bylo systemowe ograniczanie ruchu, ktore
 * animacje wylacza celowo (patrz prefers-reduced-motion w styles.css).
 * Mechanizm zostaje, bo sam w sobie jest poprawny, ale NIE jest
 * lekarstwem na zaden potwierdzony blad przegladarki. Jesli kiedys
 * bedzie przeszkadzal, mozna go zdjac: wystarczy przeniesc
 * `animation-name` z regul `.mp-lot ...` na `.diag .strzala ...`
 * i usunac ten plik razem z trzema tagami <script>.
 *
 * Bez JavaScriptu strzala stoi w pozycji koncowej — nic nie znika
 * i nic nie zostaje poza ekranem. To warunek calego mechanizmu:
 * stanem bazowym w CSS jest pozycja koncowa.
 */
(function () {
  var html = document.documentElement;

  function wlacz() {
    if (html.classList.contains('mp-lot')) return;
    requestAnimationFrame(function () {
      requestAnimationFrame(function () { html.classList.add('mp-lot'); });
    });
  }

  if (document.readyState === 'complete') wlacz();
  else window.addEventListener('load', wlacz, { once: true });
})();
