@echo off
:: BusiHealth RPData Installer for Windows
:: This script handles Python installation and environment setup

echo ======================================================
echo   BusiHealth RPData Setup - Windows Installation
echo ======================================================
echo.

:: Check if running as administrator
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo This script requires administrator privileges.
    echo Please right-click on this file and select "Run as administrator".
    echo.
    pause
    exit /b 1
)

:: Create a log file
echo Starting installation at %date% %time% > setup_log.txt

:: Check if Python is installed
echo Checking for Python installation...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found. We need to install Python first. >> setup_log.txt
    echo Python not found. We'll download and install it now.
    
    :: Create a temporary directory for downloads
    mkdir temp_downloads 2>nul
    cd temp_downloads
    
    :: Download Python installer
    echo Downloading Python 3.10...
    powershell -Command "(New-Object Net.WebClient).DownloadFile('https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe', 'python_installer.exe')"
    
    if not exist python_installer.exe (
        echo Failed to download Python installer. >> ..\setup_log.txt
        echo Failed to download Python installer.
        echo Please check your internet connection or try manual installation.
        cd ..
        goto :error
    )
    
    :: Install Python with PATH option enabled
    echo Installing Python 3.10 (this may take a few minutes)...
    echo Make sure to check "Add Python 3.10 to PATH" if an installer appears!
    start /wait "" python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    
    :: Return to the original directory and clean up
    cd ..
    rmdir /s /q temp_downloads

    :: Verify Python installation
    echo Verifying Python installation...
    where python >nul 2>&1
    if %errorlevel% neq 0 (
        echo Python installation failed. Unable to find Python in PATH. >> setup_log.txt
        echo The Python installation didn't add Python to your PATH.
        echo.
        echo Please install Python manually:
        echo 1. Download Python 3.10 from https://www.python.org/downloads/
        echo 2. During installation, CHECK the box for "Add Python 3.10 to PATH"
        echo 3. Run this script again after installation
        echo.
        goto :error
    )
    
    echo Python installed successfully! >> setup_log.txt
) else (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo %PYTHON_VERSION% is already installed. >> setup_log.txt
    echo %PYTHON_VERSION% is already installed.
)

:: Check if Chrome is installed
echo.
echo Checking for Google Chrome...
if not exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" (
    if not exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" (
        echo Chrome not found. Downloading Chrome... >> setup_log.txt
        echo Chrome not found. Downloading Chrome installer...
        
        :: Create a temporary directory for downloads
        mkdir temp_downloads 2>nul
        cd temp_downloads
        
        :: Download Chrome installer
        powershell -Command "(New-Object Net.WebClient).DownloadFile('https://dl.google.com/chrome/install/latest/chrome_installer.exe', 'chrome_installer.exe')"
        
        if not exist chrome_installer.exe (
            echo Failed to download Chrome installer. >> ..\setup_log.txt
            echo Failed to download Chrome installer.
            echo Please check your internet connection or install Chrome manually.
            cd ..
            goto :error
        )
        
        :: Install Chrome
        echo Installing Google Chrome (this may take a few minutes)...
        start /wait "" chrome_installer.exe /silent /install
        
        :: Return to the original directory and clean up
        cd ..
        rmdir /s /q temp_downloads
        
        echo Chrome installation completed. >> setup_log.txt
    ) else (
        echo Google Chrome (32-bit) is already installed. >> setup_log.txt
        echo Google Chrome (32-bit) is already installed.
    )
) else (
    echo Google Chrome (64-bit) is already installed. >> setup_log.txt
    echo Google Chrome (64-bit) is already installed.
)

:: Set directory permissions for project directories
echo.
echo Setting up project directories...
if not exist downloads mkdir downloads
if not exist merged_properties mkdir merged_properties
if not exist tmp mkdir tmp

echo Setting directory permissions...
icacls downloads /grant Everyone:F
icacls merged_properties /grant Everyone:F
icacls tmp /grant Everyone:F
echo Directories set up. >> setup_log.txt

