@echo off
:: BusiHealth RPData Setup Script for Windows
:: This script installs everything needed to run the application

echo ================================================
echo  BusiHealth RPData Setup - Windows Installation
echo ================================================
echo.

:: Download Python if not installed
where python >nul 2>&1
if errorlevel 1 (
    echo Python not found. Downloading Python installer...
    
    :: Download Python installer
    mkdir temp_downloads 2>nul
    cd temp_downloads
    
    echo Downloading Python 3.10...
    powershell -Command "(New-Object Net.WebClient).DownloadFile('https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe', 'python_installer.exe')"
    
    if not exist python_installer.exe (
        echo Failed to download Python installer.
        echo Please download Python 3.10 from https://www.python.org/downloads/
        echo Make sure to check "Add Python to PATH" during installation.
        cd ..
        goto error_exit
    )
    
    echo Installing Python 3.10...
    echo IMPORTANT: If the installer appears, CHECK "Add Python 3.10 to PATH"
    start /wait python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    
    cd ..
    rmdir /s /q temp_downloads
    
    echo Refreshing environment variables...
    call RefreshEnv.cmd >nul 2>&1
    if errorlevel 1 (
        echo Please close this window and open a new Command Prompt
        echo Then run this script again.
        goto error_exit
    )
)

:: Download Chrome if not installed
if not exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" (
    if not exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" (
        echo Chrome not found. Downloading Chrome installer...
        
        mkdir temp_downloads 2>nul
        cd temp_downloads
        
        echo Downloading Chrome...
        powershell -Command "(New-Object Net.WebClient).DownloadFile('https://dl.google.com/chrome/install/latest/chrome_installer.exe', 'chrome_installer.exe')"
        
        if not exist chrome_installer.exe (
            echo Failed to download Chrome installer.
            echo Please download Chrome from https://www.google.com/chrome/
            cd ..
            goto error_exit
        )
        
        echo Installing Google Chrome...
        start /wait chrome_installer.exe /silent /install
        
        cd ..
        rmdir /s /q temp_downloads
    )
)

:: Set directory permissions
echo Setting directory permissions...
icacls downloads /grant Everyone:F >nul 2>&1
icacls merged_properties /grant Everyone:F >nul 2>&1
icacls tmp /grant Everyone:F >nul 2>&1

:: Create Python virtual environment
echo Creating Python virtual environment...
python -m venv venv
if errorlevel 1 (
    echo Failed to create virtual environment.
    echo Trying alternative method...
    
    python -m pip install virtualenv
    python -m virtualenv venv
    
    if errorlevel 1 (
        echo Failed to create virtual environment.
        goto error_exit
    )
)

:: Activate the virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo Failed to activate virtual environment.
    goto error_exit
)

:: Update pip
echo Updating pip...
python -m pip install --upgrade pip

:: Install Python packages
echo Installing Python packages (this may take a few minutes)...
python -m pip install flask==2.3.3
python -m pip install flask-cors==4.0.0
python -m pip install selenium==4.29.0
python -m pip install undetected-chromedriver==3.5.5
python -m pip install pandas==2.2.3
python -m pip install openpyxl==3.1.2
python -m pip install webdriver-manager==4.0.0
python -m pip install requests==2.31.0
python -m pip install Pillow==10.0.0
python -m pip install Werkzeug==2.3.7
python -m pip install lxml

:: Create run script
echo @echo off > run_app.bat
echo call venv\Scripts\activate.bat >> run_app.bat
echo python app.py >> run_app.bat
echo pause >> run_app.bat

echo.
echo ================================================
echo  Setup Complete!
echo ================================================
echo.
echo To run the application:
echo 1. Double-click the "run_app.bat" file
echo    OR
echo 2. Run these commands:
echo    call venv\Scripts\activate.bat
echo    python app.py
echo.
echo After starting, open your browser to:
echo http://localhost:5000
echo.

pause
exit /b 0

:error_exit
echo.
echo Setup failed. Please see error messages above.
echo.
pause
exit /b 1