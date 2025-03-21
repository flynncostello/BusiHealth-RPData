#!/usr/bin/env bash
set -e
set -x

echo "Starting build process on Render..."

# Define Chrome installation directory
CHROME_DIR="$HOME/chrome"
CHROME_BINARY="$CHROME_DIR/google-chrome"

# Check if Chrome is already installed
if [ -f "$CHROME_BINARY" ]; then
  echo "Google Chrome is already installed."
else
  echo "Installing Google Chrome..."

  # Create installation directory
  mkdir -p "$CHROME_DIR"

  # Download and extract Chrome
  wget -O /tmp/chrome.tar.gz "https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb"
  ar x /tmp/chrome.tar.gz
  tar -xvf data.tar.xz -C "$CHROME_DIR"
  rm /tmp/chrome.tar.gz data.tar.xz control.tar.xz debian-binary

  # Set the Chrome binary path
  CHROME_BINARY=$(find "$CHROME_DIR" -name "google-chrome" | head -n 1)
  
  if [ -n "$CHROME_BINARY" ]; then
    chmod +x "$CHROME_BINARY"
    echo "Chrome installed at: $CHROME_BINARY"
  else
    echo "ERROR: Chrome installation failed!"
    exit 1
  fi
fi

# Ensure Chrome is in the PATH
export CHROME_BINARY_PATH="$CHROME_BINARY"
echo "export CHROME_BINARY_PATH=$CHROME_BINARY" >> "$HOME/.bashrc"

# Create necessary directories
mkdir -p downloads merged_properties tmp
chmod -R 777 downloads merged_properties tmp

echo "==================================="
echo "Build environment ready on Render!"
echo "Chrome is at: $CHROME_BINARY"
echo "==================================="