:: Set up Python virtual environment
echo.
echo Setting up Python virtual environment...
python -m venv venv
if %errorlevel% neq 0 (
    echo Failed to create virtual environment. >> setup_log.txt
    echo Failed to create virtual environment.
    echo Trying alternative method with the venv module...
    
    python -m pip install --upgrade pip
    python -m pip install virtualenv
    python -m virtualenv venv
    
    if %errorlevel% neq 0 (
        echo Virtual environment creation failed with both methods. >> setup_log.txt
        echo Failed to create a virtual environment.
        echo.
        echo Please try running these commands manually:
        echo python -m pip install virtualenv
        echo python -m virtualenv venv
        echo.
        goto :error
    )
)

:: Activate the virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo Failed to activate virtual environment. >> setup_log.txt
    echo Failed to activate the virtual environment.
    echo Please try running this command manually:
    echo call venv\Scripts\activate.bat
    goto :error
)

:: Set the PATH to include the virtual environment's Scripts directory
set PATH=%cd%\venv\Scripts;%PATH%

:: Update pip to the latest version
echo.
echo Upgrading pip...
python -m pip install --upgrade pip
if %errorlevel% neq 0 (
    echo Failed to upgrade pip. >> setup_log.txt
    echo Failed to upgrade pip, but continuing with installation...
)

:: Install required Python packages
echo.
echo Installing required Python packages (this may take several minutes)...
echo Installing packages... >> setup_log.txt

:: Install packages in smaller groups to avoid command line length limits
python -m pip install flask==2.3.3 flask-cors==4.0.0
python -m pip install selenium==4.29.0 undetected-chromedriver==3.5.5
python -m pip install pandas==2.2.3 openpyxl==3.1.2
python -m pip install webdriver-manager==4.0.0 requests==2.31.0
python -m pip install Pillow==10.0.0 Werkzeug==2.3.7 lxml

:: Check if requirements.txt exists and install from it
if exist requirements.txt (
    echo Installing packages from requirements.txt...
    python -m pip install -r requirements.txt
)

:: Create a run script for easy execution
echo.
echo Creating startup script...
echo @echo off > run_app.bat
echo echo Starting BusiHealth RPData application... >> run_app.bat
echo call "%cd%\venv\Scripts\activate.bat" >> run_app.bat
echo echo. >> run_app.bat
echo python app.py >> run_app.bat
echo if %%errorlevel%% neq 0 ( >> run_app.bat
echo   echo Error running application. Please contact support. >> run_app.bat
echo   pause >> run_app.bat
echo   exit /b 1 >> run_app.bat
echo ) >> run_app.bat
echo pause >> run_app.bat

echo.
echo ======================================================
echo   Installation Complete!
echo ======================================================
echo.
echo To run the application:
echo 1. Double-click the "run_app.bat" file that was created
echo    OR
echo 2. Open Command Prompt in this directory
echo 3. Type: call venv\Scripts\activate.bat
echo 4. Type: python app.py
echo.
echo After starting the application, open your browser and go to:
echo http://localhost:5000
echo.
echo Installation successful! >> setup_log.txt

:: Offer to run the application now
set /p run_now="Would you like to run the application now? (y/n): "
if /i "%run_now%"=="y" (
    echo Starting application...
    start cmd /k "call venv\Scripts\activate.bat && python app.py"
    echo Application started in a new window. Open http://localhost:5000 in your browser.
) else (
    echo You can run the application later using run_app.bat
)

goto :eof

:error
echo.
echo ======================================================
echo   Setup encountered errors
echo ======================================================
echo Please review the error messages above.
echo For additional help, check the setup_log.txt file.
echo.
echo If you need to troubleshoot Python:
echo 1. Try typing "python --version" in a new Command Prompt
echo 2. If that doesn't work, your Python installation may have issues
echo.
pause
exit /b 1