#!/usr/bin/env bash

# Update package lists
apt-get update

# Install dependencies for Chrome
apt-get install -y wget gnupg ca-certificates

# Add Google Chrome repository
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list

# Update package lists again with new repository
apt-get update

# Install Chrome
apt-get install -y google-chrome-stable

# Print Chrome version for debugging
google-chrome --version

# Install additional system dependencies for Python packages
apt-get install -y build-essential python3-dev

# Create necessary directories
mkdir -p downloads merged_properties tmp

# Set permissions for created directories
chmod -R 777 downloads merged_properties tmp

# Print working directory for debugging
echo "Working directory: $(pwd)"
echo "Directory listing:"
ls -la