#!/usr/bin/env python3
"""
RP Data Scraper - CoreLogic Property Data Automation Tool
========================================================

OVERVIEW:
---------
This script automates the process of searching, filtering, and exporting property data
from the RP Data (CoreLogic) platform. It handles the entire workflow from login to 
data export, with robust error handling and logging at each step.

FUNCTIONALITY:
-------------
- Automatically logs into the RP Data platform
- Clears download directory to prevent file confusion
- Performs property searches based on specified locations
- Applies filters such as property types and floor area constraints
- Handles selection of search results (all or first 10,000 if more)
- Exports data to CSV/Excel format
- Handles cases where searches return no results
- Includes comprehensive logging for troubleshooting

WORKFLOW STEPS:
--------------
1. Clear download directory
2. Login to RP Data
3. Select search type (Sales, For Sale, For Rent)
4. Search for specified locations
5. Apply property type and floor area filters
6. Check if results exist; if none, skip to next search
7. Select all results (or first 10,000)
8. Export data to CSV
9. Verify download and return file path
10. Return to dashboard for next search

REQUIREMENTS:
------------
- Selenium WebDriver with undetected_chromedriver
- Valid RP Data credentials
- Chrome browser installed
- rpdata_base.py containing the base class with common utilities

USAGE:
------
Create an instance of RPDataScraper and use the run_search method with appropriate parameters:

    scraper = RPDataScraper(download_dir="/path/to/downloads", headless=False)
    file_path = scraper.run_search(
        username="your_username",
        password="your_password",
        search_type="Sales",  # or "For Sale" or "For Rent"
        locations=["Sydney", "Melbourne"],
        property_types=["House", "Unit"],
        min_floor_area="100",
        max_floor_area="500"
    )

Each method can also be called individually for more granular control over the process.
"""

import os
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from rpdata_base import RPDataBase, logger

# Define constants for filter results to avoid string comparison issues
FILTER_NO_RESULTS = 0
FILTER_SUCCESS = 1
FILTER_ERROR = 2

