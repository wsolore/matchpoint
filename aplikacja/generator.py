# -*- coding: utf-8 -*-
"""Sklada pliki strony z danych wydarzen.

Wszystko tu to czyste funkcje: tekst pliku na wejsciu, tekst pliku na
wyjsciu. Nie ma tu ani sieci, ani okienek, dzieki czemu ten sam kod
obsluguje aplikacje, testy i reczne uzycie z wiersza polecen.

Pliki, ktore generator rusza:
  config.js     - blok miedzy znacznikami >>> WYDARZENIA / <<< WYDARZENIA
  index.html    - karty w sprzedazy i lista "Za nami", tez miedzy znacznikami
  sitemap.xml   - w calosci
  <strona>.html - strona wydarzenia, ze szablonu szablony/wydarzenie.html
"""
import html
import json
import re
from datetime import date as _date
from urllib.parse import quote, quote_plus

SITE = 'https://matchpointdate.pl'
MAIL = 'match.point.date@gmail.com'

ZNACZNIK_CFG_OD = '/* >>> WYDARZENIA'
ZNACZNIK_CFG_DO = '/* <<< WYDARZENIA */'
ZNACZNIK_KARTY_OD = '<!-- >>> KARTY'
ZNACZNIK_KARTY_DO = '<!-- <<< KARTY -->'
ZNACZNIK_ARCH_OD = '<!-- >>> ARCHIWUM'
ZNACZNIK_ARCH_DO = '<!-- <<< ARCHIWUM -->'

DNI = ['Poniedziałek', 'Wtorek', 'Środa', 'Czwartek', 'Piątek', 'Sobota', 'Niedziela']

# Kolejnosc pol w configu. Trzymamy ja stala, zeby diff w gicie po
# zapisie z aplikacji pokazywal tylko to, co sie naprawde zmienilo.
POLA = ['id', 'name', 'sport', 'city', 'date', 'weekday', 'time', 'venue',
        'address', 'age', 'ageMin', 'ageMax', 'level', 'surface', 'shoes',
        'transport', 'bring', 'bringExtra', 'included', 'cardNote',
        'priceW', 'priceM', 'page', 'sheetTab', 'formUrl', 'blik',
        'limitWomen', 'limitMen', 'soldOutWomen', 'soldOutMen']
POLA_ARCH = ['name', 'sport', 'date', 'weekday', 'venue', 'note', 'page']


class BladDanych(Exception):
    """Dane, z ktorych nie da sie zlozyc poprawnej strony. Tresc idzie
    wprost do okienka, wiec pisana jest dla czlowieka, nie dla nas."""


# ------------------------------------------------------------ config.js

def _blok(tekst, od, do, plik):
    a = tekst.find(od)
    b = tekst.find(do)
    if a < 0 or b < 0 or b < a:
        raise BladDanych('W pliku %s nie ma znacznikow %s ... %s. '
                         'Ktos go przerobil recznie — zadzwon do nas, zanim cokolwiek zapiszesz.'
                         % (plik, od, do))
    return a, b


def czytaj_config(tekst):
    """Zwraca {'upcoming': [...], 'past': [...]} z config.js."""
    a, b = _blok(tekst, ZNACZNIK_CFG_OD, ZNACZNIK_CFG_DO, 'config.js')
    srodek = tekst[a:b]
    m = re.search(r'MATCHPOINT_WYDARZENIA\s*=\s*(\{.*\})\s*;\s*$', srodek, re.S)
    if not m:
        raise BladDanych('Blok wydarzen w config.js nie jest w formacie, ktory rozumie aplikacja.')
    return json.loads(m.group(1))


def _uloz(wpis, pola):
    wynik = {k: wpis[k] for k in pola if k in wpis}
    for k in wpis:
        if k not in wynik:
            wynik[k] = wpis[k]
    return wynik


def pisz_config(tekst, dane):
    a, b = _blok(tekst, ZNACZNIK_CFG_OD, ZNACZNIK_CFG_DO, 'config.js')
    naglowek_konec = tekst.index('*/', a) + 2
    upcoming = sorted(dane['upcoming'], key=klucz_czasu)
    past = sorted(dane['past'], key=klucz_czasu, reverse=True)
    uporzadkowane = {
        'upcoming': [_uloz(e, POLA) for e in upcoming],
        'past': [_uloz(e, POLA_ARCH) for e in past],
    }
    js = json.dumps(uporzadkowane, ensure_ascii=False, indent=2)
    return (tekst[:naglowek_konec] + '\nconst MATCHPOINT_WYDARZENIA = ' + js + ';\n'
            + tekst[b:])


