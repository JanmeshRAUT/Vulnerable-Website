@echo off
REM Setup script for APK building on Windows

echo ========================================
echo APK Build Setup for Vulnerable E-Commerce Lab
echo ========================================
echo.

REM Check Python
echo [1/5] Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Please install Python 3.9+
    pause
    exit /b 1
)
echo OK - Python installed

REM Install Kivy and Buildozer
echo.
echo [2/5] Installing Kivy and Buildozer...
pip install --upgrade kivy buildozer cython

REM Set JAVA_HOME
echo.
echo [3/5] Setting up Java path...
for /f "tokens=*" %%A in ('where java') do (
    set JAVA_PATH=%%A
    set JAVA_PATH=!JAVA_PATH:\bin\java.exe=!
)

if defined JAVA_PATH (
    echo Setting JAVA_HOME to: %JAVA_PATH%
    setx JAVA_HOME "%JAVA_PATH%"
) else (
    echo ERROR: Java not found. Please download and install JDK 11+
    echo Download from: https://www.oracle.com/java/technologies/downloads/
    pause
    exit /b 1
)

REM SDK/NDK Download Instructions
echo.
echo [4/5] Android SDK and NDK Setup
echo.
echo you need to download:
echo 1. Android SDK - https://developer.android.com/studio/releases/platform-tools
echo 2. Android NDK r23b - https://developer.android.com/ndk/downloads
echo.
echo After downloading:
echo.
echo Step 1: Extract Android SDK to: C:\Android\Sdk
echo Step 2: Extract NDK to: C:\android-ndk-r23b
echo Step 3: Add environment variables:
echo    - ANDROID_SDK_ROOT = C:\Android\Sdk
echo    - ANDROID_NDK_ROOT = C:\android-ndk-r23b
echo.
echo [5/5] Configuration
echo.
echo buildozer.spec - Ready
echo main.py - Ready (Kivy wrapper)
echo APK_BUILD_GUIDE.md - Full instructions
echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Download and extract Android SDK and NDK
echo 2. Set the environment variables (see above)
echo 3. Run: buildozer android debug
echo.
pause
