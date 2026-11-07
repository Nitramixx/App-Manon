@echo off
chcp 65001 >nul
title App Manon

:: ============================================================
:: LANCEUR D'URGENCE — ne déconnecte JAMAIS la session Windows
:: ============================================================
:: 1) Mets ce fichier DANS le dossier du projet (à côté de app.py)
::    OU change la ligne PROJET_DIR ci-dessous.
:: 2) Enlève App Manon du démarrage Windows (shell:startup).
:: ============================================================

set "PROJET_DIR=%~dp0"
cd /d "%PROJET_DIR%"

if not exist "%PROJET_DIR%app.py" (
    echo [ERREUR] app.py introuvable dans :
    echo   %PROJET_DIR%
    echo.
    echo Place ce .bat a cote de app.py, ou corrige PROJET_DIR.
    pause
    exit /b 1
)

echo [1/3] Python...
python --version
if errorlevel 1 (
    echo [ERREUR] Python introuvable. Installe Python puis relance.
    pause
    exit /b 1
)

echo [2/3] Modules + serveur...
python -m pip install Flask Pillow Werkzeug >nul 2>&1
start "Serveur_Manon" /min python app.py

echo Attente du serveur...
timeout /t 5 /nobreak >nul

set "CHROME="
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" set "CHROME=C:\Program Files\Google\Chrome\Application\chrome.exe"
if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" set "CHROME=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

if "%CHROME%"=="" (
    echo [ERREUR] Chrome introuvable.
    echo Ouvre manuellement : http://127.0.0.1:5000
    start http://127.0.0.1:5000
    pause
    goto :cleanup
)

echo [3/3] Chrome...
echo La fenetre reste ouverte tant que Chrome est ouvert.
echo Fermer Chrome = fermer l'app (SANS deconnecter Windows).
echo.

start "" /wait "%CHROME%" --kiosk --user-data-dir="%TEMP%\profil_manon" http://127.0.0.1:5000

:cleanup
echo Fermeture du serveur uniquement...
taskkill /FI "WINDOWTITLE eq Serveur_Manon*" /F >nul 2>&1
echo Termine. Session Windows intacte.
timeout /t 2 /nobreak >nul
exit /b 0