# ------------------------------------------------------------ daty i drobiazgi

def parsuj_date(d):
    m = re.match(r'^\s*(\d{1,2})\.(\d{1,2})\.(\d{4})\s*$', str(d or ''))
    if not m:
        raise BladDanych('Data "%s" nie jest w formacie DD.MM.RRRR, np. 18.10.2026.' % d)
    try:
        return _date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        raise BladDanych('Data "%s" nie istnieje w kalendarzu.' % d)


def parsuj_godziny(t):
    m = re.match(r'^\s*(\d{1,2}):(\d{2})\s*[–\-]\s*(\d{1,2}):(\d{2})\s*$', str(t or ''))
    if not m:
        raise BladDanych('Godziny "%s" wpisz jako OD–DO, np. 17:00–19:30.' % t)
    od = '%02d:%s' % (int(m.group(1)), m.group(2))
    do = '%02d:%s' % (int(m.group(3)), m.group(4))
    if do <= od:
        raise BladDanych('Koniec wydarzenia (%s) musi byc po poczatku (%s).' % (do, od))
    return od, do


def klucz_czasu(e):
    try:
        d = parsuj_date(e.get('date'))
    except BladDanych:
        d = _date(1970, 1, 1)
    t = str(e.get('time') or '').strip()[:5]
    return (d.isoformat(), t)


def dzien_tygodnia(d):
    return DNI[parsuj_date(d).weekday()]


def normalizuj_godziny(t):
    od, do = parsuj_godziny(t)
    return od + '–' + do


def data_krotka(d):
    """'18.10.2026' -> '18.10', tak jak w nazwach zakladek."""
    x = parsuj_date(d)
    return '%02d.%02d' % (x.day, x.month)


def plik_strony(sport_preset, e, zajete):
    """Nazwa pliku jak dotad: tennis-speed-dating-18-10.html. Gdy tego
    dnia jest juz strona (dwa sloty), dokladamy godzine startu —
    tak samo nazywa sie padel-speed-dating-03-10-1500.html."""
    x = parsuj_date(e['date'])
    baza = '%s-%02d-%02d' % (sport_preset['plikPrefix'], x.day, x.month)
    nazwa = baza + '.html'
    if nazwa in zajete:
        nazwa = baza + '-' + parsuj_godziny(e['time'])[0].replace(':', '') + '.html'
    if nazwa in zajete:
        raise BladDanych('Strona %s juz istnieje. Dwa wydarzenia tej samej dyscypliny, '
                         'tego samego dnia i o tej samej godzinie?' % nazwa)
    return nazwa


def id_wydarzenia(sport_preset, e, zajete):
    x = parsuj_date(e['date'])
    baza = '%s-%02d%02d' % (sport_preset['idPrefix'], x.day, x.month)
    if baza not in zajete:
        return baza
    kandydat = baza + '-' + parsuj_godziny(e['time'])[0][:2]
    if kandydat in zajete:
        raise BladDanych('Wydarzenie o identyfikatorze %s juz jest.' % kandydat)
    return kandydat


def ulica(adres):
    return str(adres or '').split(',')[0].strip()


def miasto(e):
    if e.get('city'):
        return e['city']
    czesci = str(e.get('address') or '').split(',')
    return czesci[-1].strip() if len(czesci) > 1 else 'Warszawa'


def nbsp_ostatnia(tekst):
    """'Annopol 3' -> 'Annopol&nbsp;3': numer nie ucieka do nowej linii."""
    t = html.escape(tekst)
    i = t.rfind(' ')
    return t if i < 0 else t[:i] + '&nbsp;' + t[i + 1:]


def odmiana(n, jeden, kilka, wiele):
    n = int(n)
    if n == 1:
        return jeden
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return kilka
    return wiele


def sklad_slownie(e):
    k, m = int(e['limitWomen']), int(e['limitMen'])
    return '%d %s i %d %s' % (k, odmiana(k, 'kobieta', 'kobiety', 'kobiet'),
                              m, odmiana(m, 'mężczyzna', 'mężczyzn', 'mężczyzn'))


