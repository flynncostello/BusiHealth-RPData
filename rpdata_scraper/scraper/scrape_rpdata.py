#!/usr/bin/env python3
# Main script for running RP Data scraper

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from setup_rpdata_scraper import RPDataScraper, logger

def scrape_rpdata(locations=None, property_types=None, min_floor_area="Min", max_floor_area="Max", 
                  headless=False, progress_callback=None, download_dir=None):
    """
    Scrape property data from RP Data.
    
    Args:
        locations (list): List of locations to search
        property_types (list): List of property types to filter for
        min_floor_area (str): Minimum floor area
        max_floor_area (str): Maximum floor area
        headless (bool): Whether to run in headless mode
        progress_callback (function): Optional callback for progress updates
        download_dir (str, optional): Specific download directory for this job
    
    Returns:
        tuple: (result_files dict, scraper instance) - Dictionary with file paths for each search type and the scraper instance
    """
    # Default progress reporting function if none provided
    if progress_callback is None:
        def progress_callback(percentage, message):
            pass  # No-op if no callback provided
            return True  # Always continue
    
    # Default download directory if not specified
    if download_dir is None:
        download_dir = os.path.join(os.getcwd(), "downloads")
    
    # Ensure download directory exists
    os.makedirs(download_dir, exist_ok=True)
    
    # Set default parameters
    if locations is None:
        locations = []
    
    if property_types is None:
        property_types = ["Business", "Commercial"]
    
    # Create scraper with specific download directory
    scraper = RPDataScraper(headless=headless, download_dir=download_dir)
    result_files = {}
    
    try:
        # Check for cancellation before login
        if progress_callback(15, "Logging into RP Data...") is False:
            logger.info("Job cancelled before login")
            scraper.close()
            return {}, None

        # Login
        login_success = scraper.login("busihealth", "Busihealth123")
        if not login_success:
            logger.error("Login failed, aborting")
            scraper.close()
            return result_files, None
        
        # Process each search type
        search_types = ["For Rent", "For Sale", "Sales"]

        # Check for cancellation after login
        if progress_callback(16, "Getting each search type data from RP Data...") is False:
            logger.info("Job cancelled after login")
            scraper.close()
            return {}, None

        for i, search_type in enumerate(search_types):
            # Check for cancellation at the beginning of each search type
            if progress_callback(20+i*10, f"Getting results for {search_type} data...") is False:
                logger.info(f"Job cancelled before {search_type} search")
                scraper.close()
                return result_files, None

            logger.info(f"\n===== STARTING SEARCH TYPE: {search_type} =====\n")
            
            # Select search type
            if not scraper.select_search_type(search_type):
                logger.error(f"Failed to select search type: {search_type}, skipping")
                continue
            
            # Check for cancellation after selecting search type
            if progress_callback(21+i*10, f"Searching locations for {search_type}...") is False:
                logger.info(f"Job cancelled after selecting {search_type}")
                scraper.close()
                return result_files, None
            
            # Search for locations
            if not scraper.search_locations(locations, search_type):
                logger.error(f"Failed to search locations for: {search_type}, skipping")
                continue
            
            # Check for cancellation after searching locations
            if progress_callback(24+i*10, f"Applying filters for {search_type}...") is False:
                logger.info(f"Job cancelled after searching locations for {search_type}")
                scraper.close()
                return result_files, None
            
            # Apply filters
            if not scraper.apply_filters(property_types, min_floor_area, max_floor_area):
                logger.error(f"Failed to apply filters for: {search_type}, skipping")
                continue
            
            # Check for cancellation after applying filters
            if progress_callback(27+i*10, f"Selecting results for {search_type}...") is False:
                logger.info(f"Job cancelled after applying filters for {search_type}")
                scraper.close()
                return result_files, None
            
            # Select all results
            if not scraper.select_all_results():
                logger.error(f"Failed to select all results for: {search_type}, skipping")
                continue
            
            # Check for cancellation before export
            if progress_callback(29+i*10, f"Exporting data for {search_type}...") is False:
                logger.info(f"Job cancelled before export for {search_type}")
                scraper.close()
                return result_files, None
            
            # Export to CSV
            if not scraper.export_to_csv(search_type):
                logger.error(f"Failed to export to CSV for: {search_type}, skipping")
                continue
            
            # Find the downloaded file
            prefix_map = {
                "Sales": "recentSaleExport",
                "For Sale": "forSaleExport",
                "For Rent": "forRentExport"
            }
            
            prefix = prefix_map.get(search_type)
            downloaded_files = [f for f in os.listdir(scraper.download_dir) if f.startswith(prefix)]
            
            if downloaded_files:
                result_files[search_type] = os.path.join(scraper.download_dir, downloaded_files[0])
                logger.info(f"Added file for {search_type}: {downloaded_files[0]}")
            
            # Return to dashboard for next search type (except for the last one)
            if search_type != search_types[-1]:
                # Check for cancellation before returning to dashboard
                if progress_callback(30+i*10, f"Preparing for next search type...") is False:
                    logger.info(f"Job cancelled after export for {search_type}")
                    scraper.close()
                    return result_files, None
                
                if not scraper.return_to_dashboard():
                    logger.error(f"Failed to return to dashboard after: {search_type}, aborting")
                    break
        
        progress_callback(43, "Downloaded all data from RPData...")

        # Return both the result files and the scraper instance
        # The scraper instance is needed to properly close the browser if cancellation occurs
        return result_files, scraper
    
    except Exception as e:
        logger.error(f"An error occurred during scraping: {e}")
        return result_files, scraper


if __name__ == "__main__":
    # Example usage
    locations = ["Hunters Hill NSW 2110", "Crows Nest NSW 2065"]
    property_types = ["Land"]  # ["Business", "Commercial"]
    min_floor = "Min"  # Can do a number (From 0 - 9999999999, 10 digit num is max, and min <= max otherwise error), or "Min"
    max_floor = "100"  # Can do a number, or "Max"
    
    result_files = scrape_rpdata(
        locations=locations,
        property_types=property_types,
        min_floor_area=min_floor,
        max_floor_area=max_floor,
        headless=False
    )
    
    logger.info("Scraping completed")
    logger.info(f"Result files: {result_files}")