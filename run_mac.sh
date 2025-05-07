#!/bin/bash

# Terminal colors for better visibility
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}===========================================${NC}"
echo -e "${GREEN}🚀 Starting Property Scraper on macOS...${NC}"
echo -e "${BLUE}===========================================${NC}"
echo -e "Starting at: $(date)"
echo ""

# Get Mac architecture
ARCH=$(uname -m)
echo -e "${YELLOW}Detected architecture: $ARCH${NC}"

# Quick check for virtual environment
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Virtual environment not found!${NC}"
    echo -e "${YELLOW}🔧 Running build script first...${NC}"
    ./build_mac.sh
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Build script failed. Please fix the errors and try again.${NC}"
        exit 1
    fi
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to activate virtual environment.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Virtual environment activated.${NC}"

# Check if Chrome is installed
if [ ! -e "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ]; then
    echo -e "${RED}❌ Google Chrome is not installed.${NC}"
    echo -e "${YELLOW}Running build script to install Chrome...${NC}"
    ./build_mac.sh
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Build script failed. Please fix the errors and try again.${NC}"
        exit 1
    fi
fi

# Check for ChromeDriver
if [ ! -e "$HOME/.chromedriver/chromedriver" ]; then
    echo -e "${RED}❌ ChromeDriver not found.${NC}"
    echo -e "${YELLOW}Running build script to install ChromeDriver...${NC}"
    ./build_mac.sh
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Build script failed. Please fix the errors and try again.${NC}"
        exit 1
    fi
fi

# Make sure required directories exist
echo -e "${YELLOW}Ensuring required directories exist...${NC}"
mkdir -p downloads merged_properties tmp

# Set environment variables for Chrome and ChromeDriver
echo -e "${YELLOW}Setting environment variables...${NC}"
export CHROME_BINARY="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
export CHROMEDRIVER_PATH="$HOME/.chromedriver/chromedriver"

# Enable WebGL and hardware acceleration
echo -e "${YELLOW}Enabling GPU acceleration for WebGL support...${NC}"
export CHROME_FLAGS="--ignore-gpu-blocklist --enable-gpu-rasterization --enable-webgl --enable-accelerated-2d-canvas"

# Add specific options for Apple Silicon (M1/M2/M3)
if [[ "$ARCH" == "arm64" ]]; then
    echo -e "${YELLOW}Applying Apple Silicon specific settings...${NC}"
    # Additional settings can be added here if needed
fi

echo -e "${BLUE}===========================================${NC}"
echo -e "${GREEN}🌐 Starting web app on http://127.0.0.1:8000${NC}"
echo -e "${YELLOW}The app will open in your browser automatically.${NC}"
echo -e "${YELLOW}Press CTRL+C to stop the app when finished.${NC}"
echo -e "${BLUE}===========================================${NC}"

# Open the browser automatically
open http://127.0.0.1:8000

# Run the app
python app.py

# If the app exits normally, display a message
echo -e "${BLUE}===========================================${NC}"
echo -e "${GREEN}✓ Application stopped. Thank you for using Property Scraper!${NC}"
echo -e "${BLUE}===========================================${NC}"