import os
import sys
import subprocess
import logging
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("/home/LogFiles/startup.log")
    ]
)
logger = logging.getLogger("startup")

def create_directories():
    """Create necessary directories"""
    try:
        os.makedirs("downloads", exist_ok=True)
        os.makedirs("merged_properties", exist_ok=True)
        os.makedirs("tmp", exist_ok=True)
        logger.info("Created required directories")
    except Exception as e:
        logger.error(f"Failed to create directories: {e}")

def install_chrome():
    """Install Chrome if not present"""
    try:
        # Check if Chrome is already installed
        try:
            subprocess.check_output(["google-chrome", "--version"])
            logger.info("Chrome is already installed")
            return True
        except:
            logger.info("Chrome not found, installing...")
        
        # Install Chrome
        commands = [
            "apt-get update",
            "apt-get install -y wget",
            "wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -O /tmp/chrome.deb",
            "apt-get install -y /tmp/chrome.deb"
        ]
        
        for cmd in commands:
            logger.info(f"Running: {cmd}")
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning(f"Command failed: {cmd}")
                logger.warning(f"Error: {result.stderr}")
            else:
                logger.info(f"Command succeeded: {cmd}")
        
        # Verify installation
        try:
            chrome_version = subprocess.check_output(["google-chrome", "--version"], text=True)
            logger.info(f"Chrome installed: {chrome_version.strip()}")
            return True
        except:
            logger.error("Chrome installation verification failed")
            return False
            
    except Exception as e:
        logger.error(f"Chrome installation failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting application setup")
    create_directories()
    install_chrome()
    
    # Start the application
    logger.info("Starting web application")
    os.chdir("/home/site/wwwroot")
    os.execvp("gunicorn", ["gunicorn", "--bind=0.0.0.0:8000", "wsgi:app"])