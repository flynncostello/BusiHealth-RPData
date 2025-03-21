RPData Scraper - Quick Setup

Setup (One-Time)

# Clone repository (if needed)

git clone https://github.com/flynncostello/BusiHealth-RPData
cd your-repo

# Make build script executable
chmod +x build_local.sh

# Run the build script (installs everything)
./build_local.sh



Run the Application

# Activate virtual environment
source venv/bin/activate

# Run the application
python3 app.py

Open browser: http://127.0.0.1:5000
Common Issues

If script fails, try: sudo ./build_local.sh
If "Address in use": Change port in app.py or restart computer


------------------
- PURE COMMANDS: -
------------------
Go to desktop
git clone https://github.com/flynncostello/BusiHealth-RPData
cd repo
chmod +x build_local.sh
./build_local.sh
source venv/bin/activate
python3 app.py
Open browser: http://127.0.0.1:5000