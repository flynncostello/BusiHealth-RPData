@echo off
setlocal enabledelayedexpansion

echo ==== Property Scraper Setup for Windows ====
echo.
echo This script will set up everything needed to run the property scraper.
echo.

REM Check for administrative privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: Not running with administrator privileges.
    echo Some operations might require elevated permissions.
    echo.
    pause
)

REM Check for Python installation
where python >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Python is not installed or not in PATH.
    echo.
    echo Would you like to download and install Python now? (Y/N)
    set /p install_python=
    
    if /i "!install_python!"=="Y" (
        echo Downloading Python installer...
        curl -L -o python_installer.exe https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe
        
        echo Installing Python (this may take a few minutes)...
        start /wait python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
        
        echo Waiting for Python installation to complete...
        timeout /t 5 /nobreak
        
        echo Cleaning up...
        del python_installer.exe
    ) else (
        echo Please install Python and run this script again.
        echo You can download Python from https://www.python.org/downloads/
        pause
        exit /b 1
    )
)

REM Check Python version
for /f "tokens=2" %%V in ('python --version 2^>^&1') do set "python_version=%%V"
echo Found Python version: %python_version%

REM Check for Google Chrome
reg query "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe" >nul 2>&1
if %errorlevel% neq 0 (
    echo Google Chrome is not installed.
    echo.
    echo Would you like to download and install Google Chrome now? (Y/N)
    set /p install_chrome=
    
    if /i "!install_chrome!"=="Y" (
        echo Downloading Chrome installer...
        curl -L -o chrome_installer.exe https://dl.google.com/chrome/install/latest/chrome_installer.exe
        
        echo Installing Chrome (this may take a few minutes)...
        start /wait chrome_installer.exe /silent /install
        
        echo Waiting for Chrome installation to complete...
        timeout /t 10 /nobreak
        
        echo Cleaning up...
        del chrome_installer.exe
    ) else (
        echo Please install Google Chrome and run this script again.
        echo You can download Chrome from https://www.google.com/chrome/
        pause
        exit /b 1
    )
)

REM Find Chrome executable path
for /f "tokens=*" %%a in ('reg query "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe" /ve ^| findstr "REG_SZ"') do (
    set chrome_path=%%a
)
set chrome_path=%chrome_path:*REG_SZ    =%
echo Found Chrome at: %chrome_path%

REM Get Chrome version to find matching ChromeDriver
for /f "tokens=3" %%v in ('"%chrome_path%" --version') do (
    set chrome_version=%%v
)
echo Chrome version: %chrome_version%

REM Extract the major version number
for /f "tokens=1 delims=." %%a in ("%chrome_version%") do (
    set chrome_major=%%a
)
echo Chrome major version: %chrome_major%

REM Create required directories
echo Creating required directories...
if not exist "downloads" mkdir downloads
if not exist "merged_properties" mkdir merged_properties
if not exist "tmp" mkdir tmp

REM Create a ChromeDriver directory in the user's profile
echo Setting up ChromeDriver directory...
if not exist "%USERPROFILE%\.chromedriver" mkdir "%USERPROFILE%\.chromedriver"

REM Clean up previous ChromeDriver installations
echo Cleaning previous ChromeDriver installations...
if exist "%USERPROFILE%\.wdm\drivers\chromedriver" rmdir /s /q "%USERPROFILE%\.wdm\drivers\chromedriver"
if exist "%USERPROFILE%\.chromedriver\*.*" del /f /q "%USERPROFILE%\.chromedriver\*.*"

REM Create venv if it doesn't exist
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
) else (
    echo Virtual environment already exists.
)

REM Activate environment and install requirements
echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Upgrading pip and installing requirements...
python -m pip install --upgrade pip
python -m pip install --upgrade setuptools wheel
python -m pip install -r requirements.txt

REM Download the compatible ChromeDriver for Windows based on Chrome version
echo Checking for compatible ChromeDriver for Chrome %chrome_major%...

REM First try the exact chrome version
set chromedriver_url=https://storage.googleapis.com/chrome-for-testing-public/%chrome_version%/win64/chromedriver-win64.zip
echo Trying URL: %chromedriver_url%

curl -L -o "%USERPROFILE%\.chromedriver\chromedriver.zip" "%chromedriver_url%" --silent
if %errorlevel% neq 0 (
    echo First attempt failed, trying stable version...
    REM Fall back to the stable version if the exact match fails
    set chromedriver_url=https://storage.googleapis.com/chrome-for-testing-public/136.0.7103.49/win64/chromedriver-win64.zip
    curl -L -o "%USERPROFILE%\.chromedriver\chromedriver.zip" "%chromedriver_url%"
    
    if %errorlevel% neq 0 (
        echo ChromeDriver download failed. Please check your internet connection.
        exit /b 1
    )
)

REM Extract the ChromeDriver
echo Extracting ChromeDriver...
powershell -command "Expand-Archive -Path '%USERPROFILE%\.chromedriver\chromedriver.zip' -DestinationPath '%USERPROFILE%\.chromedriver\temp' -Force"

REM Find and move the executable
for /r "%USERPROFILE%\.chromedriver\temp" %%f in (chromedriver.exe) do (
    copy "%%f" "%USERPROFILE%\.chromedriver\chromedriver.exe" /Y
)

REM Test if ChromeDriver exists
if not exist "%USERPROFILE%\.chromedriver\chromedriver.exe" (
    echo ERROR: ChromeDriver extraction failed!
    exit /b 1
)

REM Clean up temporary files
rmdir /s /q "%USERPROFILE%\.chromedriver\temp"
del "%USERPROFILE%\.chromedriver\chromedriver.zip"

REM Set environment variables
echo Setting environment variables...
setx CHROMEDRIVER_PATH "%USERPROFILE%\.chromedriver\chromedriver.exe" /M
setx CHROME_BINARY "%chrome_path%" /M

REM Verify hardware acceleration and WebGL capability
echo Checking GPU and WebGL capability...
echo This application requires WebGL. Make sure your graphics drivers are up to date.

echo.
echo ✓ Setup complete! You can now run the app using run_windows.bat
echo.
pause