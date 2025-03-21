#!/usr/bin/env bash
# Ensure script exits on first error and prints commands
set -e
set -x

echo "Starting build process on Render..."

# Update package lists
apt-get update -qq

# Install minimal dependencies for Chrome
apt-get install -y --no-install-recommends wget gnupg ca-certificates

# Add Google Chrome repository with proper error handling for Render
echo "Adding Google Chrome repository..."
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - > /dev/null 2>&1 || {
  echo "Failed to add Google signing key. Trying alternate method..."
  mkdir -p /etc/apt/trusted.gpg.d/
  wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor > /etc/apt/trusted.gpg.d/google.gpg
}

echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google.list

# Update package lists with new repository
apt-get update -qq

# Install Chrome with specific version to ensure compatibility with undetected-chromedriver
echo "Installing Google Chrome..."
apt-get install -y --no-install-recommends google-chrome-stable

# Print Chrome version and location
echo "Chrome version installed:"
google-chrome-stable --version || google-chrome --version

echo "Chrome binary location:"
CHROME_PATH=$(which google-chrome-stable || which google-chrome)
echo $CHROME_PATH

# Create a symlink to ensure Chrome is in a standard location
if [ -n "$CHROME_PATH" ]; then
  ln -sf $CHROME_PATH /usr/bin/chrome
  echo "Created symlink to Chrome at /usr/bin/chrome -> $CHROME_PATH"
  # Make sure it's executable
  chmod +x /usr/bin/chrome
else
  echo "ERROR: Chrome installation failed! Trying Chromium as fallback..."
  apt-get install -y --no-install-recommends chromium-browser
  CHROMIUM_PATH=$(which chromium-browser)
  if [ -n "$CHROMIUM_PATH" ]; then
    ln -sf $CHROMIUM_PATH /usr/bin/chrome
    echo "Created symlink to Chromium at /usr/bin/chrome -> $CHROMIUM_PATH"
    chmod +x /usr/bin/chrome
  else
    echo "FATAL ERROR: Neither Chrome nor Chromium could be installed!"
    exit 1
  fi
fi

# Print the final Chrome path that will be used
echo "Final Chrome binary path: $(readlink -f /usr/bin/chrome)"

# Add environment variables to indicate we're in Render and specify Chrome location
echo "export RENDER=true" >> /etc/environment
echo "export CHROME_BINARY_PATH=/usr/bin/chrome" >> /etc/environment

# These will be available in the current session too
export RENDER=true
export CHROME_BINARY_PATH=/usr/bin/chrome

# Install Xvfb for headless browser support
apt-get install -y --no-install-recommends xvfb

# Create necessary directories
mkdir -p downloads merged_properties tmp
chmod -R 777 downloads merged_properties tmp

# Clean up to reduce image size
apt-get clean
rm -rf /var/lib/apt/lists/*

echo "==================================="
echo "Build environment ready on Render!"
echo "Chrome is at: $(readlink -f /usr/bin/chrome)"
echo "==================================="