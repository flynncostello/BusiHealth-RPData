#!/usr/bin/env python3
# Installation - pip install selenium webdriver-manager undetected-chromedriver requests beautifulsoup4

import time
import random
import logging
import platform
import os
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from chrome_utils import setup_chrome_driver

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LandcheckerScraper:
    def __init__(self, headless=False):
        """Initialize the scraper with Undetected ChromeDriver."""
        self.driver = setup_chrome_driver(headless=headless)
        self.login_url = "https://app.landchecker.com.au/login"
        
    def random_delay(self, min_sec=0.1, max_sec=0.2):
        """Add a minimal random delay between actions - ultra minimal but still avoiding detection."""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)
    
    def human_like_typing(self, element, text):
        """Type text with minimal delays between keypresses - ultra fast typing."""
        # Focus the element directly
        self.driver.execute_script("arguments[0].focus();", element)
        
        # Clear any existing value while preserving focus
        self.driver.execute_script("arguments[0].value = '';", element)
        
        # Type with faster random delays
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.003, 0.008))  # Ultra-fast typing
    
    def wait_and_find_element(self, by, value, timeout=1):  # Minimal timeout
        """Wait for an element to be present and return it."""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            logger.error(f"Timed out waiting for element: {value}")
            return None
    
    def wait_and_find_clickable(self, by, value, timeout=1):  # Minimal timeout
        """Wait for an element to be clickable and return it."""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
            return element
        except TimeoutException:
            logger.error(f"Timed out waiting for clickable element: {value}")
            return None
    
    def safe_click(self, element, retries=1):  # Single retry
        """Attempt to click an element with single retry and minimal delays."""
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
    
    def login(self, email, password):
        """Log in to the Landchecker website with optimized timing."""
        logger.info("Attempting to log in...")
        
        try:
            # Navigate to login page
            self.driver.get(self.login_url)
            self.random_delay(0.2, 0.3)  # Minimal wait after page load
            
            logger.info("Login page loaded")
            
            # Find and fill email field - using selector that worked in logs
            email_field = self.wait_and_find_element(By.CSS_SELECTOR, "input#email")
            
            if email_field:
                self.human_like_typing(email_field, email)
                logger.info("Email entered successfully")
            else:
                logger.error("Email field not found")
                return False
            
            self.random_delay(0.03, 0.05)  # Ultra minimal delay between fields
            
            # Find and fill password field - using selector that worked in logs
            password_field = self.wait_and_find_element(By.CSS_SELECTOR, "input#password")
            
            if password_field:
                self.human_like_typing(password_field, password)
                logger.info("Password entered successfully")
            else:
                logger.error("Password field not found")
                return False
            
            self.random_delay(0.03, 0.05)  # Ultra minimal delay before clicking
            
            # Find and click login button - using selector that worked in logs
            login_button = self.wait_and_find_clickable(By.CSS_SELECTOR, "button[type='submit']")
            
            if login_button:
                success = self.safe_click(login_button)
                if not success:
                    logger.error("Failed to click the login button")
                    return False
                logger.info("Login button clicked successfully")
            else:
                logger.error("Login button not found")
                return False
            
            # Wait for login to complete
            try:
                # Wait for redirection away from login page
                WebDriverWait(self.driver, 3).until(  # Reduced timeout
                    lambda driver: "login" not in driver.current_url.lower()
                )
                logger.info("Login successful - redirected away from login page")
                
                # Minimal wait for page load after login
                self.random_delay(0.2, 0.3)
                
                return True
            except TimeoutException:
                logger.error("Login appears to have failed - still on login page after 3 seconds")
                return False
                
        except Exception as e:
            logger.error(f"Login failed with exception: {e}")
            return False
    
    def is_popup_open(self):
        """Quick check if a zoning info popup is currently open."""
        try:
            # Ultra fast check for dialog elements
            dialog_elements = self.driver.find_elements(By.CSS_SELECTOR, "div[role='dialog'], div[role='presentation']")
            return any(dialog.is_displayed() for dialog in dialog_elements)
        except Exception:
            return False
    
    def close_popup(self):
        """Close the zoning info popup dialog quickly."""
        try:
            # First check if there's actually a popup open
            if not self.is_popup_open():
                logger.info("No popup detected, skipping close operation")
                return True
            
            # If popup is open, find the close button
            close_button = None
            
            # Try the main selector that worked in logs first
            try:
                close_button = self.wait_and_find_clickable(
                    By.CSS_SELECTOR, 
                    "button[data-test='zoneOverlayInfoDialog-closeIcon']", 
                    timeout=0.3  # Ultra minimal timeout
                )
            except Exception:
                pass
            
            # If not found, try a few other selectors with shorter timeout
            if not close_button:
                close_selectors = [
                    "button[aria-label='Close']",
                    "//button[@aria-label='Close']"
                ]
                
                for selector in close_selectors:
                    try:
                        if selector.startswith("//"):
                            close_button = self.wait_and_find_clickable(By.XPATH, selector, timeout=0.2)  # Ultra minimal timeout
                        else:
                            close_button = self.wait_and_find_clickable(By.CSS_SELECTOR, selector, timeout=0.2)  # Ultra minimal timeout
                        
                        if close_button and close_button.is_displayed():
                            logger.info(f"Found close button with alternative selector: {selector}")
                            break
                    except Exception:
                        continue
            
            if close_button:
                # Use JavaScript to click the button - fastest method
                self.driver.execute_script("arguments[0].click();", close_button)
                logger.info("Closed popup successfully")
                # Brief wait for popup to close
                self.random_delay(0.03, 0.05)  # Ultra minimal wait
                return True
            else:
                # If no close button found but we detected a popup, try escape key
                try:
                    logger.info("No close button found, trying Escape key")
                    webdriver.ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                    self.random_delay(0.03, 0.05)  # Ultra minimal wait after Escape
                    return True
                except Exception:
                    logger.warning("Failed to close popup with Escape key")
                    return False
                
        except Exception as e:
            logger.error(f"Error closing popup: {e}")
            return False
    
    def return_to_search(self):
        """Return to the map page and clear the search bar quickly."""
        try:
            # Only close popup if it's open
            if self.is_popup_open():
                self.close_popup()
                # Minimal wait
                self.random_delay(0.03, 0.05)  # Ultra minimal wait
            
            # Look for the search bar
            search_field = self.wait_and_find_clickable(
                By.CSS_SELECTOR, 
                "input[placeholder='Search by address, lot, locality, municipality or postcode']",
                timeout=0.8  # Ultra minimal timeout
            )
            
            if not search_field:
                logger.error("Search field not found when trying to return to search")
                return False
                
            # Clear the search field completely using faster method
            search_field.click()
            
            # Use keyboard shortcuts to select all and delete - faster
            if platform.system() == "Darwin":
                search_field.send_keys(Keys.COMMAND, 'a')
            else:
                search_field.send_keys(Keys.CONTROL, 'a')
                
            self.random_delay(0.02, 0.04)  # Ultra minimal delay
            search_field.send_keys(Keys.DELETE)
            
            logger.info("Cleared search field successfully")
            return True
        except Exception as e:
            logger.error(f"Error returning to search: {e}")
            return False
    
    def search_address(self, address):
        """Search for a specified address with optimized timing."""
        logger.info(f"Searching for address: {address}")
        
        try:
            # Find and click on the search bar
            search_field = self.wait_and_find_clickable(
                By.CSS_SELECTOR, 
                "input[placeholder='Search by address, lot, locality, municipality or postcode']",
                timeout=1  # Minimal timeout
            )
            
            if not search_field:
                logger.error("Search field not found")
                return False
            
            # Clear any existing text
            search_field.clear()
            
            # Enter the address with faster typing
            self.human_like_typing(search_field, address)
            logger.info("Address entered in search field")
            
            self.random_delay(0.15, 0.25)  # Minimal wait for dropdown
            
            # Look specifically for the first dropdown result
            first_result = self.wait_and_find_element(
                By.CSS_SELECTOR, 
                "div[data-test^='appBarSearch-result']:first-of-type",
                timeout=1  # Minimal timeout
            )
            
            if first_result:
                logger.info(f"First result text: {first_result.text}")
                
                # Direct JavaScript click - fastest
                self.driver.execute_script("arguments[0].click();", first_result)
                logger.info("Clicked on first dropdown result using JavaScript")
            else:
                logger.error("No dropdown results found to click")
                return False
            
            logger.info("Search submitted")
            
            # Wait for search results to load
            self.random_delay(0.4, 0.6)  # Minimal but necessary wait
            
            # Fast check for property page indicators
            try:
                # Look for specific property details elements - first direct approach
                property_details = self.wait_and_find_element(By.XPATH, "//div[contains(text(), 'PROPERTY DETAILS')]", timeout=0.8)
                
                if property_details:
                    logger.info("Address found and property details section loaded")
                    return True
                
                # Fallback: check page text for key indicators
                page_text = self.driver.find_element(By.TAG_NAME, "body").text
                property_indicators = ["PROPERTY DETAILS", "LOT/PLAN", "LAND SIZE", "PLANNING ZONE"]
                
                for indicator in property_indicators:
                    if indicator in page_text:
                        logger.info(f"Found property indicator in page text: {indicator}")
                        return True
                
                logger.error("Property details section not found after search")
                return False
            except Exception as e:
                logger.warning(f"Property page detection failed: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Address search failed with exception: {e}")
            return False
    
    def get_zoning_info(self):
        """Click on planning zone and extract the zoning title - optimized for speed but with improved popup waiting."""
        logger.info("Attempting to get zoning information...")
        
        try:
            # Define zone selectors in order of likely success
            zone_selectors = [
                # Specific selectors - check these first (usually faster)
                "li[data-test='zoneOverlayInfo-listItem']",
                "ul.MuiList-root.css-1uzmesd li",
                # Generic selectors as fallbacks
                "//div[text()='PLANNING ZONES']/following-sibling::div/div",
                "//div[contains(@class, 'planning-zone')]",
                "//div[contains(text(), 'PLANNING ZONE')]/following-sibling::div"
            ]
            
            # Fast parallel approach to find zone entry
            zone_entry = None
            
            # Try CSS selectors first (generally faster)
            for selector in [s for s in zone_selectors if not s.startswith("//")]:
                try:
                    zones = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for zone in zones:
                        if zone.is_displayed() and len(zone.text.strip()) > 0:
                            zone_entry = zone
                            logger.info(f"Found zone entry: {zone.text}")
                            break
                    if zone_entry:
                        break
                except Exception:
                    continue
            
            # Try XPath if CSS didn't work
            if not zone_entry:
                for selector in [s for s in zone_selectors if s.startswith("//")]:
                    try:
                        zones = self.driver.find_elements(By.XPATH, selector)
                        for zone in zones:
                            if zone.is_displayed() and len(zone.text.strip()) > 0:
                                zone_entry = zone
                                logger.info(f"Found zone entry: {zone.text}")
                                break
                        if zone_entry:
                            break
                    except Exception:
                        continue
            
            # Pattern-based search as last resort
            if not zone_entry:
                # Common zone codes
                zone_patterns = ["MU1", "MU2", "IN1", "IN2", "SP", "R1", "R2", "B1", "B2", "E1", "E2"]
                
                for pattern in zone_patterns:
                    elements = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{pattern}')]")
                    for element in elements:
                        if element.is_displayed() and len(element.text.strip()) > 0:
                            zone_entry = element
                            logger.info(f"Found zone entry through pattern search: {element.text}")
                            break
                    if zone_entry:
                        break
            
            if not zone_entry:
                logger.error("No planning zone entry found")
                return None
            
            # Get the zone text before clicking (fallback)
            zone_text = zone_entry.text.strip()
            logger.info(f"Planning zone entry text: {zone_text}")
            
            # Click on the planning zone entry to open the popup - direct JavaScript
            logger.info("Clicking on planning zone entry to open popup...")
            self.driver.execute_script("arguments[0].click();", zone_entry)
            
            # *** IMPORTANT FIX: Increased wait time for popup to fully load ***
            self.random_delay(0.5, 0.7)  # Increased wait time for popup to appear
            
            # *** IMPORTANT FIX: Add explicit wait for dialog to appear ***
            try:
                # Wait for dialog to be present in DOM
                WebDriverWait(self.driver, 1.5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='dialog'], div[role='presentation']"))
                )
                logger.info("Popup dialog appeared successfully")
            except TimeoutException:
                logger.warning("Timed out waiting for popup dialog, will try to continue anyway")
            
            # Fast approach to get title - check dialog text directly first
            popup_title = None
            
            # *** IMPORTANT FIX: More comprehensive dialog detection ***
            dialog_elements = []
            for selector in ["div[role='dialog']", "div[role='presentation']", "div.MuiDialog-paper"]:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    dialog_elements.extend([e for e in elements if e.is_displayed()])
                except Exception:
                    pass
            
            # Search for zone info in dialog text
            for dialog in dialog_elements:
                try:
                    dialog_text = dialog.text
                    logger.info(f"Dialog text found: {dialog_text[:100]}...")  # Log first 100 chars
                    
                    # Look for lines containing zone codes and descriptions
                    lines = dialog_text.split('\n')
                    
                    # First try to find a line with both zone code and description 
                    for line in lines:
                        # Check for full zoning title (code followed by description)
                        if (zone_text in line and len(line) > len(zone_text) + 5) or \
                           (any(f"{zone_text} -" in line for zone_text in ["E1", "R1", "B1", "MU1"])):
                            popup_title = line.strip()
                            logger.info(f"Found complete zoning title in dialog: {popup_title}")
                            break
                            
                    # If no complete title found, look for any paragraph with zone code
                    if not popup_title:
                        for line in lines:
                            if zone_text in line and len(line) > 3:  # Avoid just the code itself
                                popup_title = line.strip()
                                logger.info(f"Found partial zoning info in dialog: {popup_title}")
                                break
                                
                    if popup_title:
                        break
                except Exception as e:
                    logger.warning(f"Dialog text extraction error: {e}")
            
            # Try specific element selectors if dialog approach failed
            if not popup_title:
                # Dialog title selectors
                title_selectors = [
                    "div[data-test='zoneOverlayInfoDialog-dialog'] p",
                    "div[role='dialog'] p",
                    "div[role='dialog'] h2",
                    "div[role='dialog'] h3",
                    "//div[@role='dialog']//p",
                ]
                
                for selector in title_selectors:
                    try:
                        if selector.startswith("//"):
                            elements = self.driver.find_elements(By.XPATH, selector)
                        else:
                            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        
                        for element in elements:
                            if element.is_displayed():
                                title_text = element.text.strip()
                                # Check for zone indicators
                                zone_indicators = ["MU", "IN", "SP", "R", "B", "E",
                                                 "Local Centre", "Light Industrial", "Mixed Use"]
                                if title_text and (zone_text in title_text or any(i in title_text for i in zone_indicators)):
                                    popup_title = title_text
                                    logger.info(f"Found popup title in element: {popup_title}")
                                    break
                        if popup_title:
                            break
                    except Exception:
                        continue
            
            # *** IMPORTANT FIX: Try to capture the full zoning title ***
            if not popup_title:
                # Look for any h1, h2, h3, or div containing the zone code
                for tag in ["h1", "h2", "h3", "div", "span", "p"]:
                    try:
                        elements = self.driver.find_elements(By.TAG_NAME, tag)
                        for element in elements:
                            if element.is_displayed():
                                elem_text = element.text.strip()
                                # Look for zone code at start of text (like "E1 - Local Centre")
                                if elem_text.startswith(zone_text) and len(elem_text) > len(zone_text) + 3:
                                    popup_title = elem_text
                                    logger.info(f"Found zoning title in {tag}: {popup_title}")
                                    break
                        if popup_title:
                            break
                    except Exception:
                        continue
            
            # Fall back to the zone text if popup title extraction failed
            if not popup_title and zone_text:
                popup_title = zone_text
                logger.info(f"Using zone text as fallback: {popup_title}")
            
            # Close the popup quickly
            self.close_popup()
            
            return popup_title or None
            
        except Exception as e:
            logger.error(f"Error getting zoning info: {e}")
            return None
    
    def close(self):
        """Close the browser and release resources."""
        if hasattr(self, 'driver') and self.driver:
            try:
                self.driver.quit()
                logger.info("Browser closed successfully")
            except Exception as e:
                logger.error(f"Error closing browser: {e}")


