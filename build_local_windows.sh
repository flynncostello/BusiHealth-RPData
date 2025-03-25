@echo on
:: RPData Scraper Setup Script for Windows - Installs everything from scratch

echo Setting up on Windows...

:: Check if Python is installed
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Python not found. Downloading Python installer...
    
    :: Create temp directory and download Python
    mkdir temp_downloads 2>nul
    cd temp_downloads
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe' -OutFile 'python_installer.exe'"
    
    :: Install Python
    echo Installing Python 3.10...
    echo IMPORTANT: Please check "Add Python 3.10 to PATH" in the installer!
    start /wait python_installer.exe /passive PrependPath=1
    
    :: Return to original directory
    cd ..
    rmdir /s /q temp_downloads
    
    :: Refresh environment variables
    echo Refreshing environment variables...
    call refreshenv.cmd
    if %ERRORLEVEL% neq 0 (
        echo Please close this window and reopen a new command prompt
        echo Then run this script again.
        pause
        exit /b 1
    )
)

:: Check if Chrome is installed
if not exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" (
    if not exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" (
        echo Chrome not found. Downloading Chrome installer...
        
        :: Create temp directory and download Chrome
        mkdir temp_downloads 2>nul
        cd temp_downloads
        powershell -Command "Invoke-WebRequest -Uri 'https://dl.google.com/chrome/install/latest/chrome_installer.exe' -OutFile 'chrome_installer.exe'"
        
        :: Install Chrome
        echo Installing Google Chrome...
        start /wait chrome_installer.exe /silent /install
        
        :: Return to original directory
        cd ..
        rmdir /s /q temp_downloads
    )
)

:: Set permissions for existing directories
echo Setting directory permissions...
icacls downloads /grant Everyone:F
icacls merged_properties /grant Everyone:F
icacls tmp /grant Everyone:F

:: Create Python virtual environment
echo Creating virtual environment...
python -m venv venv

:: Activate virtual environment
call venv\Scripts\activate.bat

:: Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

:: Install Python packages
echo Installing Python packages...
pip install flask==2.3.3 flask-cors==4.0.0 selenium==4.29.0 undetected-chromedriver==3.5.5 pandas==2.2.3 requests==2.31.0 openpyxl==3.1.2 webdriver-manager==4.0.0 Pillow==10.0.0 Werkzeug==2.3.7 lxml

:: Install from requirements.txt if it exists
if exist requirements.txt (
    pip install -r requirements.txt
)

:: Create a simple run script for convenience
echo @echo off > run_app.bat
echo call venv\Scripts\activate.bat >> run_app.bat
echo python app.py >> run_app.bat
echo pause >> run_app.bat

echo Setup complete! Run the application with:
echo call venv\Scripts\activate.bat ^&^& python app.py
echo.
echo Or simply double-click the "run_app.bat" file that was created.

pause