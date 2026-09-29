# -*- coding: utf-8 -*-
"""Operacje na stronie: dodaj, zmien, przenies do archiwum.

Kazda operacja dostaje funkcje czytaj(sciezka) -> tekst i zwraca
slownik {sciezka: nowa_tresc} z plikami do zapisania. Skad pliki
przychodza (dysk czy GitHub) i dokad ida, decyduje wywolujacy.
Dzieki temu aplikacja zawsze liczy zmiane od NAJSWIEZSZEJ wersji
repo, a nie od tej, ktora wczytala przy starcie — dwie osoby klikajace
po sobie nie nadpisza sobie nawzajem wydarzen.
"""
import json

import generator as g

SZABLON = 'szablony/wydarzenie.html'
SPORTY = 'szablony/sporty.json'


def presety(czytaj):
    dane = json.loads(czytaj(SPORTY))
    return {k: v for k, v in dane.items() if not k.startswith('_')}


def stan(czytaj):
    return g.czytaj_config(czytaj('config.js'))


def _pliki_list(czytaj, dane, pres):
    return {
        'config.js': g.pisz_config(czytaj('config.js'), dane),
        'index.html': g.pisz_index(czytaj('index.html'), dane, pres),
        'sitemap.xml': g.pisz_sitemap(dane),
    }


def dodaj(czytaj, e, s):
    pres = presety(czytaj)
    dane = stan(czytaj)
    e = g.uzupelnij(e, dane, pres, nowe=True)
    bledy = g.sprawdz(e)
    if bledy:
        raise g.BladDanych('\n'.join(bledy))
    zajete = [x for x in dane['upcoming'] if x['sheetTab'].strip().lower() == e['sheetTab'].strip().lower()]
    if zajete:
        raise g.BladDanych('Zakładka "%s" jest już używana przez %s %s. Każde wydarzenie '
                           'potrzebuje własnej zakładki.' % (e['sheetTab'], zajete[0]['name'], zajete[0]['date']))
    strona = g.zloz_strone(czytaj(SZABLON), e, s)
    dane['upcoming'].append(e)
    pliki = _pliki_list(czytaj, dane, pres)
    pliki[e['page']] = strona
    return pliki, e


def zmien(czytaj, e, s):
    """s = None dla stron robionych recznie: zmieniamy wtedy tylko config
    (ceny, limity, zamkniecie puli dzialaja od razu, bo strona czyta je
    z configu), a tresci strony nie ruszamy."""
    pres = presety(czytaj)
    dane = stan(czytaj)
    idx = next((i for i, x in enumerate(dane['upcoming']) if x['id'] == e['id']), None)
    if idx is None:
        raise g.BladDanych('Wydarzenia %s nie ma już w sprzedaży — ktoś je właśnie zmienił? '
                           'Kliknij "Odśwież".' % e['id'])
    stary = dane['upcoming'][idx]
    e = g.uzupelnij(dict(e, id=stary['id'], page=stary['page']), dane, pres, nowe=False)
    bledy = g.sprawdz(e)
    if bledy:
        raise g.BladDanych('\n'.join(bledy))
    dane['upcoming'][idx] = e
    pliki = _pliki_list(czytaj, dane, pres)
    if s is not None:
        pliki[e['page']] = g.zloz_strone(czytaj(SZABLON), e, s)
    return pliki, e


def archiwizuj(czytaj, id_):
    pres = presety(czytaj)
    dane, e = g.przenies_do_archiwum(stan(czytaj), id_)
    pliki = _pliki_list(czytaj, dane, pres)
    tekst = czytaj(e['page'])
    s = g.dane_ze_strony(tekst)
    if s is not None:
        pliki[e['page']] = g.zloz_strone(czytaj(SZABLON), e, s, archiwum=True)
    else:
        pliki[e['page']] = g.archiwizuj_reczna(tekst, e)
    return pliki, e


def teksty_strony(czytaj, e):
    """Teksty strony do edycji albo None, gdy strona jest reczna."""
    try:
        return g.dane_ze_strony(czytaj(e['page']))
    except Exception:
        return None
