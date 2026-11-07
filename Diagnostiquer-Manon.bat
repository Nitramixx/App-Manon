@echo off
chcp 65001 >nul
title Diagnostic App Manon
cd /d "%~dp0"

echo ========================================
echo   DIAGNOSTIC APP MANON
echo ========================================
echo Dossier : %CD%
echo.

echo [1] app.py present ?
if exist "app.py" (echo    OK app.py) else (echo    ECHEC : app.py introuvable & goto :fin)

echo [2] Python ?
where python 2>nul
python --version 2>nul
if errorlevel 1 (echo    ECHEC : Python pas dans le PATH & goto :fin) else (echo    OK Python)

echo [3] Flask / Pillow ?
python -c "import flask,PIL; print('   OK Flask', flask.__version__)" 2>nul
if errorlevel 1 (
  echo    Modules manquants — installation...
  python -m pip install Flask Pillow Werkzeug
  python -c "import flask,PIL; print('   OK apres install')" 2>nul
  if errorlevel 1 (echo    ECHEC import Flask/Pillow & goto :fin)
)

echo [4] database.json ?
if exist "database.json" (echo    OK database.json) else (echo    ATTENTION : pas de database.json — l'app peut demarrer vide)

echo [5] Chrome ?
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
  echo    OK Chrome 64-bit
) else if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
  echo    OK Chrome 32-bit
) else (
  echo    ECHEC : Chrome introuvable a l'emplacement standard
)

echo [6] Port 5000 deja pris ?
netstat -ano | findstr ":5000" | findstr "LISTENING"
if errorlevel 1 (echo    OK port 5000 libre) else (echo    ATTENTION : quelque chose utilise deja le port 5000)

echo [7] Test demarrage Flask 8 secondes...
start "Test_Serveur_Manon" /min python app.py
timeout /t 8 /nobreak >nul

powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri http://127.0.0.1:5000/ -UseBasicParsing -TimeoutSec 3; Write-Host '   OK serveur repond HTTP' $r.StatusCode } catch { Write-Host '   ECHEC : le serveur ne repond pas sur http://127.0.0.1:5000' ; Write-Host '  ' $_.Exception.Message }"

taskkill /FI "WINDOWTITLE eq Test_Serveur_Manon*" /F >nul 2>&1

echo.
echo ========================================
echo Si [7] ECHEC : regarde les erreurs ci-dessous
echo en lançant manuellement :  python app.py
echo ========================================
echo.

:fin
echo.
pause
