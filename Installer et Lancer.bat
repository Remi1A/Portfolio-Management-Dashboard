@echo off
title CYU AM - Installation et Lancement
cd /d "%~dp0"

echo ============================================
echo    CYU AM - Portfolio Dashboard
echo ============================================
echo.

:: Verifier que Python est installe
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERREUR: Python n'est pas installe.
    echo.
    echo Telechargez Python sur : https://www.python.org/downloads/
    echo IMPORTANT : Cochez "Add Python to PATH" lors de l'installation !
    echo.
    pause
    exit /b 1
)

echo Python detecte:
python --version
echo.

:: Installer les dependances
echo Installation des dependances (premiere fois uniquement)...
pip install -r requirements.txt --quiet
echo Dependances OK.
echo.

:: Lancer le dashboard
echo Demarrage du dashboard...
echo Le navigateur va s'ouvrir automatiquement.
echo (Ne fermez pas cette fenetre)
echo.

python launcher.py

pause
