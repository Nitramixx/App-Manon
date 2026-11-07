@echo off
chcp 65001 >nul
title App Manon - Soeur
cd /d "%~dp0"

:: Lanceur SOEUR (PC Manon) :
:: - libere le port 5000
:: - a la fermeture de Chrome : stoppe Flask PUIS deconnecte la session Windows

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
start "" /wait "%CHROME%" --kiosk --user-data-dir="%TEMP%\profil_manon" http://127.0.0.1:5000

:cleanup
echo Fermeture serveur...
taskkill /FI "WINDOWTITLE eq Serveur_Manon*" /F >nul 2>&1

echo Deconnexion de la session Windows...
shutdown /l /f
exit /b 0
