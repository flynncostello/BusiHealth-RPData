#!/usr/bin/env python3
# Chrome utilities for web scraping with undetected-chromedriver on Render

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

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_chrome_driver(headless=True, download_dir=None):
    """
    Set up and return an Undetected ChromeDriver instance optimized for Render environments.
    
    Args:
        headless (bool): Whether to run Chrome in headless mode
        download_dir (str): Directory where downloads should be saved
        
    Returns:
        driver: Configured undetected_chromedriver instance
    """
    try:
        logger.info("Setting up Undetected ChromeDriver for Render...")
        
        # Configure Chrome options
        options = uc.ChromeOptions()
        
        # Add headless mode - always use new headless
        if headless:
            options.add_argument("--headless=new")
        
        # Add common options required for Render
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")  # Critical for Render
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        
        # Set a realistic user agent
        user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        options.add_argument(f'user-agent={user_agent}')
        
        # Set download preferences if specified
        if download_dir:
            os.makedirs(download_dir, exist_ok=True)
            prefs = {
                "download.default_directory": download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True
            }
            options.add_experimental_option("prefs", prefs)
        
        # Determine Chrome binary location - check environment variable first
        chrome_binary = os.getenv("CHROME_BINARY_PATH", "/usr/bin/google-chrome")

        # Verify if the binary exists and is executable
        if not (chrome_binary and os.path.exists(chrome_binary) and os.access(chrome_binary, os.X_OK)):
            logger.warning(f"Chrome binary at {chrome_binary} is missing or not executable. Checking common locations...")
            render_chrome_paths = [
                "/usr/bin/chrome",  # Symlink from build script
                "/usr/bin/google-chrome-stable",
                "/usr/bin/google-chrome",
                "/opt/google/chrome/chrome",
                "/usr/bin/chromium-browser"
            ]

            for path in render_chrome_paths:
                if os.path.exists(path) and os.access(path, os.X_OK):
                    chrome_binary = path
                    logger.info(f"Found valid Chrome binary at: {chrome_binary}")
                    break
            else:
                logger.error("No valid Chrome binary found! The driver may not work.")

        # Set the binary location in Chrome options
        if chrome_binary:
            options.binary_location = chrome_binary
            logger.info(f"Using Chrome binary at: {chrome_binary}")
        else:
            logger.warning("No valid Chrome binary set. Selenium may fail to launch Chrome.")

        
        # Verify the binary exists and is executable
        if chrome_binary and os.path.exists(chrome_binary) and os.access(chrome_binary, os.X_OK):
            logger.info(f"Setting Chrome binary location to: {chrome_binary}")
            options.binary_location = chrome_binary
        else:
            logger.warning(f"Chrome binary not found or not executable at {chrome_binary}")
            logger.warning("Will attempt to use system default Chrome (may fail)")
            # Don't set binary_location if we don't have a valid path
            chrome_binary = None
        
        # Initialize driver with different approaches based on whether we have a valid binary
        if chrome_binary:
            logger.info(f"Initializing Chrome with binary: {chrome_binary}")
            driver = uc.Chrome(
                options=options,
                version_main=None,  # Auto-detect Chrome version
                use_subprocess=True,
                headless=headless,  # Explicit headless parameter
                no_sandbox=True     # Required for Render
            )
        else:
            # Try without setting binary_location explicitly
            logger.warning("Trying to initialize driver without explicit binary location")
            # Create new options without binary_location to avoid the string error
            basic_options = uc.ChromeOptions()
            basic_options.add_argument("--no-sandbox")
            basic_options.add_argument("--disable-dev-shm-usage")
            if headless:
                basic_options.add_argument("--headless=new")
            
            driver = uc.Chrome(
                options=basic_options,
                version_main=None,
                use_subprocess=True,
                headless=headless,
                no_sandbox=True
            )
        
        # Set window size explicitly
        driver.set_window_size(1920, 1080)
        
        # Make detection harder by modifying navigator properties
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
        
        logger.info("Undetected ChromeDriver initialized successfully")
        return driver
        
    except Exception as e:
        logger.error(f"Failed to initialize Undetected ChromeDriver: {e}")
        # Print traceback for debugging
        import traceback
        traceback.print_exc()
        sys.exit(1)

# Helper function for waiting with randomized delays
def random_wait(min_seconds=1, max_seconds=3):
    """Wait for a random time interval within the specified range."""
    wait_time = min_seconds + random.random() * (max_seconds - min_seconds)
    time.sleep(wait_time)
    return wait_time

# Helper function to create a WebDriverWait instance
def create_wait(driver, timeout=10):
    """Create a WebDriverWait instance with the specified timeout."""
    return WebDriverWait(driver, timeout)