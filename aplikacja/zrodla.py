# -*- coding: utf-8 -*-
"""Skad aplikacja bierze pliki strony i dokad je zapisuje.

GitHubZrodlo - normalna praca: czyta i zapisuje repo przez API GitHuba.
               Na komputerze osoby, ktora dodaje wydarzenia, nie musi byc
               ani gita, ani kopii repo — wystarczy token.
LokalneZrodlo - katalog na dysku; do testow i dla nas.

Oba maja to samo: migawka() zwraca funkcje czytaj(sciezka) przypieta do
jednej wersji repo, a zapisz(pliki, opis, migawka) wrzuca zmiany jako
JEDEN commit. Netlify wdraza strone sam po kazdym commicie na main.
"""
import base64
import io
import json
import os
import urllib.error
import urllib.request


class BladZrodla(Exception):
    pass


class Konflikt(BladZrodla):
    """Ktos zapisal cos w repo miedzy odczytem a zapisem."""


class LokalneZrodlo:
    def __init__(self, katalog):
        self.katalog = katalog

    def opis(self):
        return 'katalog ' + self.katalog

    def migawka(self):
        k = self.katalog

        def czytaj(sciezka):
            with io.open(os.path.join(k, sciezka), encoding='utf-8') as f:
                return f.read().replace('\r\n', '\n')
        czytaj.wersja = None
        return czytaj

    def czytaj_bajty(self, sciezka):
        with open(os.path.join(self.katalog, sciezka), 'rb') as f:
            return f.read()

    def zapisz(self, pliki, opis, migawka=None):
        for sciezka, tresc in pliki.items():
            with io.open(os.path.join(self.katalog, sciezka), 'w', encoding='utf-8', newline='\n') as f:
                f.write(tresc)
        return None


class GitHubZrodlo:
    API = 'https://api.github.com'

    def __init__(self, token, repo='wsolore/matchpoint', galaz='main', api=None):
        self.token = (token or '').strip()
        self.repo = repo
        self.galaz = galaz
        if api:
            self.API = api

    def opis(self):
        return 'GitHub ' + self.repo + ' (' + self.galaz + ')'

    # ---- HTTP
    def _zapytanie(self, metoda, sciezka, dane=None):
        url = self.API + sciezka
        cialo = json.dumps(dane).encode('utf-8') if dane is not None else None
        req = urllib.request.Request(url, data=cialo, method=metoda)
        req.add_header('Accept', 'application/vnd.github+json')
        req.add_header('X-GitHub-Api-Version', '2022-11-28')
        req.add_header('User-Agent', 'MatchPoint-Wydarzenia')
        if self.token:
            req.add_header('Authorization', 'Bearer ' + self.token)
        if cialo is not None:
            req.add_header('Content-Type', 'application/json')
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode('utf-8') or 'null')
        except urllib.error.HTTPError as e:
            tresc = e.read().decode('utf-8', 'replace')
            if e.code == 401:
                raise BladZrodla('GitHub nie przyjął tokenu. Sprawdź go w Ustawieniach '
                                 '(mógł wygasnąć — token ma datę ważności).')
            if e.code == 403 or (e.code == 404 and metoda != 'GET'):
                raise BladZrodla('Token nie ma uprawnień do zapisu w repozytorium %s. '
                                 'Potrzebne jest "Contents: Read and write".' % self.repo)
            if e.code == 404:
                raise BladZrodla('Nie znaleziono: %s. Sprawdź nazwę repozytorium w Ustawieniach.' % sciezka)
            if e.code == 422 and '/git/refs/' in sciezka:
                raise Konflikt(tresc)
            raise BladZrodla('GitHub odpowiedział błędem %d: %s' % (e.code, tresc[:300]))
        except urllib.error.URLError as e:
            raise BladZrodla('Brak połączenia z GitHubem (%s). Sprawdź internet.' % e.reason)

    def _repo(self, reszta):
        return '/repos/' + self.repo + reszta

    # ---- odczyt
    def glowa(self):
        ref = self._zapytanie('GET', self._repo('/git/ref/heads/' + self.galaz))
        return ref['object']['sha']

    def migawka(self):
        """Czytanie przypiete do jednego commita: wszystkie pliki jednej
        operacji pochodza z tej samej wersji repo."""
        sha = self.glowa()
        commit = self._zapytanie('GET', self._repo('/git/commits/' + sha))
        drzewo = self._zapytanie('GET', self._repo('/git/trees/' + commit['tree']['sha'] + '?recursive=1'))
        bloby = {x['path']: x['sha'] for x in drzewo.get('tree', []) if x.get('type') == 'blob'}
        pamiec = {}

        def bajty(sciezka):
            if sciezka not in bloby:
                raise BladZrodla('W repozytorium nie ma pliku ' + sciezka)
            if sciezka not in pamiec:
                b = self._zapytanie('GET', self._repo('/git/blobs/' + bloby[sciezka]))
                pamiec[sciezka] = base64.b64decode(b['content'])
            return pamiec[sciezka]

        def czytaj(sciezka):
            return bajty(sciezka).decode('utf-8').replace('\r\n', '\n')
        czytaj.wersja = sha
        czytaj.bajty = bajty
        czytaj.pliki = set(bloby)
        return czytaj

    # ---- zapis
    def zapisz(self, pliki, opis, migawka):
        rodzic = migawka.wersja
        commit = self._zapytanie('GET', self._repo('/git/commits/' + rodzic))
        drzewo = self._zapytanie('POST', self._repo('/git/trees'), {
            'base_tree': commit['tree']['sha'],
            'tree': [{'path': p, 'mode': '100644', 'type': 'blob', 'content': t}
                     for p, t in sorted(pliki.items())],
        })
        nowy = self._zapytanie('POST', self._repo('/git/commits'), {
            'message': opis, 'tree': drzewo['sha'], 'parents': [rodzic],
        })
        # Bez force: gdy ktos zdazyl zapisac cos po naszym odczycie, GitHub
        # odmowi (422), a aplikacja policzy zmiane jeszcze raz od nowa.
        self._zapytanie('PATCH', self._repo('/git/refs/heads/' + self.galaz),
                        {'sha': nowy['sha'], 'force': False})
        return nowy['sha']


def wykonaj(zrodlo, operacja, opis_commita, proby=2):
    """operacja(czytaj) -> (pliki, wynik). Przy konflikcie liczymy
    zmiane od nowa na swiezej wersji — dlatego operacja dostaje
    czytaj, a nie gotowe pliki."""
    for proba in range(proby):
        czytaj = zrodlo.migawka()
        pliki, wynik = operacja(czytaj)
        try:
            zrodlo.zapisz(pliki, opis_commita, czytaj)
            return pliki, wynik
        except Konflikt:
            if proba == proby - 1:
                raise BladZrodla('Ktoś w tym samym czasie zmieniał stronę. Kliknij "Odśwież" i spróbuj jeszcze raz.')


def stan_zakladki(endpoint, zakladka, timeout=25):
    """Pyta skrypt arkusza o zakladke. Zwraca (True, dane) albo (False, blad)."""
    from urllib.parse import quote
    url = endpoint + '?tab=' + quote(zakladka)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'MatchPoint-Wydarzenia'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read().decode('utf-8'))
    except Exception as e:
        return False, 'Arkusz nie odpowiedział (%s).' % e
    if d.get('ok'):
        return True, d
    return False, d.get('error') or 'nieznany błąd'
