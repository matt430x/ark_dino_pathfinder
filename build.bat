@echo off
setlocal EnableDelayedExpansion
title ARK Dino Pathfinder — Build

echo ============================================
echo  ARK Dino Pathfinder Build Script
echo ============================================
echo.

:: ── Step 1: Download EasyOCR models if not already present ──────────────────
if exist "models\" (
    echo [1/3] EasyOCR models already present, skipping download.
) else (
    echo [1/3] Downloading EasyOCR models (needed only once)...
    python download_models.py
    if errorlevel 1 (
        echo.
        echo ERROR: Model download failed.
        pause & exit /b 1
    )
)

echo.

:: ── Step 2: Build exe with PyInstaller ──────────────────────────────────────
echo [2/3] Building executable with PyInstaller...
pyinstaller gui.spec --clean --noconfirm
if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller build failed.
    pause & exit /b 1
)

echo.

:: ── Step 3: Create Windows installer with Inno Setup ────────────────────────
echo [3/3] Creating installer with Inno Setup...

set ISCC=
if exist "E:\Inno Setup 6\ISCC.exe"                     set ISCC="E:\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe"       set ISCC="C:\Program Files\Inno Setup 6\ISCC.exe"

if "!ISCC!"=="" (
    echo.
    echo ERROR: Inno Setup 6 not found.
    echo        Download it from: https://jrsoftware.org/isinfo.php
    pause & exit /b 1
)

if not exist "installer_output\" mkdir installer_output
%ISCC% installer.iss
if errorlevel 1 (
    echo.
    echo ERROR: Inno Setup compilation failed.
    pause & exit /b 1
)

echo.
echo ============================================
echo  Build complete!
echo  Installer: installer_output\ARKDinoPathfinder_Setup_v2.0.exe
echo ============================================
pause
