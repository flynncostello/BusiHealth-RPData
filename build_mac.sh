#!/bin/bash

# Terminal colors for better visibility
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}===========================================${NC}"
echo -e "${GREEN}📦 Setting up environment for macOS...${NC}"
echo -e "${BLUE}===========================================${NC}"
echo -e "Starting setup at: $(date)"
echo ""

# Get Mac architecture
ARCH=$(uname -m)
echo -e "${YELLOW}Detected architecture: $ARCH${NC}"

# Verify if running with sudo/admin rights
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}Note: Not running with administrator privileges.${NC}"
    echo -e "${YELLOW}Some operations might require your password.${NC}"
fi

# 1. Install Xcode CLI tools if missing
echo -e "${BLUE}[STEP 1/8] Checking for Xcode Command Line Tools...${NC}"
if ! xcode-select -p &> /dev/null; then
    echo -e "${YELLOW}🛠 Installing Xcode Command Line Tools...${NC}"
    echo -e "${YELLOW}A popup may appear. Please click 'Install' and wait for it to complete.${NC}"
    xcode-select --install
    echo -e "${RED}❗️ Please wait for Xcode tools to install, then run this script again.${NC}"
    exit 1
else
    echo -e "${GREEN}✓ Xcode Command Line Tools already installed.${NC}"
fi
echo ""

# 2. Install Homebrew if not present
echo -e "${BLUE}[STEP 2/8] Checking for Homebrew...${NC}"
if ! command -v brew &> /dev/null; then
    echo -e "${YELLOW}🍺 Installing Homebrew...${NC}"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # Setup Homebrew in PATH (for M1/M2/M3 Macs)
    if [[ "$ARCH" == "arm64" ]]; then
        echo -e "${YELLOW}Setting up Homebrew for Apple Silicon...${NC}"
        eval "$(/opt/homebrew/bin/brew shellenv)" 2>/dev/null
        # Add Homebrew to shell profile for future terminals
        if [[ -f ~/.zshrc ]]; then
            echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zshrc
        elif [[ -f ~/.bash_profile ]]; then
            echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.bash_profile
        fi
    else
        eval "$(/usr/local/bin/brew shellenv)"
    fi
    
    if ! command -v brew &> /dev/null; then
        echo -e "${RED}❌ Homebrew installation failed. Please install manually and try again.${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ Homebrew already installed.${NC}"
fi
echo ""

