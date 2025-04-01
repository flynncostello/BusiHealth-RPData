#!/usr/bin/env python3
# Merges Excel files from RP Data into a single file
# Integrates with landchecker.py to get zoning information for all properties in a single batch

import os
import logging
import pandas as pd
import re
import openpyxl
from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.drawing.image import Image
from io import BytesIO
from datetime import datetime
from collections import Counter
import requests
import time
from PIL import Image as PILImage

from landchecker import get_property_zonings  # Import the zoning lookup function
from get_image_and_agent_phone import get_image_and_agent_phone  # Import the image and phone lookup function
from check_zoning_use import check_zoning_use  # Import the zoning use checker function


# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def find_header_row(df):
    """Find the row index where 'Property Photo' appears in the first column."""
    for idx, value in enumerate(df.iloc[:, 0]):
        if str(value).strip() == 'Property Photo':
            return idx
    return None

def get_hyperlink_from_excel(file_path, sheet_name=0, row_idx=None, column_name="Open in RPData"):
    """
    Directly extract hyperlinks from Excel cells using openpyxl.
    
    Args:
        file_path (str): Path to the Excel file
        sheet_name (int/str): Sheet index or name
        row_idx (int): Row index in the dataframe (0-based)
        column_name (str): Name of the column containing hyperlinks
        
    Returns:
        dict: Mapping of row index to hyperlink URL
    """
    try:
        # Load workbook
        wb = openpyxl.load_workbook(file_path)
        
        # Get the sheet
        if isinstance(sheet_name, int):
            sheet = wb.worksheets[sheet_name]
        else:
            sheet = wb[sheet_name]
        
        # Find header row for Property Photo
        header_row = None
        for row_num, row in enumerate(sheet.iter_rows(), 1):
            for cell in row:
                if cell.value == "Property Photo":
                    header_row = row_num
                    break
            if header_row:
                break
        
        if not header_row:
            logger.error(f"Could not find 'Property Photo' header in {file_path}")
            return {}
        
        # Find column index for 'Open in RPData'
        col_idx = None
        for col_num, cell in enumerate(sheet[header_row], 1):
            if cell.value == column_name:
                col_idx = col_num
                break
        
        if not col_idx:
            logger.warning(f"Could not find '{column_name}' column in {file_path}")
            return {}
        
        # Get hyperlinks from cells
        hyperlinks = {}
        row_offset = 0  # Adjust based on row_idx being 0-based in dataframe
        
        for row_num, row in enumerate(sheet.iter_rows(min_row=header_row+1), header_row+1):
            cell = sheet.cell(row=row_num, column=col_idx)
            
            # Extract URL from cell
            url = None
            
            # Check for hyperlink attribute
            if cell.hyperlink:
                url = cell.hyperlink.target
            
            # Check for formula
            elif cell.value and isinstance(cell.value, str) and cell.value.startswith('=HYPERLINK('):
                match = re.search(r'=HYPERLINK\("([^"]+)"', cell.value)
                if match:
                    url = match.group(1)
            
            # Store URL if found
            if url:
                df_row_idx = row_num - (header_row + 1)
                hyperlinks[df_row_idx] = url
        
        return hyperlinks
    
    except Exception as e:
        logger.error(f"Error extracting hyperlinks from {file_path}: {e}")
        return {}

def extract_hyperlink(cell_content):
    """Extract hyperlink URL from Excel HYPERLINK formula or direct URL."""
    # Handle NaN values
    if pd.isna(cell_content):
        return ""
        
    # Handle Excel formula format
    if isinstance(cell_content, str) and cell_content.startswith('=HYPERLINK('):
        match = re.search(r'=HYPERLINK\("([^"]+)"', cell_content)
        if match:
            return match.group(1)
    
    # If it's already a URL string
    if isinstance(cell_content, str) and (cell_content.startswith('http://') or cell_content.startswith('https://')):
        return cell_content
            
    return cell_content

