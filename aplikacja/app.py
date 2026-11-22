# -*- coding: utf-8 -*-
"""MatchPoint Wydarzenia — okienko do dodawania i zmieniania wydarzen.

Uruchomienie ze zrodel:   python app.py
Tryb lokalny (dla nas):   python app.py --lokalnie "C:/sciezka/do/repo"
Plik exe buduje zbuduj.bat.

Skroty (opisane tez w INSTRUKCJA.html):
  okno glowne   Ctrl+F szukaj, Ctrl+N nowe, Enter zmien zaznaczone, F5 odswiez
  wydarzenie    Ctrl+F szukaj w polach, Enter / F3 nastepne trafienie,
                Shift+Enter poprzednie, Esc przejdz do znalezionego pola,
                Ctrl+Z / Ctrl+Y cofnij / ponow w dluzszych polach
"""
import json
import os
import queue
import sys
import tempfile
import threading
import tkinter as tk
import traceback
import webbrowser
from tkinter import font as tkfont, messagebox, ttk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generator as g   # noqa: E402
import operacje as op   # noqa: E402
import zrodla as zr     # noqa: E402

NAZWA = 'MatchPoint Wydarzenia'
USTAWIENIA = os.path.join(os.environ.get('APPDATA') or os.path.expanduser('~'),
                          'MatchPointWydarzenia', 'ustawienia.json')
ENDPOINT = ('https://script.google.com/macros/s/AKfycbxHiSMEiB8geAq8-VjcQl7IBm7bf51cIs0aPKPMzSSBKMot'
            '_BZZ7wFtDK5AXcAxIul4UQ/exec')
# pliki, bez ktorych podglad strony nie wyglada jak strona
ZASOBY = ['styles.css', 'znak.js', 'analytics.js', 'favicon.svg', 'icon-ball-arrow.svg']

SZARY = '#6b6f66'
ZIELEN = '#55634a'
ZOLTY = '#fff1a6'        # wszystkie trafienia wyszukiwania
POMARANCZ = '#ffbf69'    # trafienie, na ktorym stoimy

# Ile pikseli ekranu na "piksel projektu". Ustawia Aplikacja po starcie.
SKALA = 1.0


def px(n):
    return int(round(n * SKALA))


def ostry_ekran():
    """Bez tego Windows przy skalowaniu 125-150% rozciaga okno jak
    obrazek i caly tekst jest rozmyty. Czcionki Tk przelicza wtedy sam,
    wymiary w pikselach przeliczamy my (px)."""
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:  # noqa: BLE001 - starszy Windows albo nie Windows
        pass


