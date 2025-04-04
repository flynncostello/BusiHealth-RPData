#!/usr/bin/env python3
# Chrome utilities for web scraping with undetected-chromedriver - Final Fix

import os
import sys
import time
import random
import logging
import platform
import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_chrome_driver(headless=False, download_dir=None):
    """
    Set up and return an Undetected ChromeDriver instance optimized for WebGL support.
    
    Args:
        headless (bool): Whether to run Chrome in headless mode
        download_dir (str): Directory where downloads should be saved
        
    Returns:
        driver: Configured undetected_chromedriver instance
    """
    try:
        logger.info("Setting up Chrome driver with WebGL support...")
        
        # Configure Chrome options - IMPORTANT: Use standard Options for maximum compatibility
        options = uc.ChromeOptions()
        
        # Essential flags to enable WebGL
        options.add_argument("--ignore-gpu-blocklist")
        options.add_argument("--enable-gpu-rasterization")
        options.add_argument("--enable-webgl")
        
        # Basic browser settings
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Set window size
        options.add_argument("--window-size=1920,1080")
        
        # Only use headless if absolutely necessary (it often breaks WebGL)
        if headless:
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            logger.warning("Headless mode may cause WebGL and element detection issues")
        
        # Add prefs for hardware acceleration
        prefs = {
            "hardware_acceleration_mode.enabled": True
        }
        
        # Add download preferences if specified
        if download_dir:
            os.makedirs(download_dir, exist_ok=True)
            prefs.update({
                "download.default_directory": download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True
            })
        
        options.add_experimental_option("prefs", prefs)
        
        # Initialize the driver with basic settings
        logger.info("Initializing undetected_chromedriver...")
        driver = uc.Chrome(
            options=options,
            version_main=None,  # Auto-detect Chrome version
            use_subprocess=True
        )
        
        # Set window size or maximize
        if not headless:
            driver.maximize_window()
        else:
            driver.set_window_size(1920, 1080)
        
        # Apply anti-detection methods
        driver.execute_script("""
            // Hide WebDriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Add plugins array to mimic a real browser
            Object.defineProperty(navigator, 'plugins', {
                get: function() {
                    return [
                        {description: "PDF Viewer", filename: "internal-pdf-viewer", name: "Chrome PDF Viewer"},
                        {description: "Chrome PDF Viewer", filename: "internal-pdf-viewer", name: "Chrome PDF Viewer"},
                        {description: "Portable Document Format", filename: "internal-pdf-viewer", name: "Chrome PDF Plugin"}
                    ];
                }
            });
        """)
        
        logger.info("Chrome WebDriver initialized successfully")
        return driver
        
    except Exception as e:
        logger.error(f"Failed to initialize Chrome WebDriver: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

# Helper function for waiting with randomized delays
def random_wait(min_seconds=0.5, max_seconds=2):
    """Wait for a random time interval within the specified range."""
    wait_time = min_seconds + random.random() * (max_seconds - min_seconds)
    time.sleep(wait_time)
    return wait_time

# Helper function to create a WebDriverWait instance
def create_wait(driver, timeout=10):
    """Create a WebDriverWait instance with the specified timeout."""
    return WebDriverWait(driver, timeout)