def normalize_address(address):
    """
    Normalize address to make matching more reliable by removing common variations.
    
    Args:
        address (str): The address to normalize
        
    Returns:
        str: Normalized address
    """
    if not address:
        return ""
        
    # Convert to uppercase
    address = address.upper()
    
    # Replace multiple spaces with a single space
    address = re.sub(r'\s+', ' ', address)
    
    # Remove redundant commas and spaces around them
    address = re.sub(r'\s*,\s*', ',', address)
    
    # Remove trailing/leading commas and spaces
    address = address.strip(', ')
    
    # Remove unit/floor designations that might vary
    address = re.sub(r'^(UNIT|FLOOR|SUITE|SHOP|GROUND FLOOR|GF)[\s/]+\d+[/]?', '', address)
    
    # Remove "GROUND FLOOR" or similar prefixes
    address = re.sub(r'^(GROUND FLOOR|GF)[/]', '', address)
    
    # Remove state abbreviation variations
    address = address.replace(', NSW,', ',').replace(' NSW ', ' ')
    
    # Remove postal code if it exists to make matching easier
    address = re.sub(r'\s*\d{4}\s*$', '', address)
    
    return address.strip()

def generate_filename(locations, property_types, min_floor, max_floor):
    """
    Generate a filename based on search criteria and current date/time.
    
    Args:
        locations (list): List of locations searched
        property_types (list): List of property types searched
        min_floor (str): Minimum floor size
        max_floor (str): Maximum floor size
        
    Returns:
        str: Generated filename
    """
    # Format current date and time
    now = datetime.now()
    date_time_str = now.strftime("%d_%m_%Y_%H_%M")
    
    # Format locations for filename
    location_str = "_".join([loc.replace(" ", "_") for loc in locations])
    
    # Create merged_properties directory if it doesn't exist
    os.makedirs("merged_properties", exist_ok=True)
    
    # Create filename with merged_properties directory
    filename = f"merged_properties/Properties_{location_str}_{date_time_str}.xlsx"
    
    return filename

