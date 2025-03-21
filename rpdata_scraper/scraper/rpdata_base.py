#!/usr/bin/env python3
# Base functionality for RP Data scraper

import time
import random
import logging
import os
import sys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from chrome_utils import setup_chrome_driver


# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RPDataBase:
    def __init__(self, headless=False):
        """Initialize the scraper with Undetected ChromeDriver."""
        self.download_dir = os.path.join(os.getcwd(), "downloads")
        os.makedirs(self.download_dir, exist_ok=True)
        self.driver = setup_chrome_driver(headless=headless, download_dir=self.download_dir)
        self.login_url = "https://rpp.corelogic.com.au/"
    
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
        """Close the browser and release resources."""
        if hasattr(self, 'driver') and self.driver:
            try:
                self.driver.quit()
                logger.info("Browser closed successfully")
            except Exception as e:
                logger.error(f"Error closing browser: {e}")