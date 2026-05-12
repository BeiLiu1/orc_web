@echo off
chcp 65001 >nul
title Invoice OCR - Setup

echo ========================================
echo   Invoice OCR - Environment Setup
echo ========================================
echo.

:: ── Python ──────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found.

    :: Try local installer
    for %%f in (python-*.exe) do set "PY_SETUP=%%f"
    if defined PY_SETUP (
        echo Installing Python from %PY_SETUP% ...
        echo This may take a few minutes. Please wait...
        "%PY_SETUP%" /quiet InstallAllUsers=1 PrependPath=1
        if errorlevel 1 (
            echo [ERROR] Python install failed. Run %PY_SETUP% manually.
            pause
            exit /b 1
        )
        echo Python installed. Please close this window and run setup.bat again.
        pause
        exit /b 0
    )

    :: Try winget
    winget --version >nul 2>&1
    if not errorlevel 1 (
        winget install Python.Python.3.11 --accept-package-agreements --accept-source-agreements
        echo Python installed. Please close this window and run setup.bat again.
        pause
        exit /b 0
    )

    echo Please run python-3.11.6-amd64.exe to install Python.
    echo Make sure to check "Add Python to PATH".
    start "" "python-3.11.6-amd64.exe" 2>nul
    pause
    exit /b 1
)

echo [OK] Python found:
python --version

:: ── Tesseract ───────────────────────────
where tesseract >nul 2>&1
if not errorlevel 1 (
    echo [OK] Tesseract found in PATH
    goto :deps
)

if exist "D:\Tesseract-OCR\tesseract.exe" (
    echo [OK] Tesseract found at D:\Tesseract-OCR\
    goto :deps
)

:: Try local installer
for %%f in (tesseract-ocr-*.exe) do set "TESS_SETUP=%%f"
if defined TESS_SETUP (
    echo Installing Tesseract OCR from %TESS_SETUP% ...
    echo This may take a few minutes. Please wait...
    "%TESS_SETUP%" /S
    if errorlevel 1 (
        echo [WARN] Tesseract silent install failed.
        echo        Please run %TESS_SETUP% manually.
        echo        Install to: D:\Tesseract-OCR
    ) else (
        echo [OK] Tesseract installed.
    )
    goto :deps
)

:: Try winget
winget --version >nul 2>&1
if not errorlevel 1 (
    winget install UB-Mannheim.TesseractOCR --accept-package-agreements --accept-source-agreements
    goto :deps
)

echo [WARN] Tesseract not found. Please run:
echo        tesseract-ocr-w64-setup-5.5.0.20241111.exe
echo        Install to: D:\Tesseract-OCR

:deps
:: ── Virtual Environment ────────────────
if not exist "venv\Scripts\python.exe" (
    echo.
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create venv.
        pause
        exit /b 1
    )
) else (
    echo [OK] Virtual environment ready.
)

:: ── Dependencies ───────────────────────
echo.
echo Installing dependencies...
venv\Scripts\python.exe -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Setup complete! Run: run.bat
echo ========================================
pause
