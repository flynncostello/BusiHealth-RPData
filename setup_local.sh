#!/bin/bash

# Setup script for local development of RP Data Scraper

# Exit on any error
set -e

# Print each command
set -x

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p downloads merged_properties tmp

# Check if Chrome is installed (for Mac)
if [[ "$OSTYPE" == "darwin"* ]]; then
    if [ ! -d "/Applications/Google Chrome.app" ]; then
        echo "Google Chrome not found. Please install Chrome browser."
        echo "You can download it from: https://www.google.com/chrome/"
        exit 1
    fi
fi

# Check if Chrome is installed (for Linux)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if ! command -v google-chrome &> /dev/null; then
        echo "Google Chrome not found. Please install Chrome browser."
        echo "On Ubuntu/Debian, you can install it with:"
        echo "wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb"
        echo "sudo apt install ./google-chrome-stable_current_amd64.deb"
        exit 1
    fi
fi

echo "==================================================="
echo "Setup complete! To run the application locally:"
echo "source venv/bin/activate"
echo "python app.py"
echo "==================================================="
echo "Or use: flask run --host=0.0.0.0 --port=5000"
echo "==================================================="