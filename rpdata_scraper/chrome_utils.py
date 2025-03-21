#!/usr/bin/env python3
# Chrome utilities for web scraping with undetected-chromedriver

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

def setup_chrome_driver(headless=False, download_dir=None):
    """
    Set up and return an Undetected ChromeDriver instance with optimal settings.
    Works across different environments including Render.
    
    Args:
        headless (bool): Whether to run Chrome in headless mode
        download_dir (str): Directory where downloads should be saved
        
    Returns:
        driver: Configured undetected_chromedriver instance
    """
    try:
        logger.info("Setting up Undetected ChromeDriver...")
        
        # Configure Chrome options
        options = uc.ChromeOptions()
        
        if headless:
            options.add_argument("--headless=new")  # Use new headless mode
        
        # Add common options to make detection harder
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")  # Helps avoid crashes in headless mode
        
        # Set a realistic user agent
        user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
        options.add_argument(f'user-agent={user_agent}')
        
        # Set download preferences if a download directory is specified
        if download_dir:
            os.makedirs(download_dir, exist_ok=True)
            prefs = {
                "download.default_directory": download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True
            }
            options.add_experimental_option("prefs", prefs)
        
        # Detect environment
        is_render = os.environ.get("RENDER") == "true" or "RENDER" in os.environ
        
        # Binary location handling for different environments
        if is_render:
            logger.info("Detected Render environment - using special configuration")
            # Check specific Render paths for Chrome
            render_chrome_paths = [
                "/usr/bin/chrome",  # Our symlink from build script
                "/usr/bin/google-chrome-stable",
                "/usr/bin/google-chrome",
                "/opt/google/chrome/chrome"
            ]
            
            for chrome_path in render_chrome_paths:
                if os.path.exists(chrome_path):
                    logger.info(f"Found Chrome in Render at: {chrome_path}")
                    options.binary_location = chrome_path
                    break
                    
            # If no binary is found, let it use default but log it
            if not hasattr(options, 'binary_location') or not options.binary_location:
                logger.warning("No Chrome binary found in Render environment!")
                
        elif platform.system() == "Darwin" and platform.machine() == "arm64":
            logger.info("Detected Mac with ARM architecture")
            # Check for common browser locations on Mac
            mac_chrome_paths = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Chromium.app/Contents/MacOS/Chromium",
                "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
                os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
            ]
            
            for chrome_path in mac_chrome_paths:
                if os.path.exists(chrome_path):
                    logger.info(f"Using browser at: {chrome_path}")
                    options.binary_location = chrome_path
                    break
                    
        elif platform.system() == "Linux":
            logger.info("Detected Linux environment")
            # Common Chrome locations on Linux
            linux_chrome_paths = [
                "/usr/bin/google-chrome-stable",
                "/usr/bin/google-chrome",
                "/usr/bin/chromium-browser",
                "/usr/bin/chromium",
                "/opt/google/chrome/chrome"
            ]
            
            for chrome_path in linux_chrome_paths:
                if os.path.exists(chrome_path):
                    logger.info(f"Using Chrome at: {chrome_path}")
                    options.binary_location = chrome_path
                    break
        
        # Log the binary location being used
        if hasattr(options, 'binary_location') and options.binary_location:
            logger.info(f"Chrome binary location set to: {options.binary_location}")
        else:
            logger.info("No specific Chrome binary set, using system default")
        
        # Initialize the driver with different approaches based on environment
        if is_render:
            logger.info("Using custom driver initialization for Render")
            # For Render, we need to be explicit about not auto-detecting the version
            # and ensuring binary_location is properly set
            driver = uc.Chrome(
                options=options,
                version_main=None,  # Auto-detect Chrome version
                use_subprocess=True,
                headless=headless,  # This is needed for newer versions
                no_sandbox=True     # Important on Render
            )
        else:
            # Standard initialization for non-Render environments
            driver = uc.Chrome(
                options=options,
                version_main=None,
                use_subprocess=True
            )
        
        # Explicitly set window size
        driver.set_window_size(1920, 1080)
        
        # Make detection harder by modifying navigator properties
        driver.execute_script("""
            // Hide WebDriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Add plugins array to seem more like a real browser
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