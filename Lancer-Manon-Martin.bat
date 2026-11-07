@echo off
chcp 65001 >nul
title App Manon - Martin
cd /d "%~dp0"

:: Lanceur MARTIN : ne deconnecte JAMAIS la session Windows
:: Libere le port 5000 si un ancien serveur traine

if not exist "%~dp0app.py" (
    echo [ERREUR] app.py introuvable. Place ce .bat a cote de app.py.
    pause
    exit /b 1
)

echo [1/4] Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python introuvable.
    pause
    exit /b 1
)

echo [2/4] Modules...
python -m pip install Flask Pillow Werkzeug >nul 2>&1

echo [3/4] Liberation port 5000 + serveur...
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":5000" ^| findstr "LISTENING"') do (
    taskkill /PID %%P /F >nul 2>&1
)
timeout /t 1 /nobreak >nul
start "Serveur_Manon" /min python app.py
timeout /t 4 /nobreak >nul

set "CHROME="
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" set "CHROME=C:\Program Files\Google\Chrome\Application\chrome.exe"
if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" set "CHROME=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
if "%CHROME%"=="" (
    echo [ERREUR] Chrome introuvable. Ouvre http://127.0.0.1:5000
    start http://127.0.0.1:5000
    pause
    goto :cleanup
)

echo [4/4] Chrome kiosk...
start "" /wait "%CHROME%" --kiosk --user-data-dir="%TEMP%\profil_manon_martin" http://127.0.0.1:5000

:cleanup
echo Fermeture serveur (session Windows conservee)...
taskkill /FI "WINDOWTITLE eq Serveur_Manon*" /F >nul 2>&1
exit /b 0
