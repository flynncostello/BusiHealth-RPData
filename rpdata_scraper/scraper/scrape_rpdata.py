#!/usr/bin/env python3
# Main script for running RP Data scraper

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from setup_rpdata_scraper import RPDataScraper, logger

def scrape_rpdata(locations=None, property_types=None, min_floor_area="Min", max_floor_area="Max", 
                  headless=False, progress_callback=None, download_dir=None):
    if progress_callback is None:
        def progress_callback(percentage, message):
            pass
            return True
    
    # Add global progress protection to ensure values never decrease
    highest_percentage_seen = 0
    original_callback = progress_callback
    
    def protected_progress_callback(percentage, message):
        nonlocal highest_percentage_seen
        
        # Ensure progress never goes backwards
        if percentage > highest_percentage_seen:
            highest_percentage_seen = percentage
        else:
            # If a lower percentage is reported, use the highest we've seen
            percentage = highest_percentage_seen
            
        # Call the original callback with the adjusted percentage
        return original_callback(percentage, message)
    
    # Replace the callback with our protected version
    progress_callback = protected_progress_callback
    
    if download_dir is None:
        download_dir = os.path.join(os.getcwd(), "downloads")
    
    os.makedirs(download_dir, exist_ok=True)
    
    if locations is None:
        locations = []
    if property_types is None:
        property_types = ["Business", "Commercial"]
    
    scraper = RPDataScraper(headless=headless, download_dir=download_dir)
    result_files = {}
    
    try:
        if progress_callback(5, "Logging into RP Data...") is False:
            logger.info("Job cancelled before login")
            scraper.close()
            return {}, None

        login_success = scraper.login("busihealth", "Busihealth123")
        if not login_success:
            logger.error("Login failed, aborting")
            scraper.close()
            return result_files, None
        
        if progress_callback(12, "Login successful. Preparing to search...") is False:
            logger.info("Job cancelled after login")
            scraper.close()
            return {}, None

        search_types = ["For Rent", "For Sale", "Sales"]
        total_steps = len(search_types)
        
        # Calculate progress ranges
        base_progress = 10
        max_progress = 90
        progress_range = max_progress - base_progress
        progress_per_type = progress_range / total_steps

        for i, search_type in enumerate(search_types):
            # Calculate minimum progress for this search type
            current_progress_minimum = base_progress + i * progress_per_type
            
            # Create a step function for this search type that ensures progress
            # is always at least the minimum for this type
            def calculate_step(s, search_index=i, min_progress=current_progress_minimum):
                calculated_progress = base_progress + search_index * progress_per_type + s * (progress_per_type / 6)
                return int(max(min_progress, calculated_progress))

            if progress_callback(calculate_step(0), f"Starting {search_type}...") is False:
                logger.info(f"Job cancelled before {search_type} search")
                scraper.close()
                return result_files, None

            logger.info(f"\n===== STARTING SEARCH TYPE: {search_type} =====\n")

            if not scraper.select_search_type(search_type):
                logger.error(f"Failed to select search type: {search_type}, skipping")
                continue

            if progress_callback(calculate_step(1), f"Searching locations for {search_type}...") is False:
                logger.info(f"Job cancelled during {search_type} location search")
                scraper.close()
                return result_files, None

            if not scraper.search_locations(locations, search_type):
                logger.error(f"Failed to search locations for: {search_type}, skipping")
                continue

            if progress_callback(calculate_step(2), f"Applying filters for {search_type}...") is False:
                logger.info(f"Job cancelled during {search_type} filters")
                scraper.close()
                return result_files, None

            if not scraper.apply_filters(property_types, min_floor_area, max_floor_area):
                logger.error(f"Failed to apply filters for: {search_type}, skipping")
                continue

            if progress_callback(calculate_step(3), f"Selecting results for {search_type}...") is False:
                logger.info(f"Job cancelled after filter for {search_type}")
                scraper.close()
                return result_files, None

            if not scraper.select_all_results():
                logger.error(f"Failed to select all results for: {search_type}, skipping")
                continue

            if progress_callback(calculate_step(4), f"Exporting data for {search_type}...") is False:
                logger.info(f"Job cancelled before export for {search_type}")
                scraper.close()
                return result_files, None

            if not scraper.export_to_csv(search_type):
                logger.error(f"Failed to export to CSV for: {search_type}, skipping")
                continue

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

            if progress_callback(calculate_step(5), f"Finished {search_type} export.") is False:
                logger.info(f"Job cancelled after export for {search_type}")
                scraper.close()
                return result_files, None

            if search_type != search_types[-1]:
                if not scraper.return_to_dashboard():
                    logger.error(f"Failed to return to dashboard after: {search_type}, aborting")
                    break
        
        progress_callback(90, "All RPData downloads completed.")
        return result_files, scraper

    except Exception as e:
        logger.error(f"An error occurred during scraping: {e}")
        return result_files, scraper

if __name__ == "__main__":
    locations = ["Hunters Hill NSW 2110", "Crows Nest NSW 2065"]
    property_types = ["Land"]
    min_floor = "Min"
    max_floor = "100"
    
    result_files, _ = scrape_rpdata(
        locations=locations,
        property_types=property_types,
        min_floor_area=min_floor,
        max_floor_area=max_floor,
        headless=False
    )
    
    logger.info("Scraping completed")
    logger.info(f"Result files: {result_files}")