def tekst_inline(t):
    """Tekst od czlowieka -> bezpieczny HTML. Umie tylko dwie rzeczy:
    **pogrubienie** i adres e-mail jako link. Reszta jest escapowana,
    wiec zaden znak wpisany w aplikacji nie rozwali strony."""
    t = html.escape(str(t or ''), quote=False)
    t = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', t)
    t = re.sub(r'([\w.+-]+@[\w-]+\.[\w.]+[\w])',
               r'<a href="mailto:\1">\1</a>', t)
    return t


# ------------------------------------------------------------ walidacja

def sprawdz(e):
    """Zwraca liste bledow; pusta lista = mozna publikowac."""
    bledy = []
    wymagane = {
        'name': 'nazwa', 'sport': 'dyscyplina', 'date': 'data', 'time': 'godziny',
        'venue': 'miejsce', 'address': 'adres', 'sheetTab': 'nazwa zakładki w arkuszu',
        'blik': 'numer BLIK',
    }
    for k, opis in wymagane.items():
        if not str(e.get(k) or '').strip():
            bledy.append('Brak pola: ' + opis + '.')
    try:
        parsuj_date(e.get('date'))
    except BladDanych as err:
        bledy.append(str(err))
    try:
        parsuj_godziny(e.get('time'))
    except BladDanych as err:
        bledy.append(str(err))
    for k, opis in (('priceW', 'cena dla kobiet'), ('priceM', 'cena dla mężczyzn'),
                    ('limitWomen', 'limit kobiet'), ('limitMen', 'limit mężczyzn'),
                    ('ageMin', 'wiek od'), ('ageMax', 'wiek do')):
        v = e.get(k)
        if not isinstance(v, int) or v < 0:
            bledy.append('Pole "%s" musi być liczbą całkowitą.' % opis)
    if isinstance(e.get('ageMin'), int) and isinstance(e.get('ageMax'), int):
        if e['ageMin'] < 18:
            bledy.append('Wiek od nie może być mniejszy niż 18.')
        if e['ageMax'] < e['ageMin']:
            bledy.append('Wiek do jest mniejszy niż wiek od.')
    for k in ('limitWomen', 'limitMen'):
        if isinstance(e.get(k), int) and e[k] < 1:
            bledy.append('Limit miejsc musi wynosić co najmniej 1.')
            break
    return bledy


# ------------------------------------------------------------ strona wydarzenia

LI = ('          <li><img class="ico" src="icon-ball-arrow.svg" alt="" width="22" '
      'height="22" loading="lazy"><span>%s</span></li>\n')


def _tablica(e, s):
    wiersze = [
        ('Data', html.escape(e['date']) + ' <small>' + html.escape(e['weekday'].lower()) + '</small>'),
        ('Godzina', html.escape(e['time'])),
        ('Miejsce', html.escape(e['venue']) + ' <small>' + html.escape(ulica(e['address'])) + '</small>'),
    ]
    if e.get('surface'):
        pow_ = html.escape(e['surface'][:1].upper() + e['surface'][1:])
        if s.get('nawierzchniaOpis'):
            pow_ += ' <small>' + html.escape(s['nawierzchniaOpis']) + '</small>'
        wiersze.append(('Nawierzchnia', pow_))
    if e.get('level'):
        poz = html.escape(e['level'])
        if s.get('poziomOpis'):
            poz += ' <small>' + html.escape(s['poziomOpis']) + '</small>'
        wiersze.append(('Poziom', poz))
    wiersze.append(('Wiek', '%d–%d <small>lat</small>' % (e['ageMin'], e['ageMax'])))
    wiersze.append(('Limit', '%d + %d <small>osób</small>' % (e['limitWomen'], e['limitMen'])))
    # Rowna cena to jedna linijka "Cena", a nie dwie identyczne
    # "Kobiety 130 / Mezczyzni 130" — tak wygladalo to jak pomylka.
    if e['priceW'] == e['priceM']:
        wiersze.append(('Cena', '%d <small>zł</small>' % e['priceW']))
    else:
        wiersze.append(('Kobiety', '%d <small>zł</small>' % e['priceW']))
        wiersze.append(('Mężczyźni', '%d <small>zł</small>' % e['priceM']))
    wiersze.append(('Płatność', 'BLIK <small>' + html.escape(e['blik']) + '</small>'))
    # Siatka ma 5 kolumn na komputerze i 2 na telefonie, wiec przy
    # nieparzystej liczbie pol zostaje pusta kratka, ktora wyglada jak
    # brakujaca informacja. Dokladamy wtedy dyscypline na poczatek.
    if len(wiersze) % 2:
        wiersze.insert(0, ('Dyscyplina', html.escape(e['sport'])))
    def klasa(v):
        # liczy sie najdluzsze slowo samej wartosci, bez dopisku w <small>
        slowa = re.sub(r'<small>.*?</small>|<[^>]+>', '', v).split() or ['']
        return 'v v--dlugi' if len(html.unescape(max(slowa, key=len))) > 11 else 'v'
    return ''.join('      <div><span class="k">%s</span><span class="%s">%s</span></div>\n'
                   % (k, klasa(v), v) for k, v in wiersze)


