#!/bin/bash

# Script to run the RPData Scraper application locally
# Ensures virtual environment is activated and starts the Flask server

# Exit on any error
set -e

# Activate virtual environment
source venv/bin/activate

# Create necessary directories if they don't exist
mkdir -p downloads merged_properties tmp

# Clean up old log file
if [ -f "rpdata_scraper.log" ]; then
    echo "Removing old log file..."
    rm rpdata_scraper.log
fi

# Run Flask application
echo "==================================================="
echo "Starting RPData Scraper application..."
echo "Access the web interface at http://127.0.0.1:5000"
echo "Press Ctrl+C to stop the server"
echo "==================================================="

python3 app.py

# This line won't be reached unless the app exits normally
echo "Application has stopped."