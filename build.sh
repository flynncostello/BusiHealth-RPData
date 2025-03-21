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

# Save Chrome path to multiple locations to ensure it's available at runtime
# 1. Add to ~/.profile (traditional location)
echo "export CHROME_BINARY_PATH=\"$CHROME_BIN\"" >> ~/.profile
echo "export PATH=\"\$PATH:/opt/render/project/bin\"" >> ~/.profile

# 2. Add to ~/.bashrc (alternative location)
echo "export CHROME_BINARY_PATH=\"$CHROME_BIN\"" >> ~/.bashrc
echo "export PATH=\"\$PATH:/opt/render/project/bin\"" >> ~/.bashrc

# 3. Add to project .env file (another alternative)
echo "export CHROME_BINARY_PATH=\"$CHROME_BIN\"" >> /opt/render/project/src/.env
echo "export PATH=\"\$PATH:/opt/render/project/bin\"" >> /opt/render/project/src/.env

# 4. Create a dedicated env.sh script that can be sourced
mkdir -p /opt/render/project/src/env
cat > /opt/render/project/src/env/chrome.sh << EOL
#!/bin/bash
export CHROME_BINARY_PATH="$CHROME_BIN"
export PATH="\$PATH:/opt/render/project/bin"
EOL
chmod +x /opt/render/project/src/env/chrome.sh

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

# Print all locations where we've stored environment variables for debugging
echo "Environment variable locations:"
echo "1. Profile: $(ls -la ~/.profile 2>/dev/null || echo 'Not found')"
echo "2. Bashrc: $(ls -la ~/.bashrc 2>/dev/null || echo 'Not found')"
echo "3. Project .env: $(ls -la /opt/render/project/src/.env 2>/dev/null || echo 'Not found')"
echo "4. Chrome env script: $(ls -la /opt/render/project/src/env/chrome.sh 2>/dev/null || echo 'Not found')"

# Show Chrome environment for debugging
echo "CHROME_BINARY_PATH: $CHROME_BINARY_PATH"
echo "Chrome executable: $(which chrome 2>/dev/null || echo 'Not in PATH')"
echo "Symlink status: $(ls -la /opt/render/project/bin/chrome 2>/dev/null || echo 'No symlink found')"

echo "===================================="
echo "Render Build Complete!"
echo "Chrome is at: $CHROME_BINARY_PATH"
echo "====================================">