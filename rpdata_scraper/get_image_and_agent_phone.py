#!/usr/bin/env python3
# Extracts property images and agent phone numbers from RP Data property pages

import logging
import time
import random
import re
import requests
import sys
import os
import platform
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
import numpy as np


# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def random_delay(min_sec=0.5, max_sec=2.0):
    """Add a random delay to simulate human behavior."""
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)

def is_map_or_pin_image(url):
    """Check if the image URL is a map or pin marker image."""
    if not url:
        return False
    
    # List of patterns that indicate a map or pin image rather than a property photo
    map_patterns = [
        'maps.googleapis.com',
        'staticmap',
        'target-property-inactive-pin',
        'target-property-pin',
        'marker',
        'pin.png',
        'map-marker',
        'satellite'
    ]
    
    return any(pattern in url.lower() for pattern in map_patterns)

def is_valid_downloadable_url(url):
    """Check if the URL is valid and can be downloaded."""
    if not url:
        return False
        
    # Reject blob URLs - these are browser-internal references that can't be downloaded
    if url.startswith('blob:'):
        logger.warning(f"Detected blob URL which can't be downloaded: {url}")
        return False
        
    # Reject data URLs
    if url.startswith('data:'):
        return False
        
    # Check for valid HTTP/HTTPS URLs
    if not (url.startswith('http://') or url.startswith('https://')):
        return False
    
    # Check if URL contains valid image indicators
    valid_indicators = ['corelogic.asia', 'images.', '.jpg', '.jpeg', '.png', '.gif', '.webp']
    if any(indicator in url.lower() for indicator in valid_indicators):
        return True
        
    return True  # Default to true for any http/https URLs

def test_image_url(url, timeout=5):
    """
    Test if an image URL is valid and can be downloaded.
    
    Args:
        url (str): The image URL to test
        timeout (int): Timeout in seconds
        
    Returns:
        bool: True if the image can be downloaded, False otherwise
    """
    if not is_valid_downloadable_url(url):
        return False
        
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36',
            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://rpp.corelogic.com.au/'
        }
        
        response = requests.head(url, timeout=timeout, headers=headers)
        
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            return 'image' in content_type.lower()
        return False
    except Exception as e:
        logger.warning(f"Error testing image URL {url}: {e}")
        return False


