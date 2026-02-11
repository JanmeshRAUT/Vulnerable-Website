@echo off
REM ============================================================================
REM Automated Build Script for Vulnerable E-Commerce Lab Executable
REM ============================================================================

echo.
echo ========================================================================
echo   Vulnerable E-Commerce Lab - Executable Builder
echo ========================================================================
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo [WARNING] Virtual environment not found or incomplete!
    echo.
    set /p create_venv="Do you want to create a virtual environment? (Y/N): "
    if /i "%create_venv%"=="Y" (
        echo Creating virtual environment...
        python -m venv venv
        if errorlevel 1 (
            echo [ERROR] Failed to create virtual environment
            echo Trying to build with global Python installation...
            goto :skip_venv
        )
        echo Virtual environment created successfully!
    ) else (
        echo Building with global Python installation...
        goto :skip_venv
    )
)

REM Activate virtual environment
echo [1/5] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [WARNING] Failed to activate virtual environment
    echo Trying with global Python installation...
    goto :skip_venv
)
goto :continue

:skip_venv
echo [1/5] Using global Python installation...

:continue
REM Check if PyInstaller is installed
echo [2/5] Checking PyInstaller installation...
python -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    python -m pip install pyinstaller
    if errorlevel 1 (
        echo [ERROR] Failed to install PyInstaller
        echo.
        echo Please install manually: pip install pyinstaller
        pause
        exit /b 1
    )
)

REM Install other dependencies if needed
echo Installing/updating dependencies...
python -m pip install flask werkzeug --quiet

REM Clean previous builds
echo [3/5] Cleaning previous builds...
if exist "build\" rmdir /s /q build
if exist "dist\" rmdir /s /q dist

REM Build the executable
echo [4/5] Building executable (this may take 2-5 minutes)...
echo Please wait...
echo.
cmd /c "python -m PyInstaller VulnerableEcommerceLab.spec"
if exist "dist\VulnerableEcommerceLab.exe" (
    ver > nul
)
REM Check if build succeeded by verifying the executable exists
if not exist "dist\VulnerableEcommerceLab.exe" (
    echo.
    echo [ERROR] Build failed! Executable not created.
    echo.
    echo Common solutions:
    echo   1. Make sure all files are present (templates, static, data folders)
    echo   2. Try: pip install --upgrade pyinstaller
    echo   3. Check the error messages above for details
    echo.
    pause
    exit /b 1
)

REM Verify the executable was created
echo [5/5] Verifying build...
if not exist "dist\VulnerableEcommerceLab.exe" (
    echo.
    echo [ERROR] Executable not found in dist folder!
    echo The build may have failed silently.
    pause
    exit /b 1
)

REM Calculate file size
for %%A in (dist\VulnerableEcommerceLab.exe) do set size=%%~zA
set /a sizeMB=%size% / 1048576

REM Calculate SHA256 checksum
echo.
echo Calculating SHA256 checksum...
certutil -hashfile dist\VulnerableEcommerceLab.exe SHA256 > checksum.txt 2>nul
if exist checksum.txt (
    findstr /v ":" checksum.txt | findstr /v "CertUtil" > dist\SHA256.txt
    del checksum.txt
)

REM Packaging Distribution
echo.
echo [INFO] Creating distribution package...

REM Copy instructions
if exist "STUDENT_README.txt" (
    copy "STUDENT_README.txt" "dist\README.txt" >nul
) else (
    echo [WARNING] STUDENT_README.txt not found. Creating a basic readme...
    echo Vulnerable E-Commerce Lab > dist\README.txt
)

REM Create ZIP file
echo Compressing files into VulnerableEcommerceLab-Distribution.zip...
powershell -Command "Compress-Archive -Path 'dist\VulnerableEcommerceLab.exe', 'dist\README.txt' -DestinationPath 'dist\VulnerableEcommerceLab-Distribution.zip' -Force"

if exist "dist\VulnerableEcommerceLab-Distribution.zip" (
    echo [SUCCESS] Zip file created successfully!
) else (
    echo [ERROR] Failed to create zip file.
)

REM Success message
echo.
echo ========================================================================
echo   BUILD SUCCESSFUL!
echo ========================================================================
echo.
echo Executable location: dist\VulnerableEcommerceLab.exe
echo Zip file location: dist\VulnerableEcommerceLab-Distribution.zip
echo File size: %sizeMB% MB
echo.
if exist "dist\SHA256.txt" (
    echo SHA256 checksum saved to: dist\SHA256.txt
)
echo.
echo Next steps:
echo   1. Test the executable: cd dist ^&^& VulnerableEcommerceLab.exe
echo   2. Share the .zip file with students (Contains .exe and instructions)
echo.
echo ========================================================================
echo.

REM Ask if user wants to test now
set /p test="Do you want to test the executable now? (Y/N): "
if /i "%test%"=="Y" (
    echo.
    echo Starting executable...
    cd dist
    start VulnerableEcommerceLab.exe
    cd ..
)

echo.
echo Build complete! Press any key to exit...
pause >nul
