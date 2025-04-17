#!/bin/bash
# For testing - skip Chrome setup temporarily
echo "Starting application in test mode..."
gunicorn --bind=0.0.0.0:8000 app:app