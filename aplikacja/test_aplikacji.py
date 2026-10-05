# -*- coding: utf-8 -*-
"""Test aplikacji na kopii repo i na udawanym GitHubie.

    python aplikacja/test_aplikacji.py

Nie dotyka ani prawdziwego repo, ani GitHuba, ani arkusza.
"""
import base64
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

TU = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TU)
sys.path.insert(0, TU)
import generator as g   # noqa: E402
import operacje as op   # noqa: E402
import zrodla as zr     # noqa: E402
from archiwizuj_minione import archiwizuj_minione  # noqa: E402
from datetime import datetime  # noqa: E402

bledy = []


def ok(warunek, opis):
    print(('  ok   ' if warunek else '  ZLE  ') + opis)
    if not warunek:
        bledy.append(opis)


def kopia_repo():
    kat = tempfile.mkdtemp(prefix='mp-test-')
    for p in os.listdir(REPO):
        if p in ('.git', 'docs', 'aplikacja') or p.endswith('.png'):
            continue
        zrodlo = os.path.join(REPO, p)
        (shutil.copytree if os.path.isdir(zrodlo) else shutil.copy)(zrodlo, os.path.join(kat, p))
    return kat


def z_reczna_strona(kat):
    """Testy 3 i 5 potrzebuja recznej strony w sprzedazy. Od 05.10 padel
    03.10 siedzi w archiwum, wiec bierzemy go z gita sprzed archiwizacji."""
    def git(plik):
        return subprocess.run(['git', 'show', '83fcde7:' + plik], cwd=REPO, capture_output=True,
                              encoding='utf-8', check=True).stdout
    padel = next(x for x in g.czytaj_config(git('config.js'))['upcoming'] if x['id'] == 'PSD-0310')
    sciezka = os.path.join(kat, 'config.js')
    tekst = io.open(sciezka, encoding='utf-8').read()
    dane = g.czytaj_config(tekst)
    dane['upcoming'].append(padel)
    dane['past'] = [x for x in dane['past'] if x['page'] != padel['page']]
    io.open(sciezka, 'w', encoding='utf-8').write(g.pisz_config(tekst, dane))
    io.open(os.path.join(kat, padel['page']), 'w', encoding='utf-8').write(git(padel['page']))


def config_w_node(kat):
    """Config musi dalej dzialac w przegladarce — sprawdzamy go w node."""
    kod = ("const fs=require('fs');const M=new Function(fs.readFileSync(process.argv[1],'utf8')"
           "+';return MATCHPOINT;')();console.log(JSON.stringify({u:M.upcoming.map(e=>e.id),"
           "p:M.past.map(e=>e.date),n:M.next&&M.next.id,b:M.byId('TSD-2510')&&M.byId('TSD-2510').id}))")
    out = subprocess.run(['node', '-e', kod, os.path.join(kat, 'config.js')],
                         capture_output=True, text=True, encoding='utf-8')
    return json.loads(out.stdout) if out.returncode == 0 else {'blad': out.stderr}


print('1. Nowe wydarzenie na kopii repo')
kat = kopia_repo()
z_reczna_strona(kat)
lok = zr.LokalneZrodlo(kat)
cz = lok.migawka()
pres = op.presety(cz)
e, s = g.nowe_wydarzenie(pres, 'Tenis')
e.update(date='25.10.2026', time='16:00-18:00', venue='Korty Testowe', address='Testowa 1, Warszawa',
         priceW=120, priceM=140, sheetTab='')
