#!/bin/bash
# Setup script for RP Data Scraper on Azure

# Exit on any error
set -e

# Print each command for debugging
set -x

# Install Chrome
echo "Installing Chrome..."
curl -sS -o - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list
apt-get -y update
apt-get -y install google-chrome-stable

# Create necessary directories
mkdir -p downloads merged_properties tmp

# Log the Chrome installation and version
echo "Chrome installed successfully: $(google-chrome --version)"

# Log completion
echo "===================================================" 
echo "Azure setup complete!" 
echo "==================================================="