def get_property_zonings(addresses, email="daniel@busivet.com.au", password="Landchecker 2025", headless=False):
    """
    Get zoning information for multiple properties.
    
    Args:
        addresses (list): List of property addresses to search for
        email (str): Login email
        password (str): Login password
        headless (bool): Whether to run browser in headless mode
    
    Returns:
        dict: Dictionary with addresses as keys and zoning info as values
    """
    # Check if we're running in Docker - if so, force headless mode
    is_docker = os.environ.get('RUNNING_IN_DOCKER', 'false').lower() == 'true'
    if is_docker and not headless:
        logger.info("Running in Docker, forcing headless mode")
        headless = True
        
    scraper = LandcheckerScraper(headless=headless)
    results = {}
    
    try:
        # Step 1: Login
        login_success = scraper.login(email, password)
        if not login_success:
            logger.error("Login failed, aborting")
            scraper.close()
            return results
        
        # Step 2: Process each address
        for i, address in enumerate(addresses):
            logger.info(f"Processing address ({i+1}/{len(addresses)}): {address}")
            
            # Search for the address
            search_success = scraper.search_address(address)
            if not search_success:
                logger.error(f"Search failed for address: {address}")
                results[address] = "-"
                continue
            
            # Get zoning information
            zoning_info = scraper.get_zoning_info()
            
            # Store the result
            if zoning_info:
                results[address] = zoning_info
            else:
                results[address] = "-"
            
            # Return to search for next address (if not the last one)
            if address != addresses[-1]:
                scraper.return_to_search()
                scraper.random_delay(0.15, 0.25)  # Minimal wait before next search
        
        return results
        
    except Exception as e:
        logger.error(f"An error occurred during the process: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return results
    finally:
        scraper.close()


def format_zonings_dict(zonings_dict):
    """Format the dictionary of zonings for display."""
    max_addr_len = max([len(addr) for addr in zonings_dict.keys()]) if zonings_dict else 0
    
    result = "\n" + "=" * 80 + "\n"
    result += "ZONING SEARCH RESULTS\n"
    result += "=" * 80 + "\n\n"
    
    for address, zoning in zonings_dict.items():
        result += f"{address.ljust(max_addr_len + 2)}: {zoning}\n"
    
    result += "\n" + "=" * 80 + "\n"
    return result


# Test function to allow running the module directly for testing
def test_landchecker():
    """Test function to verify landchecker functionality."""
    print("Testing Landchecker module...")
    
    # Test with a small set of addresses
    test_addresses = [
        "4/79 ERCEG ROAD, YANGEBUP, WA",
        "1/51 ERCEG ROAD, YANGEBUP, WA",
    ]
    
    # Determine headless mode
    is_docker = os.environ.get('RUNNING_IN_DOCKER', 'false').lower() == 'true'
    headless = is_docker  # Use headless in Docker, otherwise interactive
    
    # Get zoning information
    results = get_property_zonings(test_addresses, headless=headless)
    
    # Format and display results
    formatted_results = format_zonings_dict(results)
    print(formatted_results)
    
    return len(results) > 0


if __name__ == "__main__":
    # Run the test function when this script is executed directly
    test_landchecker()