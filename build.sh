#!/usr/bin/env bash

# Update package lists (with less output)
apt-get update -qq

# Install minimal dependencies for Chrome using --no-install-recommends
apt-get install -y --no-install-recommends wget gnupg ca-certificates

# Add Google Chrome repository
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - > /dev/null 2>&1
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list

# Update package lists again with minimal output
apt-get update -qq

# Install Chrome with minimal dependencies
apt-get install -y --no-install-recommends google-chrome-stable

# Print Chrome version and location
echo "Chrome version installed:"
google-chrome --version
echo "Chrome binary location:"
which google-chrome

# Create a symlink to ensure Chrome is in a standard location
ln -sf $(which google-chrome) /usr/bin/chrome
echo "Created symlink to Chrome at /usr/bin/chrome"

# Add environment variable to indicate we're in Render
echo "export RENDER=true" >> /etc/environment

# Install other dependencies
apt-get install -y --no-install-recommends xvfb

# Create necessary directories
mkdir -p downloads merged_properties tmp
chmod -R 777 downloads merged_properties tmp

# Clean up to reduce image size and speed up future steps
apt-get clean
rm -rf /var/lib/apt/lists/*

echo "Build environment ready"