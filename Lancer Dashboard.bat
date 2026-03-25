@echo off
title CY Tech AM - Portfolio Dashboard
cd /d "%~dp0"

echo ============================================
echo    CY Tech AM - Portfolio Dashboard
echo ============================================
echo.
echo Demarrage du dashboard...
echo (Ne fermez pas cette fenetre)
echo.

python -m streamlit run cyu_am/app.py --server.headless true --server.fileWatcherType none --browser.gatherUsageStats false

if %errorlevel% neq 0 (
    echo.
    echo ERREUR: Python n'est pas installe ou les dependances manquent.
    echo.
    echo Installez les dependances avec:
    echo   pip install -r requirements.txt
    echo.
    pause
)
