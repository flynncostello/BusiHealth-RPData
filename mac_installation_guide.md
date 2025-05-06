# Property Scraper - Mac Installation Guide

## Prerequisites

- **Google Chrome version 136** (critical for compatibility with ChromeDriver)
- MacOS 10.15 or newer
- Admin privileges on your Mac

## Setup Instructions

1. **Update Chrome**:
   - Open Chrome
   - Click "Chrome" in the menu bar
   - Select "About Google Chrome"
   - Chrome will update automatically if needed
   - Restart Chrome when prompted

2. **Download the Project**:
   - Clone or download the repository to your computer
   - Open Terminal (from Applications → Utilities → Terminal)
   - Navigate to the project folder: `cd path/to/folder`

3. **Run Setup**:
   - Make the setup script executable: `chmod +x build_mac.sh`
   - Run the setup script: `./build_mac.sh`
   - The script will take 5-10 minutes to complete
   - Wait for "Build complete!" message

## Running the Application

1. In Terminal, run the application script:
   ```
   ./run_mac.sh
   ```
   - If you get a permissions error, run: `chmod +x run_mac.sh` first

2. The application will open at http://127.0.0.1:8000 in your browser

3. To stop the application, press CTRL+C in the Terminal window

## Troubleshooting

- **M1/M2/M3 Mac Support**: The scripts handle Apple Silicon automatically
- **WebGL Issues**: If maps don't render, update your graphics drivers
- **Chrome Version Issues**: Make sure to update Chrome to version 136
- **Downloads Not Working**: Restart the application after updating Chrome
- **File Permission Errors**: Run `chmod +x *.sh` to make all scripts executable