def is_valid_image_url(url):
    """
    Check if the URL is a valid image URL that can be downloaded.
    
    Args:
        url (str): URL to check
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not url:
        return False
        
    # Check for blob URLs which can't be downloaded
    if url.startswith('blob:'):
        logger.warning(f"Detected blob URL which can't be downloaded: {url}")
        return False
        
    # Check for data URLs
    if url.startswith('data:'):
        return False
        
    # Check for valid HTTP/HTTPS URLs
    if not (url.startswith('http://') or url.startswith('https://')):
        return False
        
    # Check for common image extensions or patterns
    image_patterns = ['.jpg', '.jpeg', '.png', '.gif', '.webp', 'images.', 'corelogic.asia']
    has_image_pattern = any(pattern in url.lower() for pattern in image_patterns)
    
    return has_image_pattern

def download_image(url, max_retries=3):
    """
    Download image from URL and return as BytesIO object.
    
    Args:
        url (str): URL of the image
        max_retries (int): Maximum number of retry attempts
        
    Returns:
        BytesIO: Image data as BytesIO object or None if failed
    """
    # Validate URL before attempting download
    if not is_valid_image_url(url):
        logger.warning(f"Invalid image URL, cannot download: {url}")
        return None
        
    for attempt in range(max_retries):
        try:
            # Add proper headers to simulate a browser request
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36',
                'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://rpp.corelogic.com.au/'
            }
            
            # Make the request with increased timeout and headers
            response = requests.get(url, timeout=15, headers=headers, stream=True)
            
            if response.status_code == 200:
                # Check if the content type is an image
                content_type = response.headers.get('Content-Type', '')
                if 'image' in content_type:
                    # Verify it's a valid image by trying to open it
                    try:
                        img_data = BytesIO(response.content)
                        img = PILImage.open(img_data)
                        img.verify()  # Verify it's a valid image
                        # Reset the BytesIO position
                        img_data.seek(0)
                        return img_data
                    except Exception as e:
                        logger.warning(f"Downloaded data is not a valid image: {e}")
                        return None
                else:
                    logger.warning(f"URL returned non-image content type: {content_type}")
                    
                    # Some servers might return the wrong content type but still serve an image
                    # Try to load the content as an image anyway
                    try:
                        img_data = BytesIO(response.content)
                        img = PILImage.open(img_data)
                        img.verify()  # Verify it's a valid image
                        # Reset the BytesIO position
                        img_data.seek(0)
                        return img_data
                    except Exception as e:
                        logger.warning(f"Content verification failed, not an image: {e}")
                        
            elif response.status_code == 403 or response.status_code == 401:
                logger.warning(f"Access denied (HTTP {response.status_code}), image URL may require authentication")
                break  # Don't retry auth errors
            else:
                logger.warning(f"Failed to download image (attempt {attempt+1}/{max_retries}): HTTP {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading image (attempt {attempt+1}/{max_retries}): {e}")
            
        # Wait before retrying, with exponential backoff
        if attempt < max_retries - 1:
            wait_time = 2 ** attempt  # 1, 2, 4 seconds
            logger.info(f"Retrying download in {wait_time} seconds...")
            time.sleep(wait_time)
    
    return None

def process_excel_files(files_dict, locations, property_types, min_floor, max_floor, business_type, headless=False, output_file=None, progress_callback=None):
    """
    Process and merge RP Data Excel files.
    
    Args:
        files_dict (dict): Dictionary with search types as keys and file paths as values
        locations (list): List of locations searched
        property_types (list): List of property types searched
        min_floor (str): Minimum floor size
        max_floor (str): Maximum floor size
        business_type (str): Type of business searched either Vet or Health
        output_file (str, optional): Path to save the merged Excel file. If None, will be generated.
        
    Returns:
        bool: Success status
    """
    # Default progress reporting function if none provided
    if progress_callback is None:
        def progress_callback(percentage, message):
            pass  # No-op if no callback provided
    logger.info("===== PROCESSING EXCEL FILES =====")
    
    # Generate filename if not provided
    if output_file is None:
        output_file = generate_filename(locations, property_types, min_floor, max_floor)
    
    try:
        # Create a new workbook and select the active worksheet
        wb = Workbook()
        ws = wb.active
        
        # Set worksheet name to "Properties" as requested
        ws.title = "Properties"
        
        # Create headers for the merged file
        headers = [
            "Type", "Property Photo", "Street Address", "Suburb", "State", "Postcode",
            "Site Zoning", "Property Type", "Bed", "Bath", "Car", "Extra Cost for Parks", "Land Size (m²)",
            "Floor Size (m²)", "Year Built", "Agency", "Agent", "Contact Phone", "Email",
            "Contacted (T/F)", "Land Use", "Development Zone", "Parcel Details", "Owner Type",
            "Website Link",
            # For "Sales" only
            "Sale Price", "Sale Date", "Settlement Date", "Sale Type", "Owner 1 Name",
            "Owner 2 Name", "Owner 3 Name", "Vendor 1 Name", "Vendor 2 Name", "Vendor 3 Name",
            # For "For Sale" only
            "First Listed Price", "First Listed Date", "Last Listed Price", "Last Listed Date",
            "Listing Type",
            # For "For Rent" only
            "First Rental Price", "First Rental Date", "Last Rental Price", "Last Rental Date",
            "Outgoings Ex GST", "Total Lease Price (Base + Outgoings)",
            # For "For Rent" and "For Sale" only
            "Days on Market", "Active Listing",
            # Additional blank columns
            "Comments Y=Recommended, E=Evaluating, R=Rejected", "Date Added", "Date Presented",
            "Allowable Use in Zone (T/F)", "$/m²", "Available (T/F)", "Suitable (T/F)",
            "PUT IN REPORT (T/F)", "Client Feedback", "Busi's Comment"
        ]
        
        # Add headers to the first row
        ws.append(headers)
        
        # Make the header row bold
        for cell in ws[1]:
            cell.font = Font(bold=True, size=14)

        # First pass: collect all rows and addresses
        all_rows = []
        all_addresses = []
        
        # Count occurrences of each address to handle duplicates
        address_counter = Counter()
        # Map to store (address, count) -> row_index
        address_to_row_index = {}
        # Map to store normalized addresses
        normalized_address_map = {}
        
        logger.info("First pass: collecting all property data and addresses...")
        
        progress_callback(48, "Extracting data from forSale, forRent and Sales...")

        row_index = 0
        for search_type, file_path in files_dict.items():
            logger.info(f"Reading file for {search_type}: {file_path}")
            
            try:
                # First get hyperlinks directly from Excel file
                hyperlinks = get_hyperlink_from_excel(file_path)
                logger.info(f"Retrieved {len(hyperlinks)} hyperlinks directly from {file_path}")
                
                # Read the Excel file
                df = pd.read_excel(file_path, engine='openpyxl')
                
                # Find the header row
                header_row = find_header_row(df)
                
                if header_row is None:
                    logger.error(f"Could not find header row in {file_path}")
                    continue
                
                # Set the header row as the column names and get data
                df.columns = df.iloc[header_row]
                data_df = df.iloc[header_row + 1:].reset_index(drop=True)
                
                # Log column headers for debugging
                logger.info(f"Columns in {search_type} file: {list(data_df.columns)}")
                
                # Process each row and collect addresses
                for idx, row in data_df.iterrows():
                    new_row = ["N/A"] * len(headers)  # Initialize with N/A for all columns
                    
                    # Set type based on search type
                    if search_type == "Sales":
                        new_row[0] = "Sold"
                    elif search_type == "For Sale":
                        new_row[0] = "For Sale"
                    elif search_type == "For Rent":
                        # Check Active Listing column for For Rent
                        active_listing = row.get("Active Listing")
                        new_row[0] = "For Lease" if str(active_listing) == "True" else "Already Leased"
                    
                    # Common fields across all file types
                    new_row[1] = row.get("Property Photo", "")
                    
                    # Extract address components
                    street_address = str(row.get("Street Address", ""))
                    suburb = str(row.get("Suburb", ""))
                    state = str(row.get("State", ""))
                    postcode = str(row.get("Postcode", ""))
                    
                    new_row[2] = street_address
                    new_row[3] = suburb
                    new_row[4] = state
                    new_row[5] = postcode
                    
                    # Create full address for landchecker lookup
                    full_address = f"{street_address}, {suburb}, {state}, {postcode}"
                    full_address = full_address.strip().replace(", ,", ",").replace(",,", ",")
                    
                    # Only add address if we have enough information
                    if street_address and suburb and state:
                        # Count this address occurrence
                        address_counter[full_address] += 1
                        occurrence = address_counter[full_address]
                        
                        # Store unique address identifier (address with occurrence count)
                        unique_address_key = (full_address, occurrence)
                        
                        all_addresses.append(full_address)
                        address_to_row_index[unique_address_key] = row_index
                        
                        # Store normalized address mapping for better matching
                        norm_address = normalize_address(full_address)
                        normalized_address_map[norm_address] = full_address
                    
                    # Site Zoning will be filled in later
                    new_row[6] = ""
                    
                    new_row[7] = row.get("Property Type", "")
                    new_row[8] = row.get("Bed", "")
                    new_row[9] = row.get("Bath", "")
                    new_row[10] = row.get("Car", "")
                    
                    # Fields that should be blank
                    new_row[11] = ""  # Extra Cost for Parks
                    
                    # Land Size and Floor Size with correct symbol
                    new_row[12] = row.get("Land Size (m²)", "")
                    new_row[13] = row.get("Floor Size (m²)", "")
                    new_row[14] = row.get("Year Built", "")
                    new_row[15] = row.get("Agency", "")
                    new_row[16] = row.get("Agent", "")
                    
                    # Fields that should be blank
                    new_row[17] = ""  # Contact Phone
                    new_row[18] = ""  # Email
                    new_row[19] = ""  # Contacted (T/F)
                    
                    # Common fields across all file types
                    new_row[20] = row.get("Land Use", "")
                    new_row[21] = row.get("Development Zone", "")
                    new_row[22] = row.get("Parcel Details", "")
                    new_row[23] = row.get("Owner Type", "")
                    
                    # Website Link from Open in RPData - multi-step approach to get the link
                    # First try using the hyperlinks extracted directly from Excel
                    if idx in hyperlinks:
                        # We found a direct hyperlink from the Excel file
                        new_row[24] = hyperlinks[idx]
                        logger.info(f"Found hyperlink directly from Excel: {hyperlinks[idx]}")
                    else:
                        # Otherwise try different approaches for getting the link
                        rp_data_link = None
                        
                        # Method 1: Try direct column access
                        if "Open in RPData" in row:
                            rp_data_link = row["Open in RPData"]
                        
                        # Method 2: Look for column with RPData or Link in its name
                        if pd.isna(rp_data_link) or not rp_data_link:
                            for col in row.index:
                                if "RPData" in col or "Link" in col:
                                    if not pd.isna(row[col]) and row[col]:
                                        rp_data_link = row[col]
                                        break
                        
                        # Method 3: If it's still NaN but we have a street address, create a generic URL
                        if (pd.isna(rp_data_link) or not rp_data_link) and street_address:
                            # Clean the address for a URL-friendly format
                            clean_addr = f"{street_address.lower().replace(' ', '-')}-{suburb.lower().replace(' ', '-')}-{state.lower()}-{postcode}"
                            rp_data_link = f"https://rpp.corelogic.com.au/property/{clean_addr}"
                            logger.warning(f"Created generic URL for {street_address}: {rp_data_link}")
                        
                        # Extract hyperlink and set it
                        new_row[24] = extract_hyperlink(rp_data_link) if not pd.isna(rp_data_link) else ""
                        
                        # As a last resort, preserve the raw formula
                        if not new_row[24] and isinstance(rp_data_link, str) and "HYPERLINK" in rp_data_link:
                            # Just use the raw formula - we'll extract the URL during export
                            new_row[24] = rp_data_link
                    
                    # Fields specific to "Sales"
                    if search_type == "Sales":
                        new_row[25] = row.get("Sale Price", "")
                        new_row[26] = row.get("Sale Date", "")
                        new_row[27] = row.get("Settlement Date", "")
                        new_row[28] = row.get("Sale Type", "")
                        new_row[29] = row.get("Owner 1 Name", "")
                        new_row[30] = row.get("Owner 2 Name", "")
                        new_row[31] = row.get("Owner 3 Name", "")
                        new_row[32] = row.get("Vendor 1 Name", "")
                        new_row[33] = row.get("Vendor 2 Name", "")
                        new_row[34] = row.get("Vendor 3 Name", "")
                    
                    # Fields specific to "For Sale"
                    if search_type == "For Sale":
                        new_row[35] = row.get("First Listed Price", "")
                        new_row[36] = row.get("First Listed Date", "")
                        new_row[37] = row.get("Last Listed Price", "")
                        new_row[38] = row.get("Last Listed Date", "")
                        new_row[39] = row.get("Listing Type", "")
                        
                        # For Sale also has Days on Market and Active Listing
                        new_row[46] = row.get("Days on Market", "")
                        new_row[47] = row.get("Active Listing", "")
                    
                    # Fields specific to "For Rent"
                    if search_type == "For Rent":
                        new_row[40] = row.get("First Rental Price", "")
                        new_row[41] = row.get("First Rental Date", "")
                        new_row[42] = row.get("Last Rental Price", "")
                        new_row[43] = row.get("Last Rental Date", "")
                        new_row[44] = row.get("Outgoings Ex GST", "")
                        new_row[45] = row.get("Total Lease Price (Base + Outgoings)", "")
                        
                        # For Rent also has Days on Market and Active Listing
                        new_row[46] = row.get("Days on Market", "")
                        new_row[47] = row.get("Active Listing", "")
                    
                    # Make additional columns blank instead of N/A
                    for i in range(48, len(headers)):
                        new_row[i] = ""
                    
                    # Add the new row to our collection
                    all_rows.append(new_row)
                    row_index += 1
                
                logger.info(f"Collected {len(data_df)} rows from {search_type}")
            
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        # Log duplicate addresses
        for address, count in address_counter.items():
            if count > 1:
                logger.info(f"Duplicate address detected: '{address}' appears {count} times")



        progress_callback(50, "Obtaining zoning info for all properties...")

        # Second pass: get all zonings in one batch if we have addresses
        if all_addresses:
            logger.info(f"Second pass: getting zoning information for {len(all_addresses)} addresses in a single batch...")
            
            # Create a list of unique addresses to query
            unique_addresses = list(set(all_addresses))
            
            # Call get_property_zonings with unique addresses
            try:
                print(f"Getting zoning info for {len(unique_addresses)} unique addresses")
                zonings_dict = get_property_zonings(unique_addresses, headless=headless)
                logger.info(f"Successfully retrieved zoning info for {len(zonings_dict)} properties")
                
                # Create a mapping of normalized zonings addresses to their values
                normalized_zonings = {}
                for address, zoning in zonings_dict.items():
                    normalized_zonings[normalize_address(address)] = zoning
                
                # Debug: Print all normalized addresses and their zonings
                logger.info("Normalized address mappings for zoning lookups:")
                for norm_addr, orig_addr in normalized_address_map.items():
                    logger.info(f"Normalized: '{norm_addr}' --> Original: '{orig_addr}'")
                
                # Update rows with zoning information - using the unique address keys
                processed_addresses = set()  # Keep track of which addresses we've already processed
                
                for address, count in address_counter.items():
                    # Get the zoning for this address
                    zoning = zonings_dict.get(address)
                    
                    # If direct match fails, try normalized match
                    if not zoning:
                        norm_address = normalize_address(address)
                        zoning = normalized_zonings.get(norm_address)
                        
                        if zoning:
                            logger.info(f"Found zoning through normalized address matching for {address}")
                    
                    # Apply zoning if we have a valid one
                    if zoning and zoning != "-" and len(zoning) > 5:
                        # Apply the zoning to all occurrences of this address
                        for i in range(1, count + 1):
                            unique_key = (address, i)
                            if unique_key in address_to_row_index:
                                row_idx = address_to_row_index[unique_key]
                                logger.info(f"Applying zoning '{zoning}' to address '{address}' (occurrence {i})")
                                
                                # Update the row with zoning information
                                all_rows[row_idx][6] = zoning
                                processed_addresses.add(unique_key)
                    else:
                        # If we still don't have a zoning value, try fuzzy matching as last resort
                        norm_address = normalize_address(address)
                        for search_addr, search_zoning in zonings_dict.items():
                            if search_zoning != "-" and len(search_zoning) > 5:
                                norm_search = normalize_address(search_addr)
                                # Simple partial matching - if the street address part matches
                                if norm_address.split(',')[0] == norm_search.split(',')[0]:
                                    # Apply the zoning to all occurrences of this address
                                    for i in range(1, count + 1):
                                        unique_key = (address, i)
                                        if unique_key in address_to_row_index and unique_key not in processed_addresses:
                                            row_idx = address_to_row_index[unique_key]
                                            logger.info(f"Fuzzy match found! Applying zoning '{search_zoning}' to address '{address}' (occurrence {i})")
                                            all_rows[row_idx][6] = search_zoning
                                            processed_addresses.add(unique_key)
                                    break
                
                # Log any addresses that didn't get zoning information
                for unique_key in address_to_row_index.keys():
                    if unique_key not in processed_addresses:
                        address, occurrence = unique_key
                        logger.warning(f"No zoning found for address: '{address}' (occurrence {occurrence})")
                
            except Exception as e:
                logger.error(f"Error getting zoning information in batch: {e}")
        else:
            logger.warning("No valid addresses found for zoning lookup")



        progress_callback(60, "Checking zoning table for allowable use...")

        ########################################################################################################################
        # TRYING TO SET AS MANY 'ALLOWABLE USE IN ZONE (T/F)' AS POSSIBLE
        # check_zoning_use.py
        logger.info("===== CHECKING ZONING ALLOWANCES =====")
        try:
            all_rows = check_zoning_use(all_rows, business_type)
            logger.info(f"Completed zoning allowance check for business type: {business_type}")
        except Exception as e:
            logger.error(f"Error checking zoning allowances: {e}")
            import traceback
            logger.error(traceback.format_exc())



        progress_callback(61, "Obtaining all images and agent contact details for each property from RPData links...")

        ########################################################################################################################
        # get_image_and_agent_phone.py
        # GETTING PROPERTY IMAGES AND AGENT DETAILS FOR EACH ROW
        logger.info("===== RETRIEVING PROPERTY IMAGES AND AGENT CONTACT DETAILS =====")
        try:
            # Call get_image_and_agent_phone to update the rows with image URLs and phone numbers
            all_rows = get_image_and_agent_phone(all_rows, headless=headless)
            logger.info(f"Successfully retrieved images and contact details for {len(all_rows)} properties")
            
            # Count how many images and phone numbers were retrieved
            image_count = sum(1 for row in all_rows if isinstance(row[1], str) and row[1].startswith("http"))
            phone_count = sum(1 for row in all_rows if row[17] and row[17] != "")
            
            logger.info(f"Retrieved {image_count}/{len(all_rows)} property images and {phone_count}/{len(all_rows)} agent phone numbers")
        except Exception as e:
            logger.error(f"Error retrieving property images and agent details: {e}")
            import traceback
            logger.error(traceback.format_exc())



        progress_callback(96, "Writing all properties to final merged file...")

        # Third pass: write all rows to the worksheet
        logger.info("Third pass: writing all rows to the output file...")
        for i, row_data in enumerate(all_rows, 2):  # Start from row 2 (after headers)
            # Handle image URL (column 2, index 1)
            image_url = row_data[1]
            
            # If image_url is a URL, download it and add as image
            if isinstance(image_url, str) and image_url.startswith("http") and is_valid_image_url(image_url):
                logger.info(f"Downloading image from URL: {image_url}")
                try:
                    img_data = download_image(image_url)
                    if img_data:
                        try:
                            # Create an openpyxl Image object
                            img = Image(img_data)
                            
                            # Set reasonable fixed dimensions
                            img.width = 150
                            img.height = 120
                            
                            # Add image to cell
                            ws.add_image(img, f'B{i}')
                            
                            # Set row height to accommodate image
                            ws.row_dimensions[i].height = 90
                            
                            logger.info(f"Successfully added image to row {i}")
                        except Exception as e:
                            logger.error(f"Error adding image to Excel cell: {e}")
                            # Write the URL as text if there's an error with the Excel image
                            ws.cell(row=i, column=2, value=image_url)
                    else:
                        logger.warning(f"Failed to download image from {image_url}")
                        # Store as text only
                        ws.cell(row=i, column=2, value=f"Image URL: {image_url}")
                except Exception as e:
                    logger.error(f"Error processing image: {e}")
                    # Write the URL as text if there's an error
                    ws.cell(row=i, column=2, value=f"Image URL: {image_url}")
            else:
                # Write the cell value as-is if it's not a valid image URL
                if isinstance(image_url, str) and image_url.startswith("blob:"):
                    # For blob URLs, just write a note that there was an invalid URL
                    ws.cell(row=i, column=2, value="Image not available (invalid URL format)")
                else:
                    # Write the cell value as-is
                    ws.cell(row=i, column=2, value=image_url)
            
            # Write all other values for this row (except the image which is already handled)
            for j, value in enumerate(row_data):
                # Skip the image cell (already handled)
                if j == 1:
                    continue
                
                # For Website Link column (25th column, index 24)
                if j == 24 and isinstance(value, str) and (value.startswith('http://') or value.startswith('https://')):
                    cell = ws.cell(row=i, column=j+1, value=value)
                    cell.hyperlink = value
                    cell.style = "Hyperlink"
                else:
                    # Regular value
                    ws.cell(row=i, column=j+1, value=value)
        
        # Set font size for all cells
        for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
            for cell in row:
                if cell.row == 1:
                    # Header row - bold and size 14
                    cell.font = Font(bold=True, size=14)
                else:
                    # Data rows - size 14
                    cell.font = Font(size=14)
        
        # Adjust column widths
        for col in ws.columns:
            col_letter = col[0].column_letter
            if col_letter == 'B':  # Image column
                ws.column_dimensions[col_letter].width = 25
            elif col_letter in ['C', 'D', 'G']:  # Address, Suburb, Zoning columns
                ws.column_dimensions[col_letter].width = 25
            else:
                # Set a default width for other columns
                ws.column_dimensions[col_letter].width = 15
        
        # Save the merged file
        wb.save(output_file)
        logger.info(f"Merged file saved to {output_file}")
        return True
    
    except Exception as e:
        logger.error(f"Error processing Excel files: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    # Example usage
    files = {
        "Sales": "downloads/recentSaleExport_20250320144701.xlsx",
        "For Sale": "downloads/forSaleExport_20250320144623.xlsx",
        "For Rent": "downloads/forRentExport_20250320144544.xlsx"
    }
    
    # Search criteria
    locations = ["Hunters Hill NSW 2110", "Crows Nest NSW 2065", "Balmain NSW 2041"]
    property_types = ["Business", "Commercial"]
    min_floor = "Min"
    max_floor = "1200"
    business_type = "Vet" # "Vet"
    
    process_excel_files(files, locations, property_types, min_floor, max_floor, business_type, headless=False)