def _kolumny(s):
    wynik = ''
    for tytul, tekst in s.get('kolumny') or []:
        wynik += ('      <div class="col">\n'
                  '        <h3><img class="ico" src="icon-ball-arrow.svg" alt="" width="22" height="22" '
                  'loading="lazy"><span>%s</span></h3>\n'
                  '        <p>%s</p>\n'
                  '      </div>\n') % (tekst_inline(tytul), tekst_inline(tekst))
    return wynik


def _transit(e, s):
    wiersze = [('Adres', e['address'])] + [tuple(x) for x in (s.get('transit') or [])]
    return ''.join('      <div><b>%s</b><span>%s</span></div>\n'
                   % (html.escape(k), tekst_inline(v)) for k, v in wiersze)


def _faq(s):
    return ''.join('      <details>\n        <summary>%s</summary>\n        <p>%s</p>\n      </details>\n'
                   % (tekst_inline(p), tekst_inline(o)) for p, o in (s.get('faq') or []))


def _opcje(s):
    return ''.join('          <option value="%s">%s</option>\n'
                   % (html.escape(o, quote=True), html.escape(o)) for o in (s.get('poziomOpcje') or []))


def _jsonld(e, s):
    od, do = parsuj_godziny(e['time'])
    d = parsuj_date(e['date']).isoformat()
    # Polska w pazdzierniku zmienia czas: do ostatniej niedzieli
    # pazdziernika +02:00, potem +01:00. Liczymy to, zamiast wpisywac.
    strefa = '+02:00' if _czas_letni(parsuj_date(e['date'])) else '+01:00'
    url = SITE + '/' + e['page']
    obj = {
        '@context': 'https://schema.org',
        '@type': 'Event',
        'name': e['name'] + ', ' + od,
        'startDate': d + 'T' + od + strefa,
        'endDate': d + 'T' + do + strefa,
        'eventStatus': 'https://schema.org/EventScheduled',
        'eventAttendanceMode': 'https://schema.org/OfflineEventAttendanceMode',
        'organizer': {'@type': 'Organization', 'name': 'Match Point', 'url': SITE},
        'location': {
            '@type': 'Place', 'name': e['venue'],
            'address': {'@type': 'PostalAddress', 'streetAddress': ulica(e['address']),
                        'addressLocality': miasto(e), 'addressCountry': 'PL'},
        },
        'description': (s.get('opis') or '') + ' Wiek %d–%d lat, %s.' % (e['ageMin'], e['ageMax'], sklad_slownie(e)),
        'url': url,
        'typicalAgeRange': '%d-%d' % (e['ageMin'], e['ageMax']),
        'maximumAttendeeCapacity': e['limitWomen'] + e['limitMen'],
        'offers': {'@type': 'Offer', 'priceCurrency': 'PLN',
                   'lowPrice': str(min(e['priceW'], e['priceM'])),
                   'highPrice': str(max(e['priceW'], e['priceM'])),
                   'availability': 'https://schema.org/InStock', 'url': url + '#zapisy'},
    }
    return json.dumps(obj, ensure_ascii=False, indent=2).replace('</', '<\\/')


def _czas_letni(d):
    def ostatnia_niedziela(rok, mies):
        x = _date(rok, mies, 31)
        return x.toordinal() - (x.weekday() + 1) % 7
    o = d.toordinal()
    return ostatnia_niedziela(d.year, 3) <= o < ostatnia_niedziela(d.year, 10)


def _sekcje(t, flagi):
    for klucz, wl in flagi.items():
        wzor = re.compile(r'\[\[\?' + klucz + r'\]\](.*?)\[\[/' + klucz + r'\]\]', re.S)
        t = wzor.sub(lambda m: m.group(1) if wl else '', t)
    if '[[' in t and re.search(r'\[\[[?/]\w+\]\]', t):
        raise BladDanych('Szablon ma nieobsluzona sekcje: ' + re.search(r'\[\[[?/]\w+\]\]', t).group(0))
    return t


