#!/usr/bin/env python3
# Main script for running RP Data scraper
# Clean implementation with consistent progress flow and robust cancellation

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from setup_rpdata_scraper import RPDataScraper, logger


def scrape_rpdata(locations=None, property_types=None, min_floor_area="Min", max_floor_area="Max", 
                  headless=False, progress_callback=None, is_cancelled=None, download_dir=None):
    """
    Scrape RP Data with consistent progress reporting and robust cancellation checking.
    
    This function handles all the detailed scraping work with frequent cancellation
    checks and smooth progress updates that align perfectly with the overall job milestones.
    
    The progress flow is designed to be strictly monotonic (always increasing) to prevent
    race conditions with the UI progress bar.
    
    Args:
        locations: List of locations to search
        property_types: List of property types to filter for
        min_floor_area: Minimum floor area requirement
        max_floor_area: Maximum floor area requirement  
        headless: Whether to run browser in headless mode
        progress_callback: Function to report progress (percentage, message)
        is_cancelled: Function that returns True if job should be cancelled
        download_dir: Directory to save downloaded files
    
    Returns:
        Tuple of (result_files dict, scraper instance) or (empty dict, None) if cancelled
    """
    # Default functions if none provided
    if progress_callback is None:
        def progress_callback(percentage, message):
            pass
            return True
    
    if is_cancelled is None:
        def is_cancelled():
            return False
    
    # Set up download directory
    if download_dir is None:
        download_dir = os.path.join(os.getcwd(), "downloads")
    os.makedirs(download_dir, exist_ok=True)
    
    # Default values
    if locations is None:
        locations = []
    if property_types is None:
        property_types = ["Business", "Commercial"]
    
    scraper = None
    result_files = {}
    
    # Define exact progress milestones that match main.py and app.py
    PROGRESS_MILESTONES = {
        'start': 5,
        'login_start': 8,
        'login_complete': 15,
        'rent_start': 20,
        'rent_complete': 45,
        'sale_start': 50,
        'sale_complete': 75,
        'sales_start': 78,
        'sales_complete': 90
    }
    
    # Define sub-steps within each search type as absolute percentages
    # This ensures monotonic progress without any backwards movement
    def get_search_milestones(search_type):
        """Get absolute progress milestones for a specific search type."""
        if search_type == 'For Rent':
            return {
                'start': PROGRESS_MILESTONES['rent_start'],
                'locations': PROGRESS_MILESTONES['rent_start'] + 5,    # 25%
                'filters': PROGRESS_MILESTONES['rent_start'] + 10,     # 30%
                'selection': PROGRESS_MILESTONES['rent_start'] + 15,   # 35%
                'export': PROGRESS_MILESTONES['rent_complete']         # 45%
            }
        elif search_type == 'For Sale':
            return {
                'start': PROGRESS_MILESTONES['sale_start'],
                'locations': PROGRESS_MILESTONES['sale_start'] + 5,    # 55%
                'filters': PROGRESS_MILESTONES['sale_start'] + 10,     # 60%
                'selection': PROGRESS_MILESTONES['sale_start'] + 15,   # 65%
                'export': PROGRESS_MILESTONES['sale_complete']         # 75%
            }
        elif search_type == 'Sales':
            return {
                'start': PROGRESS_MILESTONES['sales_start'],
                'locations': PROGRESS_MILESTONES['sales_start'] + 3,   # 81%
                'filters': PROGRESS_MILESTONES['sales_start'] + 6,     # 84%
                'selection': PROGRESS_MILESTONES['sales_start'] + 9,   # 87%
                'export': PROGRESS_MILESTONES['sales_complete']        # 90%
            }
        else:
            # Fallback for any other search type
            return {
                'start': 0,
                'locations': 25,
                'filters': 50,
                'selection': 75,
                'export': 100
            }
    
    try:
        # Check cancellation at the very start
        if is_cancelled():
            logger.info("Job cancelled before starting scraper")
            return {}, None
        
        # Progress update - login start
        if progress_callback(PROGRESS_MILESTONES['login_start'], "Logging into RP Data...") is False:
            logger.info("Job cancelled before login")
            return {}, None
        
        # Initialize scraper
        scraper = RPDataScraper(headless=headless, download_dir=download_dir)
        
        # Attempt login
        login_success = scraper.login("busihealth", "Busihealth123")
        if not login_success:
            logger.error("Login failed, aborting")
            scraper.close()
            return result_files, None
        
        # Check cancellation after login
        if is_cancelled() or progress_callback(PROGRESS_MILESTONES['login_complete'], "Login successful. Preparing to search...") is False:
            logger.info("Job cancelled after login")
            scraper.close()
            return {}, None

        # Define search configurations in order
        search_configs = [
            {'name': 'For Rent'},
            {'name': 'For Sale'}, 
            {'name': 'Sales'}
        ]

        # Process each search type
        for search_config in search_configs:
            search_type = search_config['name']
            milestones = get_search_milestones(search_type)
            
            # Check cancellation before starting this search type
            if is_cancelled():
                logger.info(f"Job cancelled before {search_type} search")
                scraper.close()
                return result_files, None
            
            # Start this search type - progress update
            if progress_callback(milestones['start'], f"Starting {search_type} search...") is False:
                logger.info(f"Job cancelled before {search_type} search")
                scraper.close()
                return result_files, None

            logger.info(f"\n===== STARTING SEARCH TYPE: {search_type} =====\n")

            # Select search type
            if not scraper.select_search_type(search_type):
                logger.error(f"Failed to select search type: {search_type}, skipping")
                continue

            # Check cancellation after selection
            if is_cancelled():
                logger.info(f"Job cancelled after selecting {search_type}")
                scraper.close()
                return result_files, None

            # Search locations with progress update
            if progress_callback(milestones['locations'], f"Searching locations for {search_type}...") is False:
                logger.info(f"Job cancelled during {search_type} location search")
                scraper.close()
                return result_files, None

            if not scraper.search_locations(locations, search_type):
                logger.error(f"Failed to search locations for: {search_type}, skipping")
                continue

            # Check cancellation after locations
            if is_cancelled():
                logger.info(f"Job cancelled after locations for {search_type}")
                scraper.close()
                return result_files, None

            # Apply filters with progress update
            if progress_callback(milestones['filters'], f"Applying filters for {search_type}...") is False:
                logger.info(f"Job cancelled during {search_type} filters")
                scraper.close()
                return result_files, None

            if not scraper.apply_filters(property_types, min_floor_area, max_floor_area):
                logger.error(f"Failed to apply filters for: {search_type}, skipping")
                continue

            # Check cancellation after filters
            if is_cancelled():
                logger.info(f"Job cancelled after filters for {search_type}")
                scraper.close()
                return result_files, None

            # Select results with progress update
            if progress_callback(milestones['selection'], f"Selecting results for {search_type}...") is False:
                logger.info(f"Job cancelled after filter for {search_type}")
                scraper.close()
                return result_files, None

            if not scraper.select_all_results():
                logger.error(f"Failed to select all results for: {search_type}, skipping")
                continue

            # Check cancellation after selection
            if is_cancelled():
                logger.info(f"Job cancelled after selection for {search_type}")
                scraper.close()
                return result_files, None

            # Export data with progress update
            if progress_callback(milestones['export'], f"Exporting {search_type} data...") is False:
                logger.info(f"Job cancelled before export for {search_type}")
                scraper.close()
                return result_files, None

            if not scraper.export_to_csv(search_type):
                logger.error(f"Failed to export to CSV for: {search_type}, skipping")
                continue

            # Check cancellation after export
            if is_cancelled():
                logger.info(f"Job cancelled after export for {search_type}")
                scraper.close()
                return result_files, None

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
            if search_type != 'Sales':  # Sales is the last search type
                if not scraper.return_to_dashboard():
                    logger.error(f"Failed to return to dashboard after: {search_type}, aborting")
                    break
        
        # Final check before completing
        if is_cancelled():
            logger.info("Job cancelled before final completion")
            scraper.close()
            return result_files, None
        
        # All searches completed - final progress update
        progress_callback(PROGRESS_MILESTONES['sales_complete'], "All RP Data downloads completed.")
        return result_files, scraper

    except Exception as e:
        logger.error(f"An error occurred during scraping: {e}")
        import traceback
        logger.error(traceback.format_exc())
        if scraper:
            scraper.close()
        return result_files, None


if __name__ == "__main__":
    # Test with example data
    locations = ["Hunters Hill NSW 2110", "Crows Nest NSW 2065"]
    property_types = ["Business", "Commercial"]
    min_floor = "Min"
    max_floor = "100"
    
    # Test progress callback
    def test_progress(percentage, message):
        print(f"Progress: {percentage}% - {message}")
        return True
    
    result_files, scraper = scrape_rpdata(
        locations=locations,
        property_types=property_types,
        min_floor_area=min_floor,
        max_floor_area=max_floor,
        headless=True,
        progress_callback=test_progress
    )
    
    if scraper:
        scraper.close()
    
    logger.info("Scraping completed")
    logger.info(f"Result files: {result_files}")