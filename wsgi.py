"""WSGI entry point for Azure Web App with integrated Chrome setup"""
import os
import logging
import sys
import subprocess
from pathlib import Path

# Configure logging
log_dir = os.environ.get('HOME', '') + '/LogFiles'
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"{log_dir}/wsgi.log")
    ]
)
logger = logging.getLogger("wsgi")

# Create directories
def create_directories():
    """Create necessary directories for the application"""
    for dir_name in ['downloads', 'merged_properties', 'tmp']:
        try:
            os.makedirs(dir_name, exist_ok=True)
            logger.info(f"Created directory: {dir_name}")
        except Exception as e:
            logger.error(f"Failed to create directory {dir_name}: {str(e)}")

# Ensure Chrome is installed
def ensure_chrome_installed():
    """Make sure Chrome is installed on startup"""
    try:
        # Check if Chrome is installed
        try:
            chrome_version = subprocess.check_output(["google-chrome", "--version"], stderr=subprocess.STDOUT)
            logger.info(f"Chrome is already installed: {chrome_version.decode().strip()}")
            return True
        except:
            logger.warning("Chrome not detected, attempting to install...")
            
            # Run the setup script
            setup_script = Path(__file__).parent / "setup_azure.sh"
            if not setup_script.exists():
                logger.error(f"Setup script not found at {setup_script}")
                return False
                
            logger.info(f"Running setup script: {setup_script}")
            result = subprocess.run(["bash", str(setup_script)], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE)
            
            if result.returncode != 0:
                logger.error(f"Setup script failed with code {result.returncode}")
                logger.error(f"STDOUT: {result.stdout.decode()}")
                logger.error(f"STDERR: {result.stderr.decode()}")
                return False
            
            logger.info("Chrome installation attempt completed")
            return True
    except Exception as e:
        logger.error(f"Failed to ensure Chrome is installed: {str(e)}")
        return False

# Initialize the environment
logger.info("Initializing application environment")
create_directories()
ensure_chrome_installed()

# Import Flask app
try:
    from app import app as application
    logger.info("Application imported successfully")
except Exception as e:
    logger.error(f"Error importing application: {e}")
    raise

# For local debugging
if __name__ == '__main__':
    application.run(host='0.0.0.0', port=8000)