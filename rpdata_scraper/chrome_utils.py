#!/usr/bin/env python3
# Chrome utilities for web scraping with undetected-chromedriver
# Optimized for Docker and Azure environments

import os
import sys
import time
import random
import logging
import platform
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_chrome_driver(headless=True, download_dir=None):
    """
    Set up and return a ChromeDriver instance optimized for cloud environments.
    
    Args:
        headless (bool): Whether to run Chrome in headless mode
        download_dir (str): Directory where downloads should be saved
        
    Returns:
        driver: Configured chromedriver instance
    """
    try:
        logger.info("Setting up Chrome driver for cloud/Docker environment...")
        
        # Detect environment - critical for configuration
        is_azure = os.environ.get('WEBSITE_SITE_NAME') is not None
        is_container = is_azure or 'DOCKER_CONTAINER' in os.environ or os.path.exists('/.dockerenv')
        is_macos = platform.system() == "Darwin"
        
        logger.info(f"Environment detection: Azure={is_azure}, Container={is_container}, macOS={is_macos}")
        
        # CRITICAL: Always use headless mode in container environments regardless of input parameter
        if is_container and not headless:
            logger.info("Running in container environment - forcing headless mode")
            headless = True
        
        logger.info(f"Using headless mode: {headless}")
        
        # Use standard Selenium (more reliable in containers)
        options = Options()
        
        # Essential options for container environments
        options.add_argument("--no-sandbox")  # Required for containers
        options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource issues
        
        # ANTI-DETECTION SETTINGS
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Add a realistic user agent to avoid detection
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
        options.add_argument(f"--user-agent={user_agent}")
        
        # Standard window size
        options.add_argument("--window-size=1920,1080")
        
        # Platform-specific settings
        if is_macos:
            logger.info("Applying macOS-specific WebGL settings")
            options.add_argument("--ignore-gpu-blocklist")
            options.add_argument("--enable-webgl")
            options.add_argument("--disable-gpu-sandbox")
        else:
            logger.info("Applying standard WebGL settings for container")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-software-rasterizer")
        
        # HEADLESS MODE CONFIGURATION
        if headless:
            logger.info("Configuring stealth headless mode")
            options.add_argument("--headless=new")  # Modern headless mode
            
            # Parameters to help with downloads and stealth in headless mode
            options.add_argument("--disable-features=IsolateOrigins,site-per-process")
            options.add_argument("--disable-site-isolation-trials")
        
        # Configure download directory
        if download_dir:
            # Ensure download_dir is an absolute path
            download_dir = os.path.abspath(download_dir)
            logger.info(f"Setting download directory to: {download_dir}")
            
            # Ensure the download directory exists
            os.makedirs(download_dir, exist_ok=True)
            
            # Try to set permissions in container
            if is_container:
                try:
                    # Ensure directory is fully writable
                    os.chmod(download_dir, 0o777)
                    logger.info(f"Set permissions on download directory: {download_dir}")
                except Exception as e:
                    logger.warning(f"Could not set permissions on download directory: {e}")
            
            # Configure download preferences
            prefs = {
                "download.default_directory": download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": False,
                "plugins.always_open_pdf_externally": True,
                "profile.default_content_settings.popups": 0,
                # Excel and CSV MIME types
                "browser.helperApps.neverAsk.saveToDisk": (
                    "application/vnd.ms-excel,"
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,"
                    "text/csv,application/csv,application/excel,"
                    "application/vnd.msexcel,application/zip,application/octet-stream"
                ),
                "browser.download.manager.showWhenStarting": False,
                "browser.download.manager.useWindow": False,
                "browser.download.folderList": 2
            }
            options.add_experimental_option("prefs", prefs)
        
        # Log all options for debugging
        logger.info("Chrome Options:")
        for arg in options.arguments:
            logger.info(f"  {arg}")
        
        # Initialize driver based on environment
        try:
            if is_container:
                # In Azure/Docker containers, Chrome is often at a standard path
                if os.path.exists("/opt/chrome/chrome"):
                    logger.info("Using Chrome at /opt/chrome/chrome")
                    options.binary_location = "/opt/chrome/chrome"
                
                if os.path.exists("/usr/bin/chromedriver"):
                    logger.info("Using ChromeDriver at /usr/bin/chromedriver")
                    service = Service(executable_path="/usr/bin/chromedriver")
                    driver = webdriver.Chrome(service=service, options=options)
                else:
                    logger.info("Using auto-detected ChromeDriver")
                    driver = webdriver.Chrome(options=options)
            else:
                # For local environments
                driver = webdriver.Chrome(options=options)
            
            # Set window size
            driver.set_window_size(1920, 1080)
            
            # CRITICAL: Apply additional stealth JavaScript
            driver.execute_script("""
                // Hide automation
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Add missing navigator components
                if (navigator.plugins.length === 0) {
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                }
                
                if (navigator.languages.length === 0) {
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en', 'es']
                    });
                }
                
                // Modify permissions API
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
                );
            """)
            
            # Setup for downloads in headless mode
            if headless and download_dir:
                try:
                    params = {'behavior': 'allow', 'downloadPath': download_dir}
                    driver.execute_cdp_cmd('Page.setDownloadBehavior', params)
                    logger.info("Set up CDP download behavior for headless mode")
                except Exception as e:
                    logger.warning(f"Could not set CDP download behavior: {e}")
            
            logger.info("Chrome WebDriver initialized successfully")
            return driver
            
        except Exception as e:
            logger.error(f"Failed to initialize Chrome: {e}")
            raise
        
    except Exception as e:
        logger.error(f"Chrome setup failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

# Helper function for random delays
def random_wait(min_seconds=0.5, max_seconds=2):
    """Wait for a random time interval within the specified range."""
    wait_time = min_seconds + random.random() * (max_seconds - min_seconds)
    time.sleep(wait_time)
    return wait_time

# Helper function to create a WebDriverWait instance
def create_wait(driver, timeout=10):
    """Create a WebDriverWait instance with the specified timeout."""
    return WebDriverWait(driver, timeout)

if __name__ == "__main__":
    # Test the driver setup
    driver = setup_chrome_driver(headless=True)
    try:
        driver.get("https://www.google.com")
        logger.info(f"Test successful: {driver.title}")
    except Exception as e:
        logger.error(f"Test failed: {e}")
    finally:
        driver.quit()