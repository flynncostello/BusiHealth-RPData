@echo off
:: BusiHealth RPData Setup Script for Windows
:: Fixed version to handle Python not found errors

echo ================================================
echo  BusiHealth RPData Setup - Windows Installation
echo ================================================
echo.

:: Define Python installer location and Python path variables
set PYTHON_INSTALLER=python-3.10.11-amd64.exe
set PYTHONPATH=

:: First check if Python is in PATH
echo Checking for Python installation...
where python >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('where python') do set PYTHONPATH=%%i
    echo Found Python at: %PYTHONPATH%
) else (
    echo Python not found in PATH.
    
    :: Check common installation locations
    if exist "C:\Python310\python.exe" (
        set PYTHONPATH=C:\Python310\python.exe
        echo Found Python at: %PYTHONPATH%
    ) else if exist "C:\Program Files\Python310\python.exe" (
        set PYTHONPATH=C:\Program Files\Python310\python.exe
        echo Found Python at: %PYTHONPATH%
    ) else if exist "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python310\python.exe" (
        set PYTHONPATH=C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python310\python.exe
        echo Found Python at: %PYTHONPATH%
    ) else (
        echo Python installation not found. Will install now.
        
        :: Download Python installer
        echo Downloading Python installer...
        if not exist %PYTHON_INSTALLER% (
            echo Downloading from python.org...
            powershell -Command "(New-Object Net.WebClient).DownloadFile('https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe', '%PYTHON_INSTALLER%')"
            
            if not exist %PYTHON_INSTALLER% (
                echo Failed to download Python installer.
                echo.
                echo MANUAL STEPS REQUIRED:
                echo 1. Download Python 3.10 from https://www.python.org/downloads/release/python-31011/
                echo 2. Run the installer and CHECK "Add Python 3.10 to PATH"
                echo 3. Restart your computer
                echo 4. Run this setup script again
                echo.
                goto error_exit
            )
        )
        
        :: Install Python with explicit PATH option
        echo.
        echo Installing Python 3.10...
        echo *** IMPORTANT: If an installer window appears, CHECK "Add Python to PATH" ***
        echo.
        start /wait "" %PYTHON_INSTALLER% /passive InstallAllUsers=1 PrependPath=1 Include_test=0
        
        :: After installation, find the Python executable
        if exist "C:\Python310\python.exe" (
            set PYTHONPATH=C:\Python310\python.exe
        ) else if exist "C:\Program Files\Python310\python.exe" (
            set PYTHONPATH=C:\Program Files\Python310\python.exe
        ) else if exist "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python310\python.exe" (
            set PYTHONPATH=C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python310\python.exe
        ) else (
            echo.
            echo Python was installed but we cannot find the executable.
            echo You may need to restart your computer for PATH changes to take effect.
            echo.
            echo MANUAL STEPS:
            echo 1. Restart your computer
            echo 2. Run this setup script again
            echo.
            goto error_exit
        )
    )
)

:: At this point, PYTHONPATH should contain the path to python.exe
echo Using Python at: %PYTHONPATH%
echo.

:: Download Chrome if not installed
echo Checking for Chrome installation...
if not exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" (
    if not exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" (
        echo Chrome not found. Downloading Chrome installer...
        
        if not exist chrome_installer.exe (
            powershell -Command "(New-Object Net.WebClient).DownloadFile('https://dl.google.com/chrome/install/latest/chrome_installer.exe', 'chrome_installer.exe')"
            
            if not exist chrome_installer.exe (
                echo Failed to download Chrome installer.
                echo.
                echo MANUAL STEPS REQUIRED:
                echo 1. Download Chrome from https://www.google.com/chrome/
                echo 2. Install Chrome
                echo 3. Run this setup script again
                echo.
                goto error_exit
            )
        )
        
        echo Installing Google Chrome...
        start /wait "" chrome_installer.exe /silent /install
        
        :: Verify Chrome installation
        if not exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" (
            if not exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" (
                echo Chrome installation may have failed.
                echo.
                echo MANUAL STEPS REQUIRED:
                echo 1. Download Chrome from https://www.google.com/chrome/
                echo 2. Install Chrome manually
                echo 3. Run this setup script again
                echo.
                goto error_exit
            )
        )
    )
)
echo Chrome is installed.
echo.

