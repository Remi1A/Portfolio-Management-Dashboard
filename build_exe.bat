@echo off
title CY Tech AM - Build EXE
cd /d "%~dp0"

echo ============================================
echo    CY Tech AM - Construction du .exe
echo ============================================
echo.

:: 1. Verifier que PyInstaller est installe
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo Installation de PyInstaller...
    pip install pyinstaller
    echo.
)

:: 2. Construire le .exe
echo Construction en cours (ca peut prendre 2-5 minutes)...
echo.

pyinstaller --noconfirm --onedir --console ^
    --name "CY Tech AM Dashboard" ^
    --add-data "cyu_am;cyu_am" ^
    --add-data "requirements.txt;." ^
    --hidden-import streamlit ^
    --hidden-import streamlit_option_menu ^
    --hidden-import yfinance ^
    --hidden-import plotly ^
    --hidden-import scipy ^
    --hidden-import scipy.optimize ^
    --hidden-import statsmodels ^
    --hidden-import reportlab ^
    --hidden-import kaleido ^
    --hidden-import openpyxl ^
    --hidden-import sqlite3 ^
    --collect-all streamlit ^
    --collect-all streamlit_option_menu ^
    --collect-all plotly ^
    --collect-all kaleido ^
    launcher.py

if %errorlevel% neq 0 (
    echo.
    echo ERREUR lors de la construction.
    echo Verifiez que toutes les dependances sont installees:
    echo   pip install -r requirements.txt
    echo   pip install pyinstaller
    pause
    exit /b 1
)

echo.
echo ============================================
echo    Construction terminee !
echo ============================================
echo.
echo Le .exe se trouve dans:
echo   dist\CY Tech AM Dashboard\CY Tech AM Dashboard.exe
echo.
echo Pour distribuer: copiez le dossier "dist\CY Tech AM Dashboard" en entier.
echo.
pause
