#!/usr/bin/env python3
# Main script for running RP Data scraper

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from setup_rpdata_scraper import RPDataScraper, logger

def scrape_rpdata(locations=None, property_types=None, min_floor_area="Min", max_floor_area="Max", headless=False, progress_callback=None):
    """
    Scrape property data from RP Data.
    
    Args:
        locations (list): List of locations to search
        property_types (list): List of property types to filter for
        min_floor_area (str): Minimum floor area
        max_floor_area (str): Maximum floor area
        headless (bool): Whether to run in headless mode
    
    Returns:
        dict: Dictionary with file paths for each search type
    """
    # Default progress reporting function if none provided
    if progress_callback is None:
        def progress_callback(percentage, message):
            pass  # No-op if no callback provided
    if locations is None:
        locations = []
    
    if property_types is None:
        property_types = ["Business", "Commercial"]
    
    scraper = RPDataScraper(headless=headless)
    result_files = {}
    
    try:
        progress_callback(15, "Logging into RP Data...")

        # Login
        login_success = scraper.login("busihealth", "Busihealth123")
        if not login_success:
            logger.error("Login failed, aborting")
            scraper.close()
            return result_files
        
        
        # Process each search type
        search_types = ["For Rent", "For Sale", "Sales"]

        progress_callback(16, "Getting each search type data from RP Data...")


        i = 0
        for search_type in search_types:
            progress_callback(20+i*10, f"Getting results for {search_type} data...")
            i += 1

            logger.info(f"\n===== STARTING SEARCH TYPE: {search_type} =====\n")
            
            # Select search type
            if not scraper.select_search_type(search_type):
                logger.error(f"Failed to select search type: {search_type}, skipping")
                continue
            
            # Search for locations
            if not scraper.search_locations(locations):
                logger.error(f"Failed to search locations for: {search_type}, skipping")
                continue
            
            # Apply filters
            if not scraper.apply_filters(property_types, min_floor_area, max_floor_area):
                logger.error(f"Failed to apply filters for: {search_type}, skipping")
                continue
            
            # Select all results
            if not scraper.select_all_results():
                logger.error(f"Failed to select all results for: {search_type}, skipping")
                continue
            
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
                if not scraper.return_to_dashboard():
                    logger.error(f"Failed to return to dashboard after: {search_type}, aborting")
                    break
        
        progress_callback(43, "Downloaded all data from RPData...")

        return result_files
    
    except Exception as e:
        logger.error(f"An error occurred during scraping: {e}")
        return result_files
    finally:
        scraper.close()


if __name__ == "__main__":
    # Example usage
    locations = ["Hunters Hill NSW 2110", "Crows Nest NSW 2065"]
    property_types = ["Land"]#["Business", "Commercial"]
    min_floor = "Min" # Can do a number (From 0 - 9999999999, 10 digit num is max, and min <= max otherwise error), or "Min"
    max_floor = "100" # Can do a number, or "Max"
    
    result_files = scrape_rpdata(
        locations=locations,
        property_types=property_types,
        min_floor_area=min_floor,
        max_floor_area=max_floor,
        headless=False
    )
    
    logger.info("Scraping completed")
    logger.info(f"Result files: {result_files}")