przed = op.stan(cz)
zr.wykonaj(lok, lambda c: op.dodaj(c, e, s), 'test')
po = op.stan(lok.migawka())
nowy = next((x for x in po['upcoming'] if x['id'] == 'TSD-2510'), None)
ok(nowy is not None, 'wpis TSD-2510 jest w configu')
ok(nowy and nowy['weekday'] == 'Niedziela', 'dzien tygodnia policzony (25.10.2026 = niedziela)')
ok(nowy and nowy['time'] == '16:00–18:00', 'godziny z polpauza, jak w reszcie configu')
ok(nowy and nowy['sheetTab'] == '25.10', 'pusta zakladka = data krotka')
ok(nowy and nowy['page'] == 'tennis-speed-dating-25-10.html', 'nazwa pliku jak dotad')
ok(len(po['upcoming']) == len(przed['upcoming']) + 1, 'reszta wydarzen nietknieta')
ok(po['upcoming'] == sorted(po['upcoming'], key=g.klucz_czasu), 'lista od najblizszego')
strona = io.open(os.path.join(kat, 'tennis-speed-dating-25-10.html'), encoding='utf-8').read()
ok("MATCHPOINT.byId('TSD-2510')" in strona, 'strona siega po wlasny wpis')
ok('Kobiety</span><span class="v">120' in strona and '140 <small>zł' in strona, 'dwie rozne ceny = dwa pola')
ok('2026-10-25T16:00+01:00' in strona, 'po zmianie czasu (25.10) strefa +01:00')
ok('{{' not in strona and not __import__('re').search(r'\[\[[?/]\w+\]\]', strona), 'nie zostal zaden znacznik szablonu')
ok(g.dane_ze_strony(strona) == s or g.dane_ze_strony(strona)['lead'] == s['lead'], 'teksty strony da sie odczytac z powrotem')
idx = io.open(os.path.join(kat, 'index.html'), encoding='utf-8').read()
ok('data-free="TSD-2510"' in idx, 'karta na stronie glownej')
ok(idx.count('<!-- >>> KARTY') == 1 and idx.count('<!-- <<< KARTY -->') == 1, 'znaczniki kart nietkniete')
pierwszy = next(x for x in po['upcoming'] if not g.minelo(x))
ok('data-next-date>%s, ' % pierwszy['date'] in idx and 'href="%s" data-next-link' % pierwszy['page'] in idx,
   'hero w HTML wskazuje najblizszy termin, ktory jeszcze nie minal')
ok('tennis-speed-dating-25-10.html' in io.open(os.path.join(kat, 'sitemap.xml'), encoding='utf-8').read(), 'sitemap')
w = config_w_node(kat)
ok(w.get('b') == 'TSD-2510' and w.get('n') == next(x for x in po['upcoming'] if not g.minelo(x))['id'],
   'config dziala w JS: byId i next')
padel_17 = {'date': '03.10.2026', 'time': '17:00–18:30'}
ok(g.minelo(padel_17, datetime(2026, 10, 3, 17, 0)) and not g.minelo(padel_17, datetime(2026, 10, 3, 16, 59)),
   'minelo: od godziny startu')

print('2. Zmiana ceny i zamkniecie puli')
e2 = dict(nowy, priceW=130, priceM=130, soldOutMen=True)
zr.wykonaj(lok, lambda c: op.zmien(c, e2, g.dane_ze_strony(c(e2['page']))), 'test')
po2 = op.stan(lok.migawka())
x = next(x for x in po2['upcoming'] if x['id'] == 'TSD-2510')
ok(x['priceW'] == 130 and x['soldOutMen'] is True, 'config zmieniony')
strona = io.open(os.path.join(kat, x['page']), encoding='utf-8').read()
ok('Cena</span><span class="v">130' in strona and 'Kobiety</span><span class="v">' not in strona, 'rowna cena = jedno pole "Cena"')
ok(x['page'] == nowy['page'] and x['id'] == nowy['id'], 'id i plik bez zmian po edycji')

print('3. Zmiana strony recznej (padel) rusza tylko config')
padel = next(x for x in po2['upcoming'] if x['id'] == 'PSD-0310')
przed_html = io.open(os.path.join(kat, padel['page']), encoding='utf-8').read()
pliki, _ = op.zmien(lok.migawka(), dict(padel, limitMen=8), op.teksty_strony(lok.migawka(), padel))
ok(padel['page'] not in pliki, 'strona reczna nie jest przepisywana')

print('4. Bledne dane')
for zmiana, opis in ((dict(date='31.02.2026'), 'nieistniejaca data'),
                     (dict(time='19:00-17:00'), 'koniec przed poczatkiem'),
                     (dict(ageMin=16), 'wiek ponizej 18'),
                     (dict(sheetTab='25.10', date='25.10.2026', time='19:00-20:00'), 'zakladka zajeta')):
    try:
        op.dodaj(lok.migawka(), dict(e, **zmiana), s)
        ok(False, opis + ' — przeszlo, a nie powinno')
    except g.BladDanych:
        ok(True, opis + ' — odrzucone')
drugi = dict(e, time='19:00-20:00', sheetTab='25.10 19:00')
pliki, d2 = op.dodaj(lok.migawka(), drugi, s)
ok(d2['page'] == 'tennis-speed-dating-25-10-1900.html' and d2['id'] == 'TSD-2510-19', 'drugi slot tego dnia: osobny plik i id')
ok(g.tekst_inline('<script>**x**</script> a@b.pl') ==
   '&lt;script&gt;<b>x</b>&lt;/script&gt; <a href="mailto:a@b.pl">a@b.pl</a>', 'tekst z aplikacji nie wstrzyknie HTML')

