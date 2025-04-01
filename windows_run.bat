@echo off
:: BusiHealth RPData Update and Run Script for Windows
:: Run this after git pull to update dependencies and launch the app

echo ================================================
echo  BusiHealth RPData - Update and Run
echo ================================================
echo.

:: Check if virtual environment exists
if not exist venv (
    echo Virtual environment not found. Please run build_local_windows.bat first.
    pause
    exit /b 1
)

:: Activate the virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo Failed to activate virtual environment.
    echo Please run build_local_windows.bat to set up the environment.
    pause
    exit /b 1
)

:: Update dependencies
echo Checking for dependency updates...
python -m pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo Warning: Some dependencies may not have updated correctly.
    echo You might need to run build_local_windows.bat if you encounter issues.
    echo.
    echo Press any key to continue anyway...
    pause > nul
)

echo.
echo ================================================
echo  Starting BusiHealth RPData...
echo ================================================
echo.

:: Run the application
python app.py

:: If application exits with error
if %errorlevel% neq 0 (
    echo.
    echo Application exited with an error. 
    echo If you're experiencing issues, try running build_local_windows.bat
    echo to perform a complete rebuild.
)

echo.
pause
exit /b 0