/* Start animacji znaku marki (strzaly w hero).
 *
 * Animacja NIE jest przypisana do wczytania strony. Dodajemy klase
 * `mp-lot` na <html> dopiero wtedy, gdy przegladarka wymalowala juz
 * pierwsza klatke, i to ona wlacza animacje w CSS.
 *
 * Dlaczego: Safari na iOS wstrzymuje pierwsze malowanie do konca
 * nawigacji. Animacja trwa 0,37 s razem z opoznieniem, wiec caly jej
 * czas mijal za czarnym ekranem i na iPhonie nikt jej nie widzial —
 * strzala pojawiala sie od razu w pozycji koncowej. Potwierdzone
 * nagraniem z iPhone'a: klatka przed pojawieniem sie strony jest czarna,
 * a pierwsza wymalowana pokazuje juz strzale na miejscu, bez zadnej
 * klatki przelotu pomiedzy. Skrocenie lotu z 0,8 s do 0,25 s pogorszylo
 * sprawe, bo okno, w ktorym cokolwiek dalo sie zobaczyc, zrobilo sie
 * ponad trzy razy krotsze.
 *
 * Bez JavaScriptu strzala po prostu stoi w pozycji koncowej — nic nie
 * znika i nic nie zostaje poza ekranem. To jest warunek, ktory trzyma
 * caly ten mechanizm: stanem bazowym w CSS jest pozycja koncowa.
 *
 * Podwojne requestAnimationFrame po zdarzeniu `load`: `load` daje
 * pewnosc, ze pierwsze malowanie juz bylo, a dwie klatki rAF daja
 * pewnosc, ze przegladarka zdazyla je oddac na ekran.
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