print('5. Archiwum')
zr.wykonaj(lok, lambda c: op.archiwizuj(c, 'TSD-2510'), 'test')
po3 = op.stan(lok.migawka())
ok(all(x['id'] != 'TSD-2510' for x in po3['upcoming']), 'zniknelo ze sprzedazy')
ok(po3['past'][0]['date'] == '25.10.2026', 'jest na gorze archiwum')
strona = io.open(os.path.join(kat, 'tennis-speed-dating-25-10.html'), encoding='utf-8').read()
ok('To wydarzenie już się odbyło' in strona and 'id="signup"' not in strona and 'MATCHPOINT.byId' not in strona,
   'strona: baner, bez formularza i skryptu')
zr.wykonaj(lok, lambda c: op.archiwizuj(c, 'PSD-0310'), 'test')
strona = io.open(os.path.join(kat, 'padel-speed-dating-03-10.html'), encoding='utf-8').read()
ok('To wydarzenie już się odbyło' in strona and 'id="signup"' not in strona and 'id="zapisy"' not in strona
   and 'MATCHPOINT.byId' not in strona and 'hero--short' in strona, 'reczna strona padla tez zarchiwizowana')
ok('Czym padel różni się od tenisa' in strona, 'FAQ zostalo')
idx = io.open(os.path.join(kat, 'index.html'), encoding='utf-8').read()
ok('data-free="PSD-0310"' not in idx and 'href="padel-speed-dating-03-10.html">' in idx.split('ARCHIWUM')[1],
   'karta przeszla do "Za nami"')
w = config_w_node(kat)
ok('blad' not in w and 'PSD-0310' not in w['u'], 'config po archiwizacji dziala w JS')
shutil.rmtree(kat)

print('5a. Automat archiwum: od godziny startu, dwa sloty jednego dnia')
kat = kopia_repo()
lok = zr.LokalneZrodlo(kat)
for godz, zakladka in (('16:00-18:00', '25.10 16:00'), ('19:00-20:00', '25.10 19:00')):
    zr.wykonaj(lok, lambda c, x=dict(e, date='25.10.2026', time=godz, sheetTab=zakladka): op.dodaj(c, x, s), 'test')
ok(archiwizuj_minione(lok, datetime(2026, 10, 18, 16, 59)) == [], 'przed startem nic nie rusza')
pierwsze = archiwizuj_minione(lok, datetime(2026, 10, 25, 16, 0))
ok([x['id'] for x in pierwsze] == ['TSD-1810', 'TSD-2510'], 'o 16:00 schodzi 18.10 i slot 16:00, slot 19:00 zostaje')
archiwizuj_minione(lok, datetime(2026, 10, 25, 19, 0))
po5 = op.stan(lok.migawka())
ok(po5['upcoming'] == [], 'o 19:00 schodzi ostatni')
ok([(x['page'], x['note']) for x in po5['past'][:3]] ==
   [('tennis-speed-dating-25-10-1900.html', 'Godz. 19:00.'), ('tennis-speed-dating-25-10.html', 'Godz. 16:00.'),
    ('tennis-speed-dating-18-10.html', '')], 'w "Za nami" pozniejszy slot wyzej, oba z godzina')
strona = io.open(os.path.join(kat, 'tennis-speed-dating-18-10.html'), encoding='utf-8').read()
ok('To wydarzenie już się odbyło' in strona and 'id="signup"' not in strona, 'strona 18.10 bez formularza')
ok(archiwizuj_minione(lok, datetime(2026, 10, 26)) == [], 'drugie przejscie nic nie zmienia')
w = config_w_node(kat)
ok('blad' not in w and w['u'] == [], 'config po automacie dziala w JS')
shutil.rmtree(kat)


print('6. GitHub: jeden commit, konflikt, zle uprawnienia')


