#!/usr/bin/env python3
# Chrome utilities for web scraping in Azure/Docker

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
    try:
        logger.info("Setting up Chrome driver for cloud/Docker environment...")

        is_azure = os.environ.get('WEBSITE_SITE_NAME') is not None
        is_container = is_azure or 'DOCKER_CONTAINER' in os.environ or os.path.exists('/.dockerenv')
        is_macos = platform.system() == "Darwin"

        logger.info(f"Environment detection: Azure={is_azure}, Container={is_container}, macOS={is_macos}")

        if is_container and not headless:
            logger.info("Running in container environment - forcing headless mode")
            headless = True

        logger.info(f"Using headless mode: {headless}")

        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36")
        options.add_argument("--window-size=1920,1080")
        
        # Initialize prefs dictionary
        prefs = {
            "download.default_directory": download_dir if download_dir else "/tmp",
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": False,
            "plugins.always_open_pdf_externally": True,
            # Additional performance preferences
            "profile.default_content_setting_values.cookies": 1,  # Accept cookies
            "profile.managed_default_content_settings.javascript": 1,  # Enable JavaScript
            # Network timeouts
            "network.tcp.connect_timeout_ms": 10000  # 10 seconds
        }
        
        # Special configuration for Azure that focuses on performance and stability
        if is_azure:
            logger.info("Using Azure-specific Chrome configuration")
            # Set page load strategy to eager
            options.page_load_strategy = 'eager'
            
            # Add performance options
            options.add_argument("--disable-notifications")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-setuid-sandbox")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-sync")
            
            # Headless mode for Azure
            if headless:
                options.add_argument("--headless=new")
        
        # Container but not Azure (like local Docker)
        elif is_container:
            logger.info("Using general container Chrome configuration")
            if headless:
                options.add_argument("--headless=new")
        
        # Local environment (macOS or other)
        else:
            if headless:
                options.add_argument("--headless=new")
        
        if download_dir:
            download_dir = os.path.abspath(download_dir)
            os.makedirs(download_dir, exist_ok=True)
            if is_container:
                try:
                    os.chmod(download_dir, 0o777)
                except Exception as e:
                    logger.warning(f"Could not set permissions on download directory: {e}")

            # Update the download directory path in prefs
            prefs["download.default_directory"] = download_dir

        # Apply prefs to options
        options.add_experimental_option("prefs", prefs)

        logger.info("Chrome Options:")
        for arg in options.arguments:
            logger.info(f"  {arg}")

        # Create driver with appropriate service
        service = Service(executable_path="/usr/bin/chromedriver") if is_container else None
        
        # Configure timeouts for the service
        service_args = []
        if is_container:
            service_args = ['--log-level=INFO']
            if service:
                service.service_args = service_args
        
        # Create Chrome driver
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_window_size(1920, 1080)
        
        # Set shorter timeouts to prevent hanging
        driver.set_page_load_timeout(60)  # 60 second page load timeout
        driver.set_script_timeout(30)     # 30 second script execution timeout
        
        # Basic automation hiding
        automation_hiding_script = """
        // Basic automation hiding
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        
        // Override canvas fingerprinting
        HTMLCanvasElement.prototype.toDataURL = function() {
            return "data:image/png;base64,fakecanvasfingerprint==";
        };
        """
        
        try:
            # Inject the automation hiding script
            driver.execute_script(automation_hiding_script)
            logger.info("Successfully injected automation hiding script")
        except Exception as e:
            # If script fails, log but continue
            logger.warning(f"Automation hiding script injection failed, but continuing: {e}")

        if headless and download_dir:
            try:
                # Fix the download behavior command to include downloadPath
                driver.execute_cdp_cmd('Page.setDownloadBehavior', {
                    'behavior': 'allow',
                    'downloadPath': download_dir
                })
            except Exception as e:
                logger.warning(f"CDP download behavior setup failed: {e}")

        logger.info("Chrome WebDriver initialized successfully")
        return driver

    except Exception as e:
        logger.error(f"Chrome setup failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


def random_wait(min_seconds=0.5, max_seconds=2):
    wait_time = min_seconds + random.random() * (max_seconds - min_seconds)
    time.sleep(wait_time)
    return wait_time

def create_wait(driver, timeout=10):
    return WebDriverWait(driver, timeout)

if __name__ == "__main__":
    driver = setup_chrome_driver(headless=True)
    try:
        driver.get("https://www.google.com")
        logger.info(f"Test successful: {driver.title}")
    except Exception as e:
        logger.error(f"Test failed: {e}")
    finally:
        driver.quit()