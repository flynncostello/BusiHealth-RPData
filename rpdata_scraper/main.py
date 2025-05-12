#!/usr/bin/env python3
# Main script to run the RP Data scraper and merger
# Clean implementation with robust progress synchronization and race condition prevention

import os
import sys
import logging
import time
import traceback
import threading

# Add package to path if needed
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Import required modules from the package
from scraper.scrape_rpdata import scrape_rpdata
from merge_excel import process_excel_files

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Thread-local storage for progress synchronization
_progress_state = threading.local()

def get_progress_state():
    """Get thread-local progress state, initializing if needed."""
    if not hasattr(_progress_state, 'last_percentage'):
        _progress_state.last_percentage = 0
        _progress_state.last_update_time = time.time()
        _progress_state.lock = threading.Lock()
    return _progress_state

def main(locations=None, property_types=None, min_floor_area="Min", max_floor_area="Max", 
         business_type=None, headless=False, progress_callback=None, is_cancelled=None,
         download_dir=None, output_dir=None):
    """
    Main function to scrape RP Data and process the results.
    
    This function coordinates between scraping and merging phases with clean
    cancellation checking and robust progress reporting that prevents race conditions.
    
    Args:
        locations (list): List of locations to search
        property_types (list): List of property types to filter for
        min_floor_area (str): Minimum floor area
        max_floor_area (str): Maximum floor area
        business_type (str): Type of business to search for (either Vet or Health)
        headless (bool): Whether to run in headless mode
        progress_callback (function): Function to report progress updates
        is_cancelled (function): Function that returns True if job should be cancelled
        download_dir (str): Job-specific directory for downloads
        output_dir (str): Job-specific directory for output files
    
    Returns:
        str: Path to the merged Excel file, or None if the process failed
    """
    start_time = time.time()
    
    # Initialize progress state for this thread
    progress_state = get_progress_state()
    
    # Default functions if none provided
    if progress_callback is None:
        def progress_callback(percentage, message):
            logger.info(f"Progress: {percentage}% - {message}")
            return True
    
    if is_cancelled is None:
        def is_cancelled():
            return False
    
    # Define progress milestones that align with scrape_rpdata.py and app.py
    PROGRESS_MILESTONES = {
        'start': 5,
        'login_start': 8,
        'login_complete': 15,
        'rent_start': 20,
        'rent_complete': 45,
        'sale_start': 50,
        'sale_complete': 75,
        'sales_start': 78,
        'sales_complete': 90,
        'merge_start': 92,
        'merge_complete': 95,  # Reduced to allow time for verification
        'file_verification': 97,
        'file_ready': 100
    }
    
    # Wrapper for progress callback with race condition prevention
    def safe_progress_callback(percentage, message):
        """Progress callback wrapper that prevents backwards progress and race conditions."""
        if message is None or (message and 'cancel' in message.lower()):
            # Still do the cancellation check even for skipped messages
            return not is_cancelled()
        
        try:
            with progress_state.lock:
                # Prevent backwards progress (with small tolerance for accuracy)
                current_time = time.time()
                if isinstance(percentage, (int, float)):
                    if percentage < progress_state.last_percentage - 2:
                        logger.debug(f"Prevented backwards progress: {progress_state.last_percentage} -> {percentage}")
                        percentage = progress_state.last_percentage
                    
                    # Rate limiting: don't update more than once per 100ms for same percentage
                    if (percentage == progress_state.last_percentage and 
                        current_time - progress_state.last_update_time < 0.1):
                        return not is_cancelled()
                    
                    progress_state.last_percentage = percentage
                    progress_state.last_update_time = current_time
            
            # Call the actual progress callback
            return progress_callback(percentage, message)
            
        except Exception as e:
            logger.error(f"Error in safe_progress_callback: {e}")
            return not is_cancelled()
    
    try:
        # Initial progress and cancellation check
        if safe_progress_callback(PROGRESS_MILESTONES['start'], "Initializing RP Data scraper...") is False:
            logger.info("Job cancelled before starting")
            return None

        # Set up directories
        if download_dir is None:
            download_dir = "downloads"
        if output_dir is None:
            output_dir = "merged_properties"
            
        os.makedirs(download_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

        # Handle Azure environment
        is_azure = os.environ.get('WEBSITE_SITE_NAME') is not None
        if is_azure and not headless:
            logger.info("Running in Azure App Service, forcing headless mode")
            headless = True

        # Default values
        if locations is None:
            locations = []
        if property_types is None:
            property_types = ["Business", "Commercial"]
        if business_type is None:
            business_type = "Vet"
        
        # Log parameters
        logger.info("===== RP DATA SCRAPER AND PROCESSOR =====")
        logger.info(f"Locations: {locations}")
        logger.info(f"Property Types: {property_types}")
        logger.info(f"Floor Area: {min_floor_area} - {max_floor_area}")
        logger.info(f"Business Type: {business_type}")
        logger.info(f"Headless Mode: {headless}")
        
        # Check cancellation before starting scraping
        if is_cancelled():
            logger.info("Job cancelled before scraping")
            return None
        
        # Step 1: Scrape the data
        logger.info("\n===== STEP 1: SCRAPING DATA FROM RP DATA =====\n")
        
        # Create a progress callback for scraping that maps to our milestones
        def scraping_progress_callback(percentage, message):
            """Map scraping progress to our milestone range (5-90%)."""
            if message is None:
                return not is_cancelled()
            
            # The scraping process covers milestones from start to sales_complete
            # Map the scraper's internal progress to this range
            if percentage < PROGRESS_MILESTONES['login_start']:
                actual_percentage = PROGRESS_MILESTONES['start']
            elif percentage >= PROGRESS_MILESTONES['sales_complete']:
                actual_percentage = PROGRESS_MILESTONES['sales_complete']
            else:
                actual_percentage = percentage
            
            return safe_progress_callback(actual_percentage, message)
        
        result_files, global_scraper = scrape_rpdata(
            locations=locations,
            property_types=property_types,
            min_floor_area=min_floor_area,
            max_floor_area=max_floor_area,
            headless=headless,
            progress_callback=scraping_progress_callback,
            is_cancelled=is_cancelled,
            download_dir=download_dir
        )
        
        # Check cancellation after scraping
        if is_cancelled() or safe_progress_callback(PROGRESS_MILESTONES['sales_complete'], "Scraping completed, preparing to merge files...") is False:
            logger.info("Job cancelled after scraping")
            if global_scraper:
                try:
                    global_scraper.close()
                except Exception as e:
                    logger.warning(f"Error closing scraper on cancellation: {e}")
            return None
        
        if not result_files:
            logger.error("No files were downloaded during scraping")
            return 'No files downloaded'
        
        logger.info(f"Downloaded files: {result_files}")

        # Wait for files to finalize
        logger.info("Waiting for files to finalize...")
        time.sleep(3)
        
        # Check cancellation before merging
        if is_cancelled() or safe_progress_callback(PROGRESS_MILESTONES['merge_start'], "Starting merge process...") is False:
            logger.info("Job cancelled before merging")
            return None
        
        # Step 2: Process and merge the Excel files
        logger.info("\n===== STEP 2: PROCESSING AND MERGING FILES =====\n")
        
        # Create merge progress callback that maps to the remaining range (92-95%)
        def merge_progress_callback(percentage, message):
            """Map merge progress to our milestones (92-95% range)"""
            if message is None:
                return not is_cancelled()
            
            # Map percentage to merge range
            merge_range_start = PROGRESS_MILESTONES['merge_start']
            merge_range_end = PROGRESS_MILESTONES['merge_complete']
            
            # Calculate actual percentage within our milestone range
            actual_percentage = merge_range_start + \
                (percentage / 100) * (merge_range_end - merge_range_start)
            
            return safe_progress_callback(int(actual_percentage), message)
        
        # Process and merge files
        success = process_excel_files(
            files_dict=result_files,
            locations=locations,
            property_types=property_types,
            min_floor=min_floor_area,
            max_floor=max_floor_area,
            business_type=business_type,
            headless=headless,
            progress_callback=merge_progress_callback,
            output_dir=output_dir
        )
        
        # Final cancellation check
        if is_cancelled() or safe_progress_callback(PROGRESS_MILESTONES['merge_complete'], "Processing complete, preparing final file...") is False:
            logger.info("Job cancelled at final stage")
            return None
        
        # Log completion time
        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.info(f"Total processing time: {elapsed_time:.2f} seconds")
        
        if success:
            logger.info(f"Processing complete. Files saved to: {output_dir}")
            
            # Note: File verification will be handled by app.py
            # We don't update progress to 100% here to allow app.py to handle verification
            return output_dir
        else:
            logger.error("Failed to process and merge files")
            safe_progress_callback(100, "Processing failed. Please check logs.")
            return None
    
    except Exception as e:
        logger.error(f"An error occurred in the main process: {e}")
        logger.error(traceback.format_exc())
        safe_progress_callback(100, f"Error: {str(e)}")
        return None
    finally:
        # Ensure browser is closed
        if 'global_scraper' in locals() and global_scraper:
            try:
                global_scraper.close()
                logger.info("Closed global scraper instance")
            except Exception as e:
                logger.warning(f"Error closing global scraper: {e}")


# Function to allow testing this module directly
def test_main():
    """Run a test of the entire process with minimal data."""
    test_locations = ["Test Location"]
    property_types = ["Business", "Commercial"]
    min_floor = "Min"
    max_floor = "Max"
    business_type = "Vet"
    
    # Create job-specific directories for test
    test_job_id = "test_job"
    test_download_dir = os.path.join("downloads", test_job_id)
    test_output_dir = os.path.join("merged_properties", test_job_id)
    
    os.makedirs(test_download_dir, exist_ok=True)
    os.makedirs(test_output_dir, exist_ok=True)
    
    print("Running main() function in test mode...")
    result = main(
        locations=test_locations, 
        property_types=property_types,
        min_floor_area=min_floor,
        max_floor_area=max_floor,
        business_type=business_type,
        headless=True,
        download_dir=test_download_dir,
        output_dir=test_output_dir
    )
    
    print(f"Test result: {result}")
    return result is not None


if __name__ == "__main__":
    # Generate test directories
    test_job_id = f"test_{int(time.time())}"
    test_download_dir = os.path.join("downloads", test_job_id) 
    test_output_dir = os.path.join("merged_properties", test_job_id)
    
    os.makedirs(test_download_dir, exist_ok=True)
    os.makedirs(test_output_dir, exist_ok=True)
    
    # Test with real locations
    locations = ["Hunters Hill NSW 2110", "Crows Nest NSW 2065"]
    property_types = ["Business", "Commercial"]
    min_floor = "Min"
    max_floor = "1250"
    business_type = "Vet"
    headless = True
    
    output_location = main(
        locations=locations,
        property_types=property_types,
        min_floor_area=min_floor,
        max_floor_area=max_floor,
        business_type=business_type,
        headless=headless,
        download_dir=test_download_dir,
        output_dir=test_output_dir
    )
    
    if output_location:
        logger.info(f"Success! Output saved to: {output_location}")
    else:
        logger.error("Process completed with errors")