class UdawanyGitHub(BaseHTTPRequestHandler):
    """Tyle API gita, ile uzywa aplikacja. Stan w atrybutach klasy."""
    pliki = {}
    commity = {}
    glowa = None
    zapisy_ref = 0
    wtracenie = False   # przy nastepnym PATCH udaj, ze ktos zdazyl zapisac
    token = 'dobry'

    def log_message(self, *a):
        pass

    def _odp(self, kod, obj):
        b = json.dumps(obj).encode()
        self.send_response(kod)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(b)

    def _auth(self):
        if self.headers.get('Authorization') != 'Bearer ' + self.token:
            self._odp(401, {'message': 'Bad credentials'})
            return False
        return True

    @classmethod
    def zrob_commit(cls, pliki, rodzic):
        sha = hashlib.sha1(json.dumps([pliki, rodzic], sort_keys=True).encode()).hexdigest()
        cls.commity[sha] = {'pliki': dict(pliki), 'rodzic': rodzic}
        return sha

    def do_GET(self):
        if not self._auth():
            return
        p = self.path.split('/repos/o/r')[1]
        k = type(self)
        if p == '/git/ref/heads/main':
            return self._odp(200, {'object': {'sha': k.glowa}})
        if p.startswith('/git/commits/'):
            return self._odp(200, {'tree': {'sha': 'T' + p.split('/')[-1]}})
        if p.startswith('/git/trees/T'):
            sha = p.split('/')[-1].split('?')[0][1:]
            return self._odp(200, {'tree': [{'path': x, 'type': 'blob', 'sha': sha + ':' + x}
                                            for x in k.commity[sha]['pliki']]})
        if p.startswith('/git/blobs/'):
            sha, sciezka = p[len('/git/blobs/'):].split(':', 1)
            tresc = k.commity[sha]['pliki'][sciezka]
            return self._odp(200, {'content': base64.b64encode(tresc.encode()).decode()})
        self._odp(404, {})

    def do_POST(self):
        if not self._auth():
            return
        dane = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        p = self.path.split('/repos/o/r')[1]
        k = type(self)
        if p == '/git/trees':
            baza = k.commity[dane['base_tree'][1:]]['pliki']
            nowe = dict(baza)
            for x in dane['tree']:
                nowe[x['path']] = x['content']
            k.commity['DRZEWO'] = nowe
            return self._odp(201, {'sha': 'DRZEWO'})
        if p == '/git/commits':
            sha = k.zrob_commit(k.commity[dane['tree']], dane['parents'][0])
            return self._odp(201, {'sha': sha})
        self._odp(404, {})

    def do_PATCH(self):
        if not self._auth():
            return
        dane = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        k = type(self)
        if k.wtracenie:
            k.wtracenie = False
            pl = dict(k.commity[k.glowa]['pliki'])
            pl['README.md'] = 'ktos inny cos zapisal'
            k.glowa = k.zrob_commit(pl, k.glowa)
        if k.commity[dane['sha']]['rodzic'] != k.glowa:
            return self._odp(422, {'message': 'Update is not a fast forward'})
        k.glowa = dane['sha']
        k.zapisy_ref += 1
        self._odp(200, {})


pliki_repo = {}
for p in ('config.js', 'index.html', 'sitemap.xml', 'szablony/wydarzenie.html', 'szablony/sporty.json',
          'padel-speed-dating-03-10.html'):
    pliki_repo[p] = io.open(os.path.join(REPO, p), encoding='utf-8').read().replace('\r\n', '\n')
UdawanyGitHub.glowa = UdawanyGitHub.zrob_commit(pliki_repo, None)
serwer = HTTPServer(('127.0.0.1', 0), UdawanyGitHub)
threading.Thread(target=serwer.serve_forever, daemon=True).start()
api = 'http://127.0.0.1:%d' % serwer.server_port

gh = zr.GitHubZrodlo('dobry', repo='o/r', api=api)
UdawanyGitHub.wtracenie = True
zr.wykonaj(gh, lambda c: op.dodaj(c, e, s), 'Nowe wydarzenie (test)')
koniec = UdawanyGitHub.commity[UdawanyGitHub.glowa]['pliki']
ok(UdawanyGitHub.zapisy_ref == 1, 'po konflikcie jedna udana proba, bez force')
ok(koniec.get('README.md') == 'ktos inny cos zapisal', 'cudzy zapis nie zostal nadpisany')
ok('tennis-speed-dating-25-10.html' in koniec and '"TSD-2510"' in koniec['config.js'],
   'nowa strona i config w jednym commicie')
try:
    zr.GitHubZrodlo('zly', repo='o/r', api=api).migawka()
    ok(False, 'zly token przeszedl')
except zr.BladZrodla as err:
    ok('tokenu' in str(err), 'zly token: czytelny komunikat')
serwer.shutdown()

print('\n' + ('wszystko czyste' if not bledy else 'BLEDY: %d' % len(bledy)))
sys.exit(1 if bledy else 0)
