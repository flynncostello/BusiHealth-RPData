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
        
        # Add timeouts to prevent hanging
        options.add_argument("--browser-process-hint-timeout=60")
        
        # WebGL configurations - critical flags to enable WebGL in headless mode
        if headless:
            # Set headless mode with the new syntax
            options.add_argument("--headless=new")
            
            # Critical WebGL flags
            options.add_argument("--ignore-gpu-blocklist")
            options.add_argument("--enable-webgl")
            options.add_argument("--use-gl=angle")  # Use ANGLE backend for better compatibility
            
            # macOS specific flags to help with WebGL in headless
            if is_macos:
                options.add_argument("--use-angle=metal")  # Use Metal on macOS
            else:
                # Non-macOS flags
                options.add_argument("--use-angle=swiftshader")  # Software rendering fallback
            
            # Additional flags to improve WebGL support
            options.add_argument("--in-process-gpu")  # Run GPU process in same process
            options.add_argument("--disable-features=IsolateOrigins,site-per-process")
            options.add_argument("--disable-site-isolation-trials")
        else:
            # For non-headless mode
            if is_macos:
                options.add_argument("--ignore-gpu-blocklist")
                options.add_argument("--enable-webgl")
                options.add_argument("--use-angle=metal")  # Use Metal on macOS
            else:
                options.add_argument("--enable-webgl")
                options.add_argument("--ignore-gpu-blocklist")
                options.add_argument("--use-gl=swiftshader")

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

        # Set reasonable timeouts to prevent hangs but allow WebGL initialization
        service = Service(executable_path="/usr/bin/chromedriver") if is_container else None
        
        # Create the Chrome driver
        if service:
            driver = webdriver.Chrome(service=service, options=options)
        else:
            driver = webdriver.Chrome(options=options)

        driver.set_window_size(1920, 1080)
        
        # Set script timeout with a reasonable value (60s)
        driver.set_script_timeout(60)
        
        # Enhanced stealth script with specific WebGL support
        webgl_script = """
        // Hide automation
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3]});
        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});

        // Enhanced WebGL spoofing to ensure site detects WebGL as available
        try {
            // Add dummy WebGL detection
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                // UNMASKED_VENDOR_WEBGL
                if (parameter === 37445) return "Intel Inc.";
                // UNMASKED_RENDERER_WEBGL
                if (parameter === 37446) return "Intel(R) UHD Graphics 630";
                return getParameter.apply(this, arguments);
            };
            
            // Create a dummy canvas and initialize WebGL to ensure it's available
            const canvas = document.createElement('canvas');
            const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
            if (gl) {
                console.log('WebGL is available in this browser');
                
                // This ensures GPU process starts correctly
                gl.clearColor(0.0, 0.0, 0.0, 1.0);
                gl.clear(gl.COLOR_BUFFER_BIT);
            } else {
                console.log('WebGL not available, using fallback');
            }
        } catch (e) {
            console.error('Error setting up WebGL:', e);
        }
        
        // More stealth techniques
        HTMLCanvasElement.prototype.toDataURL = function() {
            return "data:image/png;base64,fakecanvasfingerprint==";
        };
        
        const originalQuery = navigator.permissions.query;
        navigator.permissions.query = parameters => (
            parameters.name === 'notifications'
                ? Promise.resolve({ state: Notification.permission })
                : originalQuery(parameters)
        );
        """
        
        try:
            # Execute with a specific timeout
            driver.set_script_timeout(30)
            driver.execute_script(webgl_script)
            logger.info("Successfully injected WebGL support scripts")
        except Exception as e:
            # If script fails, log but continue
            logger.warning(f"WebGL script injection failed, but continuing: {e}")

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