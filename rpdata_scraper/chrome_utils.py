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
        
        # Find Chrome binary - search in this priority order:
        
        # 1. Check environment variable (set in build.sh)
        chrome_binary = os.getenv("CHROME_BINARY_PATH")
        if chrome_binary and os.path.exists(chrome_binary) and os.access(chrome_binary, os.X_OK):
            logger.info(f"Using Chrome binary from environment variable: {chrome_binary}")
        else:
            # 2. Check common locations on Render
            render_chrome_paths = [
                "/opt/render/project/.render/chrome/opt/google/chrome/chrome",  # Our build.sh location
                "/opt/render/project/bin/chrome",  # Symlink created in build.sh
                "/usr/bin/chrome",  # Another possible symlink
                "/usr/bin/google-chrome-stable",
                "/usr/bin/google-chrome",
                "/opt/google/chrome/chrome",
                "/usr/bin/chromium-browser"
            ]
            
            # Find the first valid Chrome binary
            chrome_binary = None
            for path in render_chrome_paths:
                if os.path.exists(path) and os.access(path, os.X_OK):
                    chrome_binary = path
                    logger.info(f"Found valid Chrome binary at: {chrome_binary}")
                    break
            
            # If still not found and we're on macOS (local development)
            if chrome_binary is None and platform.system() == "Darwin":
                mac_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
                if os.path.exists(mac_path):
                    chrome_binary = mac_path
                    logger.info(f"Using macOS Chrome at: {chrome_binary}")
        
        # Only set binary_location if we found a valid binary
        # This prevents "Binary Location Must be a String" error
        if chrome_binary:
            options.binary_location = chrome_binary
            logger.info(f"Setting Chrome binary location to: {chrome_binary}")
        else:
            logger.warning("No valid Chrome binary found! Will attempt to use system default.")
            # We intentionally DON'T set options.binary_location here to avoid errors
        
        # Initialize the driver
        logger.info("Initializing undetected_chromedriver...")
        driver = uc.Chrome(
            options=options,
            version_main=None,  # Auto-detect Chrome version
            use_subprocess=True,
            headless=headless,  # Explicit headless parameter
            no_sandbox=True     # Required for Render
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