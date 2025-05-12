#!/usr/bin/env python3
# Main script for running RP Data scraper with proper milestone integration

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from setup_rpdata_scraper import RPDataScraper, logger


def scrape_rpdata(locations=None, property_types=None, min_floor_area="Min", max_floor_area="Max", 
                  headless=False, progress_callback=None, download_dir=None):
    """
    Scrape RP Data with integrated progress milestones.
    
    This function now works in harmony with main.py's milestone system,
    ensuring smooth progress reporting for all sub-steps within each search type.
    """
    if progress_callback is None:
        def progress_callback(percentage, message):
            pass
            return True
    
    if download_dir is None:
        download_dir = os.path.join(os.getcwd(), "downloads")
    
    os.makedirs(download_dir, exist_ok=True)
    
    if locations is None:
        locations = []
    if property_types is None:
        property_types = ["Business", "Commercial"]
    
    scraper = RPDataScraper(headless=headless, download_dir=download_dir)
    result_files = {}
    
    # Define progress milestones that match main.py exactly
    PROGRESS_MILESTONES = {
        'login_start': 8,
        'login_complete': 15,
        'rent_start': 20,
        'rent_complete': 45,
        'sale_start': 50,
        'sale_complete': 75,
        'sales_start': 78,
        'sales_complete': 90
    }
    
    # Define sub-steps within each search type (as percentages of the total range)
    SEARCH_SUBSTEPS = {
        'search_start': 0,      # Starting the search
        'locations_done': 0.25, # Locations searched
        'filters_done': 0.50,   # Filters applied
        'selection_done': 0.75, # Results selected
        'export_done': 1.0      # Export completed
    }
    
    try:
        # Check for early cancellation
        if progress_callback(5, "Preparing to log into RP Data...") is False:
            logger.info("Job cancelled before login")
            scraper.close()
            return {}, None
        
        # Added: Improved cancellation checking that doesn't interfere with progress
        def check_cancelled():
            # Pass None as message so it doesn't show in UI
            if progress_callback and progress_callback(0, None) is False:
                logger.info("Cancellation detected during operation")
                return True
            return False
        # Pass this check function to the scraper
        scraper.check_cancelled = check_cancelled

        # Login with progress updates
        if progress_callback(PROGRESS_MILESTONES['login_start'], "Logging into RP Data...") is False:
            logger.info("Job cancelled before login")
            scraper.close()
            return {}, None
            
        login_success = scraper.login("busihealth", "Busihealth123")
        if not login_success:
            logger.error("Login failed, aborting")
            scraper.close()
            return result_files, None
        
        if progress_callback(PROGRESS_MILESTONES['login_complete'], "Login successful. Preparing to search...") is False:
            logger.info("Job cancelled after login")
            scraper.close()
            return {}, None

        # Process each search type with detailed progress tracking
        search_types = ["For Rent", "For Sale", "Sales"]
        search_configs = [
            {
                'name': 'For Rent',
                'start_milestone': PROGRESS_MILESTONES['rent_start'],
                'end_milestone': PROGRESS_MILESTONES['rent_complete']
            },
            {
                'name': 'For Sale', 
                'start_milestone': PROGRESS_MILESTONES['sale_start'],
                'end_milestone': PROGRESS_MILESTONES['sale_complete']
            },
            {
                'name': 'Sales',
                'start_milestone': PROGRESS_MILESTONES['sales_start'], 
                'end_milestone': PROGRESS_MILESTONES['sales_complete']
            }
        ]

        for search_config in search_configs:
            search_type = search_config['name']
            start_percent = search_config['start_milestone']
            end_percent = search_config['end_milestone']
            
            # Calculate progress for this search type's sub-steps
            def calculate_progress(substep_key):
                """Calculate the actual progress percentage for a given substep"""
                substep_percent = SEARCH_SUBSTEPS[substep_key]
                actual_percent = start_percent + (end_percent - start_percent) * substep_percent
                return int(actual_percent)
            
            # Start this search type
            if progress_callback(calculate_progress('search_start'), f"Starting {search_type} search...") is False:
                logger.info(f"Job cancelled before {search_type} search")
                scraper.close()
                return result_files, None

            logger.info(f"\n===== STARTING SEARCH TYPE: {search_type} =====\n")

            if not scraper.select_search_type(search_type):
                logger.error(f"Failed to select search type: {search_type}, skipping")
                continue

            # Search locations with progress update
            if progress_callback(calculate_progress('locations_done'), f"Searching locations for {search_type}...") is False:
                logger.info(f"Job cancelled during {search_type} location search")
                scraper.close()
                return result_files, None

            if not scraper.search_locations(locations, search_type):
                logger.error(f"Failed to search locations for: {search_type}, skipping")
                continue

            # Apply filters with progress update
            if progress_callback(calculate_progress('filters_done'), f"Applying filters for {search_type}...") is False:
                logger.info(f"Job cancelled during {search_type} filters")
                scraper.close()
                return result_files, None

            if not scraper.apply_filters(property_types, min_floor_area, max_floor_area):
                logger.error(f"Failed to apply filters for: {search_type}, skipping")
                continue

            # Select results with progress update
            if progress_callback(calculate_progress('selection_done'), f"Selecting results for {search_type}...") is False:
                logger.info(f"Job cancelled after filter for {search_type}")
                scraper.close()
                return result_files, None

            if not scraper.select_all_results():
                logger.error(f"Failed to select all results for: {search_type}, skipping")
                continue

            # Export data with progress update
            if progress_callback(calculate_progress('export_done'), f"Exporting {search_type} data...") is False:
                logger.info(f"Job cancelled before export for {search_type}")
                scraper.close()
                return result_files, None

            if not scraper.export_to_csv(search_type):
                logger.error(f"Failed to export to CSV for: {search_type}, skipping")
                continue

            # Check for downloaded files
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

            # Return to dashboard for next search (if not the last one)
            if search_type != search_types[-1]:
                if not scraper.return_to_dashboard():
                    logger.error(f"Failed to return to dashboard after: {search_type}, aborting")
                    break
        
        # All searches completed
        progress_callback(PROGRESS_MILESTONES['sales_complete'], "All RPData downloads completed.")
        return result_files, scraper

    except Exception as e:
        logger.error(f"An error occurred during scraping: {e}")
        import traceback
        logger.error(traceback.format_exc())
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