def czytaj_ustawienia():
    try:
        with open(USTAWIENIA, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def zapisz_ustawienia(u):
    os.makedirs(os.path.dirname(USTAWIENIA), exist_ok=True)
    with open(USTAWIENIA, 'w', encoding='utf-8') as f:
        json.dump(u, f, ensure_ascii=False, indent=2)


_BEZ_OGONKOW = str.maketrans('ąćęłńóśźż', 'acelnoszz')


def normalizuj(t):
    """Do szukania: bez wielkosci liter i bez polskich znakow, zeby
    "dziala" znalazlo "działa". Zamiana idzie znak za znak, wiec pozycja
    trafienia jest ta sama w oryginale i po normalizacji."""
    return ''.join(c.lower() if len(c.lower()) == 1 else c for c in str(t)).translate(_BEZ_OGONKOW)


def indeks_tk(tekst, i):
    """Pozycja znaku dla Tk. Tk liczy emoji (🎾, ❤️) jako dwa znaki,
    Python jako jeden — bez poprawki podswietlenie za emoji sie przesuwa."""
    return '1.0 + %d chars' % (i + sum(1 for c in tekst[:i] if ord(c) > 0xFFFF))


def nie_skrot(e):
    """AltGr to dla Windows Ctrl+Alt. Gdy klawisz daje literę (ś, ż, ń),
    to pisanie, a nie skrot — nie przechwytujemy go."""
    return bool(e.char) and e.char.isprintable()


# ---------------------------------------------------------------- pola

# (klucz, etykieta, rodzaj, podpowiedz[, kolumny dla 'para'])
# Klucz '#' to naglowek grupy: (#, tytul, '', opis grupy).
POLA_PODSTAWOWE = [
    ('#', 'Wydarzenie', '', ''),
    ('sport', 'Dyscyplina', 'sport', 'Przy nowym wydarzeniu zmiana dyscypliny podpowiada jej teksty.'),
    ('name', 'Nazwa wydarzenia', 'tekst', 'np. Tennis Speed Dating'),
    ('date', 'Data', 'tekst', 'DD.MM.RRRR, np. 18.10.2026. Dzień tygodnia dopisze się sam.'),
    ('time', 'Godziny', 'tekst', 'OD-DO, np. 17:00-19:30'),
    ('#', 'Miejsce', '', ''),
    ('venue', 'Nazwa miejsca', 'tekst', 'np. WTS Orzeł'),
    ('address', 'Adres', 'tekst', 'ulica z numerem, miasto — np. Podskarbińska 14, Warszawa'),
    ('city', 'Miasto', 'tekst', ''),
    ('#', 'Dla kogo', '', ''),
    ('ageMin', 'Wiek od', 'liczba', 'formularz nie przyjmie nikogo młodszego'),
    ('ageMax', 'Wiek do', 'liczba', 'ani starszego'),
    ('level', 'Poziom', 'tekst', 'np. Początkujący+'),
    ('#', 'Ceny i miejsca', '', ''),
    ('priceW', 'Cena — kobiety (zł)', 'liczba', ''),
    ('priceM', 'Cena — mężczyźni (zł)', 'liczba', 'ta sama kwota = na stronie jedna pozycja "Cena"'),
    ('limitWomen', 'Miejsca — kobiety', 'liczba', 'liczone po OPŁACONYCH'),
    ('limitMen', 'Miejsca — mężczyźni', 'liczba', ''),
    ('soldOutWomen', 'Zamknij pulę kobiet', 'tak', 'ręcznie, niezależnie od arkusza'),
    ('soldOutMen', 'Zamknij pulę mężczyzn', 'tak', ''),
    ('#', 'Zapisy i płatność', '', ''),
    ('sheetTab', 'Zakładka w arkuszu', 'tekst', 'dokładnie jak nazwa zakładki, np. 18.10. Puste = data.'),
    ('blik', 'Numer BLIK', 'tekst', ''),
]
POLA_MAIL = [
    ('#', 'Mail z potwierdzeniem', '',
     'Idzie do uczestnika po wpisaniu TAK w arkuszu. Sekcję „Jak to działa” wpisujesz '
     'w zakładce 3 — ten sam tekst jest na stronie i w mailu.'),
    ('surface', 'Nawierzchnia', 'tekst', 'np. mączka — w mailu "Kort: …" i na stronie'),
    ('shoes', 'Obuwie', 'tekst', ''),
    ('included', 'W cenie', 'tekst', 'np. Kort i piłki.'),
    ('bring', 'Co zabrać', 'tekst', ''),
    ('bringExtra', 'Dopisek do "co zabrać"', 'tekst', 'puste = linii nie ma w mailu'),
    ('transport', 'Dojazd', 'tekst', 'puste = linii nie ma w mailu'),
    ('#', 'Karta na stronie głównej', '', ''),
    ('cardNote', 'Dopisek na karcie', 'tekst', 'wiek dopisze się sam'),
]
OPIS_JAK = ('Ten sam tekst idzie do maila z potwierdzeniem (w mailu bez serduszek). '
            'Pod nim strona sama dopisuje kroki zapisu: formularz, BLIK, potwierdzenie.')
POLE_JAK = ('howItWorks', 'Tekst', 'dlugi', 'Enter = nowa linia. Puste = tekst domyślny.')
# Teksty strony w kolejnosci, w jakiej stoja na stronie wydarzenia.
POLA_STRONY = [
    ('#', 'Góra strony', '', ''),
    ('lead', 'Zdanie pod tytułem', 'dlugi', ''),
    ('opis', 'Opis dla Google i Facebooka', 'dlugi', '1–2 zdania; na samej stronie go nie widać'),
    ('#', 'Szczegóły', '', ''),
    ('nawierzchniaOpis', 'Nawierzchnia — dopisek', 'tekst', 'np. kort ziemny'),
    ('poziomOpis', 'Poziom — dopisek', 'tekst', 'np. po kilku razach na korcie'),
    ('wCenie', 'W cenie', 'lista', 'jedna pozycja w linii; **tak** = pogrubienie'),
    ('wezZeSoba', 'Weź ze sobą', 'lista', 'jedna pozycja w linii'),
    ('#', 'Dlaczego warto', '', 'Trzy punkty na ciemnym tle, pod hasłem „Będzie match na korcie”.'),
    ('kolumny', 'Punkty', 'para', '', ('Tytuł', 'Tekst')),
    ('#', 'Jak to działa', '', OPIS_JAK),
    POLE_JAK,
    ('formularzPoziom', 'Krok 1 — o co pytamy', 'tekst', 'dokończenie zdania "Imię, …, kontakt i …"'),
    ('#', 'Jak dotrzeć', '', ''),
    ('dojazd', 'Tekst nad tabelką', 'dlugi', 'adres e-mail zamieni się w link'),
    ('transit', 'Tabelka', 'para',
     'Adres dopisze się sam jako pierwszy wiersz. Bez etykiety = tekst na całą szerokość.',
     ('Etykieta (krótko)', 'Treść')),
    ('#', 'Formularz zapisu', '', ''),
    ('poziomPytanie', 'Pytanie o poziom', 'tekst', ''),
    ('poziomOpcje', 'Odpowiedzi do wyboru', 'lista', 'jedna w linii; nie dodawaj "pierwszy raz"'),
    ('poziomPodpowiedz', 'Podpowiedź pod pytaniem', 'tekst', 'może być puste'),
    ('#', 'Pytania (FAQ)', '',
     'Pytania o płatność, rezygnację i dane osobowe strona ma zawsze — tu dopisujesz własne.'),
    ('faq', 'Pytania', 'para', '', ('Pytanie', 'Odpowiedź')),
]
# Dla stron sprzed aplikacji: tekstow strony nie ruszamy, ale "Jak to
# dziala" siedzi w configu i trafia do maila, wiec da sie je zmienic.
POLA_TYLKO_JAK = [('#', 'Jak to działa (mail)', '', 'Ten tekst trafia do maila z potwierdzeniem.'), POLE_JAK]


class PoleTekstowe(tk.Text):
    """Pole na dluzszy tekst. Rosnie razem z trescia, wiec nie trzeba go
    przewijac w srodku (kolko myszy przewija cale okno). Ma Ctrl+Z,
    a Tab przechodzi do nastepnego pola zamiast wstawiac tabulator."""

    def __init__(self, rodzic, min_linii=2, width=70):
        super().__init__(rodzic, height=min_linii, width=width, wrap='word', undo=True, maxundo=-1,
                         font='TkTextFont', relief='flat', borderwidth=0, highlightthickness=1,
                         highlightcolor='#7d8f68', highlightbackground='#b9b6ad', padx=6, pady=4)
        self.min_linii = min_linii
        self.tag_configure('trafienie', background=ZOLTY)
        self.tag_configure('biezace', background=POMARANCZ)
        self.tag_raise('biezace')
        self.bind('<<Modified>>', self._zmiana)
        self.bind('<Configure>', lambda e: self.after_idle(self.dopasuj))
        self.bind('<Tab>', lambda e: self._skocz(e.widget.tk_focusNext()))
        self.bind('<Shift-Tab>', lambda e: self._skocz(e.widget.tk_focusPrev()))
        # "ż" to AltGr+Z, a AltGr Windows zglasza jako Ctrl+Alt. Gdyby Tk
        # wzial to za Ctrl+Z, zamiast litery cofnalby tekst — wtedy
        # wstawiamy litere sami i nie puszczamy zdarzenia dalej.
        self.bind('<Control-Key-z>', self._litera_zamiast_skrotu)
        self.bind('<Control-Key-y>', self._litera_zamiast_skrotu)

    def _litera_zamiast_skrotu(self, e):
        if nie_skrot(e):
            self.insert('insert', e.char)
            return 'break'
        return None

    @staticmethod
    def _skocz(w):
        if w is not None:
            w.focus_set()
        return 'break'

    def _zmiana(self, _):
        if self.edit_modified():
            self.edit_modified(False)
            self.dopasuj()

    def dopasuj(self):
        try:
            n = self.count('1.0', 'end', 'displaylines')
        except tk.TclError:
            return
        n = (n[0] if isinstance(n, tuple) else n) or 1
        h = max(self.min_linii, min(n, 40))
        if h != int(self.cget('height')):
            self.configure(height=h)

    def tekst(self):
        return self.get('1.0', 'end-1c')

    def ustaw(self, t):
        self.delete('1.0', 'end')
        self.insert('1.0', t or '')
        self.edit_reset()
        self.dopasuj()


class EdytorPar(ttk.Frame):
    """Lista par (pytanie i odpowiedz, etykieta i tresc): kazda para to
    wiersz z dwoma polami, plus przyciski w gore / w dol / usun.
    Zastepuje dawne "lewa | prawa" w jednej linii — kto wpisywal zwykly
    tekst, musial dokladac kreske, i tak trafila ona na strone 28.11."""

    def __init__(self, rodzic, kolumny, przy_zmianie=None):
        super().__init__(rodzic)
        self.kolumny = kolumny
        self.przy_zmianie = przy_zmianie
        self.wiersze = []
        self.ramka = ttk.Frame(self)
        self.ramka.pack(fill='x')
        self.ramka.columnconfigure(1, weight=1)
        ttk.Label(self.ramka, text=kolumny[0], foreground=SZARY).grid(row=0, column=0, sticky='w')
        ttk.Label(self.ramka, text=kolumny[1], foreground=SZARY).grid(row=0, column=1, sticky='w', padx=(8, 0))
        ttk.Button(self, text='+ Dodaj wiersz', command=self._nowy).pack(anchor='w', pady=(6, 0))

    def _nowy(self):
        self.dodaj()
        self.wiersze[-1]['lewa'].focus_set()
        self._zmienione()

    def _zmienione(self):
        if self.przy_zmianie:
            self.przy_zmianie()

    def dodaj(self, a='', b=''):
        r = len(self.wiersze) + 1
        lewa = ttk.Entry(self.ramka, width=22)
        lewa.insert(0, a)
        prawa = PoleTekstowe(self.ramka, min_linii=1, width=48)
        prawa.ustaw(b)
        przyc = ttk.Frame(self.ramka)
        w = {'lewa': lewa, 'prawa': prawa, 'przyc': przyc}
        for znak, ruch, opis in (('↑', -1, 'wyżej'), ('↓', 1, 'niżej'), ('✕', 0, 'usuń')):
            b_ = ttk.Button(przyc, text=znak, width=3, takefocus=False,
                            command=lambda ruch=ruch: self.usun(w) if ruch == 0 else self.przesun(w, ruch))
            b_.pack(side='left', padx=(0 if znak == '↑' else 2, 0))
        lewa.grid(row=r, column=0, sticky='new', pady=(4, 0))
        prawa.grid(row=r, column=1, sticky='we', padx=(8, 0), pady=(4, 0))
        przyc.grid(row=r, column=2, sticky='n', padx=(6, 0), pady=(4, 0))
        self.wiersze.append(w)

    def _surowe(self):
        return [[w['lewa'].get(), w['prawa'].tekst()] for w in self.wiersze]

    def ustaw(self, pary):
        for w in self.wiersze:
            for x in w.values():
                x.destroy()
        self.wiersze = []
        for x in pary or []:
            a, b = (list(x) + ['', ''])[:2]
            self.dodaj(a, b)
        if not self.wiersze:
            self.dodaj()

    def pobierz(self):
        return [[a.strip(), b.strip()] for a, b in self._surowe() if a.strip() or b.strip()]

    def przesun(self, w, o):
        i = self.wiersze.index(w)
        j = i + o
        if not 0 <= j < len(self.wiersze):
            return
        d = self._surowe()
        d[i], d[j] = d[j], d[i]
        self.ustaw(d)
        self.wiersze[j]['lewa'].focus_set()
        self._zmienione()

    def usun(self, w):
        if (w['lewa'].get().strip() or w['prawa'].tekst().strip()) and not messagebox.askyesno(
                NAZWA, 'Usunąć ten wiersz?\n\n%s' % (w['lewa'].get() or w['prawa'].tekst())[:80], parent=self):
            return
        d = self._surowe()
        del d[self.wiersze.index(w)]
        self.ustaw(d)
        self._zmienione()


class Element:
    """Jedno miejsce do wpisywania, tak jak widzi je wyszukiwarka."""

    def __init__(self, widget, etykieta, nazwa, tekst, formularz):
        self.widget = widget          # Entry, Text, Checkbutton, Combobox
        self.etykieta = etykieta      # tk.Label z nazwa pola (podswietlamy)
        self.nazwa = nazwa            # po czym szukamy samego pola ('' = nie szukamy)
        self.tekst = tekst            # funkcja -> aktualna tresc
        self.formularz = formularz


class Formularz(ttk.Frame):
    """Siatka pol z naglowkami grup, etykietami i podpowiedziami.
    Zwraca i przyjmuje slownik w formacie configu / tekstow strony."""

    def __init__(self, rodzic, pola, sporty=None, przy_zmianie_sportu=None, przy_zmianie=None):
        super().__init__(rodzic, padding=(px(16), px(4), px(16), px(16)))
        self.pola = [p for p in pola if p[0] != '#']
        self.w, self.widzety, self.etykiety, self.grupy = {}, {}, {}, {}
        self.columnconfigure(1, weight=1)
        r, grupa = 0, ''
        for p in pola:
            k, et, rodzaj, podp = p[:4]
            if k == '#':
                grupa = et
                ramka = ttk.Frame(self)
                ramka.grid(row=r, column=0, columnspan=2, sticky='we', pady=(px(18) if r else px(6), px(2)))
                ttk.Label(ramka, text=et, style='Grupa.TLabel').pack(anchor='w')
                if podp:
                    ttk.Label(ramka, text=podp, foreground=SZARY, wraplength=px(760),
                              justify='left').pack(anchor='w', pady=(px(2), 0))
                ttk.Separator(ramka).pack(fill='x', pady=(px(5), 0))
                r += 1
                continue
            lab = tk.Label(self, text=et, anchor='w', justify='left', padx=px(3))
            lab.tlo = lab.cget('background')
            lab.grid(row=r, column=0, sticky='nw', padx=(0, px(12)), pady=(px(9), 0))
            if rodzaj == 'sport':
                v = tk.StringVar()
                wid = ttk.Combobox(self, textvariable=v, values=sporty or [], state='readonly', width=20)
                if przy_zmianie_sportu:
                    wid.bind('<<ComboboxSelected>>', lambda ev, v=v: przy_zmianie_sportu(v.get()))
                self.w[k] = v
            elif rodzaj == 'tak':
                v = tk.BooleanVar()
                wid = ttk.Checkbutton(self, variable=v)
                self.w[k] = v
            elif rodzaj in ('lista', 'dlugi'):
                wid = PoleTekstowe(self, min_linii=3 if rodzaj == 'lista' else 2)
                self.w[k] = wid
            elif rodzaj == 'para':
                wid = EdytorPar(self, p[4], przy_zmianie=przy_zmianie)
                self.w[k] = wid
            else:
                v = tk.StringVar()
                wid = ttk.Entry(self, textvariable=v, width=60 if rodzaj == 'tekst' else 10)
                self.w[k] = v
            self.widzety[k], self.etykiety[k], self.grupy[k] = wid, lab, grupa
            wid.grid(row=r, column=1, sticky='w' if rodzaj in ('liczba', 'tak', 'sport') else 'we',
                     pady=(px(8), 0))
            r += 1
            if podp:
                ttk.Label(self, text=podp, foreground=SZARY, wraplength=px(640),
                          justify='left').grid(row=r, column=1, sticky='w', pady=(px(1), 0))
                r += 1

    def ustaw(self, dane):
        for p in self.pola:
            k, _, rodzaj = p[:3]
            w, v = self.w[k], dane.get(k)
            if rodzaj == 'lista':
                w.ustaw('\n'.join(v or []))
            elif rodzaj == 'dlugi':
                w.ustaw(v or '')
            elif rodzaj == 'para':
                w.ustaw(v or [])
            elif rodzaj == 'tak':
                w.set(bool(v))
            else:
                w.set('' if v is None else str(v))

    def pobierz(self):
        """Zwraca (dane, bledy)."""
        dane, bledy = {}, []
        for p in self.pola:
            k, et, rodzaj = p[:3]
            w = self.w[k]
            if rodzaj == 'lista':
                dane[k] = [x.strip() for x in w.tekst().split('\n') if x.strip()]
            elif rodzaj == 'dlugi':
                dane[k] = w.tekst().strip()
            elif rodzaj == 'para':
                dane[k] = w.pobierz()
            elif rodzaj == 'tak':
                dane[k] = bool(w.get())
            elif rodzaj == 'liczba':
                t = w.get().strip()
                try:
                    dane[k] = int(t)
                except ValueError:
                    bledy.append('%s: wpisz liczbę całkowitą (jest "%s").' % (et, t))
            else:
                dane[k] = w.get().strip()
        return dane, bledy

    def elementy(self):
        """Pola dla wyszukiwarki, w kolejnosci z ekranu. Nazwa pola to
        jego etykieta razem z tytulem grupy i kluczem: "jak to dziala"
        ma znalezc pole "Tekst" w grupie "Jak to dziala", a "dojazd"
        pole dojazdu na stronie, ktore na ekranie nazywa sie inaczej."""
        wynik = []
        for p in self.pola:
            k, et, rodzaj = p[:3]
            w, lab = self.widzety[k], self.etykiety[k]
            nazwa = ' '.join((self.grupy[k], et, k))
            if rodzaj == 'para':
                for i, x in enumerate(w.wiersze):
                    wynik.append(Element(x['lewa'], lab, nazwa if i == 0 else '', x['lewa'].get, self))
                    wynik.append(Element(x['prawa'], lab, '', x['prawa'].tekst, self))
            elif rodzaj in ('lista', 'dlugi'):
                wynik.append(Element(w, lab, nazwa, w.tekst, self))
            elif rodzaj == 'tak':
                wynik.append(Element(w, lab, nazwa, lambda: '', self))
            else:
                wynik.append(Element(w, lab, nazwa, lambda v=self.w[k]: str(v.get()), self))
        return wynik


def przewijane(rodzic):
    """Ramka z paskiem przewijania — formularze nie mieszcza sie na
    malym ekranie laptopa. Kolkiem myszy przewija Aplikacja._kolko."""
    zew = ttk.Frame(rodzic)
    plotno = tk.Canvas(zew, highlightthickness=0, yscrollincrement=px(24))
    plotno.przewijane = True
    pasek = ttk.Scrollbar(zew, orient='vertical', command=plotno.yview)
    wew = ttk.Frame(plotno)
    wew.bind('<Configure>', lambda e: plotno.configure(scrollregion=plotno.bbox('all')))
    okno = plotno.create_window((0, 0), window=wew, anchor='nw')
    plotno.bind('<Configure>', lambda e: plotno.itemconfigure(okno, width=e.width))
    plotno.configure(yscrollcommand=pasek.set)
    plotno.pack(side='left', fill='both', expand=True)
    pasek.pack(side='right', fill='y')
    return zew, wew, plotno


# ---------------------------------------------------------------- aplikacja

class Aplikacja(tk.Tk):
    def __init__(self, lokalnie=None):
        super().__init__()
        global SKALA
        SKALA = self.winfo_fpixels('1i') / 96.0
        self.title(NAZWA)
        self.geometry('%dx%d' % (px(1060), px(700)))
        self.minsize(px(820), px(520))
        self.lokalnie = lokalnie
        self.ustawienia = czytaj_ustawienia()
        self.kolejka = queue.Queue()
        self.dane = {'upcoming': [], 'past': []}
        self.presety = {}
        self._styl()
        # Jedno kolko myszy na cala aplikacje: przewija to, co jest pod
        # kursorem. Wczesniej kazda zakladka podpinala wlasne i kolko
        # przewijalo naraz wszystkie formularze, tez te niewidoczne.
        self.bind_all('<MouseWheel>', self._kolko, add='+')
        # Kolko nad lista "Dyscyplina" zmienialo dyscypline, a to
        # podmienia wszystkie teksty nowego wydarzenia.
        self.bind_class('TCombobox', '<MouseWheel>', lambda e: (self._kolko(e), 'break')[1])
        self.after(100, self._odbierz)
        self._zbuduj()
        if not lokalnie and not self.ustawienia.get('token'):
            self.after(200, self.okno_ustawien)
        else:
            self.after(200, self.odswiez)

    def _styl(self):
        styl = ttk.Style(self)
        try:
            styl.theme_use('vista')
        except tk.TclError:
            pass
        for nazwa in ('TkDefaultFont', 'TkTextFont', 'TkMenuFont', 'TkHeadingFont'):
            try:
                tkfont.nametofont(nazwa).configure(family='Segoe UI', size=10)
            except tk.TclError:
                pass
        styl.configure('Treeview', rowheight=px(26))
        styl.configure('Treeview.Heading', font=('Segoe UI', 10, 'bold'))
        styl.configure('Grupa.TLabel', font=('Segoe UI', 12, 'bold'), foreground=ZIELEN)
        styl.configure('Tytul.TLabel', font=('Segoe UI', 15, 'bold'), foreground=ZIELEN)
        styl.configure('Sekcja.TLabel', font=('Segoe UI', 11, 'bold'))
        styl.configure('Wazny.TButton', font=('Segoe UI', 10, 'bold'))

    def _kolko(self, e):
        try:
            w = self.winfo_containing(e.x_root, e.y_root)
        except (KeyError, tk.TclError):
            return
        while w is not None:
            if getattr(w, 'przewijane', False):
                kroki = int(-e.delta / 120) or (-1 if e.delta > 0 else 1)
                w.yview_scroll(kroki * 2, 'units')
                return
            w = w.master

    # ---- praca w tle: siec nie zamraza okna
    def w_tle(self, opis, praca, gotowe):
        self.status.set(opis + '…')
        self.config(cursor='watch')

        def watek():
            try:
                wynik = praca()
                self.kolejka.put((gotowe, wynik, None))
            except Exception as e:  # noqa: BLE001 - kazdy blad ma dojsc do okienka
                traceback.print_exc()
                self.kolejka.put((gotowe, None, e))
        threading.Thread(target=watek, daemon=True).start()

    def _odbierz(self):
        try:
            while True:
                gotowe, wynik, blad = self.kolejka.get_nowait()
                self.config(cursor='')
                self.status.set('')
                if blad is not None:
                    messagebox.showerror(NAZWA, str(blad) or blad.__class__.__name__)
                else:
                    gotowe(wynik)
        except queue.Empty:
            pass
        self.after(100, self._odbierz)

    def zrodlo(self):
        if self.lokalnie:
            return zr.LokalneZrodlo(self.lokalnie)
        u = self.ustawienia
        return zr.GitHubZrodlo(u.get('token'), u.get('repo') or 'wsolore/matchpoint',
                               u.get('galaz') or 'main')

    # ---- widok glowny
    def _zbuduj(self):
        gora = ttk.Frame(self, padding=(px(14), px(12), px(14), px(6)))
        gora.pack(fill='x')
        ttk.Label(gora, text=NAZWA, style='Tytul.TLabel').pack(side='left')
        ttk.Button(gora, text='Ustawienia', command=self.okno_ustawien).pack(side='right')
        ttk.Button(gora, text='Odśwież (F5)', command=self.odswiez).pack(side='right', padx=px(6))
        ttk.Button(gora, text='Otwórz stronę', command=lambda: webbrowser.open(g.SITE)).pack(side='right')

        self.status = tk.StringVar()
        ttk.Label(self, textvariable=self.status, padding=(px(14), px(5)), foreground=SZARY).pack(
            fill='x', side='bottom')

        srodek = ttk.Frame(self, padding=(px(14), 0, px(14), px(4)))
        srodek.pack(fill='both', expand=True)

        szuk = ttk.Frame(srodek)
        szuk.pack(fill='x', pady=(px(2), px(10)))
        ttk.Label(szuk, text='Szukaj:').pack(side='left')
        self.filtr = tk.StringVar()
        self.filtr_pole = ttk.Entry(szuk, textvariable=self.filtr, width=36)
        self.filtr_pole.pack(side='left', padx=px(6))
        ttk.Label(szuk, text='data, nazwa, miejsce…  (Ctrl+F)', foreground=SZARY).pack(side='left')
        self.filtr.trace_add('write', lambda *a: self.pokaz_liste())
        self.filtr_pole.bind('<Escape>', lambda e: self.filtr.set(''))
        self.filtr_pole.bind('<Down>', lambda e: self._do_listy())
        self.filtr_pole.bind('<Return>', lambda e: self._do_listy())

        ttk.Label(srodek, text='W sprzedaży', style='Sekcja.TLabel').pack(anchor='w')
        kol = ('data', 'godz', 'nazwa', 'miejsce', 'ceny', 'zakladka', 'pule')
        ramka_listy = ttk.Frame(srodek)
        ramka_listy.pack(fill='both', expand=True, pady=(px(4), px(6)))
        self.lista = ttk.Treeview(ramka_listy, columns=kol, show='headings', height=8, selectmode='browse')
        for k, t, s in (('data', 'Data', 95), ('godz', 'Godziny', 100), ('nazwa', 'Wydarzenie', 180),
                        ('miejsce', 'Miejsce', 190), ('ceny', 'Ceny K / M', 95),
                        ('zakladka', 'Zakładka', 90), ('pule', 'Zamknięte pule', 115)):
            self.lista.heading(k, text=t)
            self.lista.column(k, width=px(s), anchor='w')
        self.lista.tag_configure('minelo', foreground='#b00')
        pasek = ttk.Scrollbar(ramka_listy, orient='vertical', command=self.lista.yview)
        self.lista.configure(yscrollcommand=pasek.set)
        self.lista.pack(side='left', fill='both', expand=True)
        pasek.pack(side='right', fill='y')
        self.lista.bind('<Double-1>', lambda e: self.edytuj())
        self.lista.bind('<Return>', lambda e: self.edytuj())

        przyciski = ttk.Frame(srodek)
        przyciski.pack(fill='x')
        ttk.Button(przyciski, text='+ Nowe wydarzenie', style='Wazny.TButton',
                   command=self.nowe).pack(side='left')
        ttk.Button(przyciski, text='Zmień zaznaczone', command=self.edytuj).pack(side='left', padx=px(6))
        ttk.Button(przyciski, text='Strona wydarzenia', command=self.otworz_zaznaczone).pack(side='left')
        ttk.Button(przyciski, text='Sprawdź zakładkę w arkuszu',
                   command=self.sprawdz_zakladke).pack(side='left', padx=px(6))
        # Na prawym brzegu, z dala od reszty: tego nie da sie cofnac.
        ttk.Button(przyciski, text='Przenieś do archiwum', command=self.archiwizuj).pack(side='right')

        ttk.Label(srodek, text='Archiwum  ·  dwuklik otwiera stronę', style='Sekcja.TLabel').pack(
            anchor='w', pady=(px(18), 0))
        self.archiwum = tk.Listbox(srodek, height=6, relief='flat', activestyle='none',
                                   highlightthickness=1, highlightbackground='#d9d6cc',
                                   selectbackground='#dfe6d6', selectforeground='black')
        self.archiwum.pack(fill='x', pady=(px(4), px(8)))
        self.archiwum.bind('<Double-1>', lambda e: self.otworz_archiwalne())
        self.archiwum.bind('<Return>', lambda e: self.otworz_archiwalne())
        self._strony_archiwum = []

        self.bind('<Control-f>', self._skrot(self._do_szukania))
        self.bind('<Control-F>', self._skrot(self._do_szukania))
        self.bind('<Control-n>', self._skrot(self.nowe))
        self.bind('<Control-N>', self._skrot(self.nowe))
        self.bind('<F5>', lambda e: self.odswiez())

    @staticmethod
    def _skrot(f):
        def h(e):
            if nie_skrot(e):
                return None
            f()
            return 'break'
        return h

    def _do_szukania(self):
        self.filtr_pole.focus_set()
        self.filtr_pole.select_range(0, 'end')

    def _do_listy(self):
        dzieci = self.lista.get_children()
        if dzieci:
            self.lista.focus_set()
            if not self.lista.selection():
                self.lista.selection_set(dzieci[0])
            self.lista.focus(self.lista.selection()[0])
        return 'break'

    def odswiez(self):
        zrodlo = self.zrodlo()

        def praca():
            czytaj = zrodlo.migawka()
            return op.stan(czytaj), op.presety(czytaj)

        def gotowe(w):
            self.dane, self.presety = w
            self.pokaz_liste()
            minione = ['%s %s' % (e['date'][:5], e['time'][:5])
                       for e in sorted(self.dane['upcoming'], key=g.klucz_czasu) if g.minelo(e)]
            # Strona chowa minione terminy sama, ale formularz na stronie
            # wydarzenia zdejmuje dopiero archiwum — stad przypomnienie.
            if minione:
                self.status.set('Już się odbyło, przenieś do archiwum: ' + ', '.join(minione))
            else:
                self.status.set('Wczytano: ' + zrodlo.opis())
        self.w_tle('Wczytuję wydarzenia', praca, gotowe)

    def pokaz_liste(self):
        q = normalizuj(self.filtr.get().strip())

        def pasuje(*pola):
            return not q or q in normalizuj(' '.join(str(x) for x in pola))

        zaznaczone = self.lista.selection()
        self.lista.delete(*self.lista.get_children())
        for e in sorted(self.dane['upcoming'], key=g.klucz_czasu):
            if not pasuje(e.get('date'), e.get('weekday'), e.get('time'), e.get('name'), e.get('sport'),
                          e.get('venue'), e.get('address'), e.get('sheetTab')):
                continue
            pule = ', '.join(x for x, z in (('K', e.get('soldOutWomen')), ('M', e.get('soldOutMen'))) if z) or '—'
            self.lista.insert('', 'end', iid=e['id'], tags=('minelo',) if g.minelo(e) else (), values=(
                e['date'], e['time'], e['name'], e['venue'], '%s / %s' % (e['priceW'], e['priceM']),
                e['sheetTab'], pule))
        dzieci = self.lista.get_children()
        if zaznaczone and zaznaczone[0] in dzieci:
            self.lista.selection_set(zaznaczone[0])
        elif dzieci:
            self.lista.selection_set(dzieci[0])
        self.archiwum.delete(0, 'end')
        self._strony_archiwum = []
        for p in sorted(self.dane['past'], key=g.klucz_czasu, reverse=True):
            if pasuje(p.get('date'), p.get('name'), p.get('venue'), p.get('note')):
                # note to np. "Godz. 15:00." — bez niego dwa sloty jednego
                # dnia wygladaja na liscie jak ten sam wpis dwa razy
                self.archiwum.insert('end', '  %s   %s   %s   %s' % (
                    p['date'], p['name'], p['venue'], p.get('note') or ''))
                self._strony_archiwum.append(p.get('page'))

    def zaznaczone(self):
        sel = self.lista.selection()
        if not sel:
            messagebox.showinfo(NAZWA, 'Najpierw kliknij wydarzenie na liście.')
            return None
        return next(e for e in self.dane['upcoming'] if e['id'] == sel[0])

    # ---- akcje
    def nowe(self):
        if not self.presety:
            messagebox.showinfo(NAZWA, 'Najpierw wczytaj wydarzenia (Odśwież).')
            return
        sport = 'Tenis' if 'Tenis' in self.presety else list(self.presety)[0]
        e, s = g.nowe_wydarzenie(self.presety, sport)
        OknoWydarzenia(self, e, s, nowe=True)

    def edytuj(self):
        e = self.zaznaczone()
        if not e:
            return
        zrodlo = self.zrodlo()
        self.w_tle('Wczytuję stronę wydarzenia',
                   lambda: op.teksty_strony(zrodlo.migawka(), e),
                   lambda s: OknoWydarzenia(self, e, s, nowe=False))

    def otworz_zaznaczone(self):
        e = self.zaznaczone()
        if e:
            webbrowser.open('%s/%s' % (g.SITE, e['page']))

    def otworz_archiwalne(self):
        sel = self.archiwum.curselection()
        if sel and self._strony_archiwum[sel[0]]:
            webbrowser.open('%s/%s' % (g.SITE, self._strony_archiwum[sel[0]]))

    def archiwizuj(self):
        e = self.zaznaczone()
        if not e:
            return
        if not messagebox.askyesno(NAZWA, 'Przenieść "%s %s, %s" do archiwum?\n\n'
                                   'Karta zniknie ze strony głównej i trafi do "Za nami", '
                                   'a ze strony wydarzenia zniknie formularz zapisów.\n'
                                   'Rób to dopiero po wydarzeniu.' % (e['name'], e['date'], e['time']),
                                   icon='warning'):
            return
        zrodlo = self.zrodlo()
        self.w_tle('Przenoszę do archiwum',
                   lambda: zr.wykonaj(zrodlo, lambda cz: op.archiwizuj(cz, e['id']),
                                      'Archiwum: %s %s (aplikacja)' % (e['name'], e['date'])),
                   lambda w: (messagebox.showinfo(NAZWA, 'Gotowe. Strona odświeży się za około minutę.'),
                              self.odswiez()))

    def sprawdz_zakladke(self):
        e = self.zaznaczone()
        if not e:
            return

        def gotowe(w):
            ok, d = w
            if ok:
                messagebox.showinfo(NAZWA, 'Zakładka "%s" działa.\n\nOpłacone: kobiety %s, mężczyźni %s.\n'
                                    'Lista rezerwowa: %s osób.' % (d.get('tab'), d.get('womenPaid'),
                                                                   d.get('menPaid'), d.get('reserve')))
            else:
                messagebox.showwarning(NAZWA, 'Zakładka "%s" nie odpowiada:\n\n%s' % (e['sheetTab'], d))
        self.w_tle('Pytam arkusz', lambda: zr.stan_zakladki(ENDPOINT, e['sheetTab']), gotowe)

    def okno_ustawien(self):
        OknoUstawien(self)


class OknoUstawien(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title('Ustawienia')
        self.resizable(False, False)
        self.transient(app)
        f = ttk.Frame(self, padding=px(16))
        f.pack()
        u = app.ustawienia
        self.token = tk.StringVar(value=u.get('token', ''))
        self.repo = tk.StringVar(value=u.get('repo', 'wsolore/matchpoint'))
        ttk.Label(f, text='Token GitHub').grid(row=0, column=0, sticky='w', padx=(0, px(10)))
        pole = ttk.Entry(f, textvariable=self.token, width=60, show='•')
        pole.grid(row=0, column=1, pady=px(4))
        ttk.Label(f, text='Repozytorium').grid(row=1, column=0, sticky='w', padx=(0, px(10)))
        ttk.Entry(f, textvariable=self.repo, width=60).grid(row=1, column=1, pady=px(4))
        ttk.Label(f, text='Token dostajesz od osoby, która prowadzi stronę (instrukcja, punkt 1).\n'
                          'Zapisuje się tylko na tym komputerze.', foreground=SZARY).grid(row=2, column=1, sticky='w')
        ttk.Button(f, text='Zapisz', style='Wazny.TButton', command=self.zapisz).grid(
            row=3, column=1, sticky='e', pady=(px(12), 0))
        self.bind('<Return>', lambda e: self.zapisz())
        self.bind('<Escape>', lambda e: self.destroy())
        pole.focus_set()

    def zapisz(self):
        self.app.ustawienia.update(token=self.token.get().strip(), repo=self.repo.get().strip())
        zapisz_ustawienia(self.app.ustawienia)
        self.destroy()
        self.app.odswiez()


class OknoWydarzenia(tk.Toplevel):
    def __init__(self, app, e, s, nowe):
        super().__init__(app)
        self.app, self.nowe = app, nowe
        self.reczna = s is None
        self.e_start = dict(e)
        self.title('Nowe wydarzenie' if nowe else 'Zmiana: %s %s' % (e['name'], e['date']))
        szer = min(px(1000), self.winfo_screenwidth() - px(40))
        wys = min(px(780), self.winfo_screenheight() - px(80))
        self.geometry('%dx%d' % (szer, wys))
        self.trafienia, self.ktore = [], -1
        self._podswietlone = set()

        # Kolejnosc pack: dol i pasek szukania przed zakladkami, zeby przy
        # malym oknie to zakladki sie kurczyly, a nie przyciski.
        self._pasek_szukania().pack(fill='x', side='top')
        dol = ttk.Frame(self, padding=(px(10), px(4), px(10), px(10)))
        dol.pack(fill='x', side='bottom')
        ttk.Button(dol, text='Anuluj', command=self.zamknij).pack(side='right')
        ttk.Button(dol, text='Opublikuj', style='Wazny.TButton', command=self.opublikuj).pack(
            side='right', padx=px(6))
        ttk.Button(dol, text='Podgląd w przeglądarce', command=self.podglad).pack(side='right')
        ttk.Label(dol, text='Najpierw podgląd, potem publikacja — publikacja zmienia prawdziwą stronę.',
                  foreground=SZARY).pack(side='left')

        self.zakl = ttk.Notebook(self)
        self.zakl.pack(fill='both', expand=True, padx=px(10), pady=(px(6), px(4)))
        przy_zmianie = lambda: self.after_idle(self._szukaj_znowu)  # noqa: E731

        self.f_podst = self._zakladka('1. Termin, miejsce, ceny', POLA_PODSTAWOWE, sporty=list(app.presety),
                                      przy_zmianie_sportu=self.zmiana_sportu if nowe else None)
        self.f_mail = self._zakladka('2. Mail do uczestnika', POLA_MAIL)
        if self.reczna:
            self.f_strona = self._zakladka('3. Teksty na stronie', POLA_TYLKO_JAK, przy_zmianie=przy_zmianie,
                                           uwaga=(
                'Ta strona powstała ręcznie, przed aplikacją, więc jej tekstów nie da się tu zmienić. '
                'Ceny, limity, zamknięcie puli i treść maili zmienisz normalnie w zakładkach 1 i 2 — '
                'strona czyta je z konfiguracji. Liczby wypisane w samym tekście strony (np. tabelka '
                '"Szczegóły") zostaną stare, więc przy zmianie ceny daj nam znać.'))
        else:
            self.f_strona = self._zakladka('3. Teksty na stronie', POLA_STRONY, przy_zmianie=przy_zmianie)
        self.formularze = [self.f_podst, self.f_mail, self.f_strona]

        self.f_podst.ustaw(e)
        self.f_mail.ustaw(e)
        self.s_start = s or {}
        self.f_strona.ustaw(dict(self.s_start, howItWorks=e.get('howItWorks', '')))
        if not nowe:
            # dyscypliny i nazwy pliku nie zmieniamy: link juz poszedl w swiat
            self.f_podst.widzety['sport'].configure(state='disabled')

        self.bind('<Control-f>', self._skrot_szukaj)
        self.bind('<Control-F>', self._skrot_szukaj)
        self.bind('<F3>', lambda e: self.nastepne(1))
        self.bind('<Shift-F3>', lambda e: self.nastepne(-1))
        self.protocol('WM_DELETE_WINDOW', self.zamknij)
        self._start = self._migawka()

    def _zakladka(self, tytul, pola, uwaga=None, **kw):
        zew, wew, plotno = przewijane(self.zakl)
        if uwaga:
            ttk.Label(wew, text=uwaga, wraplength=px(760), justify='left',
                      padding=(px(16), px(12), px(16), 0)).pack(anchor='w')
        f = Formularz(wew, pola, **kw)
        f.pack(fill='x')
        f.zakladka, f.wew, f.plotno = zew, wew, plotno
        self.zakl.add(zew, text=tytul)
        return f

    # ---- szukanie (Ctrl+F)
    def _pasek_szukania(self):
        pasek = ttk.Frame(self, padding=(px(12), px(10), px(12), 0))
        ttk.Label(pasek, text='Szukaj w polach:').pack(side='left')
        self.q = tk.StringVar()
        self.q_pole = ttk.Entry(pasek, textvariable=self.q, width=34)
        self.q_pole.pack(side='left', padx=px(6))
        ttk.Button(pasek, text='▲', width=3, takefocus=False, command=lambda: self.nastepne(-1)).pack(side='left')
        ttk.Button(pasek, text='▼', width=3, takefocus=False, command=lambda: self.nastepne(1)).pack(
            side='left', padx=(px(2), 0))
        self.q_wynik = ttk.Label(pasek, foreground=SZARY, width=16)
        self.q_wynik.pack(side='left', padx=px(8))
        ttk.Label(pasek, text='Ctrl+F  ·  Enter następne  ·  Esc do pola', foreground=SZARY).pack(side='right')
        self.q.trace_add('write', lambda *a: self.szukaj())
        self.q_pole.bind('<Return>', lambda e: self.nastepne(1))
        self.q_pole.bind('<Shift-Return>', lambda e: self.nastepne(-1))
        self.q_pole.bind('<Escape>', self.do_pola)
        return pasek

    def _skrot_szukaj(self, e):
        if nie_skrot(e):
            return None
        self.q_pole.focus_set()
        self.q_pole.select_range(0, 'end')
        return 'break'

    def _elementy(self):
        return [el for f in self.formularze for el in f.elementy()]

    def _wyczysc(self):
        for w in self._podswietlone:
            try:
                if isinstance(w, tk.Text):
                    w.tag_remove('trafienie', '1.0', 'end')
                    w.tag_remove('biezace', '1.0', 'end')
                else:
                    w.configure(background=w.tlo)
            except tk.TclError:
                pass   # wiersz tabelki usuniety w miedzyczasie
        self._podswietlone = set()

    def _szukaj_znowu(self):
        if self.q.get().strip():
            self.szukaj(zostan=True)

    def szukaj(self, zostan=False):
        """Wszystkie trafienia naraz na zolto, biezace na pomaranczowo —
        jak Ctrl+F w przegladarce. Szuka w nazwach pol i w ich tresci."""
        self._wyczysc()
        q = normalizuj(self.q.get().strip())
        stare = self.ktore
        self.trafienia, self.ktore = [], -1
        if not q:
            self.q_wynik.configure(text='')
            return
        for el in self._elementy():
            przed = len(self.trafienia)
            if el.nazwa and q in normalizuj(el.nazwa):
                self.trafienia.append((el, None))
            tekst = el.tekst()
            n = normalizuj(tekst)
            i = n.find(q)
            while i >= 0:
                self.trafienia.append((el, (indeks_tk(tekst, i), indeks_tk(tekst, i + len(q)))))
                if isinstance(el.widget, tk.Text):
                    el.widget.tag_add('trafienie', *self.trafienia[-1][1])
                    self._podswietlone.add(el.widget)
                i = n.find(q, i + len(q))
            if len(self.trafienia) > przed:
                el.etykieta.configure(background=ZOLTY)
                self._podswietlone.add(el.etykieta)
        if not self.trafienia:
            self.q_wynik.configure(text='nie ma', foreground='#b00')
            return
        self.ktore = min(max(stare, 0), len(self.trafienia) - 1) if zostan else 0
        self.pokaz()

    def nastepne(self, kierunek):
        if not self.trafienia:
            if self.q.get().strip():
                self.bell()
            return 'break'
        self.ktore = (self.ktore + kierunek) % len(self.trafienia)
        self.pokaz()
        return 'break'

    def pokaz(self):
        for w in self._podswietlone:
            try:
                if isinstance(w, tk.Text):
                    w.tag_remove('biezace', '1.0', 'end')
                elif w.cget('background') == POMARANCZ:
                    w.configure(background=ZOLTY)
            except tk.TclError:
                pass
        el, zakres = self.trafienia[self.ktore]
        self.q_wynik.configure(text='%d z %d' % (self.ktore + 1, len(self.trafienia)), foreground=SZARY)
        try:
            self.zakl.select(el.formularz.zakladka)
            el.etykieta.configure(background=POMARANCZ)
            self.update_idletasks()
            y = 0
            if zakres and isinstance(el.widget, tk.Text):
                el.widget.tag_add('biezace', *zakres)
                ramka = el.widget.bbox(zakres[0])
                y = ramka[1] if ramka else 0
            self._przewin_do(el, y)
        except tk.TclError:
            self.szukaj()   # pole zniknelo (usuniety wiersz) — liczymy od nowa

    def _przewin_do(self, el, y_w_polu=0):
        f = el.formularz
        y = el.widget.winfo_rooty() - f.wew.winfo_rooty() + y_w_polu
        calosc = max(1, f.wew.winfo_height())
        widok = f.plotno.winfo_height()
        gora = f.plotno.canvasy(0)
        if y < gora + px(10) or y > gora + widok - px(70):
            f.plotno.yview_moveto(max(0.0, (y - widok / 3.0) / calosc))

    def do_pola(self, _=None):
        """Esc w polu szukania: kursor laduje w znalezionym miejscu."""
        if not self.trafienia or self.ktore < 0:
            return 'break'
        el, zakres = self.trafienia[self.ktore]
        try:
            el.widget.focus_set()
            if isinstance(el.widget, tk.Text):
                el.widget.mark_set('insert', zakres[0] if zakres else '1.0')
                el.widget.see('insert')
            elif isinstance(el.widget, ttk.Entry) and zakres:
                a = int(zakres[0].split()[2])
                b = int(zakres[1].split()[2])
                el.widget.icursor(b)
                el.widget.select_range(a, b)
        except tk.TclError:
            pass
        return 'break'

    # ---- zamykanie bez publikacji
    def _migawka(self):
        try:
            return json.dumps([f.pobierz()[0] for f in self.formularze], ensure_ascii=False, sort_keys=True)
        except Exception:  # noqa: BLE001
            return None

    def zamknij(self):
        if self._start is not None and self._migawka() != self._start:
            if not messagebox.askyesno(NAZWA, 'Zmiany w tym oknie nie są opublikowane.\n\n'
                                       'Zamknąć okno i je porzucić?', icon='warning', parent=self):
                return
        self.destroy()

    def zmiana_sportu(self, sport):
        e, s = g.nowe_wydarzenie(self.app.presety, sport)
        biezace, _ = self.f_podst.pobierz()
        # to, co czlowiek juz wpisal o terminie i miejscu, zostaje
        for k in ('date', 'time', 'venue', 'address', 'city', 'ageMin', 'ageMax', 'priceW', 'priceM',
                  'limitWomen', 'limitMen', 'sheetTab', 'blik'):
            if k in biezace:
                e[k] = biezace[k]
        self.f_podst.ustaw(e)
        self.f_mail.ustaw(e)
        self.f_strona.ustaw(dict(s, howItWorks=e.get('howItWorks', '')))
        self.s_start = s
        self._szukaj_znowu()

    def zbierz(self):
        e1, b1 = self.f_podst.pobierz()
        e2, b2 = self.f_mail.pobierz()
        s3, b3 = self.f_strona.pobierz()
        bledy = b1 + b2 + b3
        e = dict(self.e_start)
        e.update(e1)
        e.update(e2)
        # "Jak to dziala" stoi w zakladce stron, ale zapisuje sie w configu:
        # stamtad bierze je tez mail z potwierdzeniem.
        e['howItWorks'] = s3.pop('howItWorks', '')
        # Podpowiedz obiecuje "puste = data", a sprawdz() wymaga zakladki,
        # wiec bez tego puste pole konczylo sie bledem.
        if not e.get('sheetTab'):
            try:
                e['sheetTab'] = g.data_krotka(e.get('date'))
            except g.BladDanych:
                pass   # zla date i tak zglosi sprawdz()
        s = None
        if not self.reczna:
            s = dict(self.s_start)
            s.update(s3)
            preset = self.app.presety.get(e['sport'], {})
            s.setdefault('kolor', preset.get('kolor'))
            s.setdefault('klasaBody', preset.get('klasaBody'))
        if not bledy:
            try:
                bledy = g.sprawdz(dict(e, weekday='', age=''))
            except Exception as err:  # noqa: BLE001
                bledy = [str(err)]
        if bledy:
            messagebox.showerror(NAZWA, 'Popraw, proszę:\n\n• ' + '\n• '.join(bledy), parent=self)
            return None
        return e, s

    def operacja(self, e, s):
        if self.nowe:
            return lambda cz: op.dodaj(cz, e, s)
        return lambda cz: op.zmien(cz, e, s)

    def podglad(self):
        z = self.zbierz()
        if not z:
            return
        e, s = z
        zrodlo = self.app.zrodlo()
        oper = self.operacja(e, s)

        def praca():
            czytaj = zrodlo.migawka()
            pliki, wynik = oper(czytaj)
            kat = tempfile.mkdtemp(prefix='matchpoint-podglad-')
            for p in ZASOBY:
                bajty = czytaj.bajty(p) if hasattr(czytaj, 'bajty') else zrodlo.czytaj_bajty(p)
                with open(os.path.join(kat, p), 'wb') as f:
                    f.write(bajty)
            for p, t in pliki.items():
                with open(os.path.join(kat, p), 'w', encoding='utf-8') as f:
                    f.write(t)
            return os.path.join(kat, wynik['page'])
        self.app.w_tle('Składam podgląd', praca, lambda sciezka: webbrowser.open('file:///' + sciezka.replace('\\', '/')))

    def opublikuj(self):
        z = self.zbierz()
        if not z:
            return
        e, s = z
        zrodlo = self.app.zrodlo()
        oper = self.operacja(e, s)
        opis = ('Nowe wydarzenie: ' if self.nowe else 'Zmiana wydarzenia: ') + \
            '%s %s %s (aplikacja)' % (e['name'], e['date'], e['time'])

        def sprawdz_i_publikuj():
            ok, info = zr.stan_zakladki(ENDPOINT, e.get('sheetTab') or g.data_krotka(e['date']))
            return ok, info

        def po_sprawdzeniu(w):
            ok, info = w
            tab = e.get('sheetTab') or g.data_krotka(e['date'])
            if not ok:
                if not messagebox.askyesno(NAZWA, (
                        'Arkusz nie widzi zakładki "%s":\n%s\n\n'
                        'Bez niej zapisy na stronie NIE zadziałają. Załóż ją z szablonu '
                        '(instrukcja, punkt 2) i opublikuj jeszcze raz.\n\n'
                        'Opublikować mimo to?') % (tab, info), icon='warning', parent=self):
                    return
            if not messagebox.askyesno(NAZWA, 'Opublikować na matchpointdate.pl?\n\n%s\n%s, %s\n%s\n'
                                       'Ceny: %s / %s zł, miejsca %s + %s' % (
                                           e['name'], e['date'], e['time'], e['venue'],
                                           e['priceW'], e['priceM'], e['limitWomen'], e['limitMen']),
                                       parent=self):
                return
            self.app.w_tle('Publikuję', lambda: zr.wykonaj(zrodlo, oper, opis), po_publikacji)

        def po_publikacji(w):
            _, wynik = w
            messagebox.showinfo(NAZWA, 'Opublikowane.\n\nStrona będzie widoczna za około minutę:\n%s/%s'
                                % (g.SITE, wynik['page']), parent=self)
            self.destroy()
            self.app.odswiez()

        self.app.w_tle('Sprawdzam zakładkę w arkuszu', sprawdz_i_publikuj, po_sprawdzeniu)


def main():
    lokalnie = None
    if '--lokalnie' in sys.argv:
        lokalnie = sys.argv[sys.argv.index('--lokalnie') + 1]
    ostry_ekran()
    Aplikacja(lokalnie).mainloop()


if __name__ == '__main__':
    main()
