# macOS Setup Instructions for BusiHealth RPData

## Step 1: Open Terminal
1. Click on the **Spotlight Search** icon (magnifying glass) in the top-right corner of your screen
2. Type "Terminal" and press Enter
3. A Terminal window will open

## Step 2: Clone the Repository to Your Desktop
1. In Terminal, type the following commands exactly as shown:

```bash
cd ~/Desktop
git clone https://github.com/flynncostello/BusiHealth-RPData.git
```

2. If you're asked for your GitHub username and password, enter them
3. Wait for the repository to be downloaded. You should see progress messages ending with "done"

## Step 3: Navigate to the Repository
```bash
cd ~/Desktop/BusiHealth-RPData
```

## Step 4: Make the Setup Script Executable
```bash
chmod +x build_local_mac.sh
```

## Step 5: Run the Setup Script
```bash
./build_local_mac.sh
```

During this process:
- You may be prompted for your system password to install software
- If you don't have Xcode Command Line Tools, a pop-up will appear asking to install them - click "Install" and wait for it to complete
- The entire setup may take 5-10 minutes depending on your internet speed
- Various messages will appear as the script installs Homebrew, Python, and other requirements

## Step 6: Run the Application
After the setup completes, you will see a message that setup is complete. To run the application:

```bash
source venv/bin/activate
python3 app.py
```

## Step 7: Access the Web Application
1. Open any web browser (Safari, Chrome, etc.)
2. In the address bar, type:
   ```
   http://localhost:5000
   ```
   (If you see an error, try port 8080 instead: `http://localhost:8080`)

3. The BusiHealth RPData application should now be displayed in your browser

## Subsequent Use
Once you've completed the setup, you can run the application any time by:

1. Opening Terminal
2. Running:
   ```bash
   cd ~/Desktop/BusiHealth-RPData
   source venv/bin/activate
   python3 app.py
   ```

Or use the shortcut script we created:
   ```bash
   cd ~/Desktop/BusiHealth-RPData
   ./run_app.sh
   ```

## Troubleshooting
- If you see "permission denied" errors, run `chmod +x build_local_mac.sh` again
- If the browser shows "This site can't be reached", make sure the app is running in Terminal (you should see messages there)
- To stop the application, press CTRL+C in the Terminal window