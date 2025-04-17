#!/bin/bash
# Chrome installation for Azure Web App

# Make script exit on any error
set -e

# Log all output
LOGFILE="/home/LogFiles/chrome_setup.log"
exec > >(tee -a "$LOGFILE") 2>&1

echo "Chrome setup started: $(date)"

# Create directories (backup in case the Python code didn't create them)
mkdir -p downloads merged_properties tmp

# Install Chrome if not present
if ! command -v google-chrome &> /dev/null; then
    echo "Installing Chrome..."
    
    # Try direct download method
    cd /tmp
    wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb || echo "Chrome download failed, but continuing..."
    
    # Install Chrome
    apt-get update -y || echo "apt-get update failed, but continuing..."
    apt-get install -y ./google-chrome-stable_current_amd64.deb || echo "Chrome installation failed, but continuing..."
    
    # Verify installation
    if command -v google-chrome &> /dev/null; then
        echo "Chrome installation successful: $(google-chrome --version)"
    else
        echo "WARNING: Chrome installation may have issues. Web scraping might not work."
    fi
else
    echo "Chrome already installed: $(google-chrome --version)"
fi

echo "Setup completed: $(date)"
exit 0