class RPDataScraper(RPDataBase):
    def run_search(self, username, password, search_type, locations, property_types, min_floor_area="Min", max_floor_area="Max"):
        """
        Run a complete search flow from login to export.
        Returns the path to the exported CSV file, or None if no results were found or an error occurred.
        """
        logger.info(f"===== STARTING COMPLETE SEARCH FLOW: {search_type} =====")
        
        try:
            # Login if needed
            if not self.is_logged_in():
                if not self.login(username, password):
                    logger.error("Login failed, cannot proceed with search")
                    return None
            
            # Select the search type (Sales, For Sale, For Rent)
            if not self.select_search_type(search_type):
                logger.error(f"Failed to select search type {search_type}, skipping")
                self.return_to_dashboard()
                return None
            
            # Search for the specified locations
            if not self.search_locations(locations):
                logger.error(f"Failed to search locations {locations}, skipping")
                self.return_to_dashboard()
                return None
            
            # Apply filters - now using enum-like constants instead of strings
            filter_result = self.apply_filters(property_types, min_floor_area, max_floor_area)
            
            # Handle filter results
            if filter_result == FILTER_NO_RESULTS:
                logger.info(f"No matching properties found for search type {search_type} with the specified filters")
                # No need to return to dashboard as apply_filters already did this when no results were found
                return None
            elif filter_result == FILTER_ERROR:
                logger.error("Error applying filters, continuing to next search type")
                self.return_to_dashboard()
                return None
            
            # We now know filter_result must be FILTER_SUCCESS
            logger.info("Filters applied successfully, proceeding to select results")
                
            # Select all results - check if there are any results
            if not self.select_all_results():
                logger.info(f"No results found for search type {search_type} with the specified filters")
                self.return_to_dashboard()
                return None
            
            # Export to CSV
            if not self.export_to_csv(search_type):
                logger.error("Failed to export to CSV")
                self.return_to_dashboard()
                return None
            
            # Try to find the downloaded file
            prefix_map = {
                "Sales": "recentSaleExport",
                "For Sale": "forSaleExport",
                "For Rent": "forRentExport"
            }
            
            prefix = prefix_map.get(search_type)
            if not prefix:
                logger.error(f"Unknown search type for file prefix: {search_type}")
                self.return_to_dashboard()
                return None
            
            # Find the downloaded file
            downloaded_files = [f for f in os.listdir(self.download_dir) if f.startswith(prefix)]
            
            if downloaded_files:
                file_path = os.path.join(self.download_dir, downloaded_files[0])
                logger.info(f"Search completed successfully, file saved at: {file_path}")
                
                # Return to dashboard for next search
                self.return_to_dashboard()
                return file_path
            else:
                logger.error(f"No downloaded file found for {search_type}")
                self.return_to_dashboard()
                return None
                
        except Exception as e:
            logger.error(f"Unexpected error in run_search: {e}")
            # Try to return to dashboard even after an exception
            try:
                self.return_to_dashboard()
            except:
                pass
            return None
    
    def is_logged_in(self):
        """Check if already logged in by looking for dashboard elements."""
        try:
            # Look for elements that indicate we're already on the dashboard
            dashboard_indicators = [
                "//div[contains(text(), 'Start your search here')]",
                "//a[contains(@class, 'cl-logo')]"
            ]
            
            for indicator in dashboard_indicators:
                try:
                    element = self.driver.find_element(By.XPATH, indicator)
                    if element.is_displayed():
                        logger.info("Already logged in to RP Data")
                        return True
                except:
                    continue
            
            return False
        except Exception as e:
            logger.warning(f"Error checking login status: {e}")
            return False
    
    def login(self, username, password):
        """Log in to the RP Data website."""
        logger.info("===== LOGGING IN TO RP DATA =====")
        
        try:
            # Navigate to login page
            self.driver.get(self.login_url)
            self.random_delay(0.3, 0.5)  # Faster wait for page load
            
            logger.info("Login page loaded")
            
            # Find and fill username field
            username_field = self.wait_and_find_element(By.ID, "username")
            
            if username_field:
                self.human_like_typing(username_field, username, "normal")
                logger.info("Username entered successfully")
            else:
                logger.error("Username field not found")
                return False
            
            self.random_delay(0.1, 0.2)  # Brief delay between fields
            
            # Find and fill password field
            password_field = self.wait_and_find_element(By.ID, "password")
            
            if password_field:
                self.human_like_typing(password_field, password, "normal")
                logger.info("Password entered successfully")
            else:
                logger.error("Password field not found")
                return False
            
            self.random_delay(0.1, 0.2)  # Brief delay before clicking
            
            # Find and click login button
            login_button = self.wait_and_find_clickable(By.ID, "signOnButton")
            
            if login_button:
                success = self.safe_click(login_button)
                if not success:
                    logger.error("Failed to click the login button")
                    return False
                logger.info("Login button clicked successfully")
            else:
                logger.error("Login button not found")
                return False
            
            # Wait for login to complete and redirect to dashboard
            try:
                # Wait for redirection to dashboard
                WebDriverWait(self.driver, 10).until(
                    lambda driver: "Start your search here" in driver.page_source
                )
                logger.info("Login successful - redirected to dashboard")
                
                # Brief wait after login
                self.random_delay(0.5, 1.0)  # Faster wait after login
                
                return True
            except Exception as e:
                logger.error(f"Login appears to have failed - dashboard not loaded after 10 seconds: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Login failed with exception: {e}")
            return False
    
    def select_search_type(self, search_type):
        """Select the search type (Sales, For Sale, For Rent)."""
        logger.info(f"===== SELECTING SEARCH TYPE: {search_type} =====")
        
        try:
            # Wait to make sure we're on the dashboard
            try:
                WebDriverWait(self.driver, 3).until(
                    lambda driver: "Start your search here" in driver.page_source
                )
                logger.info("Dashboard confirmed, proceeding with search type selection")
            except:
                logger.warning("Could not confirm dashboard page, but proceeding anyway")
            
            # Try multiple approaches to find and select the search type
            
            # Approach 1: Try to find radio buttons by name
            try:
                radio_buttons = self.driver.find_elements(By.XPATH, "//input[@type='radio' and @name='row-radio-buttons-group']")
                logger.info(f"Found {len(radio_buttons)} radio buttons by name")
                
                for radio in radio_buttons:
                    value = radio.get_attribute("value")
                    if (search_type == "Sales" and value == "recentSale") or \
                       (search_type == "For Sale" and value == "forSale") or \
                       (search_type == "For Rent" and value == "forRent"):
                        self.safe_click(radio)
                        logger.info(f"Selected search type by radio button: {search_type}")
                        self.random_delay(0.3, 0.5)  # Faster delay
                        return True
            except Exception as e:
                logger.warning(f"Error finding radio buttons by name: {e}")
            
            # Approach 2: Try to find by text
            try:
                # Different specific XPath for different search types to be more targeted
                if search_type == "Sales":
                    type_elements = self.driver.find_elements(By.XPATH, "//span[text()='Sales' or text()='Recent Sales' or contains(text(), 'Sales')]")
                elif search_type == "For Sale":
                    type_elements = self.driver.find_elements(By.XPATH, "//span[text()='For Sale' or contains(text(), 'For Sale')]")
                elif search_type == "For Rent":
                    type_elements = self.driver.find_elements(By.XPATH, "//span[text()='For Rent' or contains(text(), 'For Rent')]")
                else:
                    type_elements = self.driver.find_elements(By.XPATH, f"//span[contains(text(), '{search_type}')]")
                
                logger.info(f"Found {len(type_elements)} elements with text matching {search_type}")
                
                for element in type_elements:
                    if element.is_displayed():
                        # Try to click the element
                        try:
                            self.safe_click(element)
                            logger.info(f"Clicked on element with text: {element.text}")
                            self.random_delay(0.3, 0.5)  # Faster delay
                            return True
                        except Exception as e:
                            logger.warning(f"Failed to click element with text '{element.text}': {e}")
                            
                            # Try to find parent element that might be clickable
                            try:
                                parent = element.find_element(By.XPATH, "./..")
                                self.safe_click(parent)
                                logger.info(f"Clicked on parent of element with text: {element.text}")
                                self.random_delay(0.3, 0.5)  # Faster delay
                                return True
                            except Exception as e2:
                                logger.warning(f"Failed to click parent of element with text '{element.text}': {e2}")
            except Exception as e:
                logger.warning(f"Error finding search type by text: {e}")
            
            # Approach 3: Try to find by label and its associated input
            try:
                labels = self.driver.find_elements(By.XPATH, f"//label[contains(., '{search_type}')]")
                logger.info(f"Found {len(labels)} labels containing text '{search_type}'")
                
                for label in labels:
                    if label.is_displayed():
                        self.safe_click(label)
                        logger.info(f"Selected search type by label: {search_type}")
                        self.random_delay(0.3, 0.5)  # Faster delay
                        return True
            except Exception as e:
                logger.warning(f"Error finding search type by label: {e}")
            
            # Approach 4: More general approach looking for ANY visible element
            try:
                xpath_patterns = [
                    f"//span[contains(text(), '{search_type}')]/..",
                    f"//div[contains(text(), '{search_type}')]",
                    f"//button[contains(text(), '{search_type}')]",
                    f"//*[contains(@role, 'button')][contains(text(), '{search_type}')]",
                    f"//*[contains(@class, 'button')][contains(text(), '{search_type}')]"
                ]
                
                for pattern in xpath_patterns:
                    elements = self.driver.find_elements(By.XPATH, pattern)
                    logger.info(f"Found {len(elements)} elements with pattern {pattern}")
                    
                    for element in elements:
                        if element.is_displayed():
                            try:
                                self.safe_click(element)
                                logger.info(f"Selected search type using pattern {pattern}")
                                self.random_delay(0.3, 0.5)  # Faster delay
                                return True
                            except Exception as e:
                                logger.warning(f"Failed to click element using pattern {pattern}: {e}")
            except Exception as e:
                logger.warning(f"Error with general approach for finding search type: {e}")
            
            # If we get here, we couldn't find the search type
            logger.error(f"Could not find search type: {search_type}")
            return False
            
        except Exception as e:
            logger.error(f"Error selecting search type: {e}")
            return False

    def search_locations(self, locations):
        """Search for the specified locations with improved handling."""
        logger.info(f"===== SEARCHING FOR LOCATIONS: {locations} =====")
        
        try:
            # For the first location, we use the initial search field
            if not locations:
                logger.error("No locations provided")
                return False
                
            # Handle first location
            first_location = locations[0]
            logger.info(f"Adding first location: {first_location}")
            
            # Try multiple search field selectors
            search_field_selectors = [
                "//input[contains(@placeholder, 'Search for an address')]",
                "//input[contains(@id, 'crux-multi-locality-search')]",
                "//div[contains(@class, 'search-bar-container')]//input",
                "//div[@id='crux-search-bar']//input",
                "//input[contains(@placeholder, 'Search')]",
                "//input[contains(@type, 'text') and contains(@class, 'MuiInputBase-input')]"
            ]
            
            search_field = None
            for selector in search_field_selectors:
                try:
                    search_field = self.wait_and_find_clickable(By.XPATH, selector, timeout=3)
                    if search_field:
                        logger.info(f"Found search field with selector: {selector}")
                        break
                except:
                    continue
            
            if not search_field:
                logger.error("Search field for first location not found")
                return False
            
            # Enter first location - using normal typing speed instead of slow
            self.human_like_typing(search_field, first_location, "normal")
            logger.info(f"Entered first location: {first_location}")
            
            # Wait for dropdown options to appear
            self.random_delay(0.5, 0.8)  # Faster wait for dropdown
            
            # Try different selectors for the dropdown option
            dropdown_selectors = [
                "//li[contains(@role, 'option') and @data-option-index='0']",
                "//li[contains(@id, 'crux-multi-locality-search-option-0')]", 
                "//li[contains(@class, 'MuiAutocomplete-option') and @data-option-index='0']",
                "//li[contains(@class, 'MuiAutocomplete-option')]",
                "//li[contains(@role, 'option')]"
            ]
            
            first_option = None
            for selector in dropdown_selectors:
                try:
                    first_option = self.wait_and_find_clickable(By.XPATH, selector, timeout=3)
                    if first_option:
                        logger.info(f"Found dropdown option with selector: {selector}")
                        break
                except:
                    continue
            
            if not first_option:
                logger.error("No dropdown options found for first location")
                return False
            
            self.safe_click(first_option)
            logger.info("Selected first location dropdown option")
            self.random_delay(0.3, 0.5)  # Faster delay
            
            # For additional locations, the UI is different
            if len(locations) > 1:
                logger.info("Processing additional locations")
                
                for location in locations[1:]:
                    logger.info(f"Adding additional location: {location}")
                    
                    # Try to find the additional search field
                    search_again_selectors = [
                        "//input[contains(@placeholder, 'Search for a suburb')]",
                        "//div[contains(@class, 'MuiAutocomplete-root')]//input",
                        "//div[@data-testid='searchbar']//input",
                        "//input[contains(@aria-label, 'Search')]",
                        "//input[contains(@type, 'text') and contains(@class, 'MuiInputBase-input')]",
                        "//input[contains(@placeholder, 'Search')]"
                    ]
                    
                    additional_search = None
                    for selector in search_again_selectors:
                        try:
                            additional_search = self.wait_and_find_clickable(By.XPATH, selector, timeout=3)
                            if additional_search:
                                logger.info(f"Found additional search field with selector: {selector}")
                                break
                        except:
                            continue
                    
                    if not additional_search:
                        logger.error(f"Could not find search field for additional location: {location}")
                        # We've added at least one location, so continue with search
                        break
                    
                    # Enter additional location - using normal typing speed
                    self.human_like_typing(additional_search, location, "normal")
                    logger.info(f"Entered additional location: {location}")
                    
                    # Wait for dropdown to appear
                    self.random_delay(0.5, 0.8)  # Faster wait for dropdown
                    
                    # Try to find and click the first option for this location
                    additional_option = None
                    for selector in dropdown_selectors:
                        try:
                            additional_option = self.wait_and_find_clickable(By.XPATH, selector, timeout=3)
                            if additional_option:
                                logger.info(f"Found dropdown option for additional location with selector: {selector}")
                                break
                        except:
                            continue
                    
                    if not additional_option:
                        logger.warning(f"Could not find dropdown option for: {location}")
                        # Try to continue anyway
                        continue
                    
                    self.safe_click(additional_option)
                    logger.info(f"Selected option for additional location: {location}")
                    self.random_delay(0.3, 0.5)  # Faster delay
            
            # Find and click the search button
            search_button_selectors = [
                "//button[contains(@class, 'search-btn')]",
                "//button[contains(@class, 'button-primary')]//img[contains(@alt, 'Search Button')]/..",
                "//button[contains(@type, 'button') and contains(@class, 'search-btn')]",
                "//button[contains(@class, 'MuiButton-contained')]",
                "//button[contains(@class, 'MuiButtonBase-root')]"
            ]
            
            search_button = None
            for selector in search_button_selectors:
                try:
                    search_button = self.wait_and_find_clickable(By.XPATH, selector, timeout=3)
                    if search_button:
                        logger.info(f"Found search button with selector: {selector}")
                        break
                except:
                    continue
            
            if not search_button:
                # Try to find by parent container and then button
                try:
                    container = self.wait_and_find_element(
                        By.XPATH, 
                        "//div[contains(@class, 'search-bar-container')]", 
                        timeout=2
                    )
                    if container:
                        buttons = container.find_elements(By.TAG_NAME, "button")
                        for button in buttons:
                            try:
                                img = button.find_element(By.TAG_NAME, "img")
                                if img and "Search" in img.get_attribute("alt"):
                                    search_button = button
                                    logger.info("Found search button through container and image")
                                    break
                            except:
                                continue
                except:
                    pass
            
            if not search_button:
                logger.error("Search button not found")
                return False
            
            # Click the search button
            self.safe_click(search_button)
            logger.info("Clicked search button")
            
            # Wait for results page to load
            self.random_delay(1.0, 1.5)  # Faster wait for results
            
            # Check if search results loaded
            try:
                WebDriverWait(self.driver, 5).until(
                    lambda driver: "Results for" in driver.page_source or 
                                  "Displaying" in driver.page_source
                )
                logger.info("Search results loaded successfully")
                return True
            except:
                logger.warning("Could not verify search results page - continuing anyway")
                return True  # Still return True to proceed with filtering
            
        except Exception as e:
            logger.error(f"Error searching locations: {e}")
            return False
    
    def apply_filters(self, property_types, min_floor_area, max_floor_area):
        """
        Apply filters for property types and floor area.
        Returns:
            - FILTER_NO_RESULTS if no matching properties found
            - FILTER_SUCCESS if filters applied successfully
            - FILTER_ERROR if there was an error applying filters
        """
        logger.info(f"===== APPLYING FILTERS =====")
        logger.info(f"Property Types: {property_types}")
        logger.info(f"Floor Area: {min_floor_area} - {max_floor_area}")
        
        try:
            # Click the filter button
            filter_button_selectors = [
                "//button[contains(@data-testid, 'filter-modal')]",
                "//button[contains(text(), 'Filters')]",
                "//button[contains(@class, 'crux-search-filters__container__row__actions__button--filters')]",
                "//button[contains(@class, 'MuiButton-contained')][contains(text(), 'Filter')]"
            ]
            
            filter_button = None
            for selector in filter_button_selectors:
                try:
                    filter_button = self.wait_and_find_clickable(By.XPATH, selector, timeout=3)
                    if filter_button:
                        logger.info(f"Found filter button with selector: {selector}")
                        break
                except:
                    continue
            
            if not filter_button:
                logger.error("Filter button not found")
                return FILTER_ERROR
            
            self.safe_click(filter_button)
            logger.info("Clicked filter button")
            self.random_delay(0.7, 1.0)  # Faster delay
            
            # Set floor area if provided
            if min_floor_area != "Min" or max_floor_area != "Max":
                logger.info("Setting floor area filters")
                
                # Try to find the Floor Area section using the new selectors from the image
                floor_area_selectors = [
                    "//h6[contains(text(), 'Floor Area')]",
                    "//div[contains(text(), 'Floor Area')]",
                    "//label[contains(text(), 'Floor Area')]"
                ]
                
                floor_area_section = None
                for selector in floor_area_selectors:
                    try:
                        floor_area_section = self.wait_and_find_element(By.XPATH, selector, timeout=2)
                        if floor_area_section:
                            logger.info(f"Found Floor Area section with selector: {selector}")
                            
                            # Scroll to the floor area section
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", floor_area_section)
                            self.random_delay(0.3, 0.5)  # Faster delay
                            break
                    except:
                        continue
                
                if floor_area_section:
                    # FIXED APPROACH: Get the input fields directly after finding the section
                    try:
                        # Get the parent container of the floor area section
                        parent_element = self.driver.execute_script("""
                            var el = arguments[0];
                            while (el && !el.querySelector('input[role="combobox"]')) {
                                el = el.parentElement;
                            }
                            return el;
                        """, floor_area_section)
                        
                        if parent_element:
                            # Now find the input fields within this container
                            input_fields = parent_element.find_elements(By.XPATH, ".//input[@role='combobox']")
                            
                            if len(input_fields) >= 2:
                                # The first field is Min, the second is Max
                                if min_floor_area != "Min":
                                    min_input = input_fields[0]
                                    # First click to activate
                                    min_input.click()
                                    self.random_delay(0.1, 0.2)  # Faster delay
                                    # Clear it
                                    min_input.clear()
                                    self.random_delay(0.1, 0.2)  # Faster delay
                                    # Type the value
                                    min_input.send_keys(min_floor_area)
                                    self.random_delay(0.1, 0.2)  # Faster delay
                                    # Press Enter to confirm
                                    min_input.send_keys(Keys.ENTER)
                                    logger.info(f"Set minimum floor area: {min_floor_area}")
                                    self.random_delay(0.2, 0.3)  # Faster delay
                                
                                if max_floor_area != "Max":
                                    max_input = input_fields[1]
                                    # First click to activate
                                    max_input.click()
                                    self.random_delay(0.1, 0.2)  # Faster delay
                                    # Clear it
                                    max_input.clear()
                                    self.random_delay(0.1, 0.2)  # Faster delay
                                    # Type the value
                                    max_input.send_keys(max_floor_area)
                                    self.random_delay(0.1, 0.2)  # Faster delay
                                    # Press Enter to confirm
                                    max_input.send_keys(Keys.ENTER)
                                    logger.info(f"Set maximum floor area: {max_floor_area}")
                                    self.random_delay(0.2, 0.3)  # Faster delay
                            else:
                                logger.warning(f"Expected 2 input fields, found {len(input_fields)}")
                    except Exception as e:
                        logger.error(f"Error setting floor area: {e}")
                else:
                    logger.warning("Floor Area section not found")
            
            # FIXED: Handle property type selection - now correctly targeting only main property types
            # First, find the property type section with the exact class from the provided HTML
            property_section_selectors = [
                "//h6[contains(@class, 'MuiTypography-subtitle2')]/span[text()='Property Type']/..",
                "//div[contains(@class, 'list-box--property-type')]//h6",
                "//div[contains(@class, 'list-box--property-type')]",
                "//h6[contains(text(), 'Property Type')]/.."
            ]
            
            property_section = None
            for selector in property_section_selectors:
                try:
                    property_section = self.wait_and_find_element(By.XPATH, selector, timeout=2)
                    if property_section:
                        logger.info(f"Found Property Type section with selector: {selector}")
                        # Scroll to property type section
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", property_section)
                        self.random_delay(0.3, 0.5)  # Faster delay
                        break
                except:
                    continue
            
            if property_section:
                # Get the direct parent container that holds all property type checkboxes
                try:
                    # Find the container that has all the property types
                    property_container = self.driver.find_element(
                        By.XPATH, 
                        "//div[contains(@class, 'list-box--property-type')]"
                    )
                    
                    # Find all property type checkboxes within this container (but not subtype checkboxes)
                    property_labels = property_container.find_elements(
                        By.XPATH,
                        ".//span[contains(@class, 'MuiFormControlLabel-label')]"
                    )
                    
                    logger.info(f"Found {len(property_labels)} property type labels")
                    
                    # Map of property labels to checkboxes
                    property_checkboxes = []
                    
                    # Get all the property types and their checkboxes
                    for label in property_labels:
                        try:
                            prop_text = label.text.strip()
                            if prop_text and len(prop_text) > 0:
                                # Find the associated checkbox input
                                parent_label = label.find_element(By.XPATH, "./..")
                                checkbox = parent_label.find_element(By.XPATH, ".//input[@type='checkbox']")
                                
                                property_checkboxes.append((prop_text, checkbox))
                        except Exception as e:
                            logger.warning(f"Error getting checkbox for property label: {e}")
                    
                    logger.info(f"Found {len(property_checkboxes)} property checkboxes")
                    
                    # Go through each checkbox and check/uncheck based on our property_types list
                    for prop_text, checkbox in property_checkboxes:
                        try:
                            is_selected = checkbox.is_selected()
                            should_be_selected = prop_text in property_types
                            
                            if is_selected and not should_be_selected:
                                # Need to uncheck this property type
                                logger.info(f"Unchecking property type: {prop_text}")
                                self.safe_click(checkbox)
                                self.random_delay(0.2, 0.3)  # Faster delay
                            elif not is_selected and should_be_selected:
                                # Need to check this property type
                                logger.info(f"Checking property type: {prop_text}")
                                self.safe_click(checkbox)
                                self.random_delay(0.2, 0.3)  # Faster delay
                            else:
                                logger.info(f"Property type {prop_text} already {'selected' if is_selected else 'unselected'} as needed")
                        except Exception as e:
                            logger.warning(f"Error handling property checkbox for {prop_text}: {e}")
                except Exception as e:
                    logger.error(f"Error handling property types: {e}")
            else:
                logger.warning("Property Type section not found")
            
            # Finally, apply the filters by clicking the button with a shorter delay
            logger.info("Waiting 1 second before applying filters...")
            time.sleep(1)  # Faster delay before applying filters
            
            apply_button_selectors = [
                "//button[@data-testid='apply-filters']",
                "//button[contains(text(), 'Show')]",
                "//button[contains(@class, 'MuiButton-containedPrimary')]",
                "//button[contains(@class, 'MuiButton-disableElevation')]",
                "//button[contains(text(), 'Apply')]",
                "//button[contains(text(), 'Filter')]"
            ]
            
            apply_button = None
            for selector in apply_button_selectors:
                try:
                    apply_button = self.wait_and_find_clickable(By.XPATH, selector, timeout=3)
                    if apply_button:
                        logger.info(f"Found apply button with selector: {selector}")
                        break
                except:
                    continue
            
            if apply_button:
                # Check if the button contains "No matching properties found" text
                no_results_found = False
                
                # First, check if there's a div with the "No matching properties found" text
                try:
                    no_results_div = apply_button.find_element(By.XPATH, ".//div[contains(text(), 'No matching properties found')]")
                    if no_results_div and no_results_div.is_displayed():
                        logger.info("Filter button indicates no matching properties found")
                        no_results_found = True
                except:
                    # Also check the button text directly
                    try:
                        button_text = apply_button.text
                        if "No matching properties found" in button_text:
                            logger.info(f"Filter button text indicates no results: {button_text}")
                            no_results_found = True
                    except:
                        pass
                
                # Always click the button to apply filters or return to search page
                self.safe_click(apply_button)
                logger.info("Clicked apply button")
                self.random_delay(1.0, 1.5)  # Wait after clicking
                
                # If we found no results, we need to explicitly navigate back to the dashboard
                if no_results_found:
                    logger.info("No matching properties found, explicitly navigating back to dashboard")
                    # Click the CoreLogic logo to return to the dashboard
                    self.click_logo_to_return_to_dashboard()
                    return FILTER_NO_RESULTS
                
                logger.info("Filters applied successfully, returning FILTER_SUCCESS")
                return FILTER_SUCCESS
            else:
                logger.error("Apply filters button not found")
                self.click_logo_to_return_to_dashboard()  # Try to return to dashboard even if apply button not found
                return FILTER_ERROR
        
        except Exception as e:
            logger.error(f"Error applying filters: {e}")
            # Try to return to dashboard even after an exception
            self.click_logo_to_return_to_dashboard()
            return FILTER_ERROR
    
    def click_logo_to_return_to_dashboard(self):
        """
        Explicitly click the CoreLogic logo to return to the dashboard.
        This is a specialized function for navigating home after finding no results.
        """
        logger.info("Attempting to click CoreLogic logo to return to dashboard")
        
        try:
            # First, try the exact logo selector from the HTML
            logo_selectors = [
                "//div[@class='logo']/a[@class='cl-logo']",
                "//a[@class='cl-logo']",
                "//img[@class='cl-logo-img' and @alt='CoreLogic']/..",
                "//img[@alt='CoreLogic']/.."
            ]
            
            logo = None
            for selector in logo_selectors:
                try:
                    logo = self.wait_and_find_clickable(By.XPATH, selector, timeout=2)
                    if logo:
                        logger.info(f"Found CoreLogic logo with selector: {selector}")
                        break
                except:
                    continue
            
            if logo:
                self.safe_click(logo)
                logger.info("Clicked CoreLogic logo to return to dashboard")
                
                # Wait for dashboard to load
                try:
                    WebDriverWait(self.driver, 5).until(
                        lambda driver: "Start your search here" in driver.page_source
                    )
                    logger.info("Successfully returned to dashboard after clicking logo")
                    return True
                except:
                    logger.warning("Could not verify dashboard page after clicking logo")
            else:
                logger.warning("Could not find CoreLogic logo to click")
            
            # If clicking the logo failed, fall back to the general return_to_dashboard method
            return self.return_to_dashboard()
            
        except Exception as e:
            logger.error(f"Error clicking CoreLogic logo: {e}")
            # Try the general return_to_dashboard as a fallback
            return self.return_to_dashboard()
    
    def select_all_results(self):
        """Select all displayed results. Returns False ONLY if no results were found."""
        logger.info("===== SELECTING ALL RESULTS =====")
        
        try:
            # First, check if there are genuinely NO results
            try:
                # Look ONLY for definitive indicators of no results
                no_results = False
                
                # Check for explicit "No matching properties found" message
                try:
                    no_matches = self.driver.find_element(
                        By.XPATH, 
                        "//div[contains(text(), 'No matching properties found')]"
                    )
                    if no_matches and no_matches.is_displayed():
                        logger.info("No matching properties found - returning to home page")
                        return False
                except:
                    pass
                    
                # Check for explicit zero results indicators
                no_results_indicators = [
                    "//div[text()='No results found']",
                    "//div[text()='No properties found']",
                    "//div[contains(text(), '0 properties') and not(contains(text(), 'of'))]",
                    "//div[contains(text(), '0 result') and not(contains(text(), 'of'))]"
                ]
                
                for indicator in no_results_indicators:
                    try:
                        element = self.driver.find_element(By.XPATH, indicator)
                        if element and element.is_displayed():
                            logger.info(f"No search results found: {element.text}")
                            no_results = True
                            break
                    except:
                        continue
                
                # Check if results count explicitly shows zero (but avoid false positives)
                if not no_results:
                    try:
                        results_element = self.driver.find_element(
                            By.XPATH, 
                            "//div[contains(@class, 'result-count-main')]"
                        )
                        results_text = results_element.text
                        
                        # Only consider it "no results" if it explicitly has "0 " at the start 
                        # (to avoid matching "10 of 10" or similar)
                        if results_text.strip().startswith("0 ") or "Displaying 0" in results_text:
                            logger.info(f"Zero results indicated in count: {results_text}")
                            no_results = True
                        else:
                            # Log what was found - this helps with debugging
                            logger.info(f"Results found: {results_text}")
                    except:
                        pass
                
                # If we've determined there are no results, return False
                if no_results:
                    return False
                
            except Exception as e:
                logger.warning(f"Error during no-results check: {e}")
                # Continue anyway - we'll try to select results
            
            # We've reached here, so we assume there ARE results - try to select them
            
            # MULTI-STRATEGY APPROACH: Try several methods to find and click the checkbox
            checkbox_clicked = False
            
            # Strategy 1: Find the checkbox input directly by its class
            if not checkbox_clicked:
                try:
                    checkbox_input = self.driver.find_element(
                        By.XPATH,
                        "//input[@class='PrivateSwitchBase-input css-1m9pwf3']"
                    )
                    logger.info("Found checkbox input directly by class")
                    checkbox_input.click()
                    logger.info("Clicked checkbox input directly")
                    checkbox_clicked = True
                    time.sleep(1.5)  # Wait for dropdown to appear
                except Exception as e:
                    logger.warning(f"Direct checkbox input click failed: {e}")
            
            # Strategy 2: Find through the parent span with data-testid
            if not checkbox_clicked:
                try:
                    checkbox_span = self.driver.find_element(
                        By.XPATH,
                        "//span[@data-testid='multi-select-check-icon']"
                    )
                    logger.info("Found checkbox span by data-testid")
                    checkbox_input = checkbox_span.find_element(By.XPATH, ".//input[@type='checkbox']")
                    logger.info("Found checkbox input within span")
                    checkbox_input.click()
                    logger.info("Clicked checkbox input within span")
                    checkbox_clicked = True
                    time.sleep(1.5)
                except Exception as e:
                    logger.warning(f"Checkbox within span click failed: {e}")
            
            # Strategy 3: Find through the container div
            if not checkbox_clicked:
                try:
                    container = self.driver.find_element(
                        By.XPATH,
                        "//div[@data-testid='rapid-multi-select-counter']"
                    )
                    logger.info("Found multi-select counter container")
                    checkbox_input = container.find_element(By.XPATH, ".//input[@type='checkbox']")
                    logger.info("Found checkbox input within container")
                    checkbox_input.click()
                    logger.info("Clicked checkbox input within container")
                    checkbox_clicked = True
                    time.sleep(1.5)
                except Exception as e:
                    logger.warning(f"Checkbox within container click failed: {e}")
            
            # Strategy 4: JavaScript approach on span
            if not checkbox_clicked:
                try:
                    checkbox_span = self.driver.find_element(
                        By.XPATH,
                        "//span[@data-testid='multi-select-check-icon']"
                    )
                    logger.info("Found checkbox span for JavaScript approach")
                    self.driver.execute_script("arguments[0].click();", checkbox_span)
                    logger.info("Clicked checkbox span with JavaScript")
                    checkbox_clicked = True
                    time.sleep(1.5)
                except Exception as e:
                    logger.error(f"All checkbox click strategies failed: {e}")
                    return False  # Only return False here if we couldn't click ANY checkbox
            
            # Only proceed to dropdown selection if we successfully clicked a checkbox
            if checkbox_clicked:
                try:
                    # Try to find all options in the dropdown
                    option_labels = self.driver.find_elements(
                        By.XPATH,
                        "//span[@data-testid='single-select-checkbox-label']"
                    )
                    
                    if len(option_labels) >= 3:
                        # Get the middle label (index 1) - usually "Select All"
                        middle_label = option_labels[1]
                        middle_text = middle_label.text
                        logger.info(f"Found middle option label: {middle_text}")
                        
                        # Click the middle option label
                        middle_label.click()
                        logger.info(f"Clicked middle option: {middle_text}")
                        time.sleep(0.5)
                        return True
                    else:
                        # Try to directly find the inputs
                        radio_inputs = self.driver.find_elements(
                            By.XPATH,
                            "//input[@data-testid='single-select-checkbox']"
                        )
                        
                        if len(radio_inputs) >= 3:
                            # Click the middle radio option (index 1)
                            middle_radio = radio_inputs[1]
                            middle_radio.click()
                            logger.info("Clicked middle radio input")
                            time.sleep(0.5)
                            return True
                        else:
                            # Last resort: try to find by id
                            all_option = self.driver.find_element(
                                By.XPATH,
                                "//input[@id='all-option']"
                            )
                            
                            all_option.click()
                            logger.info("Clicked 'all-option' by ID")
                            time.sleep(0.5)
                            return True
                except Exception as e:
                    logger.error(f"Failed to click dropdown option: {e}")
                    return False
            
            logger.error("Failed to select all results - reached end of function")
            return False
            
        except Exception as e:
            logger.error(f"Error selecting all results: {e}")
            return False
    
    def export_to_csv(self, search_type):
        """Export selected results to CSV/Excel."""
        logger.info("===== EXPORTING RESULTS TO CSV =====")
        
        try:
            # Check if the export button exists - if not, likely no results to export
            # This is a fallback check in case select_all_results() didn't catch it
            try:
                export_exists = self.driver.find_element(
                    By.XPATH,
                    "//button[@data-testid='export-to-csv-button']"
                )
                if not export_exists.is_displayed() or not export_exists.is_enabled():
                    logger.info("Export button not visible or enabled - likely no results to export")
                    return False
            except:
                logger.info("Export button not found - likely no results to export")
                return False
                
            # Wait a shorter time before looking for the export button
            logger.info("Waiting 0.5 seconds before clicking export button...")
            time.sleep(0.5)
            
            # Try to find the export button directly by data-testid
            try:
                export_button = self.driver.find_element(
                    By.XPATH,
                    "//button[@data-testid='export-to-csv-button']"
                )
                logger.info("Found export button by data-testid")
                
                # Click using regular click method
                export_button.click()
                logger.info("Clicked export button")
            except Exception as e:
                logger.warning(f"Could not find export button by data-testid: {e}")
                
                # Try alternative approaches
                try:
                    # Find by class
                    export_button = self.driver.find_element(
                        By.XPATH,
                        "//button[contains(@class, 'button-export-to-csv')]"
                    )
                    logger.info("Found export button by class")
                    
                    # Click using regular click
                    export_button.click()
                    logger.info("Clicked export button")
                except Exception as e:
                    logger.warning(f"Could not find export button by class: {e}")
                    
                    # Try text-based approach
                    try:
                        export_button = self.driver.find_element(
                            By.XPATH,
                            "//button[contains(., 'Export to CSV')]"
                        )
                        logger.info("Found export button by text content")
                        
                        # Click using regular click
                        export_button.click()
                        logger.info("Clicked export button")
                    except Exception as e:
                        logger.error(f"Could not find export button: {e}")
                        return False
            
            # Wait for dialog to appear - shorter wait time
            self.random_delay(1.0, 1.5)
            
            # Skip looking for "Analysis Export" as it wasn't found in the logs
            
            # Check all checkboxes in the export dialog
            try:
                checkboxes = self.driver.find_elements(By.XPATH, "//input[@type='checkbox']")
                logger.info(f"Found {len(checkboxes)} checkboxes in export dialog")
                
                for checkbox in checkboxes:
                    if not checkbox.is_selected() and checkbox.is_displayed():
                        try:
                            self.safe_click(checkbox)
                            self.random_delay(0.1, 0.2)  # Faster delay
                        except:
                            pass
            except:
                pass
            
            # Check the acknowledgement box - USING ONLY THE METHOD THAT WORKED IN LOGS
            logger.info("Attempting to find and click the acknowledgement checkbox...")
            
            # Using the method that worked according to the logs
            try:
                # Find by data-testid only (this was the only method that worked according to logs)
                ack_checkbox = self.driver.find_element(
                    By.XPATH,
                    "//input[@data-testid='export-disclaimer-checkbox']"
                )
                logger.info("Found acknowledgement checkbox by data-testid")
                
                # Click using JavaScript for reliability (this method worked)
                self.driver.execute_script("arguments[0].click();", ack_checkbox)
                logger.info("Clicked acknowledgement checkbox using JavaScript")
            except Exception as e:
                logger.error(f"Could not find and click acknowledgement checkbox: {e}")
                return False
            
            # Wait a shorter time before finding the final export button
            time.sleep(0.5)
            
            # Click the final export button - using exact element from the HTML
            try:
                # Try by exact data-testid first (this worked according to logs)
                final_export = self.driver.find_element(
                    By.XPATH,
                    "//button[@data-testid='submit-button']"
                )
                logger.info("Found final export button by exact data-testid")
                
                # Click the button
                final_export.click()
                logger.info("Clicked final export button")
            except Exception as e:
                logger.warning(f"Could not find export button by exact data-testid: {e}")
                
                # Try alternative approaches
                try:
                    # Try by exact class (from the HTML you provided)
                    final_export = self.driver.find_element(
                        By.XPATH,
                        "//button[contains(@class, 'MuiButton-containedPrimary')]"
                    )
                    logger.info("Found final export button by class")
                    
                    # Click the button
                    final_export.click()
                    logger.info("Clicked final export button")
                except Exception as e:
                    logger.warning(f"Could not find export button by class: {e}")
                    
                    # Try by text content only
                    try:
                        final_export = self.driver.find_element(
                            By.XPATH,
                            "//button[text()='Export']"
                        )
                        logger.info("Found final export button by exact text")
                        
                        # Click the button
                        final_export.click()
                        logger.info("Clicked final export button")
                    except Exception as e:
                        logger.error(f"All attempts to click final export button failed: {e}")
                        return False
            
            # Wait for download to complete - slightly shorter wait time
            self.random_delay(6.0, 8.0)  
            
            # Verify download
            prefix_map = {
                "Sales": "recentSaleExport",
                "For Sale": "forSaleExport",
                "For Rent": "forRentExport"
            }
            
            prefix = prefix_map.get(search_type)
            if not prefix:
                logger.error(f"Unknown search type for file prefix: {search_type}")
                return False
            
            # Check for downloaded file
            downloaded_files = [f for f in os.listdir(self.download_dir) if f.startswith(prefix)]
            
            if downloaded_files:
                logger.info(f"Successfully downloaded file: {downloaded_files[0]}")
                return True
            else:
                logger.error(f"No downloaded file found with prefix {prefix}")
                return False
        
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
            return False
    
    def return_to_dashboard(self):
        """Return to the dashboard to start a new search."""
        logger.info("===== RETURNING TO DASHBOARD =====")
        
        try:
            # First, check if we're already on the dashboard
            try:
                dashboard_text = self.driver.find_element(By.XPATH, "//div[contains(text(), 'Start your search here')]")
                if dashboard_text.is_displayed():
                    logger.info("Already on dashboard, no need to navigate")
                    return True
            except:
                # Not on dashboard, need to navigate there
                pass
                
            # Try to click the logo to return to dashboard
            logo_selectors = [
                "//a[contains(@class, 'cl-logo')]",
                "//img[contains(@alt, 'CoreLogic')]/..",
                "//img[contains(@alt, 'CoreLogic')]",
                "//a[contains(@href, '/dashboard')]",
                "//a[contains(@class, 'home')]",
                "//div[@class='logo']/a[@class='cl-logo']"
            ]
            
            logo = None
            for selector in logo_selectors:
                try:
                    logo = self.wait_and_find_clickable(By.XPATH, selector, timeout=2)
                    if logo:
                        logger.info(f"Found logo with selector: {selector}")
                        break
                except:
                    continue
            
            if logo:
                self.safe_click(logo)
                logger.info("Clicked logo to return to dashboard")
                
                # Wait for dashboard to load - shorter wait time
                self.random_delay(1.0, 2.0)
                
                # Verify we're back at the dashboard
                try:
                    WebDriverWait(self.driver, 5).until(
                        lambda driver: "Start your search here" in driver.page_source
                    )
                    logger.info("Successfully returned to dashboard")
                    return True
                except:
                    logger.warning("Could not verify dashboard page")
            
            # If that didn't work, try direct navigation
            logger.info("Trying direct navigation to dashboard")
            self.driver.get(self.login_url)
            self.random_delay(2.0, 3.0)  # Slightly shorter wait time
            
            # Check if we're on the dashboard
            try:
                WebDriverWait(self.driver, 5).until(
                    lambda driver: "Start your search here" in driver.page_source
                )
                logger.info("Successfully navigated to dashboard")
                return True
            except:
                logger.warning("Could not verify dashboard page after direct navigation")
                # Let's try one more approach - go to base URL
                try:
                    # Get the base URL 
                    base_url = self.login_url.split('://')[0] + '://' + self.login_url.split('://')[1].split('/')[0]
                    self.driver.get(base_url)
                    logger.info(f"Trying navigation to base URL: {base_url}")
                    self.random_delay(2.0, 3.0)
                    
                    WebDriverWait(self.driver, 5).until(
                        lambda driver: "Start your search here" in driver.page_source
                    )
                    logger.info("Successfully navigated to dashboard using base URL")
                    return True
                except:
                    logger.warning("All dashboard navigation attempts failed")
            
            # At this point, just assume we can continue
            logger.warning("Could not confirm return to dashboard, but continuing anyway")
            return True
        
        except Exception as e:
            logger.error(f"Error returning to dashboard: {e}")
            # Still return True because we want to continue even if return_to_dashboard fails
            return True