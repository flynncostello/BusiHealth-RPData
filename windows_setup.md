# Windows Setup Instructions for BusiHealth RPData

## Step 1: Open Command Prompt as Administrator
1. Press the **Windows key** on your keyboard
2. Type "cmd"
3. Right-click on "Command Prompt" in the search results
4. Select "Run as administrator"
5. Click "Yes" if a User Account Control prompt appears

## Step 2: Install Git (if not already installed)
   ```
   winget install --id Git.Git -e --source winget
   ```
   * Close and open a new terminal
   
4. After installation completes, close the Command Prompt window and open a new one as administrator (repeat Step 1)

## Step 3: Clone the Repository to Your Desktop
1. Navigate to your Desktop:
   ```
   cd %USERPROFILE%\Desktop
   ```
   * Or open the desktop window and copy the path at the top (right-click and copy)

2. Clone the repository:
   ```
   git clone https://github.com/flynncostello/BusiHealth-RPData.git
   ```

3. Wait for the download to complete. You'll see progress messages ending with "done"

## Step 4: Navigate to the Repository
```
cd %USERPROFILE%\Desktop\BusiHealth-RPData
```

## Step 4.5: Install Python
Go to windows app store an install python 3.10 (DON'T NEED TO DO AS THE BUILD SCRIPT INSTALLS IT)


## Step 5: Run the Setup Script
```
build_local_windows.bat
```

* Now you can go into the folder and double click the run_app.bat --> Will open in chrome 






During this process:
- You may see several windows pop up as Python and Chrome are installed
- If a Python installer window appears, make sure to check "Add Python to PATH" before continuing
- The setup may take 5-15 minutes depending on your internet speed
- Various messages will appear in the Command Prompt window

## Step 6: Run the Application
After the setup completes successfully, you will see a message that setup is complete. To run the application:

```
call venv\Scripts\activate.bat
python app.py
```

Or, more simply, double-click the `run_app.bat` file that was created during setup.

## Step 7: Access the Web Application
1. Open any web browser (Edge, Chrome, Firefox, etc.)
2. In the address bar, type:
   ```
   http://localhost:5000
   ```
   (If you see an error, try port 8080 instead: `http://localhost:8080`)

   Run data - 'Hunters Hill NSW 2110, Crows Nest NSW 2065'

3. The BusiHealth RPData application should now be displayed in your browser

## Subsequent Use
Once you've completed the setup, you can run the application any time by either:

1. Navigate to the folder in File Explorer and double-click `run_app.bat`

OR

2. Open Command Prompt and run:
   ```
   cd %USERPROFILE%\Desktop\BusiHealth-RPData
   call venv\Scripts\activate.bat
   python app.py
   ```

## Troubleshooting
- If you see "Python is not recognized as an internal or external command", you need to reinstall Python and make sure to check "Add Python to PATH"
- If "This site can't be reached" appears in the browser, make sure the app is running in Command Prompt (you should see messages there)
- If you see any error messages during setup, take a screenshot and share it with your IT support
- To stop the application, press CTRL+C in the Command Prompt window, then type "Y" and press Enter