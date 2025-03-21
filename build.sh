#!/usr/bin/env bash
# Ensure script exits on first error and prints commands
set -e
set -x

echo "Starting build process on Render..."

# Check if Google Chrome is already installed
if command -v google-chrome-stable &>/dev/null; then
  echo "Google Chrome is already installed."
else
  echo "Installing Google Chrome..."

  # Download and install Chrome
  wget -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
  dpkg -i /tmp/chrome.deb || apt-get -f install -y
  rm /tmp/chrome.deb
fi

# Verify Chrome installation
echo "Chrome version installed:"
google-chrome-stable --version || google-chrome --version

# Ensure Chrome is available at /usr/bin/chrome
CHROME_PATH=$(command -v google-chrome-stable || command -v google-chrome)
if [ -n "$CHROME_PATH" ]; then
  ln -sf "$CHROME_PATH" /usr/bin/chrome
  echo "Created symlink to Chrome at /usr/bin/chrome -> $CHROME_PATH"
fi

# Set environment variables
export CHROME_BINARY_PATH="/usr/bin/chrome"
echo "export CHROME_BINARY_PATH=/usr/bin/chrome" >> "$HOME/.bashrc"

# Create necessary directories
mkdir -p downloads merged_properties tmp
chmod -R 777 downloads merged_properties tmp

echo "==================================="
echo "Build environment ready on Render!"
echo "Chrome is at: $(readlink -f /usr/bin/chrome)"
echo "==================================="
