#!/bin/bash

# Start Xvfb in the background
Xvfb :99 -ac -screen 0 1280x1024x8 &

# Wait a moment for Xvfb to start
sleep 2

# Print Chrome and ChromeDriver versions for debugging
echo "Chrome version:"
google-chrome --version

echo "ChromeDriver version:"
chromedriver --version || echo "ChromeDriver version check failed"

# Run the main application using gunicorn
exec gunicorn --bind 0.0.0.0:8000 app:app