def setup_driver(headless):
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
        elif platform.system() == "Linux":
            logger.info("Detected Linux environment - checking Chrome locations")
            # Common Chrome locations on Linux
            linux_chrome_paths = [
                "/usr/bin/google-chrome-stable",
                "/usr/bin/google-chrome",
                "/usr/bin/chromium-browser",
                "/usr/bin/chromium",
                "/usr/bin/chrome",
                "/opt/google/chrome/chrome"
            ]
            
            for chrome_path in linux_chrome_paths:
                if os.path.exists(chrome_path):
                    logger.info(f"Using Chrome at: {chrome_path}")
                    options.binary_location = chrome_path
                    break
        
        # Log what we're doing with binary location
        if hasattr(options, 'binary_location') and options.binary_location:
            logger.info(f"Chrome binary location set to: {options.binary_location}")
        else:
            logger.info("No specific Chrome binary set, using system default")
        
        # Initialize undetected ChromeDriver with special handling for Render
        if is_render:
            logger.info("Using custom driver initialization for Render")
            driver = uc.Chrome(
                options=options,
                version_main=None,
                use_subprocess=True,
                driver_executable_path=None  # Let it auto-detect
            )
        else:
            driver = uc.Chrome(
                options=options,
                version_main=None,
                use_subprocess=True
            )
        
        # Set the window size explicitly
        driver.set_window_size(1920, 1080)
        
        # Make detection harder by modifying navigator properties
        driver.execute_script("""
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
        return driver
        
    except Exception as e:
        logger.error(f"Failed to initialize Undetected ChromeDriver: {e}")
        sys.exit(1)



def get_image_and_agent_phone(all_rows, headless=False):
    """
    Processes all property rows to add image URLs and agent phone numbers.
    
    Args:
        all_rows (list): 2D array of property data
        
    Returns:
        list: Updated 2D array with image URLs and agent phone numbers
    """

    driver = setup_driver(headless)
    logged_in = False
    
    try:
        logger.info("Starting to process property data for images and agent details")
        

        for idx, row in enumerate(all_rows):
            # Get the property URL (index 24)
            property_url = row[24]
            
            # Check for valid URL
            if (not property_url or 
                property_url == "N/A" or 
                not isinstance(property_url, str) or 
                not property_url.startswith("http")):
                logger.warning(f"No valid URL for property {idx}, skipping")
                continue
                
            logger.info(f"Processing property {idx+1}/{len(all_rows)}: {property_url}")
            
            try:
                # Navigate to the property page
                driver.get(property_url)
                random_delay(3.0, 5.0)  # Increased wait time for page to fully load
                
                # Handle login for the first property only
                if not logged_in:
                    logger.info("Checking if login is required")
                    try:
                        # Look for login elements
                        username_field = None
                        try:
                            username_field = driver.find_element(By.ID, "username")
                        except NoSuchElementException:
                            pass
                        
                        if username_field:
                            logger.info("Login form detected, attempting to log in")
                            username_field.send_keys("busihealth")
                            random_delay(0.2, 0.5)
                            
                            password_field = driver.find_element(By.ID, "password")
                            password_field.send_keys("Busihealth123")
                            random_delay(0.2, 0.5)
                            
                            login_button = driver.find_element(By.ID, "signOnButton")
                            login_button.click()
                            random_delay(4.0, 6.0)  # Increased wait time after login
                            
                            # Navigate to the property page again
                            driver.get(property_url)
                            random_delay(3.0, 5.0)  # Increased wait time for page to load
                            
                            logger.info("Successfully logged in")
                        
                        logged_in = True
                    except Exception as e:
                        logger.error(f"Login process error: {e}")
                
                # Extract property image URL using multiple approaches
                image_url = None
                
                # Wait longer for the page to fully load and stabilize
                try:
                    # Wait for the content to be visible and loaded
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "flex-container"))
                    )
                    random_delay(1.0, 2.0)  # Additional wait after main element loaded
                except Exception as e:
                    logger.warning(f"Wait for page load timed out: {e}")
                
                # Method 1: Enhanced JavaScript approach to extract valid image URLs
                try:
                    logger.info("Trying enhanced JavaScript method to get images")
                    property_images = driver.execute_script("""
                        let images = [];
                        
                        // Function to check if URL is a valid downloadable URL (not blob/data URLs)
                        function isValidUrl(url) {
                            return url && typeof url === 'string' && 
                                  url.startsWith('http') && 
                                  !url.startsWith('blob:') &&
                                  !url.startsWith('data:');
                        }
                        
                        // Function to check if an image is likely a map or pin image
                        function isMapOrPinImage(url) {
                            if (!url) return true;
                            const mapPatterns = ['maps.googleapis', 'staticmap', 'marker', 'pin', 'target-property'];
                            return mapPatterns.some(pattern => url.toLowerCase().includes(pattern));
                        }
                        
                        // Try getting images from image-gallery-slides
                        try {
                            // First look for the slides container
                            const slidesContainer = document.querySelector('.image-gallery-slides');
                            if (slidesContainer) {
                                // Get all img elements from slides
                                const slideImages = slidesContainer.querySelectorAll('img');
                                for (const img of slideImages) {
                                    if (img && img.src && isValidUrl(img.src) && !isMapOrPinImage(img.src)) {
                                        images.push(img.src);
                                    }
                                }
                            }
                        } catch(e) {
                            console.error("Error finding slides images:", e);
                        }
                        
                        // Try the first slide specifically
                        if (images.length === 0) {
                            try {
                                const firstSlide = document.querySelector('[aria-label="Go to Slide 1"]');
                                if (firstSlide) {
                                    const img = firstSlide.querySelector('img');
                                    if (img && img.src && isValidUrl(img.src) && !isMapOrPinImage(img.src)) {
                                        images.push(img.src);
                                    }
                                }
                            } catch(e) {
                                console.error("Error finding first slide image:", e);
                            }
                        }
                        
                        // Try image-gallery-center
                        if (images.length === 0) {
                            try {
                                const centerSlide = document.querySelector('.image-gallery-center');
                                if (centerSlide) {
                                    const img = centerSlide.querySelector('img');
                                    if (img && img.src && isValidUrl(img.src) && !isMapOrPinImage(img.src)) {
                                        images.push(img.src);
                                    }
                                }
                            } catch(e) {
                                console.error("Error finding center slide image:", e);
                            }
                        }
                        
                        // Fallback: find any image in the image-gallery component
                        if (images.length === 0) {
                            try {
                                const gallery = document.querySelector('section[data-testid="app-image-gallery-component"]');
                                if (gallery) {
                                    const galleryImages = gallery.querySelectorAll('img');
                                    for (const img of galleryImages) {
                                        if (img && img.src && isValidUrl(img.src) && !isMapOrPinImage(img.src)) {
                                            images.push(img.src);
                                        }
                                    }
                                }
                            } catch(e) {
                                console.error("Error finding gallery images:", e);
                            }
                        }
                        
                        // Extract image URLs from background-image styles
                        if (images.length === 0) {
                            try {
                                // Find elements with background-image styles inside the gallery
                                const galleryElements = document.querySelectorAll('.image-gallery-slide *');
                                for (const el of galleryElements) {
                                    if (el) {
                                        const style = window.getComputedStyle(el);
                                        const bgImage = style.backgroundImage;
                                        
                                        // Extract URL from background-image: url("...")
                                        if (bgImage && bgImage !== 'none' && bgImage.includes('url(')) {
                                            const match = bgImage.match(/url\\(['"]?([^'"\\)]+)['"]?\\)/i);
                                            if (match && match[1] && isValidUrl(match[1]) && !isMapOrPinImage(match[1])) {
                                                images.push(match[1]);
                                            }
                                        }
                                    }
                                }
                            } catch(e) {
                                console.error("Error extracting background images:", e);
                            }
                        }
                        
                        // Scan the whole page for large images
                        if (images.length === 0) {
                            try {
                                const allImages = document.querySelectorAll('img');
                                for (const img of allImages) {
                                    if (img && img.src && isValidUrl(img.src) && !isMapOrPinImage(img.src)) {
                                        // Prefer larger images
                                        const width = img.width || 0;
                                        const height = img.height || 0;
                                        if (width > 200 || height > 200) {
                                            images.push(img.src);
                                        }
                                        // Also accept CoreLogic images regardless of size
                                        else if (img.src.includes('corelogic')) {
                                            images.push(img.src);
                                        }
                                    }
                                }
                            } catch(e) {
                                console.error("Error finding page images:", e);
                            }
                        }
                        
                        return images;
                    """)
                    
                    # Double-check: Filter out invalid URLs and map/pin images serverside
                    valid_image_urls = []
                    for url in property_images:
                        if is_valid_downloadable_url(url) and not is_map_or_pin_image(url):
                            valid_image_urls.append(url)
                    
                    if valid_image_urls:
                        # Test the first image URL to make sure it's downloadable
                        first_url = valid_image_urls[0]
                        if test_image_url(first_url):
                            image_url = first_url
                            logger.info(f"Found and verified property image: {image_url}")
                        else:
                            logger.warning(f"Image URL failed validation test: {first_url}")
                            # Try the next URL if available
                            if len(valid_image_urls) > 1:
                                for alt_url in valid_image_urls[1:]:
                                    if test_image_url(alt_url):
                                        image_url = alt_url
                                        logger.info(f"Found alternative verified image: {image_url}")
                                        break
                    else:
                        logger.warning("No valid property images found with JavaScript method")
                
                except Exception as e:
                    logger.warning(f"JavaScript image extraction error: {e}")
                
                # Method 2: Try direct DOM traversal if JavaScript method failed
                if not image_url:
                    try:
                        logger.info("Trying DOM traversal to find images")
                        
                        # First check if the image gallery is in the DOM
                        gallery_exists = len(driver.find_elements(By.CLASS_NAME, "image-gallery-slides")) > 0
                        
                        if gallery_exists:
                            # Wait for slides to be fully loaded and try direct CSS selector for first slide
                            WebDriverWait(driver, 5).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, ".image-gallery-slides"))
                            )
                            
                            # Try the first slide specifically
                            try:
                                first_slide = driver.find_element(By.CSS_SELECTOR, "[aria-label='Go to Slide 1']")
                                img = first_slide.find_element(By.TAG_NAME, "img")
                                img_src = img.get_attribute("src")
                                if is_valid_downloadable_url(img_src) and not is_map_or_pin_image(img_src):
                                    image_url = img_src
                                    logger.info(f"Found first slide image: {image_url}")
                            except (NoSuchElementException, StaleElementReferenceException):
                                logger.warning("Could not find first slide using aria-label")
                            
                            # Try center slide if first slide failed
                            if not image_url:
                                try:
                                    center_slide = driver.find_element(By.CLASS_NAME, "image-gallery-center")
                                    img = center_slide.find_element(By.TAG_NAME, "img")
                                    img_src = img.get_attribute("src")
                                    if is_valid_downloadable_url(img_src) and not is_map_or_pin_image(img_src):
                                        image_url = img_src
                                        logger.info(f"Found center slide image: {image_url}")
                                except (NoSuchElementException, StaleElementReferenceException):
                                    logger.warning("Could not find center slide")
                            
                            # Try to get all slide divs if specific slides failed
                            if not image_url:
                                slide_divs = driver.find_elements(By.CSS_SELECTOR, ".image-gallery-slide")
                                logger.info(f"Found {len(slide_divs)} slide divs")
                                
                                for slide_div in slide_divs:
                                    try:
                                        # Try to get image from this slide
                                        img_elements = slide_div.find_elements(By.TAG_NAME, "img")
                                        if img_elements:
                                            img_src = img_elements[0].get_attribute("src")
                                            if is_valid_downloadable_url(img_src) and not is_map_or_pin_image(img_src):
                                                image_url = img_src
                                                logger.info(f"Found image from slide div: {image_url}")
                                                break
                                    except (StaleElementReferenceException, NoSuchElementException):
                                        continue
                            
                            # If no valid image found in slides, try getting any image in the gallery
                            if not image_url:
                                gallery = driver.find_element(By.CLASS_NAME, "image-gallery-slides")
                                img_elements = gallery.find_elements(By.TAG_NAME, "img")
                                
                                for img in img_elements:
                                    try:
                                        img_src = img.get_attribute("src")
                                        if is_valid_downloadable_url(img_src) and not is_map_or_pin_image(img_src):
                                            image_url = img_src
                                            logger.info(f"Found image from gallery: {image_url}")
                                            break
                                    except (StaleElementReferenceException, NoSuchElementException):
                                        continue
                        else:
                            logger.warning("No image gallery found in the DOM")
                    
                    except Exception as e:
                        logger.warning(f"DOM traversal error: {e}")
                
                # Method 3: Last resort - search for any image on the page that's not a map/pin
                if not image_url:
                    try:
                        logger.info("Trying final approach - any property image on page")
                        # Find all images
                        img_elements = driver.find_elements(By.TAG_NAME, "img")
                        
                        for img in img_elements:
                            try:
                                # Get image source and filter out small icons, logos and maps
                                src = img.get_attribute("src")
                                
                                # Skip if the image is not valid downloadable or is a map/pin
                                if not is_valid_downloadable_url(src) or is_map_or_pin_image(src):
                                    continue
                                
                                # Try to get dimensions to filter out small icons
                                width = img.get_attribute("width")
                                height = img.get_attribute("height")
                                
                                # If dimensions are available, filter out small icons
                                if (width and height and 
                                    (int(width) > 100 if width.isdigit() else True) and 
                                    (int(height) > 100 if height.isdigit() else True)):
                                    image_url = src
                                    logger.info(f"Found large image: {image_url}")
                                    break
                                # If dimensions aren't available, still use the image if it's from corelogic
                                elif "corelogic" in src:
                                    image_url = src
                                    logger.info(f"Found CoreLogic image: {image_url}")
                                    break
                            except (StaleElementReferenceException, NoSuchElementException):
                                continue
                    
                    except Exception as e:
                        logger.warning(f"Final image search error: {e}")
                
                # Verify the found image URL is downloadable
                if image_url:
                    if not is_valid_downloadable_url(image_url):
                        logger.warning(f"Found image URL {image_url} is not downloadable, skipping")
                        image_url = None
                
                # Set the image URL in the row if found
                if image_url:
                    row[1] = image_url
                    logger.info(f"Set image URL for property {idx+1}: {image_url}")
                else:
                    logger.warning(f"No valid property image found for property {idx+1}")
                
                # Extract agency name and agent name from row
                agency_name = row[15]
                agent_name = row[16]
                
                # Clean and normalize the names for comparison
                agency_name_clean = ""
                agent_name_clean = ""
                
                if agency_name and agency_name != "-" and agency_name != "N/A":
                    agency_name_clean = agency_name.lower().strip()
                    logger.info(f"Looking for agency: {agency_name_clean}")
                
                if agent_name and agent_name != "-" and agent_name != "N/A":
                    agent_name_clean = agent_name.lower().strip()
                    logger.info(f"Looking for agent: {agent_name_clean}")
                
                # Only proceed if we have either an agency or agent name
                if agency_name_clean or agent_name_clean:
                    try:
                        # Try to click "Show More" link to expand the listing description
                        try:
                            show_more_link = driver.find_element(By.XPATH, "//a[text()='Show More']")
                            logger.info("Found 'Show More' link, clicking to expand description")
                            show_more_link.click()
                            random_delay(1.0, 2.0)
                            logger.info("Clicked 'Show More' link successfully")
                        except NoSuchElementException:
                            logger.info("No 'Show More' link found, content might be already expanded")
                        except Exception as e:
                            logger.warning(f"Error clicking 'Show More' link: {e}")
                        
                        # Find the listing description panel
                        try:
                            # Wait for the panel to be present
                            listing_panel = WebDriverWait(driver, 5).until(
                                EC.presence_of_element_located((By.ID, "listing-description-panel"))
                            )
                            logger.info("Found listing description panel")
                            
                            # Find the attr-container div
                            attr_containers = listing_panel.find_elements(By.CLASS_NAME, "attr-container")
                            logger.info(f"Found {len(attr_containers)} attr-containers")
                            
                            phone_found = False
                            
                            for container in attr_containers:
                                if phone_found:
                                    break
                                    
                                # Find all advertiser-list divs
                                advertiser_lists = container.find_elements(By.CLASS_NAME, "advertiser-list")
                                logger.info(f"Found {len(advertiser_lists)} advertiser-lists")
                                
                                for advertiser_list in advertiser_lists:
                                    # Find all paragraphs
                                    paragraphs = advertiser_list.find_elements(By.CLASS_NAME, "listing-desc-attribute-label")
                                    logger.info(f"Found {len(paragraphs)} paragraphs in advertiser list")
                                    
                                    # Need at least 3 paragraphs (agency, agent, phone)
                                    if len(paragraphs) >= 3:
                                        try:
                                            # Get agency, agent, and phone info
                                            agency_value = paragraphs[0].find_element(By.CLASS_NAME, "attr-value")
                                            agent_value = paragraphs[1].find_element(By.CLASS_NAME, "attr-value")
                                            phone_value = paragraphs[2].find_element(By.CLASS_NAME, "attr-value")
                                            
                                            # Extract text values
                                            found_agency = agency_value.text.lower().strip()
                                            found_agent = agent_value.text.lower().strip()
                                            found_phone = phone_value.text.strip()
                                            
                                            logger.info(f"Found: Agency: {found_agency}, Agent: {found_agent}, Phone: {found_phone}")
                                            
                                            # Check if either agency or agent matches
                                            agency_match = agency_name_clean and found_agency == agency_name_clean
                                            agent_match = agent_name_clean and found_agent == agent_name_clean
                                            
                                            if agency_match or agent_match:
                                                logger.info(f"Match found! Agency match: {agency_match}, Agent match: {agent_match}")
                                                row[17] = found_phone
                                                phone_found = True
                                                break
                                        except Exception as e:
                                            logger.warning(f"Error processing paragraphs: {e}")
                            
                            # If no phone found, try an alternative approach
                            if not phone_found:
                                logger.info("No phone found with primary approach, trying alternative methods")
                                
                                # Use JavaScript to extract phone number
                                try:
                                    phone_results = driver.execute_script("""
                                        const agentNameToFind = arguments[0].toLowerCase();
                                        const agencyNameToFind = arguments[1].toLowerCase();
                                        
                                        // Find the listing description panel
                                        const panel = document.getElementById('listing-description-panel');
                                        if (!panel) return null;
                                        
                                        // Find all attr-container divs
                                        const attrContainers = panel.getElementsByClassName('attr-container');
                                        
                                        for (const container of attrContainers) {
                                            // Find all advertiser-list divs
                                            const advertiserLists = container.getElementsByClassName('advertiser-list');
                                            
                                            for (const list of advertiserLists) {
                                                // Get all paragraphs
                                                const paragraphs = list.getElementsByClassName('listing-desc-attribute-label');
                                                
                                                if (paragraphs.length >= 3) {
                                                    // Get agency, agent and phone values
                                                    const agencyValue = paragraphs[0].querySelector('.attr-value');
                                                    const agentValue = paragraphs[1].querySelector('.attr-value');
                                                    const phoneValue = paragraphs[2].querySelector('.attr-value');
                                                    
                                                    if (agencyValue && agentValue && phoneValue) {
                                                        const foundAgency = agencyValue.textContent.toLowerCase().trim();
                                                        const foundAgent = agentValue.textContent.toLowerCase().trim();
                                                        const foundPhone = phoneValue.textContent.trim();
                                                        
                                                        // Check for matches
                                                        const agencyMatch = agencyNameToFind && (foundAgency === agencyNameToFind);
                                                        const agentMatch = agentNameToFind && (foundAgent === agentNameToFind);
                                                        
                                                        if (agencyMatch || agentMatch) {
                                                            return {
                                                                agency: foundAgency,
                                                                agent: foundAgent,
                                                                phone: foundPhone
                                                            };
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                        
                                        return null;
                                    """, agent_name_clean, agency_name_clean)
                                    
                                    if phone_results:
                                        logger.info(f"Found phone with JavaScript: {phone_results['phone']}")
                                        row[17] = phone_results['phone']
                                        phone_found = True
                                
                                except Exception as e:
                                    logger.warning(f"Error with JavaScript approach: {e}")
                            
                            # Last resort: look for any phone number near agent name
                            if not phone_found and agent_name_clean:
                                logger.info("Looking for phone number near agent name")
                                try:
                                    # Get page text
                                    page_text = driver.find_element(By.TAG_NAME, "body").text
                                    
                                    # Find agent name position
                                    agent_pos = page_text.lower().find(agent_name_clean)
                                    
                                    if agent_pos > -1:
                                        # Look for phone pattern within 200 chars after agent name
                                        search_text = page_text[agent_pos:agent_pos+200]
                                        
                                        # Australian phone pattern
                                        phone_matches = re.findall(r'(\b04\d{2}\s*\d{3}\s*\d{3}\b|\b\d{4}\s*\d{3}\s*\d{3}\b|\b\d{4}\s*\d{4}\b)', search_text)
                                        
                                        if phone_matches:
                                            found_phone = phone_matches[0].strip()
                                            logger.info(f"Found phone near agent name: {found_phone}")
                                            row[17] = found_phone
                                except Exception as e:
                                    logger.warning(f"Error finding phone near agent name: {e}")
                            
                        except Exception as e:
                            logger.warning(f"Error finding listing panel: {e}")
                    
                    except Exception as e:
                        logger.warning(f"Error extracting agent phone number: {e}")
            
            except Exception as e:
                logger.error(f"Error processing property {idx}: {e}")
                continue
                
            # Add a random delay between properties to avoid being blocked
            random_delay(1.0, 3.0)
                
        logger.info(f"Completed processing {len(all_rows)} properties")
        return all_rows
        
    finally:
        # Close the webdriver
        driver.quit()
        logger.info("Webdriver closed")

if __name__ == "__main__":
    # Example usage
    test_rows = [
        ["Already Leased", np.nan, "GROUND FLOOR/23 WILLOUGHBY ROAD ", "CROWS NEST", "NSW", "2065", 
         "", "Commercial: Office Building", "-", "-", "-", "", 278, 145, "-", "RWC Sydney North", 
         "Max Stephens", "", "", "", "-", "Business", "3/DP24071", "-", 
         "https://rpp.corelogic.com.au/property/ground-floor-23-willoughby-road-crows-nest-nsw-2065/2026657", 
         "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", 
         "N/A", "N/A", "N/A", "N/A", "N/A", "Not Disclosed", "23 Aug 2024", "Not Disclosed", "06 Jan 2025", 
         "", "", 102, "False", "", "", "", "", "", "", "", "", ""],
        
        ["For Sale", np.nan, "95 PITTWATER ROAD ", "HUNTERS HILL", "NSW", "2110", 
         "SP2 - Infrastructure - Hunters Hill Local Environmental Plan 2012 Map Amendment No 1", 
         "Commercial", 8, 1, "-", "", 302, 105, "-", "Bresic Whitney Hunters Hill", 
         "Nicholas McEvoy", "", "", "", "-", "Business", "1/DP814063", "-", 
         "https://rpp.corelogic.com.au/property/95-pittwater-road-hunters-hill-nsw-2110/3008130", 
         "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", 
         "Guide $2,650,000", "07 Mar 2025", "Guide $2,650,000", "10 Mar 2025", "Auction", 
         "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", 11, "True", "", "", "", "", "", "", "", "", ""],
        
        ["For Sale", np.nan, "20 BURLINGTON STREET ", "CROWS NEST", "NSW", "2065", 
         "MU1 - Mixed Use - North Sydney Local Environmental Plan 2013 Map Amendment No 1", 
         "Commercial", "-", "-", "-", "", 413, 130, "-", "Dentown - Sydney", 
         "Joshua Alonzo", "", "", "", "-", "Business", "18/5/DP1265", "-", 
         "https://rpp.corelogic.com.au/property/20-burlington-street-crows-nest-nsw-2065/2024025", 
         "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", 
         "Contact Agent", "19 Jan 2025", "Contact Agent", "19 Jan 2025", "Private Treaty", 
         "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", 58, "True", "", "", "", "", "", "", "", "", ""],

        ["For Sale", np.nan, "20 BURLINGTON STREET ", "CROWS NEST", "NSW", "2065", 
         "MU1 - Mixed Use - North Sydney Local Environmental Plan 2013 Map Amendment No 1", 
         "Commercial", "-", "-", "-", "", 413, 130, "-", "No Agent Property", 
         "No Agent Property - NSW", "", "", "", "-", "Business", "18/5/DP1265", "-", 
         "https://rpp.corelogic.com.au/property/504-10-12-clarke-street-crows-nest-nsw-2065/2024726", 
         "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", 
         "Contact Agent", "19 Jan 2025", "Contact Agent", "19 Jan 2025", "Private Treaty", 
         "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", 58, "True", "", "", "", "", "", "", "", "", ""]
    ]
    
    updated_rows = get_image_and_agent_phone(test_rows)
    
    # Print results
    for row in updated_rows:
        print(f"Property: {row[2]}, {row[3]}")
        print(f"Image URL: {row[1]}")
        print(f"Phone: {row[17]}")