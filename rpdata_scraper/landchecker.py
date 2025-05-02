#!/usr/bin/env python3
# Installation - pip install selenium webdriver-manager requests beautifulsoup4

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
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from chrome_utils import setup_chrome_driver

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LandcheckerScraper:
    def __init__(self, headless=False, download_dir=None):
        """Initialize the scraper with ChromeDriver."""
        # Use a safe default download path if not provided
        if download_dir is None:
            download_dir = os.path.join(os.getcwd(), "downloads")

        # Make sure the directory exists
        os.makedirs(download_dir, exist_ok=True)
        self.download_dir = download_dir

        # Add environment detection early
        self.is_cloud = any([
            os.environ.get('WEBSITE_SITE_NAME') is not None,  # Azure App Service
            os.environ.get('DOCKER_CONTAINER') == 'true',     # Docker container
            os.environ.get('AZURE_FUNCTIONS_ENVIRONMENT') is not None,  # Azure Functions
            os.environ.get('KUBERNETES_SERVICE_HOST') is not None,  # Kubernetes
            os.path.exists('/.dockerenv'),  # Another Docker check
            os.environ.get('RUNNING_IN_AZURE') == 'true'  # Custom flag you can set
        ])
        
        # Let chrome_utils handle the headless mode
        # It will automatically force headless=True in container environments
        logger.info(f"Setting up Chrome driver with headless={headless}...")
        self.driver = setup_chrome_driver(headless=headless, download_dir=self.download_dir)
        
        # Minimal wait for browser initialization
        time.sleep(2)
        logger.info("Browser initialization complete")
        
        # Set timeouts based on environment - simplified with shorter times
        self.std_timeout = 8 if self.is_cloud else 5        # Standard timeout
        self.min_delay = 0.2                                # Minimum delay
        self.max_delay = 0.8                                # Maximum delay
        self.typing_delay_min = 0.01                        # Typing delay min
        self.typing_delay_max = 0.03                        # Typing delay max
        
        # Direct login URL
        self.login_url = "https://app.landchecker.com.au/login"
        logger.info(f"Running in cloud environment: {self.is_cloud}")
    
    def random_delay(self, min_sec=None, max_sec=None):
        """Add a random delay between actions."""
        if min_sec is None:
            min_sec = self.min_delay
        if max_sec is None:
            max_sec = self.max_delay
            
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)
        return delay
    
    def human_like_typing(self, element, text):
        """Type text with delays between keypresses."""
        # Focus the element directly
        self.driver.execute_script("arguments[0].focus();", element)
        
        # Clear any existing value while preserving focus
        self.driver.execute_script("arguments[0].value = '';", element)
        
        # Type with random delays
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(self.typing_delay_min, self.typing_delay_max))
    
    def wait_and_find_element(self, by, value, timeout=None):
        """Wait for an element to be present and return it."""
        if timeout is None:
            timeout = self.std_timeout
            
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            logger.error(f"Timed out waiting for element: {by}='{value}' after {timeout}s")
            return None
    
    def wait_and_find_clickable(self, by, value, timeout=None):
        """Wait for an element to be clickable and return it."""
        if timeout is None:
            timeout = self.std_timeout
            
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
            return element
        except TimeoutException:
            logger.error(f"Timed out waiting for clickable element: {by}='{value}' after {timeout}s")
            return None
    
    def safe_click(self, element, retries=1):
        """Attempt to click an element with retries."""
        for i in range(retries + 1):
            try:
                # Direct JavaScript click
                self.driver.execute_script("arguments[0].click();", element)
                return True
            except Exception as js_error:
                try:
                    # Fall back to regular Selenium click
                    element.click()
                    return True
                except Exception as e:
                    if i < retries:
                        self.random_delay(0.1, 0.3)
        
        logger.error("Failed to click element")
        return False
    
    def login(self, email, password):
        """Log in to the Landchecker website."""
        logger.info(f"Logging in with email: {email}")
        
        try:
            # Go directly to login page
            self.driver.get(self.login_url)
            
            # Wait for login page to load
            time.sleep(1)
            logger.info("Login page loaded")
            
            # Find and fill email field
            email_field = self.wait_and_find_element(By.CSS_SELECTOR, "input#email")
            
            if email_field:
                self.human_like_typing(email_field, email)
                logger.info("Email entered")
            else:
                logger.error("Email field not found")
                return False
            
            self.random_delay(0.1, 0.3)
            
            # Find and fill password field
            password_field = self.wait_and_find_element(By.CSS_SELECTOR, "input#password")
            
            if password_field:
                self.human_like_typing(password_field, password)
                logger.info("Password entered")
            else:
                logger.error("Password field not found")
                return False
            
            self.random_delay(0.1, 0.3)
            
            # Find and click login button
            login_button = self.wait_and_find_clickable(By.CSS_SELECTOR, "button[type='submit']")
            
            if login_button:
                success = self.safe_click(login_button)
                if not success:
                    logger.error("Failed to click the login button")
                    return False
                logger.info("Login button clicked")
            else:
                logger.error("Login button not found")
                return False
            
            # Wait for login to complete and dashboard to load
            try:
                # Wait for redirection away from login page
                WebDriverWait(self.driver, self.std_timeout).until(
                    lambda driver: "login" not in driver.current_url.lower()
                )
                logger.info(f"Login successful - redirected to: {self.driver.current_url}")
                time.sleep(2)
                return True
            except TimeoutException:
                logger.error(f"Login appears to have failed - still on login page after {self.std_timeout} seconds")
                return False
                
        except Exception as e:
            logger.error(f"Login failed with exception: {e}")
            return False
    
    def is_popup_open(self):
        """Check if a zoning info popup is currently open."""
        try:
            dialog_elements = self.driver.find_elements(By.CSS_SELECTOR, "div[role='dialog'], div[role='presentation']")
            return any(dialog.is_displayed() for dialog in dialog_elements if not isinstance(dialog, StaleElementReferenceException))
        except Exception:
            return False
    
    def close_popup(self):
        """Close the zoning info popup dialog."""
        try:
            # Use Escape key to close popup
            webdriver.ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
            self.random_delay(0.3, 0.6)
            
            # Check if popup is still open
            if not self.is_popup_open():
                logger.info("Popup closed with Escape key")
                return True
            
            # If Escape didn't work, try clicking close button
            try:
                close_button = self.wait_and_find_clickable(
                    By.CSS_SELECTOR, 
                    "button[data-test='zoneOverlayInfoDialog-closeIcon'], button[aria-label='Close']",
                    timeout=self.std_timeout / 2
                )
                
                if close_button:
                    self.driver.execute_script("arguments[0].click();", close_button)
                    logger.info("Closed popup with close button")
                    return True
            except Exception:
                pass
            
            logger.warning("Could not close popup, continuing anyway")
            return True
                
        except Exception as e:
            logger.error(f"Error closing popup: {e}")
            return False
    
    def return_to_search(self):
        """Return to the map page and clear the search bar."""
        try:
            # Close popup if open
            if self.is_popup_open():
                self.close_popup()
            
            # Find the search bar
            search_field = self.wait_and_find_clickable(
                By.CSS_SELECTOR, 
                "input[placeholder='Search by address, lot, locality, municipality or postcode']"
            )
            
            if not search_field:
                logger.error("Search field not found when trying to return to search")
                return False
                
            # Clear the search field using keyboard shortcuts
            search_field.click()
            
            if platform.system() == "Darwin":
                search_field.send_keys(Keys.COMMAND, 'a')
            else:
                search_field.send_keys(Keys.CONTROL, 'a')
                
            self.random_delay(0.1, 0.2)
            search_field.send_keys(Keys.DELETE)
            
            logger.info("Cleared search field")
            return True
        except Exception as e:
            logger.error(f"Error returning to search: {e}")
            return False
    
    def search_address(self, address):
        """Search for a specified address."""
        logger.info(f"Searching for address: {address}")
        
        try:
            # Find and click on the search bar
            search_field = self.wait_and_find_clickable(
                By.CSS_SELECTOR, 
                "input[placeholder='Search by address, lot, locality, municipality or postcode']"
            )
            
            if not search_field:
                logger.error("Search field not found")
                return False
            
            # Clear any existing text
            search_field.clear()
            
            # Enter the address
            self.human_like_typing(search_field, address)
            logger.info("Address entered in search field")
            
            # Wait for dropdown to appear
            self.random_delay(0.5, 1.0)
            
            # Look for the first dropdown result
            first_result = self.wait_and_find_element(
                By.CSS_SELECTOR, 
                "div[data-test^='appBarSearch-result']:first-of-type"
            )
            
            if first_result:
                logger.info(f"First result: {first_result.text}")
                self.driver.execute_script("arguments[0].click();", first_result)
                logger.info("Clicked on first dropdown result")
            else:
                logger.error("No dropdown results found")
                return False
            
            # Wait for search results to load
            time.sleep(2)
            
            # Check for property page indicators 
            try:
                page_text = self.driver.find_element(By.TAG_NAME, "body").text
                property_indicators = ["PROPERTY DETAILS", "LOT/PLAN", "LAND SIZE", "PLANNING ZONE"]
                
                for indicator in property_indicators:
                    if indicator in page_text:
                        logger.info(f"Found property indicator: '{indicator}'")
                        return True
                
                logger.error("Property details section not found after search")
                return False
            except Exception as e:
                logger.error(f"Error checking for property indicators: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Address search failed: {e}")
            return False
    
    def get_zoning_info(self):
        """Click on planning zone and extract the zoning title."""
        logger.info("Getting zoning information...")
        
        try:
            # Find the zone entry
            zone_entry = self.wait_and_find_element(By.CSS_SELECTOR, "li[data-test='zoneOverlayInfo-listItem']")
            
            if not zone_entry:
                logger.error("No planning zone entry found")
                return None
            
            # Get the zone text before clicking
            zone_text = zone_entry.text.strip()
            logger.info(f"Planning zone entry text: '{zone_text}'")
            
            # Click on the planning zone entry to open the popup
            logger.info("Clicking on planning zone entry...")
            self.driver.execute_script("arguments[0].click();", zone_entry)
            
            # Wait for popup to appear
            time.sleep(1)
            
            # Find zoning title in popup
            popup_title = None
            
            try:
                # Find all div elements with zoning info
                div_elements = self.driver.find_elements(By.TAG_NAME, "div")
                
                # Look for a div that starts with the zone text and is longer
                for div in div_elements:
                    try:
                        if div.is_displayed():
                            text = div.text.strip()
                            if (text.startswith(zone_text) and len(text) > len(zone_text) + 3):
                                popup_title = text
                                logger.info(f"Found zoning title: '{popup_title}'")
                                break
                    except:
                        continue
            except Exception as e:
                logger.warning(f"Error finding zoning title: {e}")
            
            # Fall back to zone text if needed
            if not popup_title and zone_text:
                popup_title = zone_text
                logger.info(f"Using zone text as fallback: '{popup_title}'")
            
            # Close the popup
            self.close_popup()
            
            return popup_title or None
            
        except Exception as e:
            logger.error(f"Error getting zoning info: {e}")
            return None
    
    def close(self):
        """Close the browser and release resources."""
        logger.info("Closing browser")
        if hasattr(self, 'driver') and self.driver:
            try:
                self.driver.quit()
                logger.info("Browser closed successfully")
            except Exception as e:
                logger.error(f"Error closing browser: {e}")


