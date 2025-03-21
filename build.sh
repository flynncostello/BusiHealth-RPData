#!/usr/bin/env bash
# exit on error
set -o errexit
set -o pipefail
set -o nounset

echo "===================================="
echo "Starting Render build process..."
echo "===================================="

# ======== CHROME INSTALLATION ========
STORAGE_DIR=/opt/render/project/.render

if [[ ! -d $STORAGE_DIR/chrome ]]; then
  echo "...Downloading Chrome"
  mkdir -p $STORAGE_DIR/chrome
  cd $STORAGE_DIR/chrome
  wget -P ./ https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
  dpkg -x ./google-chrome-stable_current_amd64.deb $STORAGE_DIR/chrome
  rm ./google-chrome-stable_current_amd64.deb
  cd $HOME/project/src # Return to project directory
else
  echo "...Using Chrome from cache"
fi

# Set Chrome binary path
CHROME_BIN="$STORAGE_DIR/chrome/opt/google/chrome/chrome"

# Make Chrome binary executable
if [[ -f "$CHROME_BIN" ]]; then
  chmod +x "$CHROME_BIN"
  echo "...Chrome binary found at: $CHROME_BIN"
else
  echo "ERROR: Chrome binary not found at expected location!"
  find $STORAGE_DIR/chrome -name chrome -type f
  echo "Will continue but Chrome-based features may fail."
fi

# Export Chrome binary path for app to use
export CHROME_BINARY_PATH="$CHROME_BIN"

# Make Chrome available in PATH
mkdir -p /opt/render/project/bin
ln -sf "$CHROME_BIN" /opt/render/project/bin/chrome || echo "Note: Could not create symlink (this is expected in some environments)"

# Save Chrome path to profile so it's available when app runs
echo "export CHROME_BINARY_PATH=\"$CHROME_BIN\"" >> $HOME/.profile
echo "export PATH=\"\$PATH:/opt/render/project/bin\"" >> $HOME/.profile

# Verify Chrome installation
if [[ -x "$CHROME_BIN" ]]; then
  "$CHROME_BIN" --version || echo "Note: Could not run Chrome version check (expected in headless environment)"
  echo "...Chrome installation complete!"
else
  echo "WARNING: Chrome binary found but not executable!"
fi

# ======== PROJECT DEPENDENCIES ========
echo "===================================="
echo "Installing project dependencies..."
echo "===================================="

# Create directories needed for your app
mkdir -p downloads merged_properties tmp
chmod -R 777 downloads merged_properties tmp

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# ======== FINAL VERIFICATION ========
echo "===================================="
echo "Verifying installation..."
echo "===================================="

# Verify undetected-chromedriver is installed
pip show undetected-chromedriver || echo "WARNING: undetected-chromedriver not found!"

# Verify Selenium is installed
pip show selenium || echo "WARNING: selenium not found!"

# Show Chrome environment for debugging
echo "CHROME_BINARY_PATH: $CHROME_BINARY_PATH"
echo "Chrome executable: $(which chrome || echo 'Not in PATH')"
echo "Symlink status: $(ls -la /opt/render/project/bin/chrome 2>/dev/null || echo 'No symlink found')"

echo "===================================="
echo "Render Build Complete!"
echo "Chrome is at: $CHROME_BINARY_PATH"
echo "===================================="