#!/bin/bash
ARCH=$(dpkg --print-architecture)
CHROME_VERSION=135.0.7049.95

if [ "$ARCH" = "amd64" ]; then
    echo "Installing Chrome + Chromedriver for AMD64..."
    wget -q https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chrome-linux64.zip
    unzip chrome-linux64.zip && mkdir -p /opt/chrome
    mv chrome-linux64/* /opt/chrome/
    ln -s /opt/chrome/chrome /usr/bin/google-chrome
    rm -rf chrome-linux64.zip chrome-linux64

    wget -q https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip
    unzip chromedriver-linux64.zip
    mv chromedriver-linux64/chromedriver /usr/local/bin/chromedriver
    chmod +x /usr/local/bin/chromedriver
    ln -s /usr/local/bin/chromedriver /usr/bin/chromedriver
    rm -rf chromedriver-linux64.zip chromedriver-linux64
else
    echo "Installing Chromium + Chromedriver for ARM64..."
    apt-get update
    apt-get install -y chromium chromium-driver
    ln -s /usr/bin/chromium /usr/bin/google-chrome
    ln -sf /usr/bin/chromedriver /usr/local/bin/chromedriver
    ln -sf /usr/bin/chromedriver /usr/bin/chromedriver
    rm -rf /var/lib/apt/lists/*
fi
