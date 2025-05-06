# Property Scraper - Windows Installation Guide

## Prerequisites

- **Google Chrome version 136** (critical for compatibility with ChromeDriver)
- Administrative access to your computer
- Windows 10 or newer

## Setup Instructions

1. **Update Chrome**:
   - Open Chrome
   - Click the three dots in the top-right corner
   - Go to Help → About Google Chrome
   - Chrome will update automatically if needed
   - Restart Chrome when prompted

2. **Download the Project**:
   - Clone or download the repository to your computer
   - Extract the ZIP file if necessary

3. **Run Setup**:
   - Double-click the `build_windows.bat` file
   - If Windows Security warning appears, click "More info" then "Run anyway"
   - The script will automatically install Python if needed
   - The setup process takes about 5-10 minutes to complete
   - When you see "Setup complete!" the installation is finished

## Running the Application

1. Double-click the `run_windows.bat` file

2. The application will automatically:
   - Open in your default browser at http://127.0.0.1:8000
   - Use hardware-accelerated WebGL for map rendering

3. To stop the application:
   - Press CTRL+C in the command window
   - Press any key to close it

## Troubleshooting

- **WebGL Issues**: If maps don't render properly, update your graphics drivers
- **Chrome Version Issues**: Make sure Chrome is updated to version 136
- **Windows Defender Alerts**: The scripts are safe but may trigger security warnings
- **Downloads Not Working**: Make sure Chrome version 136 is installed and restart app
- **"Not Recognized as an Internal Command"**: Run the setup script again