def zloz_strone(szablon, e, s, archiwum=False):
    """Strona wydarzenia z szablonu. e = wpis z configu, s = teksty strony."""
    bledy = sprawdz(e)
    if bledy:
        raise BladDanych('\n'.join(bledy))
    od, _ = parsuj_godziny(e['time'])
    nazwa = e['name']
    lockup_n, lockup_s = (nazwa[:-len('Speed Dating')].strip(), 'Speed Dating') \
        if nazwa.endswith('Speed Dating') else (nazwa, '')
    temat_rez = 'Lista rezerwowa %s %s %s' % (nazwa, data_krotka(e['date']), od)
    temat_zap = 'Zapis na %s %s %s' % (nazwa, data_krotka(e['date']), od)
    wartosci = {
        'tytul': '%s · %s, %s · %s' % (nazwa, e['date'], od, miasto(e)),
        'opisMeta': '%s, %s, %s, %s, %s. Poziom %s, wiek %d–%d, %s.' % (
            nazwa, e['date'], e['time'], e['venue'], e['address'],
            (e.get('level') or '').lower(), e['ageMin'], e['ageMax'], sklad_slownie(e)),
        'opisOg': '%s %s, wiek %d–%d, poziom %s.' % (
            s.get('opis') or '', e['venue'], e['ageMin'], e['ageMax'], (e.get('level') or '').lower()),
        'kolor': s.get('kolor') or '#7d8f68',
        'klasaBody': s.get('klasaBody') or 'ev',
        'page': e['page'],
        'id': e['id'],
        'city': miasto(e),
        'lockupN': lockup_n, 'lockupS': lockup_s,
        'name': nazwa, 'date': e['date'], 'time': e['time'],
        'age': '%d–%d' % (e['ageMin'], e['ageMax']),
        'ageMin': e['ageMin'], 'ageMax': e['ageMax'],
        'venue': e['venue'], 'ulica': ulica(e['address']),
        'blik': e['blik'],
        'skladSlownie': sklad_slownie(e),
        'limitWomen': e['limitWomen'], 'limitMen': e['limitMen'],
        'dataKrotka': data_krotka(e['date']), 'start': od,
        'formularzPoziom': s.get('formularzPoziom') or 'poziom gry',
        'poziomPytanie': s.get('poziomPytanie') or 'Poziom gry',
        'poziomPodpowiedz': s.get('poziomPodpowiedz') or '',
        'tematRezerwowa': quote(temat_rez), 'tematZapis': quote(temat_zap),
        'mapa': html.escape(quote_plus('%s %s' % (e['venue'], e['address']))),
    }
    surowe = {
        'lead': tekst_inline(s.get('lead')),
        'jsonld': _jsonld(e, s),
        'daneStrony': json.dumps(s, ensure_ascii=False, indent=2).replace('</', '<\\/'),
        'tablica': _tablica(e, s),
        'wCenie': ''.join(LI % tekst_inline(x) for x in (s.get('wCenie') or [])),
        'wezZeSoba': ''.join(LI % tekst_inline(x) for x in (s.get('wezZeSoba') or [])),
        'kolumny': _kolumny(s),
        'dojazd': tekst_inline(s.get('dojazd')),
        'transit': _transit(e, s),
        'faq': _faq(s),
        'poziomOpcje': _opcje(s),
    }
    if not s.get('poziomOpcje'):
        raise BladDanych('Formularz potrzebuje co najmniej jednej opcji poziomu gry.')

    t = _sekcje(szablon.replace('\r\n', '\n'), {
        'sprzedaz': not archiwum, 'archiwum': archiwum,
        'poziomPodpowiedz': bool(wartosci['poziomPodpowiedz']),
    })
    t = re.sub(r'\{\{\{(\w+)\}\}\}', lambda m: surowe[m.group(1)], t)
    t = re.sub(r'\{\{(\w+)\}\}', lambda m: html.escape(str(wartosci[m.group(1)])), t)
    # znaczniki sekcji w osobnych liniach zostawiaja po sobie puste wiersze
    return re.sub(r'\n[ \t]*\n(?:[ \t]*\n)+', '\n\n', t)


