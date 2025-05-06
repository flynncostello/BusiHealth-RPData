#!/usr/bin/env python3
# Chrome utilities for web scraping with stealth & WebGL spoofing in Docker

import os
import sys
import time
import uuid
import random
import logging
import traceback
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Use CHROME_BINARY environment variable (fallback to AMD64 path)
CHROME_BINARY = os.environ.get("CHROME_BINARY", "/opt/chrome/chrome")
CHROMEDRIVER_PATH = os.environ.get("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")

def setup_chrome_driver(headless=True, download_dir=None):
    try:
        logger.info("Setting up Chrome driver (Docker-only)...")

        options = Options()
        tmp_profile = f"/tmp/chrome-user-data-{uuid.uuid4()}"
        options.add_argument(f"--user-data-dir={tmp_profile}")
        options.headless = headless
        options.binary_location = CHROME_BINARY

        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-background-networking")
        options.add_argument("--disable-sync")
        options.add_argument("--metrics-recording-only")
        options.add_argument("--mute-audio")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--disable-features=NetworkService")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-default-apps")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-translate")
        options.add_argument("--start-maximized")
        options.add_argument("--single-process")
        options.add_argument("--no-zygote")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--incognito")

        if headless:
            options.add_argument("--headless=new")

        if download_dir:
            download_dir = os.path.abspath(download_dir)
            os.makedirs(download_dir, exist_ok=True)
            try:
                os.chmod(download_dir, 0o777)
            except Exception as e:
                logger.warning(f"Could not set permissions on download directory: {e}")

        logger.info("Chrome Options:")
        for arg in options.arguments:
            logger.info(f"  {arg}")

        service = Service(executable_path=CHROMEDRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(60)
        driver.set_script_timeout(30)

        # WebGL spoofing
        spoof_script = """
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        (function() {
            const getContext = HTMLCanvasElement.prototype.getContext;
            HTMLCanvasElement.prototype.getContext = function(type, attrs) {
                if (["webgl", "experimental-webgl", "webgl2", "experimental-webgl2"].includes(type)) {
                    const gl = getContext.apply(this, arguments);
                    return gl || {
                        getParameter: (param) => {
                            switch(param) {
                                case 0x1F00: return 'FakeVendor';
                                case 0x1F01: return 'FakeRenderer';
                                case 0x1F02: return 'WebGL 1.0';
                                case 35724: return 'WebGL GLSL ES 1.0';
                                default: return 0;
                            }
                        },
                        getExtension: () => ({}),
                        getSupportedExtensions: () => ['FAKE_extension']
                    };
                }
                return getContext.apply(this, arguments);
            };
        })();
        """
        try:
            driver.execute_script(spoof_script)
            logger.info("Injected WebGL spoofing script.")
        except Exception as e:
            logger.warning(f"WebGL spoof injection failed: {e}")

        # Set download behavior (only in headless mode)
        if headless and download_dir:
            try:
                driver.execute_cdp_cmd("Page.setDownloadBehavior", {
                    "behavior": "allow",
                    "downloadPath": download_dir
                })
            except Exception as e:
                logger.warning(f"CDP download behavior setup failed: {e}")

        logger.info("Chrome WebDriver initialized successfully")
        return driver

    except Exception as e:
        logger.error(f"Chrome setup failed: {e}")
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
