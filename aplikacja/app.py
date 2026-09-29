# -*- coding: utf-8 -*-
"""MatchPoint Wydarzenia — okienko do dodawania i zmieniania wydarzen.

Uruchomienie ze zrodel:   python app.py
Tryb lokalny (dla nas):   python app.py --lokalnie "C:/sciezka/do/repo"
Plik exe buduje zbuduj.bat.
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
from tkinter import messagebox, ttk

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


# ---------------------------------------------------------------- pola

# (klucz, etykieta, rodzaj, podpowiedz)
POLA_PODSTAWOWE = [
    ('sport', 'Dyscyplina', 'sport', 'Zmiana przy nowym wydarzeniu podpowiada teksty tej dyscypliny.'),
    ('name', 'Nazwa wydarzenia', 'tekst', 'np. Tennis Speed Dating'),
    ('date', 'Data', 'tekst', 'DD.MM.RRRR, np. 18.10.2026. Dzień tygodnia dopisze się sam.'),
    ('time', 'Godziny', 'tekst', 'OD-DO, np. 17:00-19:30'),
    ('venue', 'Miejsce', 'tekst', 'np. WTS Orzeł'),
    ('address', 'Adres', 'tekst', 'ulica z numerem, miasto — np. Podskarbińska 14, Warszawa'),
    ('city', 'Miasto', 'tekst', ''),
    ('ageMin', 'Wiek od', 'liczba', 'formularz nie przyjmie nikogo młodszego'),
    ('ageMax', 'Wiek do', 'liczba', 'ani starszego'),
    ('level', 'Poziom', 'tekst', 'np. Początkujący+'),
    ('priceW', 'Cena — kobiety (zł)', 'liczba', ''),
    ('priceM', 'Cena — mężczyźni (zł)', 'liczba', 'ta sama kwota = na stronie jedna pozycja "Cena"'),
    ('limitWomen', 'Miejsca — kobiety', 'liczba', 'liczone po OPŁACONYCH'),
    ('limitMen', 'Miejsca — mężczyźni', 'liczba', ''),
    ('soldOutWomen', 'Zamknij pulę kobiet', 'tak', 'ręcznie, niezależnie od arkusza'),
    ('soldOutMen', 'Zamknij pulę mężczyzn', 'tak', ''),
    ('sheetTab', 'Zakładka w arkuszu', 'tekst', 'dokładnie jak nazwa zakładki, np. 18.10. Puste = data.'),
    ('blik', 'Numer BLIK', 'tekst', ''),
]
POLA_MAIL = [
    ('surface', 'Nawierzchnia', 'tekst', 'np. mączka — w mailu "Kort: …" i na stronie'),
    ('shoes', 'Obuwie', 'tekst', ''),
    ('included', 'W cenie (mail)', 'tekst', 'np. Kort i piłki.'),
    ('bring', 'Co zabrać (mail)', 'tekst', ''),
    ('bringExtra', 'Dopisek do "co zabrać"', 'tekst', 'puste = linii nie ma w mailu'),
    ('transport', 'Dojazd (mail)', 'tekst', 'puste = linii nie ma w mailu'),
    ('cardNote', 'Dopisek na karcie', 'tekst', 'na stronie głównej; wiek dopisze się sam'),
]
# (klucz, etykieta, rodzaj, podpowiedz); lista = jedna pozycja w linii,
# para = "lewa | prawa" w linii
POLA_STRONY = [
    ('lead', 'Zdanie pod tytułem', 'dlugi', ''),
    ('opis', 'Opis dla Google i Facebooka', 'dlugi', '1–2 zdania'),
    ('nawierzchniaOpis', 'Nawierzchnia — dopisek', 'tekst', 'np. kort ziemny'),
    ('poziomOpis', 'Poziom — dopisek', 'tekst', 'np. po kilku razach na korcie'),
    ('wCenie', 'W cenie', 'lista', 'jedna pozycja w linii; **tak** = pogrubienie'),
    ('wezZeSoba', 'Weź ze sobą', 'lista', 'jedna pozycja w linii'),
    ('kolumny', 'Dlaczego warto (3 punkty)', 'para', 'Tytuł | tekst — jeden punkt w linii'),
    ('formularzPoziom', 'Krok 1 — o co pytamy', 'tekst', 'dokończenie zdania "Imię, …, kontakt i …"'),
    ('poziomPytanie', 'Pytanie o poziom', 'tekst', ''),
    ('poziomOpcje', 'Odpowiedzi do wyboru', 'lista', 'jedna w linii; nie dodawaj "pierwszy raz"'),
    ('poziomPodpowiedz', 'Podpowiedź pod pytaniem', 'tekst', 'może być puste'),
    ('dojazd', 'Jak dotrzeć — tekst', 'dlugi', 'adres e-mail zamieni się w link'),
    ('transit', 'Jak dotrzeć — tabelka', 'para', 'Etykieta | wartość; adres dopisze się sam'),
    ('faq', 'Pytania (FAQ)', 'para', 'Pytanie | odpowiedź — jedno w linii. Płatność, rezygnacja, dane są zawsze.'),
]


class Formularz(ttk.Frame):
    """Siatka pol z etykietami i podpowiedziami. Zwraca i przyjmuje
    slownik w formacie configu / tekstow strony."""

    def __init__(self, rodzic, pola, sporty=None, przy_zmianie_sportu=None):
        super().__init__(rodzic, padding=12)
        self.pola = pola
        self.w = {}
        self.columnconfigure(1, weight=1)
        for i, (k, et, rodzaj, podp) in enumerate(pola):
            ttk.Label(self, text=et).grid(row=i * 2, column=0, sticky='nw', padx=(0, 10), pady=(6, 0))
            if rodzaj == 'sport':
                v = tk.StringVar()
                wid = ttk.Combobox(self, textvariable=v, values=sporty or [], state='readonly', width=20)
                if przy_zmianie_sportu:
                    wid.bind('<<ComboboxSelected>>', lambda ev: przy_zmianie_sportu(self.w['sport'].get()))
                self.w[k] = v
            elif rodzaj == 'tak':
                v = tk.BooleanVar()
                wid = ttk.Checkbutton(self, variable=v)
                self.w[k] = v
            elif rodzaj in ('lista', 'para', 'dlugi'):
                wid = tk.Text(self, height=4 if rodzaj != 'dlugi' else 3, width=70, wrap='word',
                              font=('Segoe UI', 10), relief='solid', borderwidth=1)
                self.w[k] = wid
            else:
                v = tk.StringVar()
                wid = ttk.Entry(self, textvariable=v, width=60 if rodzaj == 'tekst' else 10)
                self.w[k] = v
            wid.grid(row=i * 2, column=1, sticky='we' if rodzaj not in ('liczba', 'tak', 'sport') else 'w',
                     pady=(6, 0))
            if podp:
                ttk.Label(self, text=podp, foreground='#777').grid(row=i * 2 + 1, column=1, sticky='w')

    def ustaw(self, dane):
        for k, _, rodzaj, _ in self.pola:
            w = self.w[k]
            v = dane.get(k)
            if rodzaj in ('lista', 'para', 'dlugi'):
                if rodzaj == 'lista':
                    tekst = '\n'.join(v or [])
                elif rodzaj == 'para':
                    tekst = '\n'.join(' | '.join(x) for x in (v or []))
                else:
                    tekst = v or ''
                w.delete('1.0', 'end')
                w.insert('1.0', tekst)
            elif rodzaj == 'tak':
                w.set(bool(v))
            else:
                w.set('' if v is None else str(v))

    def pobierz(self):
        """Zwraca (dane, bledy)."""
        dane, bledy = {}, []
        for k, et, rodzaj, _ in self.pola:
            w = self.w[k]
            if rodzaj in ('lista', 'para', 'dlugi'):
                tekst = w.get('1.0', 'end').strip()
                linie = [x.strip() for x in tekst.split('\n') if x.strip()]
                if rodzaj == 'lista':
                    dane[k] = linie
                elif rodzaj == 'para':
                    pary = []
                    for x in linie:
                        if '|' not in x:
                            bledy.append('%s: w linii "%s" brakuje kreski | między częściami.' % (et, x[:40]))
                            continue
                        a, b = x.split('|', 1)
                        pary.append([a.strip(), b.strip()])
                    dane[k] = pary
                else:
                    dane[k] = tekst
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


def przewijane(rodzic):
    """Ramka z paskiem przewijania — formularze nie mieszcza sie na
    malym ekranie laptopa."""
    zew = ttk.Frame(rodzic)
    plotno = tk.Canvas(zew, highlightthickness=0)
    pasek = ttk.Scrollbar(zew, orient='vertical', command=plotno.yview)
    wew = ttk.Frame(plotno)
    wew.bind('<Configure>', lambda e: plotno.configure(scrollregion=plotno.bbox('all')))
    okno = plotno.create_window((0, 0), window=wew, anchor='nw')
    plotno.bind('<Configure>', lambda e: plotno.itemconfigure(okno, width=e.width))
    plotno.configure(yscrollcommand=pasek.set)
    plotno.pack(side='left', fill='both', expand=True)
    pasek.pack(side='right', fill='y')

    def kolko(e):
        # Text przewija sie sam; reszta okna przewija plotno
        if not isinstance(e.widget, tk.Text):
            plotno.yview_scroll(int(-e.delta / 120), 'units')
    zew.bind_all('<MouseWheel>', kolko, add='+')
    return zew, wew


# ---------------------------------------------------------------- aplikacja

class Aplikacja(tk.Tk):
    def __init__(self, lokalnie=None):
        super().__init__()
        self.title(NAZWA)
        self.geometry('980x640')
        self.minsize(820, 520)
        self.lokalnie = lokalnie
        self.ustawienia = czytaj_ustawienia()
        self.kolejka = queue.Queue()
        self.dane = {'upcoming': [], 'past': []}
        self.presety = {}
        self.after(100, self._odbierz)
        self._zbuduj()
        if not lokalnie and not self.ustawienia.get('token'):
            self.after(200, self.okno_ustawien)
        else:
            self.after(200, self.odswiez)

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
        styl = ttk.Style(self)
        try:
            styl.theme_use('vista')
        except tk.TclError:
            pass
        gora = ttk.Frame(self, padding=(12, 10))
        gora.pack(fill='x')
        ttk.Label(gora, text=NAZWA, font=('Segoe UI', 14, 'bold')).pack(side='left')
        ttk.Button(gora, text='Ustawienia', command=self.okno_ustawien).pack(side='right')
        ttk.Button(gora, text='Odśwież', command=self.odswiez).pack(side='right', padx=6)
        ttk.Button(gora, text='Otwórz stronę', command=lambda: webbrowser.open(g.SITE)).pack(side='right')

        srodek = ttk.Frame(self, padding=(12, 0))
        srodek.pack(fill='both', expand=True)

        ttk.Label(srodek, text='W sprzedaży', font=('Segoe UI', 11, 'bold')).pack(anchor='w')
        kol = ('data', 'godz', 'nazwa', 'miejsce', 'ceny', 'zakladka', 'pule')
        self.lista = ttk.Treeview(srodek, columns=kol, show='headings', height=8, selectmode='browse')
        for k, t, s in (('data', 'Data', 90), ('godz', 'Godziny', 95), ('nazwa', 'Wydarzenie', 180),
                        ('miejsce', 'Miejsce', 170), ('ceny', 'Ceny K / M', 90),
                        ('zakladka', 'Zakładka', 90), ('pule', 'Zamknięte pule', 110)):
            self.lista.heading(k, text=t)
            self.lista.column(k, width=s, anchor='w')
        self.lista.pack(fill='both', expand=True, pady=(4, 6))
        self.lista.bind('<Double-1>', lambda e: self.edytuj())

        przyciski = ttk.Frame(srodek)
        przyciski.pack(fill='x')
        ttk.Button(przyciski, text='+ Nowe wydarzenie', command=self.nowe).pack(side='left')
        ttk.Button(przyciski, text='Zmień zaznaczone', command=self.edytuj).pack(side='left', padx=6)
        ttk.Button(przyciski, text='Przenieś do archiwum', command=self.archiwizuj).pack(side='left')
        ttk.Button(przyciski, text='Sprawdź zakładkę w arkuszu', command=self.sprawdz_zakladke).pack(side='left', padx=6)

        ttk.Label(srodek, text='Archiwum', font=('Segoe UI', 11, 'bold')).pack(anchor='w', pady=(16, 0))
        self.archiwum = tk.Listbox(srodek, height=5, relief='flat')
        self.archiwum.pack(fill='x', pady=(4, 8))

        self.status = tk.StringVar()
        ttk.Label(self, textvariable=self.status, padding=(12, 4), foreground='#555').pack(fill='x', side='bottom')

    def odswiez(self):
        zrodlo = self.zrodlo()

        def praca():
            czytaj = zrodlo.migawka()
            return op.stan(czytaj), op.presety(czytaj)

        def gotowe(w):
            self.dane, self.presety = w
            self.lista.delete(*self.lista.get_children())
            for e in sorted(self.dane['upcoming'], key=g.klucz_czasu):
                pule = ', '.join(x for x, z in (('K', e.get('soldOutWomen')), ('M', e.get('soldOutMen'))) if z) or '—'
                self.lista.insert('', 'end', iid=e['id'], values=(
                    e['date'], e['time'], e['name'], e['venue'], '%s / %s' % (e['priceW'], e['priceM']),
                    e['sheetTab'], pule))
            self.archiwum.delete(0, 'end')
            for p in sorted(self.dane['past'], key=g.klucz_czasu, reverse=True):
                self.archiwum.insert('end', '%s   %s   %s' % (p['date'], p['name'], p['venue']))
            self.status.set('Wczytano: ' + zrodlo.opis())
        self.w_tle('Wczytuję wydarzenia', praca, gotowe)

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

    def archiwizuj(self):
        e = self.zaznaczone()
        if not e:
            return
        if not messagebox.askyesno(NAZWA, 'Przenieść "%s %s, %s" do archiwum?\n\n'
                                   'Karta zniknie ze strony głównej i trafi do "Za nami", '
                                   'a ze strony wydarzenia zniknie formularz zapisów.\n'
                                   'Rób to dopiero po wydarzeniu.' % (e['name'], e['date'], e['time'])):
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
        f = ttk.Frame(self, padding=16)
        f.pack()
        u = app.ustawienia
        self.token = tk.StringVar(value=u.get('token', ''))
        self.repo = tk.StringVar(value=u.get('repo', 'wsolore/matchpoint'))
        ttk.Label(f, text='Token GitHub').grid(row=0, column=0, sticky='w')
        ttk.Entry(f, textvariable=self.token, width=60, show='•').grid(row=0, column=1, pady=4)
        ttk.Label(f, text='Repozytorium').grid(row=1, column=0, sticky='w')
        ttk.Entry(f, textvariable=self.repo, width=60).grid(row=1, column=1, pady=4)
        ttk.Label(f, text='Token dostajesz od osoby, która prowadzi stronę (instrukcja, rozdział 1).\n'
                          'Zapisuje się tylko na tym komputerze.', foreground='#777').grid(row=2, column=1, sticky='w')
        ttk.Button(f, text='Zapisz', command=self.zapisz).grid(row=3, column=1, sticky='e', pady=(12, 0))

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
        self.geometry('900x700')

        zakl = ttk.Notebook(self)
        zakl.pack(fill='both', expand=True, padx=8, pady=8)

        z1, w1 = przewijane(zakl)
        self.f_podst = Formularz(w1, POLA_PODSTAWOWE, sporty=list(app.presety),
                                 przy_zmianie_sportu=self.zmiana_sportu if nowe else None)
        self.f_podst.pack(fill='x')
        zakl.add(z1, text='1. Termin, miejsce, ceny')

        z2, w2 = przewijane(zakl)
        ttk.Label(w2, text='Te pola trafiają do maila z potwierdzeniem udziału (po TAK w arkuszu).',
                  padding=(12, 8, 0, 0)).pack(anchor='w')
        self.f_mail = Formularz(w2, POLA_MAIL)
        self.f_mail.pack(fill='x')
        zakl.add(z2, text='2. Mail do uczestnika')

        z3, w3 = przewijane(zakl)
        if self.reczna:
            ttk.Label(w3, padding=16, wraplength=760, text=(
                'Ta strona powstała ręcznie, przed aplikacją, więc jej tekstów nie da się tu zmienić. '
                'Ceny, limity, zamknięcie puli i treść maili zmienisz normalnie w zakładkach 1 i 2 — '
                'strona czyta je z konfiguracji. Liczby wypisane w samym tekście strony (np. tabelka '
                '"Szczegóły") zostaną stare, więc przy zmianie ceny daj nam znać.')).pack(anchor='w')
            self.f_strona = None
        else:
            self.f_strona = Formularz(w3, POLA_STRONY)
            self.f_strona.pack(fill='x')
        zakl.add(z3, text='3. Teksty na stronie')

        dol = ttk.Frame(self, padding=(8, 0, 8, 8))
        dol.pack(fill='x')
        ttk.Button(dol, text='Anuluj', command=self.destroy).pack(side='right')
        ttk.Button(dol, text='Opublikuj', command=self.opublikuj).pack(side='right', padx=6)
        ttk.Button(dol, text='Podgląd w przeglądarce', command=self.podglad).pack(side='right')

        self.f_podst.ustaw(e)
        self.f_mail.ustaw(e)
        self.s_start = s or {}
        if self.f_strona:
            self.f_strona.ustaw(s)
        if not nowe:
            # dyscypliny i nazwy pliku nie zmieniamy: link juz poszedl w swiat
            for w in self.f_podst.winfo_children():
                if isinstance(w, ttk.Combobox):
                    w.configure(state='disabled')

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
        self.f_strona.ustaw(s)
        self.s_start = s

    def zbierz(self):
        e1, b1 = self.f_podst.pobierz()
        e2, b2 = self.f_mail.pobierz()
        bledy = b1 + b2
        e = dict(self.e_start)
        e.update(e1)
        e.update(e2)
        s = None
        if self.f_strona:
            s3, b3 = self.f_strona.pobierz()
            bledy += b3
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
                        '(instrukcja, rozdział 3) i opublikuj jeszcze raz.\n\n'
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
    Aplikacja(lokalnie).mainloop()


if __name__ == '__main__':
    main()
