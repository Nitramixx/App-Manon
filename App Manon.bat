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
    
    :: On vérifie que tu as bien mis le fichier dans le dossier
    if not exist "python_installer.exe" (
        echo [ERREUR FATALE] Le fichier "python_installer.exe" est introuvable !
        echo S'il te plait, place l'installateur Python dans le meme dossier que ce script.
        pause
        exit
    )

    echo Installation silencieuse de Python en cours...
    start /wait python_installer.exe /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
    
    echo [SUCCES] Python a ete installe !
    echo /!\ IMPORTANT : Windows a besoin de rafraichir ses parametres.
    echo Veuillez fermer cette fenetre noire et relancer ce fichier .bat une seconde fois.
    pause
    exit
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

:: --- 5. NETTOYAGE AUTOMATIQUE ---
echo Fermeture de l'application...
taskkill /IM python.exe /F >nul 2>&1

:: Fermeture de session forcée (l = Logoff, F = Force)
shutdown /l /f
exit