:: Create required directories if they don't exist
echo Setting up project directories...
if not exist downloads mkdir downloads
if not exist merged_properties mkdir merged_properties
if not exist tmp mkdir tmp

:: Set permissions
echo Setting directory permissions...
icacls downloads /grant Everyone:F >nul 2>&1
icacls merged_properties /grant Everyone:F >nul 2>&1
icacls tmp /grant Everyone:F >nul 2>&1
echo Directory permissions set.
echo.

:: Create Python virtual environment
echo Creating Python virtual environment...
if exist venv (
    echo Virtual environment already exists. Removing old environment...
    rmdir /s /q venv
)

"%PYTHONPATH%" -m venv venv
if %errorlevel% neq 0 (
    echo Failed to create virtual environment with venv module.
    echo Trying alternative method with virtualenv...
    
    "%PYTHONPATH%" -m pip install virtualenv
    "%PYTHONPATH%" -m virtualenv venv
    
    if %errorlevel% neq 0 (
        echo Failed to create virtual environment.
        echo.
        echo MANUAL STEPS REQUIRED:
        echo 1. Open a new Command Prompt
        echo 2. Run: "%PYTHONPATH%" -m pip install virtualenv
        echo 3. Run: "%PYTHONPATH%" -m virtualenv venv
        echo 4. If those commands succeed, run this script again
        echo.
        goto error_exit
    )
)

:: Activate the virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo Failed to activate virtual environment.
    echo.
    echo MANUAL STEPS REQUIRED:
    echo 1. Open a new Command Prompt
    echo 2. Navigate to this directory: cd %CD%
    echo 3. Run: call venv\Scripts\activate.bat
    echo 4. If that succeeds, continue with manual package installation
    echo.
    goto error_exit
)

:: Store the path to Python in the virtual environment
set VENV_PYTHON="%CD%\venv\Scripts\python.exe"
set VENV_PIP="%CD%\venv\Scripts\pip.exe"

:: Update pip
echo Updating pip...
%VENV_PYTHON% -m pip install --upgrade pip

:: Install Python packages one by one to avoid errors
echo Installing Python packages (this may take a few minutes)...
%VENV_PIP% install flask==2.3.3
%VENV_PIP% install flask-cors==4.0.0
%VENV_PIP% install selenium==4.29.0
%VENV_PIP% install undetected-chromedriver==3.5.5
%VENV_PIP% install pandas==2.2.3
%VENV_PIP% install openpyxl==3.1.2
%VENV_PIP% install webdriver-manager==4.0.0
%VENV_PIP% install requests==2.31.0
%VENV_PIP% install Pillow==10.0.0
%VENV_PIP% install Werkzeug==2.3.7
%VENV_PIP% install lxml

:: Create run script with absolute paths to avoid PATH issues
echo Creating application run script...
echo @echo off > run_app.bat
echo echo Starting BusiHealth RPData... >> run_app.bat
echo set PYTHONPATH=%CD%\venv\Scripts\python.exe >> run_app.bat
echo call "%CD%\venv\Scripts\activate.bat" >> run_app.bat
echo if %%errorlevel%% neq 0 ( >> run_app.bat
echo   echo Failed to activate environment. >> run_app.bat
echo   pause >> run_app.bat
echo   exit /b 1 >> run_app.bat
echo ) >> run_app.bat
echo echo. >> run_app.bat
echo "%CD%\venv\Scripts\python.exe" app.py >> run_app.bat
echo if %%errorlevel%% neq 0 ( >> run_app.bat
echo   echo Error running application. Please check for error messages above. >> run_app.bat
echo   pause >> run_app.bat
echo   exit /b 1 >> run_app.bat
echo ) >> run_app.bat
echo pause >> run_app.bat

echo.
echo ================================================
echo  Setup Complete!
echo ================================================
echo.
echo To run the application:
echo 1. Double-click the "run_app.bat" file in this folder
echo    OR
echo 2. Run these commands:
echo    call venv\Scripts\activate.bat
echo    python app.py
echo.
echo After starting, open your browser to:
echo http://localhost:5000
echo.

echo Setup completed successfully!
pause
exit /b 0

:error_exit
echo.
echo Setup failed. Please see error messages above.
echo.
pause
exit /b 1