#!/usr/bin/env python3
# Chrome utilities for web scraping with stealth & WebGL support in Docker/macOS/Windows

import os
import sys
import time
import uuid
import random
import logging
import traceback
import platform
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_chromedriver_path():
    """Find the actual ChromeDriver binary."""
    # First check the environment variable
    env_path = os.environ.get("CHROMEDRIVER_PATH")
    if env_path and os.path.isfile(env_path) and os.access(env_path, os.X_OK if platform.system() != "Windows" else os.F_OK):
        logger.info(f"Using ChromeDriver from environment variable: {env_path}")
        return env_path
    
    # Check for manually installed ChromeDriver in home directory
    home_dir = os.path.expanduser("~")
    if platform.system() == "Windows":
        manual_path = os.path.join(home_dir, ".chromedriver", "chromedriver.exe")
    else:
        manual_path = os.path.join(home_dir, ".chromedriver", "chromedriver")
    
    if os.path.isfile(manual_path) and (os.access(manual_path, os.X_OK) if platform.system() != "Windows" else True):
        logger.info(f"Using manually installed ChromeDriver: {manual_path}")
        return manual_path
    
    # Fall back to WebDriver Manager
    logger.info("No direct ChromeDriver found, using WebDriverManager (this might cause issues)")
    return ChromeDriverManager().install()

# Get ChromeDriver path
try:
    CHROMEDRIVER_PATH = get_chromedriver_path()
    logger.info(f"Using ChromeDriver at: {CHROMEDRIVER_PATH}")
except Exception as e:
    logger.error(f"Failed to locate ChromeDriver: {str(e)}")
    CHROMEDRIVER_PATH = None

