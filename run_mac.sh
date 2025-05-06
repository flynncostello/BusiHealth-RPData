#!/bin/bash

# Terminal colors for better visibility
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting app on macOS...${NC}"

# Get Mac architecture
ARCH=$(uname -m)
echo -e "${YELLOW}Detected architecture: $ARCH${NC}"

# Create and activate virtualenv if needed
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}🔧 Virtual environment not found. Running build script first...${NC}"
    ./build_mac.sh
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Build script failed. Please fix the errors and try again.${NC}"
        exit 1
    fi
fi

echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Ensure Chrome is installed
if [ ! -e "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ]; then
    echo -e "${RED}❌ Google Chrome is not installed. Please install Chrome and try again.${NC}"
    echo -e "${YELLOW}Running build script to install Chrome...${NC}"
    ./build_mac.sh
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Build script failed. Please fix the errors and try again.${NC}"
        exit 1
    fi
fi

# Set environment variables for Chrome and ChromeDriver
export CHROME_BINARY="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# If we're on Apple Silicon (M1/M2/M3), set specific options
if [[ "$ARCH" == "arm64" ]]; then
    echo -e "${YELLOW}Setting options for Apple Silicon Mac...${NC}"
    # Make sure we use our manually installed ChromeDriver
    export CHROMEDRIVER_PATH="$HOME/.chromedriver/chromedriver"
fi

# Create necessary directories
mkdir -p downloads merged_properties tmp

echo -e "${GREEN}🌐 Starting web app on http://127.0.0.1:8000${NC}"
echo -e "${YELLOW}Press CTRL+C to stop the app${NC}"

# Run app
python app.py