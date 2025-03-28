#!/bin/bash
# RPData Scraper Setup Script for macOS

# Show commands as they execute
set -x

# macOS setup
echo "Setting up on macOS..."

# Set permissions for existing directories
chmod -R 777 downloads merged_properties tmp

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Python packages
pip install flask==2.3.3 flask-cors==4.0.0 selenium==4.29.0 undetected-chromedriver==3.5.5 pandas==2.2.3 requests==2.31.0 openpyxl==3.1.2 webdriver-manager==4.0.0 Pillow==10.0.0 Werkzeug==2.3.7 lxml

# Install packages from requirements.txt if it exists
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
fi

echo "Setup complete! Run the application with:"
echo "source venv/bin/activate && python3 app.py"

# Create a simple run script for convenience
echo '#!/bin/bash
source venv/bin/activate
python3 app.py' > run_app.sh
chmod +x run_app.sh

echo "Or simply run: ./run_app.sh"