#!/usr/bin/env python3
# Chrome utilities for web scraping with undetected-chromedriver
# Simplified version focusing on reliable file downloads

import os
import sys
import time
import random
import logging
import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_chrome_driver(headless=False, download_dir=None):
    """
    Set up and return an Undetected ChromeDriver instance with reliable download handling.
    
    Args:
        headless (bool): Whether to run Chrome in headless mode
        download_dir (str): Directory where downloads should be saved
        
    Returns:
        driver: Configured undetected_chromedriver instance
    """
    try:
        logger.info("Setting up Chrome driver...")
        logger.info(f"Headless mode: {headless}")
        
        # Configure Chrome options
        options = uc.ChromeOptions()
        
        # Basic browser settings
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1920,1080")
        
        # Headless-specific settings if needed
        if headless:
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            # Parameters to help with downloads in headless mode
            options.add_argument("--disable-features=IsolateOrigins,site-per-process")
            options.add_argument("--disable-site-isolation-trials")
            logger.info("Configured headless mode with download optimizations")
        
        # Initialize preferences
        prefs = {}
        
        # Configure download settings
        if download_dir:
            # Ensure download_dir is an absolute path
            download_dir = os.path.abspath(download_dir)
            logger.info(f"Setting download directory to: {download_dir}")
            
            # Ensure the download directory exists
            os.makedirs(download_dir, exist_ok=True)
            
            # Enhanced download settings for Excel and CSV files
            prefs.update({
                "download.default_directory": download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": False,
                "plugins.always_open_pdf_externally": True,
                "profile.default_content_settings.popups": 0,
                "download.open_pdf_in_system_reader": False,
                # Ensure all Excel/CSV MIME types are handled
                "browser.helperApps.neverAsk.saveToDisk": (
                    "application/vnd.ms-excel,"
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,"
                    "application/vnd.ms-excel.sheet.macroEnabled.12,"
                    "application/vnd.ms-excel.sheet.binary.macroEnabled.12,"
                    "text/csv,"
                    "application/csv,"
                    "application/excel,"
                    "application/vnd.msexcel,"
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,"
                    "application/zip,"
                    "application/octet-stream"
                ),
                "browser.download.manager.showWhenStarting": False,
                "browser.download.manager.focusWhenStarting": False,
                "browser.download.manager.closeWhenDone": True,
                "browser.download.manager.useWindow": False,
                "browser.download.folderList": 2  # 2 means use the custom download directory
            })
            
            # Log the download directory details to help with debugging
            logger.info(f"Configured download directory: {download_dir}")
            logger.info(f"Directory exists: {os.path.exists(download_dir)}")
            logger.info(f"Directory is writable: {os.access(download_dir, os.W_OK)}")
            
            # Check if the directory is empty
            try:
                dir_contents = os.listdir(download_dir)
                logger.info(f"Current directory contents: {dir_contents if dir_contents else 'Empty'}")
            except Exception as e:
                logger.warning(f"Could not list directory contents: {e}")
        else:
            logger.warning("No download directory specified - downloads may go to default location")
        
        # Add the preferences to Chrome options
        if prefs:
            options.add_experimental_option("prefs", prefs)
        
        # Initialize the driver
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
        """)
        
        # Setup for downloads in headless mode
        if headless and download_dir:
            # Set up experimental download behavior in headless mode
            params = {
                'behavior': 'allow',
                'downloadPath': download_dir
            }
            try:
                driver.execute_cdp_cmd('Page.setDownloadBehavior', params)
                logger.info("Set up CDP command for downloads in headless mode")
            except Exception as e:
                logger.warning(f"Could not set CDP download behavior: {e}")
        
        logger.info("Chrome WebDriver initialized successfully")
        return driver
        
    except Exception as e:
        logger.error(f"Failed to initialize Chrome WebDriver: {e}")
        import traceback
        logger.error(traceback.format_exc())
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

# Test function to check if Chrome and WebDriver are working
def test_chrome_setup(download_test=False):
    """
    Test function to check Chrome setup and download functionality.
    
    Args:
        download_test (bool): Whether to test file downloading capability
    """
    logger.info("Testing Chrome and WebDriver setup...")
    driver = None
    try:
        # Create a test download directory if needed
        test_download_dir = None
        if download_test:
            test_download_dir = os.path.join(os.getcwd(), "test_downloads")
            os.makedirs(test_download_dir, exist_ok=True)
            logger.info(f"Created test download directory: {test_download_dir}")
        
        # Initialize driver with download directory if testing downloads
        driver = setup_chrome_driver(headless=False, download_dir=test_download_dir)
        
        # Basic connectivity test
        driver.get("https://www.google.com")
        logger.info(f"Page title: {driver.title}")
        
        # Download test if requested
        if download_test and test_download_dir:
            logger.info("Testing download functionality...")
            
            # Go to a test page with downloadable content
            driver.get("https://file-examples.com/index.php/sample-documents-download/sample-xls-download/")
            time.sleep(3)
            
            # Try to click a download button
            try:
                from selenium.webdriver.common.by import By
                download_btn = driver.find_element(By.XPATH, "//a[contains(@href, '.xls') and contains(@href, 'download')]")
                download_btn.click()
                logger.info("Clicked download button")
                
                # Wait for download to complete
                time.sleep(10)
                
                # Check if any files were downloaded
                downloaded_files = os.listdir(test_download_dir)
                logger.info(f"Files in download directory: {downloaded_files}")
                
                if downloaded_files:
                    logger.info("Download test successful!")
                else:
                    logger.warning("No files found in download directory - download may have failed")
            except Exception as e:
                logger.error(f"Download test failed: {e}")
        
        logger.info("Chrome and WebDriver are working correctly!")
        return True
    except Exception as e:
        logger.error(f"Chrome/WebDriver test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    # Run the test function when this script is executed directly
    # Add --test-download command line arg to test download functionality
    download_test = "--test-download" in sys.argv
    test_chrome_setup(download_test=download_test)