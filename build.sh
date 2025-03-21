#!/usr/bin/env bash
set -e
set -x

echo "Starting Render build process..."

# Define Chrome installation directory (use /tmp since it's writable)
CHROME_DIR="/tmp/chrome"
CHROME_BINARY="$CHROME_DIR/google-chrome"

# If Chrome isn't already installed, install it
if [ ! -f "$CHROME_BINARY" ]; then
  echo "Installing Google Chrome..."

  mkdir -p "$CHROME_DIR"

  # Download the Chrome .deb package
  wget -O /tmp/chrome.deb "https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb"

  # Extract Chrome without using `dpkg -i` (which requires sudo)
  dpkg-deb -x /tmp/chrome.deb "$CHROME_DIR"
  rm /tmp/chrome.deb

  # Locate Chrome binary inside extracted files
  CHROME_BINARY=$(find "$CHROME_DIR" -name "google-chrome" | head -n 1)
  
  if [ -n "$CHROME_BINARY" ]; then
    chmod +x "$CHROME_BINARY"
    echo "Chrome installed at: $CHROME_BINARY"
  else
    echo "ERROR: Chrome installation failed!"
    exit 1
  fi
else
  echo "Google Chrome is already installed."
fi

# Export Chrome binary path for use in the app
echo "export CHROME_BINARY_PATH=$CHROME_BINARY" >> "$HOME/.bashrc"
export CHROME_BINARY_PATH="$CHROME_BINARY"

# Verify Chrome binary is set correctly
if [ ! -x "$CHROME_BINARY_PATH" ]; then
  echo "ERROR: Chrome binary is not executable!"
  exit 1
fi

echo "Final Chrome path: $CHROME_BINARY_PATH"

# Create necessary directories with correct permissions
mkdir -p downloads merged_properties tmp
chmod -R 777 downloads merged_properties tmp

echo "==================================="
echo "Render Build Complete!"
echo "Chrome is at: $CHROME_BINARY_PATH"
echo "==================================="
