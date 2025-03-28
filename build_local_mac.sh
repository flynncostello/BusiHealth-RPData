# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Python packages
pip install flask flask-cors selenium undetected-chromedriver pandas requests openpyxl lxml werkzeug

# Install packages from requirements.txt if it exists
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
fi

echo "Setup complete! Run the application with:"
echo "source venv/bin/activate && python3 app.py"