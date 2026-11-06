@echo off
chcp 65001 >nul

:: --- CONFIGURATION ---
set "PROJET_DIR=%~dp0"
cd /d "%PROJET_DIR%"

:: --- 1. VÉRIFICATION ET INSTALLATION DE PYTHON ---
echo [1/4] Verification de Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ATTENTION] Python n'est pas installe sur cet ordinateur.

    if not exist "python_installer.exe" (
        echo Telechargement de Python en cours...
        curl -o python_installer.exe https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe
        if %errorlevel% neq 0 (
            echo [ERREUR] Impossible de telecharger Python.
            pause
            exit /b 1
        )
    )

    echo Installation silencieuse de Python en cours...
    start /wait python_installer.exe /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
    del python_installer.exe >nul 2>&1

    echo [SUCCES] Python a ete installe !
    echo /!\ IMPORTANT : Windows a besoin de rafraichir ses parametres.
    echo Veuillez fermer cette fenetre noire et relancer ce fichier .bat une seconde fois.
    pause
    exit /b 0
)

:: --- 2. INSTALLATION DES MODULES ---
echo [2/4] Verification des modules (Flask, Pillow)...
python -m pip install --upgrade pip >nul 2>&1
python -m pip install Flask Pillow Werkzeug >nul 2>&1

:: --- 3. DÉMARRAGE DU SERVEUR ---
echo [3/4] Lancement du serveur en arriere-plan...
start "Serveur_Manon" /min python app.py

timeout /t 3 /nobreak >nul

:: --- 4. DÉMARRAGE DE CHROME EN MODE ATTENTE ---
echo [4/4] Lancement de l'interface...
start "" /wait "C:\Program Files\Google\Chrome\Application\chrome.exe" --kiosk --user-data-dir="c:\temp\profil_manon" http://127.0.0.1:5000

:: --- 5. NETTOYAGE (sans deconnecter la session Windows) ---
echo Fermeture de l'application...
taskkill /FI "WINDOWTITLE eq Serveur_Manon*" /F >nul 2>&1
exit /b 0
