@echo off
chcp 65001 >nul
title Liberer port 5000
echo Processus sur le port 5000 :
netstat -ano | findstr ":5000" | findstr "LISTENING"
echo.
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":5000" ^| findstr "LISTENING"') do (
    echo Arret du PID %%P...
    taskkill /PID %%P /F
)
echo.
echo Termine. Tu peux relancer App Manon.
pause
