@echo off
setlocal enabledelayedexpansion

echo ==== Property Scraper - Starting Application ====
echo.

REM Check if build has been run
if not exist "venv" (
    echo Virtual environment not found! Running setup script first...
    call build_windows.bat
    
    REM Check if build failed
    if not exist "venv" (
        echo Setup failed. Please fix the errors and try again.
        pause
        exit /b 1
    )
)

REM Activate virtualenv
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Check Chrome installation
reg query "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe" >nul 2>&1
if %errorlevel% neq 0 (
    echo Google Chrome is not installed! Running setup script...
    call build_windows.bat
    
    REM Check again
    reg query "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe" >nul 2>&1
    if %errorlevel% neq 0 (
        echo Google Chrome installation failed. Please install Chrome manually.
        pause
        exit /b 1
    )
)

REM Get Chrome path from registry
for /f "tokens=*" %%a in ('reg query "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe" /ve ^| findstr "REG_SZ"') do (
    set chrome_path=%%a
)
set chrome_path=%chrome_path:*REG_SZ    =%
echo Chrome found at: %chrome_path%

REM Check for ChromeDriver
if not exist "%USERPROFILE%\.chromedriver\chromedriver.exe" (
    echo ChromeDriver not found! Running setup script...
    call build_windows.bat
)

REM Make sure directories exist
if not exist "downloads" mkdir downloads
if not exist "merged_properties" mkdir merged_properties
if not exist "tmp" mkdir tmp

REM Set environment variables for Chrome and ChromeDriver
set CHROME_BINARY=%chrome_path%
set CHROMEDRIVER_PATH=%USERPROFILE%\.chromedriver\chromedriver.exe

REM Enable hardware acceleration and WebGL
echo Enabling GPU acceleration for WebGL support...
set CHROME_FLAGS=--ignore-gpu-blocklist --enable-gpu-rasterization --enable-webgl --enable-accelerated-2d-canvas

echo.
echo Starting web application on http://127.0.0.1:8000
echo The app will open in your browser automatically.
echo Press CTRL+C to stop the app when you're finished.
echo.

REM Open the browser to the application URL
timeout /t 3 /nobreak
start http://127.0.0.1:8000

REM Run app
python app.py

REM If app exits, keep the window open
pause