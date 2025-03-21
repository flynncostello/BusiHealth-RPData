#!/bin/bash
# RPData Scraper Setup Script - Installs everything from scratch

# Show commands as they execute
set -x

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    echo "Setting up on macOS..."
    
    # Install Homebrew if not installed
    if ! command -v brew &>/dev/null; then
        echo "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    
    # Install Python and Chrome
    brew install python
    
    # Check if Chrome is installed
    if [ ! -d "/Applications/Google Chrome.app" ]; then
        echo "Please install Chrome manually from https://www.google.com/chrome/"
        echo "Then run this script again."
        exit 1
    fi
    
else
    # Linux
    echo "Setting up on Linux..."
    
    # Update package lists
    sudo apt update
    
    # Install Python and required system packages
    sudo apt install -y python3 python3-pip python3-venv wget build-essential
    
    # Install Chrome
    if ! command -v google-chrome &>/dev/null; then
        wget -q -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
        sudo apt install -y /tmp/chrome.deb
        rm /tmp/chrome.deb
    fi
fi

# Create directories
mkdir -p downloads merged_properties tmp
chmod -R 777 downloads merged_properties tmp

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Python packages
pip install flask flask-cors selenium undetected-chromedriver>=3.0.0 pandas requests openpyxl lxml werkzeug

# Install packages from requirements.txt if it exists
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
fi

echo "Setup complete! Run the application with:"
echo "source venv/bin/activate && python3 app.py"