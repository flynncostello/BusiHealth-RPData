@echo off
:: BusiHealth RPData Setup Script for Windows
:: Assumes Python and Chrome are already installed

echo ================================================
echo  BusiHealth RPData Setup - Windows Installation
echo ================================================
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

python -m venv venv
if %errorlevel% neq 0 (
    echo Failed to create virtual environment with venv module.
    echo Trying alternative method with virtualenv...
    
    python -m pip install virtualenv
    python -m virtualenv venv
    
    if %errorlevel% neq 0 (
        echo Failed to create virtual environment.
        echo.
        echo MANUAL STEPS REQUIRED:
        echo 1. Open a new Command Prompt
        echo 2. Run: python -m pip install virtualenv
        echo 3. Run: python -m virtualenv venv
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