def get_property_zonings(addresses, email="daniel@busivet.com.au", password="Landchecker 2025", headless=True, progress_callback=None):
    """
    Get zoning information for multiple properties.
    
    Args:
        addresses (list): List of property addresses to search for
        email (str): Login email
        password (str): Login password
        headless (bool): Whether to run browser in headless mode (will be forced to True in containers)
        progress_callback (function): Optional callback to check for cancellation
    
    Returns:
        dict: Dictionary with addresses as keys and zoning info as values
    """
    # Default progress callback
    if progress_callback is None:
        def progress_callback(percentage, message):
            return True  # Always continue
    
    logger.info(f"Starting property zoning lookup for {len(addresses)} addresses")
    
    scraper = LandcheckerScraper(headless=headless)
    results = {}
    
    try:
        # Check for cancellation before login
        if progress_callback and progress_callback(65, "Logging into Landchecker...") is False:
            logger.info("Job cancelled before login")
            scraper.close()
            return results
        
        # Login
        login_success = scraper.login(email, password)
        if not login_success:
            logger.error("Login failed, aborting")
            scraper.close()
            return results
        
        # Check for cancellation after login
        if progress_callback and progress_callback(68, "Getting zoning information...") is False:
            logger.info("Job cancelled after login")
            scraper.close()
            return results
        
        # Process each address
        for i, address in enumerate(addresses):
            # Calculate progress percentage
            progress = 68 + int(22 * (i / len(addresses)))
            progress_msg = f"Processing address ({i+1}/{len(addresses)}): {address}"
            
            # Check for cancellation before each address
            if progress_callback and progress_callback(progress, progress_msg) is False:
                logger.info(f"Job cancelled during processing at address {i+1}/{len(addresses)}")
                scraper.close()
                return results
                
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
                logger.info(f"Found zoning for {address}: {zoning_info}")
                results[address] = zoning_info
            else:
                logger.warning(f"No zoning found for {address}")
                results[address] = "-"
            
            # Return to search for next address
            if address != addresses[-1]:
                scraper.return_to_search()
                scraper.random_delay(0.5, 1.0)
        
        logger.info(f"Zoning lookup complete. Found zoning for {sum(1 for v in results.values() if v != '-')}/{len(addresses)} addresses")
        return results
        
    except Exception as e:
        logger.error(f"An error occurred: {e}")
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
        "1/51 ERCEG ROAD, YANGEBUP, WA",
        "4/594 INKERMAN ROAD, CAULFIELD NORTH, VIC"
    ]
    
    # Get zoning information
    results = get_property_zonings(test_addresses, headless=True)
    
    # Format and display results
    formatted_results = format_zonings_dict(results)
    print(formatted_results)
    
    return len(results) > 0


if __name__ == "__main__":
    # Run the test function when this script is executed directly
    test_landchecker()