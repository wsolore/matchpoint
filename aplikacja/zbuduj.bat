@echo off
rem Buduje MatchPointWydarzenia.exe (jeden plik, bez konsoli).
rem Wymaga Pythona 3.10+ z tkinterem i:  python -m pip install pyinstaller
rem Wynik: aplikacja\dist\MatchPointWydarzenia.exe  -  ten plik wysylasz dalej.
rem
rem Szablon strony i teksty dyscyplin NIE sa w exe: aplikacja czyta je
rem z repo (szablony\). Zmiana szablonu nie wymaga wiec nowego exe.

cd /d "%~dp0"
python -m PyInstaller --noconfirm --onefile --windowed ^
  --name MatchPointWydarzenia ^
  --distpath dist --workpath build --specpath build ^
  app.py
if errorlevel 1 (
  echo.
  echo Budowanie nie wyszlo - komunikat bledu jest wyzej.
  exit /b 1
)
copy /y INSTRUKCJA.md dist\ >nul
copy /y szablon-zakladki.csv dist\ >nul
echo.
echo Gotowe: %~dp0dist\MatchPointWydarzenia.exe
