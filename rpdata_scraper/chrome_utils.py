#!/usr/bin/env python3
# Chrome utilities for web scraping with undetected-chromedriver
# Optimized for Docker environments

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
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_chrome_driver(headless=True, download_dir=None):
    """
    Set up and return an Undetected ChromeDriver instance optimized for Docker environments.
    
    Args:
        headless (bool): Whether to run Chrome in headless mode (should be True in Docker)
        download_dir (str): Directory where downloads should be saved
        
    Returns:
        driver: Configured undetected_chromedriver instance
    """
    try:
        logger.info("Setting up Chrome driver for Docker environment...")
        logger.info(f"Headless mode: {headless}")
        
        # Detect if we're in a container
        is_container = os.environ.get('WEBSITE_SITE_NAME') is not None or 'DOCKER_CONTAINER' in os.environ
        logger.info(f"Running in container: {is_container}")
        
        # Detect macOS
        is_macos = platform.system() == "Darwin"
        logger.info(f"Running on macOS: {is_macos}")
        
        # Configure Chrome options - optimized for Docker
        options = uc.ChromeOptions()
        
        # Essential options for Docker environment
        options.add_argument("--no-sandbox")  # Required for Docker
        options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource issues
        options.add_argument("--remote-debugging-port=9222")
        # WebGL fixes - macOS specific configuration
        if is_macos:
            logger.info("Applying macOS-specific WebGL settings")
            options.add_argument("--ignore-gpu-blocklist")
            options.add_argument("--enable-webgl")
            options.add_argument("--disable-gpu-sandbox")
            options.add_argument("--enable-gpu")  # Enable GPU on macOS
            options.add_argument("--enable-gpu-rasterization")
            options.add_argument("--enable-zero-copy")
            options.add_argument("--enable-accelerated-2d-canvas")
            
            # Important: Metal API support for macOS
            options.add_argument("--use-gl=angle")  # Use ANGLE instead of SwiftShader on Mac
            options.add_argument("--use-angle=metal")  # Use Metal backend
            
            # Don't add --disable-gpu on Mac
        else:
            # Non-macOS WebGL fixes (Linux/Windows)
            logger.info("Applying standard WebGL settings")
            options.add_argument("--ignore-gpu-blocklist")
            options.add_argument("--enable-webgl")
            options.add_argument("--disable-gpu-sandbox")
            options.add_argument("--use-gl=swiftshader")  # Use SwiftShader on non-Mac
            options.add_argument("--enable-gpu-rasterization")
            options.add_argument("--enable-accelerated-2d-canvas")
            options.add_argument("--disable-gpu")  # Helpful on Linux
        
        # Original options
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1920,1080")
        
        # Log all Chrome options for debugging
        logger.info("Chrome Options:")
        for arg in options.arguments:
            logger.info(f"  {arg}")
        
        # Headless settings
        # In Docker, we almost always want to run headless
        if headless or is_container:
            #options.add_argument("--headless=new")
            options.add_argument("--headless")
        


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
            
            # Fix permissions in Docker environment
            if is_container:
                try:
                    # Ensure directory is fully writable
                    os.chmod(download_dir, 0o777)
                    logger.info(f"Set permissions on download directory: {download_dir}")
                except Exception as e:
                    logger.warning(f"Could not set permissions on download directory: {e}")
            
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
        else:
            logger.warning("No download directory specified - downloads may go to default location")
        
        # Add the preferences to Chrome options
        if prefs:
            options.add_experimental_option("prefs", prefs)
        
        # Initialize the driver - with Docker-specific configurations
        logger.info("Initializing undetected_chromedriver...")
        
        # Use Chromium-specific paths for Docker
        if is_container:
            driver = uc.Chrome(
                options=options,
                browser_executable_path="/opt/chrome/chrome",  # Chrome path in Docker
                driver_executable_path="/usr/bin/chromedriver",  # ChromeDriver path in Docker
                version_main=None,  # Auto-detect browser version
                use_subprocess=True
            )
            logger.info("Initialized Chromium with Docker-specific paths")
        else:
            # Standard initialization for non-Docker environments
            driver = uc.Chrome(
                options=options,
                version_main=None,  # Auto-detect browser version
                use_subprocess=True
            )
        
        # Set window size
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
        
        # More informative error for Docker troubleshooting
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
    Particularly useful for verifying Docker configuration.
    
    Args:
        download_test (bool): Whether to test file downloading capability
    """
    logger.info("Testing Chrome and WebDriver setup in container environment...")
    driver = None
    try:
        # Create a test download directory if needed
        test_download_dir = None
        if download_test:
            test_download_dir = os.path.join(os.getcwd(), "test_downloads")
            os.makedirs(test_download_dir, exist_ok=True)
            logger.info(f"Created test download directory: {test_download_dir}")
        
        # Initialize driver - always use headless in Docker
        is_container = os.environ.get('WEBSITE_SITE_NAME') is not None or 'DOCKER_CONTAINER' in os.environ
        headless = True if is_container else False
        
        driver = setup_chrome_driver(headless=headless, download_dir=test_download_dir)
        
        # Basic connectivity test
        driver.get("https://www.google.com")
        logger.info(f"Page title: {driver.title}")
        logger.info(f"Chrome version: {driver.capabilities['browserVersion']}")
        logger.info(f"Driver version: {driver.capabilities['chrome']['chromedriverVersion'].split(' ')[0]}")
        
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
        
        logger.info("Chrome and WebDriver are working correctly in container environment!")
        return True
    except Exception as e:
        logger.error(f"Chrome/WebDriver test failed in container: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    # Set environment variable to indicate we're testing in Docker
    os.environ['DOCKER_CONTAINER'] = 'true'
    
    # Run the test function when this script is executed directly
    # Add --test-download command line arg to test download functionality
    download_test = "--test-download" in sys.argv
    test_chrome_setup(download_test=download_test)