def dane_ze_strony(tekst):
    """Teksty strony zapisane przez aplikacje, albo None dla stron
    robionych recznie (padel 3.10 i starsze)."""
    m = re.search(r'<script type="application/json" id="mp-strona">\s*(.*?)\s*</script>', tekst, re.S)
    if not m:
        return None
    return json.loads(m.group(1).replace('<\\/', '</'))


def archiwizuj_reczna(tekst, e):
    """Strona zrobiona recznie, bez danych dla szablonu: wycinamy z niej
    zapisy tak samo, jak robilismy to z 20.09 — baner na gorze, krotkie
    hero, bez formularza i bez skryptu zapisow."""
    t = tekst.replace('\r\n', '\n')
    if 'class="notice"' in t:
        return t
    t = re.sub(r'<script type="application/ld\+json">.*?</script>\n?', '', t, count=1, flags=re.S)
    baner = ('<div class="notice">\n  <div class="wrap">\n'
             '    <span><b>To wydarzenie już się odbyło.</b> Odbyło się %s w&nbsp;%s.</span>\n'
             '    <a href="index.html#terminy">Zobacz najbliższy termin</a>\n  </div>\n</div>\n'
             % (html.escape(e['date']), html.escape(e['venue'])))
    t = re.sub(r'(<body[^>]*>\n)', lambda m: m.group(1) + baner, t, count=1)
    t = t.replace('<header class="hero">', '<header class="hero hero--short">', 1)
    t = re.sub(r'<a class="cta" href="#zapisy"[^>]*>.*?</a>\s*<p class="cta-note"[^>]*>.*?</p>',
               '<a class="cta" href="index.html#terminy">Najbliższe wydarzenie <span class="arw" aria-hidden="true">→</span></a>',
               t, count=1, flags=re.S)
    t = re.sub(r'<!-- =+ ZAPISY =+ -->.*?(?=<!-- =+ FAQ =+ -->)', '', t, count=1, flags=re.S)
    t = re.sub(r'(<script src="znak.js"></script>\n)<script>\n\(function\(\)\{.*?\}\)\(\);\n</script>\n',
               r'\1', t, count=1, flags=re.S)
    return t


# ------------------------------------------------------------ index.html

def _karta(e, presety):
    p = presety.get(e.get('sport'), {})
    uwaga = (e.get('cardNote') or '').strip()
    wiek = 'Wiek %d–%d.' % (e['ageMin'], e['ageMax'])
    dopisek = (uwaga + ' ' + wiek) if uwaga else wiek
    return ('      <a class="%s" href="%s">\n'
            '        <span class="kicker">%s · %s</span>\n'
            '        <h3>%s</h3>\n'
            '        <span class="when"><small>%s · %s</small>%s</span>\n'
            '        <p class="where">\n'
            '          %s, %s<br>\n'
            '          %s\n'
            '        </p>\n'
            '        <span class="spacer"></span>\n'
            '        <span class="free" data-free="%s">Zapisy otwarte</span>\n'
            '        <span class="card-go">Zapisz się →</span>\n'
            '      </a>\n') % (
        p.get('klasaKarty', 'card'), html.escape(e['page']),
        html.escape(e['sport']), html.escape(miasto(e)),
        html.escape(e['name']).replace('Speed Dating', 'Speed&nbsp;Dating'),
        html.escape(e['weekday']), html.escape(e['time']), html.escape(e['date']),
        html.escape(e['venue']), nbsp_ostatnia(ulica(e['address'])),
        html.escape(dopisek), html.escape(e['id']))


def _fixture(p):
    gdzie = p.get('venue', '')
    if p.get('note'):
        gdzie += '. ' + p['note']
    return ('      <a class="fixture fixture--past" href="%s">\n'
            '        <span class="when"><small>%s</small>%s</span>\n'
            '        <span class="what">\n'
            '          %s\n'
            '          <span class="where">%s</span>\n'
            '        </span>\n'
            '        <span class="go">\n'
            '          <span class="free">Zakończone</span>\n'
            '          <span class="arw" aria-hidden="true">→</span>\n'
            '        </span>\n'
            '      </a>\n') % (
        html.escape(p['page']), html.escape(p.get('weekday', '')), html.escape(p['date']),
        html.escape(p['name']), html.escape(gdzie))


def _podmien_blok(tekst, od, do, nowe, plik):
    a, b = _blok(tekst, od, do, plik)
    a_konec = tekst.index('-->', a) + 3
    return tekst[:a_konec] + '\n' + nowe + '      ' + tekst[b:]


