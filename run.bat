@echo off
chcp 65001 >nul
title Invoice OCR

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Environment not set up. Please run setup.bat first.
    pause
    exit /b 1
)

venv\Scripts\python.exe main.py
pause
