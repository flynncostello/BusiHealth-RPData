@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo ==== Property Scraper Setup for Windows ====
echo ==========================================
echo.
echo This script will set up everything needed to run the property scraper.
echo Starting setup at: %TIME%
echo.

REM Check for administrative privileges
echo [STEP 1/8] Checking for administrative privileges...
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [WARNING] Not running with administrator privileges.
    echo Some operations might require elevated permissions.
    echo.
    echo Press ANY key to continue anyway or CTRL+C to abort...
    pause
)
echo Admin check complete.
echo.

REM Check Python version (Python is already installed manually)
echo [STEP 2/8] Checking Python version...
for /f "tokens=2" %%V in ('python --version 2^>^&1') do set "python_version=%%V"
echo [INFO] Found Python version: %python_version%
echo.

REM Check for Google Chrome - simplified to just detect, not install
echo [STEP 3/8] Checking for Google Chrome...
reg query "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Google Chrome is not installed.
    echo Please install Google Chrome and run this script again.
    echo You can download Chrome from https://www.google.com/chrome/
    pause
    exit /b 1
) else (
    echo [SUCCESS] Google Chrome is already installed.
)
echo.

REM Find Chrome executable path
echo [STEP 4/8] Finding Chrome executable path...
for /f "tokens=*" %%a in ('reg query "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe" /ve ^| findstr "REG_SZ"') do (
    set chrome_path=%%a
)
set chrome_path=%chrome_path:*REG_SZ    =%
echo [INFO] Found Chrome at: %chrome_path%

REM Check if the chrome_path is valid
if not exist "%chrome_path%" (
    echo [ERROR] Chrome executable not found at the detected path.
    echo Please verify Chrome installation and try again.
    pause
    exit /b 1
)
echo.

REM Get Chrome version to find matching ChromeDriver
echo [INFO] Getting Chrome version...
echo [INFO] Running Chrome to get version info...
for /f "tokens=3" %%v in ('"%chrome_path%" --version 2^>^&1') do (
    set chrome_version=%%v
)

if "%chrome_version%"=="" (
    echo [WARNING] Could not determine Chrome version.
    echo [INFO] Using default version 136.0.7103.49 for ChromeDriver.
    set chrome_version=136.0.7103.49
)

echo [INFO] Chrome version: %chrome_version%

REM Extract the major version number
for /f "tokens=1 delims=." %%a in ("%chrome_version%") do (
    set chrome_major=%%a
)
echo [INFO] Chrome major version: %chrome_major%
echo.

REM Create required directories
echo [STEP 5/8] Creating required directories...
if not exist "downloads" (
    echo [ACTION] Creating downloads directory...
    mkdir downloads
)
if not exist "merged_properties" (
    echo [ACTION] Creating merged_properties directory...
    mkdir merged_properties
)
if not exist "tmp" (
    echo [ACTION] Creating tmp directory...
    mkdir tmp
)
echo [SUCCESS] All directories created.
echo.

REM Create a ChromeDriver directory in the user's profile
echo [INFO] Setting up ChromeDriver directory...
if not exist "%USERPROFILE%\.chromedriver" (
    echo [ACTION] Creating ChromeDriver directory...
    mkdir "%USERPROFILE%\.chromedriver"
)
echo.

REM Clean up previous ChromeDriver installations
echo [INFO] Cleaning previous ChromeDriver installations...
if exist "%USERPROFILE%\.wdm\drivers\chromedriver" (
    echo [ACTION] Removing old WDM ChromeDriver...
    rmdir /s /q "%USERPROFILE%\.wdm\drivers\chromedriver"
)
if exist "%USERPROFILE%\.chromedriver\*.*" (
    echo [ACTION] Removing old ChromeDriver files...
    del /f /q "%USERPROFILE%\.chromedriver\*.*"
)
echo [SUCCESS] Cleanup complete.
echo.

REM Create venv if it doesn't exist
echo [STEP 6/8] Setting up Python virtual environment...
if not exist venv (
    echo [ACTION] Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        echo Please check your Python installation and try again.
        pause
        exit /b 1
    )
    echo [SUCCESS] Virtual environment created.
) else (
    echo [INFO] Virtual environment already exists.
)
echo.

REM Activate environment and install requirements
echo [STEP 7/8] Activating virtual environment...
echo [ACTION] Running activation script...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate virtual environment.
    pause
    exit /b 1
)
echo [SUCCESS] Virtual environment activated.
echo.

