# This executes when the app starts
import os
import logging
import subprocess
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app_startup")

def ensure_chrome_installed():
    """Make sure Chrome is installed on startup"""
    try:
        chrome_version = subprocess.check_output(["google-chrome", "--version"], stderr=subprocess.STDOUT)
        logger.info(f"Chrome is installed: {chrome_version.decode().strip()}")
    except:
        logger.warning("Chrome not detected, trying to install...")
        try:
            setup_script = Path(__file__).parent / "setup_azure.sh"
            subprocess.call(["bash", str(setup_script)])
            logger.info("Chrome installation attempt completed")
        except Exception as e:
            logger.error(f"Failed to install Chrome: {e}")

# Run at import time when the app loads
ensure_chrome_installed()