# 3. Install Python 3 and virtualenv if missing
echo -e "${BLUE}[STEP 3/8] Checking for Python 3...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}🐍 Installing Python 3...${NC}"
    brew install python
    
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python 3 installation failed. Please install manually and try again.${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ Python 3 already installed.${NC}"
    PYTHON_VERSION=$(python3 --version)
    echo -e "${YELLOW}$PYTHON_VERSION${NC}"
fi

echo -e "${YELLOW}Upgrading pip and installing virtualenv...${NC}"
python3 -m pip install --upgrade pip
python3 -m pip install virtualenv
echo ""

# 4. Create and activate virtual environment
echo -e "${BLUE}[STEP 4/8] Setting up Python virtual environment...${NC}"
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Failed to create virtual environment. Please check your Python installation.${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ Virtual environment already exists.${NC}"
fi

echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to activate virtual environment.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Virtual environment activated.${NC}"
echo ""

# 5. Install required Python packages
echo -e "${BLUE}[STEP 5/8] Installing Python dependencies...${NC}"
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}❌ requirements.txt file not found! Please ensure it exists in the current directory.${NC}"
    echo -e "Current directory: $(pwd)"
    echo -e "Files in current directory:"
    ls -la
    exit 1
fi

echo -e "${YELLOW}📦 Installing Python dependencies...${NC}"
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to install required packages. Please check the errors above.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ All Python dependencies installed successfully.${NC}"
echo ""

# 6. Install Google Chrome if missing
echo -e "${BLUE}[STEP 6/8] Checking for Google Chrome...${NC}"
if [ ! -e "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ]; then
    echo -e "${YELLOW}🌐 Installing Google Chrome...${NC}"
    brew install --cask google-chrome
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Failed to install Google Chrome. Please install manually and try again.${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ Google Chrome is already installed.${NC}"
    # Get Chrome version
    CHROME_VERSION=$(/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --version | awk '{print $3}')
    echo -e "${YELLOW}Chrome version: $CHROME_VERSION${NC}"
fi
echo ""

# 7. ChromeDriver setup with architecture detection
echo -e "${BLUE}[STEP 7/8] Setting up ChromeDriver...${NC}"

# Clean up existing ChromeDriver installations
echo -e "${YELLOW}Cleaning up previous ChromeDriver downloads...${NC}"
rm -rf ~/.wdm/drivers/chromedriver 2>/dev/null
rm -rf ~/.chromedriver 2>/dev/null

# Create ChromeDriver directory
mkdir -p ~/.chromedriver

# Determine URL based on architecture
if [[ "$ARCH" == "arm64" ]]; then
    CHROMEDRIVER_URL="https://storage.googleapis.com/chrome-for-testing-public/136.0.7103.49/mac-arm64/chromedriver-mac-arm64.zip"
else
    CHROMEDRIVER_URL="https://storage.googleapis.com/chrome-for-testing-public/136.0.7103.49/mac-x64/chromedriver-mac-x64.zip"
fi

# Download the ChromeDriver
echo -e "${YELLOW}Downloading ChromeDriver from stable channel...${NC}"
echo -e "${YELLOW}URL: $CHROMEDRIVER_URL${NC}"

curl -L --retry 3 -o ~/.chromedriver/chromedriver.zip "$CHROMEDRIVER_URL"

# Check if download was successful
if [ ! -s ~/.chromedriver/chromedriver.zip ]; then
    echo -e "${RED}❌ ChromeDriver download failed or resulted in an empty file.${NC}"
    echo -e "${YELLOW}Trying alternative download method...${NC}"
    
    # Try with alternative download approach
    wget -O ~/.chromedriver/chromedriver.zip "$CHROMEDRIVER_URL"
    
    if [ ! -s ~/.chromedriver/chromedriver.zip ]; then
        echo -e "${RED}❌ All ChromeDriver download attempts failed. Please check your internet connection.${NC}"
        exit 1
    fi
fi

# Extract the ChromeDriver
echo -e "${YELLOW}Extracting ChromeDriver...${NC}"
unzip -o -q ~/.chromedriver/chromedriver.zip -d ~/.chromedriver/temp

# Find and move the chromedriver executable to our target location
find ~/.chromedriver/temp -name "chromedriver" -type f -exec cp {} ~/.chromedriver/ \;
chmod +x ~/.chromedriver/chromedriver

# Verify the ChromeDriver was successfully installed
if [ ! -x ~/.chromedriver/chromedriver ]; then
    echo -e "${RED}❌ ChromeDriver installation failed. The file is missing or not executable.${NC}"
    exit 1
fi

# Display ChromeDriver version
echo -e "${YELLOW}Installed ChromeDriver version:${NC}"
~/.chromedriver/chromedriver --version

# Clean up temporary files
rm -rf ~/.chromedriver/temp
rm -f ~/.chromedriver/chromedriver.zip

# Set environment variable for current session
export CHROMEDRIVER_PATH="$HOME/.chromedriver/chromedriver"

# Add to shell profiles for persistence
if [[ -f ~/.zshrc ]]; then
    grep -q "CHROMEDRIVER_PATH" ~/.zshrc || echo 'export CHROMEDRIVER_PATH="$HOME/.chromedriver/chromedriver"' >> ~/.zshrc
    echo -e "${GREEN}✓ Added ChromeDriver path to .zshrc${NC}"
elif [[ -f ~/.bash_profile ]]; then
    grep -q "CHROMEDRIVER_PATH" ~/.bash_profile || echo 'export CHROMEDRIVER_PATH="$HOME/.chromedriver/chromedriver"' >> ~/.bash_profile
    echo -e "${GREEN}✓ Added ChromeDriver path to .bash_profile${NC}"
fi
echo -e "${GREEN}✓ ChromeDriver setup complete.${NC}"
echo ""

# 8. Create needed directories
echo -e "${BLUE}[STEP 8/8] Creating required directories...${NC}"
mkdir -p downloads merged_properties tmp
echo -e "${GREEN}✓ Required directories created.${NC}"

# 9. Set correct permissions for our script files
echo -e "${YELLOW}🔑 Setting executable permissions for scripts...${NC}"
chmod +x run_mac.sh
echo -e "${GREEN}✓ Permissions set for run script.${NC}"
echo ""

echo -e "${BLUE}===========================================${NC}"
echo -e "${GREEN}✅ Build complete! You can now run the app using:${NC}"
echo -e "${GREEN}    ./run_mac.sh${NC}"
echo -e "${BLUE}===========================================${NC}"
echo -e "Setup completed at: $(date)"