echo [INFO] Upgrading pip and installing requirements...
echo [ACTION] Upgrading pip...
python -m pip install --upgrade pip
if %errorlevel% neq 0 (
    echo [WARNING] Failed to upgrade pip, but continuing...
)

echo [ACTION] Upgrading setuptools and wheel...
python -m pip install --upgrade setuptools wheel
if %errorlevel% neq 0 (
    echo [WARNING] Failed to upgrade setuptools/wheel, but continuing...
)

echo [INFO] ==================== REQUIREMENTS INSTALLATION DIAGNOSTICS ====================
echo [DEBUG] Current directory: %CD%
dir requirements.txt
echo [DEBUG] ==========================================================================
echo.

echo [ACTION] Installing required packages (this may take several minutes)...
echo (Package installation progress will be displayed below)
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install required packages.
    echo Check the error messages above for details.
    pause
    exit /b 1
)
echo [SUCCESS] All required packages installed.
echo.

REM Download the compatible ChromeDriver for Windows based on Chrome version
echo [STEP 8/8] Downloading ChromeDriver...
echo [INFO] Checking for compatible ChromeDriver for Chrome %chrome_major%...

REM First try the exact chrome version
set chromedriver_url=https://storage.googleapis.com/chrome-for-testing-public/%chrome_version%/win64/chromedriver-win64.zip
echo [ACTION] Trying URL: %chromedriver_url%

echo [INFO] Downloading ChromeDriver (this may take a moment)...
curl -L -o "%USERPROFILE%\.chromedriver\chromedriver.zip" "%chromedriver_url%" --silent
if %errorlevel% neq 0 (
    echo [WARNING] First download attempt failed, trying stable version...
    REM Fall back to the stable version if the exact match fails
    set chromedriver_url=https://storage.googleapis.com/chrome-for-testing-public/136.0.7103.49/win64/chromedriver-win64.zip
    echo [ACTION] Trying alternate URL: %chromedriver_url%
    curl -L -o "%USERPROFILE%\.chromedriver\chromedriver.zip" "%chromedriver_url%"
    
    if %errorlevel% neq 0 (
        echo [ERROR] ChromeDriver download failed. Please check your internet connection.
        pause
        exit /b 1
    )
)
echo [SUCCESS] ChromeDriver downloaded.
echo.

REM Extract the ChromeDriver
echo [INFO] Extracting ChromeDriver...
echo [ACTION] Running PowerShell to extract the zip file...
powershell -command "Expand-Archive -Path '%USERPROFILE%\.chromedriver\chromedriver.zip' -DestinationPath '%USERPROFILE%\.chromedriver\temp' -Force"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to extract ChromeDriver.
    echo Check if PowerShell is available on your system.
    pause
    exit /b 1
)
echo [SUCCESS] ChromeDriver extracted.
echo.

REM Find and move the executable
echo [INFO] Installing ChromeDriver...
echo [ACTION] Copying ChromeDriver executable to final location...
for /r "%USERPROFILE%\.chromedriver\temp" %%f in (chromedriver.exe) do (
    copy "%%f" "%USERPROFILE%\.chromedriver\chromedriver.exe" /Y
)

REM Test if ChromeDriver exists
if not exist "%USERPROFILE%\.chromedriver\chromedriver.exe" (
    echo [ERROR] ChromeDriver extraction failed!
    pause
    exit /b 1
)
echo [SUCCESS] ChromeDriver installed.
echo.

REM Clean up temporary files
echo [INFO] Cleaning up temporary files...
rmdir /s /q "%USERPROFILE%\.chromedriver\temp"
del "%USERPROFILE%\.chromedriver\chromedriver.zip"
echo [SUCCESS] Cleanup complete.
echo.

REM Set environment variables
echo [INFO] Setting environment variables...
echo [ACTION] Setting CHROMEDRIVER_PATH...
setx CHROMEDRIVER_PATH "%USERPROFILE%\.chromedriver\chromedriver.exe" /M
echo [ACTION] Setting CHROME_BINARY...
setx CHROME_BINARY "%chrome_path%" /M
echo [SUCCESS] Environment variables set.
echo.

REM Verify hardware acceleration and WebGL capability
echo [INFO] GPU and WebGL capability notice:
echo This application requires WebGL. Make sure your graphics drivers are up to date.
echo.

echo =============================================
echo ✓ Setup complete! You can now run the app using run_windows.bat
echo Setup finished at: %TIME%
echo =============================================
echo.
echo Press any key to exit setup...
pause