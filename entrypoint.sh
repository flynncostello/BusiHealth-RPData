#!/bin/bash

# Set up virtual display with more memory
echo "Setting up Xvfb with increased memory..."
Xvfb :99 -ac -screen 0 1280x1024x24 -nolisten tcp &
sleep 2

# Verify Xvfb is running
if ! ps aux | grep -v grep | grep Xvfb > /dev/null; then
    echo "ERROR: Xvfb failed to start!"
else
    echo "Xvfb started successfully"
fi

# Increase shared memory for Chrome
echo "Setting system limits for Chrome..."
if [ -f /proc/sys/kernel/shmmax ]; then
    echo "Current shmmax: $(cat /proc/sys/kernel/shmmax)"
fi

# Set DBUS address to avoid issues
export DBUS_SESSION_BUS_ADDRESS=/dev/null

# Check Chrome dependencies
echo "Checking Chrome dependencies..."
ldd /opt/chrome/chrome | grep "not found" || echo "All Chrome dependencies satisfied"

# Make sure Chrome is executable
chmod +x /opt/chrome/chrome

# Print Chrome and ChromeDriver versions for debugging
echo "Chrome version:"
google-chrome --version || echo "Chrome failed to start - check dependencies"

echo "ChromeDriver version:"
chromedriver --version || echo "ChromeDriver failed to start"

# Print environment info
echo "Environment: $FLASK_ENV"
echo "Running in container: $DOCKER_CONTAINER"
echo "Working directory: $(pwd)"
echo "Display: $DISPLAY"

# Create symbolic links if needed
mkdir -p /home/downloads /home/merged_properties /home/tmp
ln -sfn /home/downloads /app/downloads 
ln -sfn /home/merged_properties /app/merged_properties
ln -sfn /home/tmp /app/tmp

# Set permissions
chmod -R 777 /home/downloads /home/merged_properties /home/tmp

# Set USE_DIRECT_CHROME environment variable
export USE_DIRECT_CHROME=true

# Run using gunicorn with timeout settings
echo "Starting application with gunicorn..."
exec gunicorn --bind 0.0.0.0:8000 --workers=1 --timeout=300 app:app