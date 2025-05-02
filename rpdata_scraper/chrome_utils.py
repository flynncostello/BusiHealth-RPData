# --- FILE: chrome_utils.py ---

#!/usr/bin/env python3
# Chrome utilities for web scraping with stealth & WebGL spoofing in Azure/Docker

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
        
        # Configure Chrome for Azure App Service containers
        if is_azure:
            logger.info("Using Azure-specific Chrome configuration")
            # Critical for Azure: We need these for stability but must keep WebGL working
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-setuid-sandbox")
            options.add_argument("--disable-breakpad")  # Disable crash reporting
            
            # These settings stabilize the renderer without disabling WebGL
            options.add_argument("--ignore-gpu-blocklist")
            options.add_argument("--enable-webgl")
            options.add_argument("--use-gl=swiftshader")  # Software rendering for WebGL
            
            # Headless mode configuration for Azure
            if headless:
                options.add_argument("--headless=new")
        
        # Container but not Azure (like local Docker)
        elif is_container:
            logger.info("Using general container Chrome configuration")
            if headless:
                options.add_argument("--headless=new")
                options.add_argument("--ignore-gpu-blocklist")
                options.add_argument("--enable-webgl")
                options.add_argument("--use-gl=swiftshader")
            else:
                # For debugging in non-headless containers
                options.add_argument("--ignore-gpu-blocklist")
                options.add_argument("--enable-webgl")
        
        # Local environment (macOS or other)
        else:
            if headless:
                options.add_argument("--headless=new")
                if is_macos:
                    # MacOS headless mode settings
                    options.add_argument("--use-gl=swiftshader")
                    options.add_argument("--enable-webgl")
                    options.add_argument("--ignore-gpu-blocklist")
                else:
                    # Non-macOS headless mode settings
                    options.add_argument("--use-gl=swiftshader")
                    options.add_argument("--enable-webgl")
                    options.add_argument("--ignore-gpu-blocklist")
            else:
                # Non-headless mode for local environments
                options.add_argument("--ignore-gpu-blocklist")
                options.add_argument("--enable-webgl")

        if download_dir:
            download_dir = os.path.abspath(download_dir)
            os.makedirs(download_dir, exist_ok=True)
            if is_container:
                try:
                    os.chmod(download_dir, 0o777)
                except Exception as e:
                    logger.warning(f"Could not set permissions on download directory: {e}")

            prefs = {
                "download.default_directory": download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": False,
                "plugins.always_open_pdf_externally": True
            }
            options.add_experimental_option("prefs", prefs)

        logger.info("Chrome Options:")
        for arg in options.arguments:
            logger.info(f"  {arg}")

        # Create driver with appropriate service
        service = Service(executable_path="/usr/bin/chromedriver") if is_container else None
        
        # For Azure, add an environment variable that might help with renderer issues
        if is_azure:
            logger.info("Setting special environment variables for Azure")
            os.environ['CHROME_HEADLESS'] = '1'
            os.environ['PYTHONUNBUFFERED'] = '1'
            
            # Create Chrome driver with adjusted timeout settings
            chrome_args = {"service": service, "options": options}
            driver = webdriver.Chrome(**chrome_args)
        else:
            driver = webdriver.Chrome(service=service, options=options) if service else webdriver.Chrome(options=options)

        driver.set_window_size(1920, 1080)
        
        # Set reasonable timeout for script execution
        driver.set_script_timeout(30)
        
        # For all environments, use a simple and reliable stealth script
        try:
            # Basic stealth script that should work in all environments
            driver.execute_script("""
            // Hide automation flags
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            """)
            
            # Only add more complex JS for non-Azure environments
            if not is_azure:
                driver.execute_script("""
                // More comprehensive stealth
                Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3]});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                
                // Simple canvas fingerprint protection
                if (typeof HTMLCanvasElement !== 'undefined') {
                    HTMLCanvasElement.prototype.toDataURL = function() {
                        return "data:image/png;base64,fakecanvasfingerprint==";
                    };
                }
                """)
            
            logger.info("Successfully injected basic stealth scripts")
        except Exception as e:
            # If script fails, log but continue
            logger.warning(f"Stealth script injection failed, but continuing: {e}")

        if headless and download_dir:
            try:
                driver.execute_cdp_cmd('Page.setDownloadBehavior', {'behavior': 'allow', 'downloadPath': download_dir})
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

# --- END chrome_utils.py ---