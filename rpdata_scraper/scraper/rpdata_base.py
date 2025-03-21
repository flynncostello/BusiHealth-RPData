#!/usr/bin/env python3
# Base functionality for RP Data scraper

import time
import random
import logging
import sys
import os
import platform
import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RPDataBase:
    def __init__(self, headless=False):
        """Initialize the scraper with Undetected ChromeDriver."""
        self.download_dir = os.path.join(os.getcwd(), "downloads")
        os.makedirs(self.download_dir, exist_ok=True)
        self.setup_driver(headless)
        self.login_url = "https://rpp.corelogic.com.au/"
        
    def setup_driver(self, headless):
        """Set up the Undetected ChromeDriver with optimal settings."""
        try:
            logger.info("Setting up Undetected ChromeDriver...")
            
            # Configure options for undetected_chromedriver
            options = uc.ChromeOptions()
            
            if headless:
                options.add_argument("--headless")
            
            # Add common options to make detection harder
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--window-size=1920,1080")
            
            # Set download preferences
            prefs = {
                "download.default_directory": self.download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True
            }
            options.add_experimental_option("prefs", prefs)
            
            # Add a realistic user agent
            user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
            options.add_argument(f'user-agent={user_agent}')
            
            # Special handling for Render environment
            is_render = "RENDER" in os.environ
            
            if is_render:
                logger.info("Detected Render environment - using special configuration")
                # For Render, don't set binary_location manually
                # Let undetected_chromedriver find installed Chrome
            elif platform.system() == "Darwin" and platform.machine() == "arm64":
                logger.info("Detected Mac with ARM architecture - applying special configuration")
                # Check for common browser locations
                chromium_paths = [
                    "/Applications/Chromium.app/Contents/MacOS/Chromium",
                    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
                    os.path.expanduser("~/Applications/Chromium.app/Contents/MacOS/Chromium"),
                    os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
                ]
                
                for browser_path in chromium_paths:
                    if os.path.exists(browser_path):
                        logger.info(f"Using browser at: {browser_path}")
                        options.binary_location = browser_path
                        break
            
            # Log what we're doing with binary location
            if hasattr(options, 'binary_location') and options.binary_location:
                logger.info(f"Chrome binary location set to: {options.binary_location}")
            else:
                logger.info("No specific Chrome binary set, using system default")
            
            # Initialize undetected ChromeDriver with special handling for Render
            if is_render:
                logger.info("Using custom driver initialization for Render")
                self.driver = uc.Chrome(
                    options=options,
                    version_main=None,
                    use_subprocess=True,
                    driver_executable_path=None  # Let it auto-detect
                )
            else:
                self.driver = uc.Chrome(
                    options=options,
                    version_main=None,
                    use_subprocess=True
                )
            
            # Set the window size explicitly
            self.driver.set_window_size(1920, 1080)
            
            # Make detection harder by modifying navigator properties
            self.driver.execute_script("""
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
            
        except Exception as e:
            logger.error(f"Failed to initialize Undetected ChromeDriver: {e}")
            sys.exit(1)
    
    def random_delay(self, min_sec=0.1, max_sec=0.2):
        """Add a minimal random delay between actions."""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)
    
    def human_like_typing(self, element, text, speed="normal"):
        """
        Type text with human-like delays between keypresses.
        
        Args:
            element: The element to type into
            text: The text to type
            speed: Speed of typing - "slow", "normal", or "fast"
        """
        # Focus the element directly
        self.driver.execute_script("arguments[0].focus();", element)
        
        # Clear any existing value while preserving focus
        self.driver.execute_script("arguments[0].value = '';", element)
        
        # Type with appropriate delays based on speed
        if speed == "slow":
            delay_min, delay_max = 0.05, 0.15  # Slower typing
        elif speed == "normal":
            delay_min, delay_max = 0.01, 0.05  # Normal typing
        else:  # fast
            delay_min, delay_max = 0.003, 0.008  # Very fast typing
        
        # Type character by character
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(delay_min, delay_max))
    
    def wait_and_find_element(self, by, value, timeout=5):
        """Wait for an element to be present and return it."""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            logger.error(f"Timed out waiting for element: {value}")
            return None
    
    def wait_and_find_clickable(self, by, value, timeout=5):
        """Wait for an element to be clickable and return it."""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
            return element
        except TimeoutException:
            logger.error(f"Timed out waiting for clickable element: {value}")
            return None
    
    def safe_click(self, element, retries=1):
        """Attempt to click an element with retries."""
        for i in range(retries + 1):  # +1 to include initial attempt
            try:
                # Direct JavaScript click - fastest method
                self.driver.execute_script("arguments[0].click();", element)
                return True
            except Exception as js_error:
                logger.warning(f"JavaScript click failed: {js_error}")
                
                try:
                    # Fall back to regular Selenium click
                    element.click()
                    return True
                except Exception as e:
                    if i < retries:
                        logger.warning(f"Click failed: {e}, retrying")
                        self.random_delay(0.05, 0.08)  # Minimal delay between retries
        
        logger.error("Failed to click element")
        return False
    
    def close(self):
        """Close the WebDriver."""
        if hasattr(self, 'driver'):
            self.driver.quit()
            logger.info("WebDriver closed")