# Get Chrome binary path (from environment variable or default locations)
CHROME_BINARY = os.environ.get("CHROME_BINARY")
if not CHROME_BINARY:
    # Try to find Chrome in common locations
    possible_paths = [
        # macOS
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        # Windows
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
        # Linux
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            CHROME_BINARY = path
            logger.info(f"Found Chrome binary at: {CHROME_BINARY}")
            break

def setup_chrome_driver(headless=False, download_dir=None):
    """Set up Chrome WebDriver with appropriate options."""
    try:
        logger.info("Setting up Chrome driver with WebGL enabled...")
        
        if not CHROMEDRIVER_PATH:
            raise Exception("ChromeDriver path not found. Please install Chrome or set CHROMEDRIVER_PATH.")
        
        options = Options()
        
        # Create a persistent user data directory for Chrome
        tmp_profile = f"/tmp/chrome-user-data-{uuid.uuid4()}"
        options.add_argument(f"--user-data-dir={tmp_profile}")
        
        if CHROME_BINARY:
            options.binary_location = CHROME_BINARY
            logger.info(f"Using Chrome binary: {CHROME_BINARY}")
        
        # CRITICAL: Enable GPU and hardware acceleration for WebGL
        options.add_argument("--ignore-gpu-blocklist")
        options.add_argument("--enable-gpu-rasterization")
        options.add_argument("--enable-webgl")
        options.add_argument("--enable-accelerated-2d-canvas")
        options.add_argument("--enable-zero-copy")
        options.add_argument("--canvas-msaa-sample-count=2")
        
        # Add common arguments
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-software-rasterizer")  # Force hardware rasterization
        options.add_argument("--disable-background-networking")
        options.add_argument("--disable-sync")
        options.add_argument("--metrics-recording-only")
        options.add_argument("--mute-audio")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-translate")
        options.add_argument("--start-maximized")
        options.add_argument("--window-size=1920,1080")
        
        # CRITICAL: Do NOT disable GPU - remove these lines if they exist
        # options.add_argument("--disable-gpu")
        
        # Avoid single-process and no-zygote on Mac which can cause issues
        if platform.system() != "Darwin":
            options.add_argument("--single-process")
            options.add_argument("--no-zygote")
        
        # Headless mode with WebGL support
        if headless:
            options.add_argument("--headless=new")
        
        if download_dir:
            download_dir = os.path.abspath(download_dir)
            os.makedirs(download_dir, exist_ok=True)
            try:
                os.chmod(download_dir, 0o777)
            except Exception as e:
                logger.warning(f"Could not set permissions on download directory: {e}")
                    
        # IMPORTANT: Create ONE combined dictionary with ALL preferences
        prefs = {
            # WebGL and GPU settings - always include these
            "hardware_acceleration_mode.enabled": True,
            "webgl.disabled": False,
            "webgl.enable_webgl2": True,
            "accelerated_2d_canvas": True,
            "plugins.always_open_pdf_externally": True,
        }

        # Add download settings only if download_dir is specified
        if download_dir:
            prefs.update({
                "download.default_directory": download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": False
            })

        # Apply ALL preferences with a single call
        options.add_experimental_option("prefs", prefs)
        
        # CRITICAL: Enable WebGL in Chrome
        options.add_experimental_option("excludeSwitches", ["disable-webgl"])
        
        logger.info("Chrome Options:")
        for arg in options.arguments:
            logger.info(f"  {arg}")
        
        service = Service(executable_path=CHROMEDRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(60)
        driver.set_script_timeout(30)
        
        # CRITICAL: Only hide WebDriver - don't spoof WebGL anymore
        stealth_script = """
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """
        try:
            driver.execute_script(stealth_script)
            logger.info("Injected WebDriver stealth script.")
        except Exception as e:
            logger.warning(f"WebDriver stealth script injection failed: {e}")
        
        # Test if WebGL is enabled and working
        try:
            webgl_test = """
            const canvas = document.createElement('canvas');
            const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
            return !!gl;
            """
            webgl_enabled = driver.execute_script(webgl_test)
            logger.info(f"WebGL enabled: {webgl_enabled}")
            
            if not webgl_enabled:
                logger.warning("WebGL does not appear to be enabled. Landchecker may not work correctly.")
        except Exception as e:
            logger.warning(f"Could not test WebGL status: {e}")
        
        # Set download behavior (only in headless mode)
        if headless and download_dir:
            try:
                driver.execute_cdp_cmd("Page.setDownloadBehavior", {
                    "behavior": "allow",
                    "downloadPath": download_dir
                })
            except Exception as e:
                logger.warning(f"CDP download behavior setup failed: {e}")
        
        logger.info("Chrome WebDriver initialized successfully with WebGL support")
        return driver
    
    except Exception as e:
        logger.error(f"Chrome setup failed: {e}")
        logger.error(traceback.format_exc())
        
        # Be more informative about common errors
        if "chromedriver" in str(e).lower() and "executable" in str(e).lower():
            logger.error("The ChromeDriver executable could not be found or is not executable.")
            logger.error(f"ChromeDriver path: {CHROMEDRIVER_PATH}")
            logger.error("Please ensure Chrome is installed and try running the build script again.")
        
        if "chrome binary" in str(e).lower():
            logger.error("The Chrome browser executable could not be found.")
            logger.error(f"Chrome binary path: {CHROME_BINARY}")
            logger.error("Please ensure Google Chrome is installed on your system.")
        
        sys.exit(1)

def random_wait(min_seconds=0.5, max_seconds=2):
    """Wait a random amount of time to mimic human behavior."""
    wait_time = min_seconds + random.random() * (max_seconds - min_seconds)
    time.sleep(wait_time)
    return wait_time

def create_wait(driver, timeout=10):
    """Create a WebDriverWait object for waiting for elements."""
    return WebDriverWait(driver, timeout)

if __name__ == "__main__":
    # Test the chrome_utils module
    print("Testing Chrome WebDriver setup...")
    driver = setup_chrome_driver(headless=False)
    try:
        driver.get("https://www.google.com")
        print(f"Test successful: {driver.title}")
        
        # Test WebGL
        webgl_test = """
        const canvas = document.createElement('canvas');
        const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
        if (!gl) {
            return "WebGL NOT SUPPORTED";
        }
        const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
        if (debugInfo) {
            return {
                vendor: gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL),
                renderer: gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL),
                version: gl.getParameter(gl.VERSION)
            };
        }
        return "WebGL supported but couldn't get debug info";
        """
        webgl_info = driver.execute_script(webgl_test)
        print("WebGL Info:", webgl_info)
    except Exception as e:
        print(f"Test failed: {e}")
    finally:
        driver.quit()