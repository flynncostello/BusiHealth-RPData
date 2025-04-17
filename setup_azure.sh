#!/bin/bash
# Chrome installation for Azure App Service

# Log all output
exec > /home/LogFiles/chrome_setup.log 2>&1
echo "Chrome setup started: $(date)"

# Create directories
mkdir -p downloads merged_properties tmp

# Install Chrome if not present
if ! command -v google-chrome &> /dev/null; then
    echo "Installing Chrome..."
    cd /tmp
    wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
    apt-get update
    apt-get install -y ./google-chrome-stable_current_amd64.deb || true
    echo "Chrome installation completed: $(google-chrome --version || echo 'FAILED')"
else
    echo "Chrome already installed: $(google-chrome --version)"
fi

echo "Setup completed: $(date)"