#!/usr/bin/env python3
# Simplified Chrome driver setup for Docker environments

import os
import sys
import logging
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_direct_chrome_driver(headless=True, download_dir=None):
    """
    Alternative Chrome setup using standard Selenium instead of undetected_chromedriver
    """
    try:
        logger.info("Setting up direct Chrome driver...")
        
        # Initialize Chrome options
        options = Options()
        
        # Essential options for stability in Docker
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-features=VizDisplayCompositor")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-software-rasterizer")
        
        # Memory management
        options.add_argument("--js-flags=--max-old-space-size=2048")  # Limit JS memory
        options.add_argument("--single-process")  # Use single process
        
        # Add headless mode if required - v2 has better stability
        if headless:
            options.add_argument("--headless=new")
        
        # Add window size
        options.add_argument("--window-size=1280,1024")
        
        # Configure download settings
        if download_dir:
            prefs = {
                "download.default_directory": os.path.abspath(download_dir),
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": False
            }
            options.add_experimental_option("prefs", prefs)
        
        # Create the service - explicitly point to the chromedriver
        chrome_path = "/opt/chrome/chrome"
        driver_path = "/usr/local/bin/chromedriver"
        
        logger.info(f"Using chromedriver at: {driver_path}")
        logger.info(f"Using chrome at: {chrome_path}")
        
        service = Service(executable_path=driver_path)
        
        # Create the driver
        options.binary_location = chrome_path
        
        # Add random delay to avoid simultaneous Chrome processes
        time.sleep(random.uniform(0.5, 1.5))
        
        driver = webdriver.Chrome(service=service, options=options)
        
        # Set page load timeout to prevent hanging
        driver.set_page_load_timeout(30)
        
        logger.info("Direct Chrome driver setup successful")
        return driver
        
    except Exception as e:
        logger.error(f"Failed to set up direct Chrome driver: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None