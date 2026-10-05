# -*- coding: utf-8 -*-
"""Przenosi do archiwum wydarzenia, ktore juz sie zaczely.

    python aplikacja/archiwizuj_minione.py [katalog_repo]

Odpala go GitHub Actions co kwadrans (.github/workflows/archiwum.yml)
i sam commituje wynik, a Netlify wdraza strone. Robi dokladnie to samo
co przycisk "Przenies do archiwum" w aplikacji. Do 05.10 archiwum
bylo tylko reczne i padel z 03.10 wisial w sprzedazy dwa dni po
wydarzeniu.

Wypisuje jedna linie na zarchiwizowane wydarzenie; brak wydruku =
nie bylo czego ruszac, workflow wtedy niczego nie commituje.
"""
import os
import sys

TU = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TU)
import generator as g   # noqa: E402
import operacje as op   # noqa: E402
import zrodla as zr     # noqa: E402


def archiwizuj_minione(zrodlo, teraz=None):
    """Zwraca liste zarchiwizowanych wpisow, od najwczesniejszego."""
    minione = [e for e in sorted(op.stan(zrodlo.migawka())['upcoming'], key=g.klucz_czasu)
               if g.minelo(e, teraz)]
    for e in minione:
        zr.wykonaj(zrodlo, lambda cz, id_=e['id']: op.archiwizuj(cz, id_),
                   'Archiwum: %s %s (automat)' % (e['name'], e['date']))
    return minione


if __name__ == '__main__':
    katalog = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(TU)
    for e in archiwizuj_minione(zr.LokalneZrodlo(katalog)):
        print('%s %s %s, %s' % (e['name'], e['date'], e['time'], e['page']))
