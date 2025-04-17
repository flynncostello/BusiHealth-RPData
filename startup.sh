#!/bin/bash
# Startup script for Azure

# Run the setup script if Chrome is not installed
if ! command -v google-chrome &> /dev/null; then
    echo "Running first-time setup..."
    bash /home/site/wwwroot/setup_azure.sh
fi

# Start the application with Gunicorn
echo "Starting application..."
gunicorn --bind=0.0.0.0:8000 app:app