@echo off
title Format Yardimcisi v2.1.0 (Debug)
cd /d "%~dp0"
py -3 src\main.py
if %errorlevel% neq 0 (
    echo.
    echo [HATA] Uygulama baslatılamadı. Python veya customtkinter kurulu mu?
    echo Kurmak icin: pip install customtkinter
    pause
)