def pisz_index(tekst, dane, presety):
    t = tekst.replace('\r\n', '\n')
    upcoming = sorted(dane['upcoming'], key=klucz_czasu)
    past = sorted(dane['past'], key=klucz_czasu, reverse=True)
    t = _podmien_blok(t, ZNACZNIK_KARTY_OD, ZNACZNIK_KARTY_DO,
                      '\n'.join(_karta(e, presety) for e in upcoming), 'index.html')
    t = _podmien_blok(t, ZNACZNIK_ARCH_OD, ZNACZNIK_ARCH_DO,
                      ''.join(_fixture(p) for p in past), 'index.html')
    return t


# ------------------------------------------------------------ sitemap.xml

def pisz_sitemap(dane):
    wpisy = [('', 'weekly', '1.0')]
    wpisy += [(e['page'], 'daily', '0.9') for e in sorted(dane['upcoming'], key=klucz_czasu)]
    wpisy += [(p['page'], 'yearly', '0.2') for p in sorted(dane['past'], key=klucz_czasu, reverse=True)]
    wpisy += [('regulamin.html', 'yearly', '0.3')]
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for adres, freq, prio in wpisy:
        xml += ('  <url>\n    <loc>%s/%s</loc>\n    <changefreq>%s</changefreq>\n'
                '    <priority>%s</priority>\n  </url>\n') % (SITE, adres, freq, prio)
    return xml + '</urlset>\n'


# ------------------------------------------------------------ operacje

def nowe_wydarzenie(presety, sport):
    """Pusty wpis z podpowiedziami dla danej dyscypliny."""
    p = presety[sport]
    e = {
        'id': '', 'name': p['name'], 'sport': sport, 'city': 'Warszawa',
        'date': '', 'weekday': '', 'time': '', 'venue': '', 'address': '',
        'age': '', 'ageMin': 25, 'ageMax': 35, 'level': p.get('level', ''),
        'surface': p.get('surface', ''), 'shoes': p.get('shoes', ''), 'transport': '',
        'bring': p.get('bring', ''), 'bringExtra': p.get('bringExtra', ''),
        'included': p.get('included', ''), 'cardNote': p.get('cardNote', ''),
        'priceW': 0, 'priceM': 0, 'page': '', 'sheetTab': '', 'formUrl': '',
        'blik': '731 210 703', 'limitWomen': 6, 'limitMen': 6,
        'soldOutWomen': False, 'soldOutMen': False,
    }
    s = json.loads(json.dumps(p['strona']))
    s['kolor'] = p['kolor']
    s['klasaBody'] = p['klasaBody']
    return e, s


def uzupelnij(e, dane, presety, nowe):
    """Pola, ktore wynikaja z innych: dzien tygodnia, 'age', id i nazwa
    pliku. Przy edycji id i pliku nie ruszamy — zmiana nazwy pliku
    zerwalaby linki wyslane juz ludziom."""
    e = dict(e)
    e['time'] = normalizuj_godziny(e['time'])
    e['date'] = parsuj_date(e['date']).strftime('%d.%m.%Y')
    e['weekday'] = dzien_tygodnia(e['date'])
    e['age'] = '%d–%d' % (e['ageMin'], e['ageMax'])
    if not str(e.get('sheetTab') or '').strip():
        e['sheetTab'] = data_krotka(e['date'])
    if nowe:
        wszystkie = dane['upcoming'] + dane['past']
        preset = presety[e['sport']]
        e['id'] = id_wydarzenia(preset, e, {x.get('id') for x in wszystkie})
        e['page'] = plik_strony(preset, e, {x.get('page') for x in wszystkie})
    return e


def przenies_do_archiwum(dane, id_):
    e = next((x for x in dane['upcoming'] if x['id'] == id_), None)
    if not e:
        raise BladDanych('Nie ma wydarzenia %s w sprzedazy.' % id_)
    dane = {'upcoming': [x for x in dane['upcoming'] if x['id'] != id_],
            'past': list(dane['past'])}
    venue = e['venue'] if e['venue'].endswith(miasto(e)) else e['venue'] + ', ' + miasto(e)
    dane['past'].append({'name': e['name'], 'sport': e['sport'], 'date': e['date'],
                         'weekday': e['weekday'], 'venue': venue, 'note': '', 'page': e['page']})
    return dane, e
