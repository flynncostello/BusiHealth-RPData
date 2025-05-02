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
        
        # Critical wait for browser initialization
        wait_time = 12 if self.is_cloud else 6
        logger.info(f"Waiting {wait_time}s for browser to fully initialize...")
        time.sleep(wait_time)
        logger.info("Browser initialization complete")
        
        # Add human-like behaviors
        self.enable_human_behavior()
        
        self.login_url = "https://app.landchecker.com.au/login"
        
        logger.info(f"Running in cloud environment: {self.is_cloud}")
        
        # Set timeouts based on environment
        if self.is_cloud:
            # Longer timeouts for cloud environments
            self.std_timeout = 10     # Standard timeout
            self.min_delay = 0.5      # Minimum delay
            self.max_delay = 1.5      # Maximum delay with more randomness
            self.page_load_delay = 4.0  # Page load delay
            self.typing_delay_min = 0.01  # Typing delay min
            self.typing_delay_max = 0.05  # Typing delay max (more human-like)
            self.popup_wait = 2.5     # Wait for popup
            self.search_dropdown_wait = 2.0  # Wait for search dropdown
            self.click_retry_delay = 1.0  # Delay between click retries
            logger.info("Using extended timeouts for cloud environment")
        else:
            # Slightly increased timeouts for local environment
            self.std_timeout = 3      # Standard timeout
            self.min_delay = 0.05     # Minimum delay
            self.max_delay = 0.2      # Maximum delay
            self.page_load_delay = 0.8  # Page load delay
            self.typing_delay_min = 0.005  # Typing delay min
            self.typing_delay_max = 0.01   # Typing delay max
            self.popup_wait = 1.0     # Wait for popup
            self.search_dropdown_wait = 0.5  # Wait for search dropdown
            self.click_retry_delay = 0.1  # Delay between click retries
            logger.info("Using standard timeouts for local environment")
    
    def enable_human_behavior(self):
        """Add random mouse movements and scrolling to appear more human-like."""
        try:
            # Add random scrolling behavior script
            self.driver.execute_script("""
                window._humanScroll = function() {
                    const scrollAmounts = [100, 200, 300, 150, 250];
                    const scrollAmount = scrollAmounts[Math.floor(Math.random() * scrollAmounts.length)];
                    window.scrollBy(0, scrollAmount);
                }
            """)
            logger.info("Human behavior simulation enabled")
        except Exception as e:
            logger.warning(f"Could not enable human behavior simulation: {e}")
            
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
        
        # Type with random delays and occasional pauses
        for i, char in enumerate(text):
            element.send_keys(char)
            # Random typing speed
            delay = random.uniform(self.typing_delay_min, self.typing_delay_max)
            
            # Add occasional longer pause (like a human thinking)
            if i > 0 and i % random.randint(5, 10) == 0:
                delay *= random.uniform(2, 5)
                
            time.sleep(delay)
    
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
                        self.random_delay(self.click_retry_delay, self.click_retry_delay * 2)
        
        logger.error("Failed to click element")
        return False
    
    def login(self, email, password):
        """Log in to the Landchecker website."""
        logger.info(f"Attempting to log in with email: {email}")
        
        try:
            # Randomize the starting URL slightly to avoid patterns
            if random.random() > 0.5:
                self.driver.get("https://app.landchecker.com.au/")
                time.sleep(random.uniform(2.0, 4.0))
                self.driver.get(self.login_url)
            else:
                self.driver.get(self.login_url)
            
            # Random scroll before login
            self.driver.execute_script("if(window._humanScroll) window._humanScroll();")
            
            # Extended wait after page load
            wait_time = random.uniform(self.page_load_delay, self.page_load_delay * 1.5)
            logger.info(f"Waiting {wait_time:.1f}s for login page to fully load...")
            time.sleep(wait_time)
            
            logger.info("Login page loaded")
            
            # Find and fill email field (using selector that works from logs)
            email_field = self.wait_and_find_element(By.CSS_SELECTOR, "input#email")
            
            if email_field:
                self.human_like_typing(email_field, email)
                logger.info("Email entered successfully")
            else:
                logger.error("Email field not found")
                return False
            
            self.random_delay()
            
            # Find and fill password field (using selector that works from logs)
            password_field = self.wait_and_find_element(By.CSS_SELECTOR, "input#password")
            
            if password_field:
                self.human_like_typing(password_field, password)
                logger.info("Password entered successfully")
            else:
                logger.error("Password field not found")
                return False
            
            self.random_delay()
            
            # Find and click login button (using selector that works from logs)
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
                login_wait = self.std_timeout * 2 if self.is_cloud else 5
                WebDriverWait(self.driver, login_wait).until(
                    lambda driver: "login" not in driver.current_url.lower()
                )
                logger.info(f"Login successful - redirected to: {self.driver.current_url}")
                
                # Wait for dashboard to load with random timing
                self.random_delay(self.page_load_delay, self.page_load_delay * 1.5)
                
                return True
            except TimeoutException:
                logger.error(f"Login appears to have failed - still on login page after {login_wait} seconds")
                return False
                
        except Exception as e:
            logger.error(f"Login failed with exception: {e}")
            return False
    
    def is_popup_open(self):
        """Check if a zoning info popup is currently open."""
        try:
            dialog_elements = self.driver.find_elements(By.CSS_SELECTOR, "div[role='dialog'], div[role='presentation']")
            return any(dialog.is_displayed() for dialog in dialog_elements if not isinstance(dialog, StaleElementReferenceException))
        except Exception as e:
            logger.warning(f"Error checking for popup: {e}")
            return False
    
    def close_popup(self):
        """Close the zoning info popup dialog."""
        try:
            # First check if there's actually a popup open
            if not self.is_popup_open():
                logger.info("No popup detected, skipping close operation")
                return True
            
            # Try using Escape key first (most reliable method based on logs)
            logger.info("Sending Escape key to close popup")
            webdriver.ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
            self.random_delay()
            
            # Check if popup is still open
            if not self.is_popup_open():
                logger.info("Popup closed successfully with Escape key")
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
                    self.random_delay()
                    return True
            except Exception:
                pass
            
            # If we get here, neither method worked
            logger.warning("Could not close popup, will continue anyway")
            return True
                
        except Exception as e:
            logger.error(f"Error closing popup: {e}")
            return False
    
    def return_to_search(self):
        """Return to the map page and clear the search bar."""
        try:
            # Only close popup if it's open
            if self.is_popup_open():
                self.close_popup()
                self.random_delay()
            
            # Look for the search bar (using selector that works from logs)
            search_field = self.wait_and_find_clickable(
                By.CSS_SELECTOR, 
                "input[placeholder='Search by address, lot, locality, municipality or postcode']",
                timeout=self.std_timeout
            )
            
            if not search_field:
                logger.error("Search field not found when trying to return to search")
                return False
                
            # Clear the search field
            search_field.click()
            
            # Use keyboard shortcuts to select all and delete
            if platform.system() == "Darwin":
                search_field.send_keys(Keys.COMMAND, 'a')
            else:
                search_field.send_keys(Keys.CONTROL, 'a')
                
            self.random_delay(self.min_delay, self.min_delay * 2)
            search_field.send_keys(Keys.DELETE)
            
            logger.info("Cleared search field successfully")
            return True
        except Exception as e:
            logger.error(f"Error returning to search: {e}")
            return False
    
    def search_address(self, address):
        """Search for a specified address."""
        logger.info(f"Searching for address: {address}")
        
        try:
            # Find and click on the search bar (using selector that works from logs)
            search_field = self.wait_and_find_clickable(
                By.CSS_SELECTOR, 
                "input[placeholder='Search by address, lot, locality, municipality or postcode']",
                timeout=self.std_timeout
            )
            
            if not search_field:
                logger.error("Search field not found")
                return False
            
            # Clear any existing text
            search_field.clear()
            
            # Enter the address
            self.human_like_typing(search_field, address)
            logger.info("Address entered in search field")
            
            self.random_delay(self.search_dropdown_wait, self.search_dropdown_wait * 1.5)
            
            # Look for the first dropdown result (using selector that works from logs)
            first_result = self.wait_and_find_element(
                By.CSS_SELECTOR, 
                "div[data-test^='appBarSearch-result']:first-of-type",
                timeout=self.std_timeout
            )
            
            if first_result:
                logger.info(f"First result text: {first_result.text}")
                
                # Direct JavaScript click
                self.driver.execute_script("arguments[0].click();", first_result)
                logger.info("Clicked on first dropdown result using JavaScript")
            else:
                logger.error("No dropdown results found to click")
                return False
            
            logger.info("Search submitted")
            
            # Wait for search results to load
            self.random_delay(self.page_load_delay, self.page_load_delay * 1.5)
            
            # Check for property page indicators - from logs we know the direct element approach fails
            # but checking page text works, so we'll use that directly
            try:
                page_text = self.driver.find_element(By.TAG_NAME, "body").text
                property_indicators = ["PROPERTY DETAILS", "LOT/PLAN", "LAND SIZE", "PLANNING ZONE"]
                
                for indicator in property_indicators:
                    if indicator in page_text:
                        logger.info(f"Found property indicator in page text: '{indicator}'")
                        return True
                
                logger.error("Property details section not found after search")
                return False
            except Exception as e:
                logger.error(f"Error checking for property indicators: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Address search failed with exception: {e}")
            return False
    
    def get_zoning_info(self):
        """Click on planning zone and extract the zoning title."""
        logger.info("Attempting to get zoning information...")
        
        try:
            # Based on logs, this is the only selector that reliably works for finding the zone entry
            zone_entry = self.wait_and_find_element(By.CSS_SELECTOR, "li[data-test='zoneOverlayInfo-listItem']")
            
            if not zone_entry:
                logger.error("No planning zone entry found")
                return None
            
            # Get the zone text before clicking (fallback)
            zone_text = zone_entry.text.strip()
            logger.info(f"Planning zone entry text: '{zone_text}'")
            
            # Click on the planning zone entry to open the popup
            logger.info("Clicking on planning zone entry to open popup...")
            self.driver.execute_script("arguments[0].click();", zone_entry)
            
            # Wait for popup to fully load
            self.random_delay(self.popup_wait, self.popup_wait * 1.5)
            
            # Add explicit wait for dialog to appear
            try:
                # Wait for dialog to be present in DOM
                WebDriverWait(self.driver, self.std_timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='dialog'], div[role='presentation']"))
                )
                logger.info("Popup dialog appeared successfully")
            except TimeoutException:
                logger.warning(f"Timed out waiting for popup dialog, will try to continue anyway")
            
            # From logs, we know that searching for <div> elements containing the zone text works best
            popup_title = None
            
            try:
                # Find all div elements
                div_elements = self.driver.find_elements(By.TAG_NAME, "div")
                
                # Look for a div that starts with the zone text and is longer than just the code
                for div in div_elements:
                    try:
                        if div.is_displayed():
                            text = div.text.strip()
                            if (text.startswith(zone_text) and len(text) > len(zone_text) + 3):
                                popup_title = text
                                logger.info(f"Found zoning title in div element: '{popup_title}'")
                                break
                    except:
                        continue
            except Exception as e:
                logger.warning(f"Error finding zoning title in divs: {e}")
            
            # Fall back to the zone text if popup title extraction failed
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
    logger.info(f"Headless mode requested: {headless}")
    
    scraper = LandcheckerScraper(headless=headless)
    results = {}
    
    try:
        # Check for cancellation before login
        if progress_callback and progress_callback(65, "Logging into Landchecker...") is False:
            logger.info("Job cancelled before Landchecker login")
            scraper.close()
            return results
        
        # Step 1: Login
        login_success = scraper.login(email, password)
        if not login_success:
            logger.error("Login failed, aborting")
            scraper.close()
            return results
        
        # Check for cancellation after login
        if progress_callback and progress_callback(68, "Getting zoning information...") is False:
            logger.info("Job cancelled after Landchecker login")
            scraper.close()
            return results
        
        # Step 2: Process each address
        for i, address in enumerate(addresses):
            # Calculate progress percentage
            progress = 68 + int(22 * (i / len(addresses)))
            progress_msg = f"Processing address ({i+1}/{len(addresses)}): {address}"
            
            # Check for cancellation before each address
            if progress_callback and progress_callback(progress, progress_msg) is False:
                logger.info(f"Job cancelled during Landchecker processing at address {i+1}/{len(addresses)}")
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
            
            # Return to search for next address (if not the last one)
            if address != addresses[-1]:
                logger.debug(f"Returning to search for next address")
                scraper.return_to_search()
                scraper.random_delay(scraper.page_load_delay / 2, scraper.page_load_delay)
        
        logger.info(f"Zoning lookup complete. Found zoning for {sum(1 for v in results.values() if v != '-')}/{len(addresses)} addresses")
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
        "1/51 ERCEG ROAD, YANGEBUP, WA",
        "4/594 INKERMAN ROAD, CAULFIELD NORTH, VIC"
    ]
    
    # Default to headless mode for consistency
    headless = True
    
    # Get zoning information
    results = get_property_zonings(test_addresses, headless=headless)
    
    # Format and display results
    formatted_results = format_zonings_dict(results)
    print(formatted_results)
    
    return len(results) > 0


if __name__ == "__main__":
    # Run the test function when this script is executed directly
    test_landchecker()