#!/usr/bin/env python3
# Main script to run the RP Data scraper and merger
# Updated to support job-specific directories for multi-user isolation

import os
import sys
import logging
import time
import traceback

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

def main(locations=None, property_types=None, min_floor_area="Min", max_floor_area="Max", 
         business_type=None, headless=False, progress_callback=None, 
         download_dir=None, output_dir=None):
    """
    Main function to scrape RP Data and process the results.
    
    Args:
        locations (list): List of locations to search
        property_types (list): List of property types to filter for
        min_floor_area (str): Minimum floor area
        max_floor_area (str): Maximum floor area
        business_type (str): Type of business to search for (either Vet or Health)
        headless (bool): Whether to run in headless mode
        progress_callback (function): Optional callback function for progress updates
        download_dir (str): Job-specific directory for downloads
        output_dir (str): Job-specific directory for output files
    
    Returns:
        str: Path to the merged Excel file, or None if the process failed
    """
    start_time = time.time()
    
    # Default progress reporting function if none provided
    if progress_callback is None:
        def progress_callback(percentage, message):
            logger.info(f"Progress: {percentage}% - {message}")
            return True  # Always continue
    
    # Define progress milestones that align with app.py
    PROGRESS_MILESTONES = {
        'login_start': 8,
        'login_complete': 15,
        'rent_start': 20,
        'rent_complete': 45,
        'sale_start': 50,
        'sale_complete': 75,
        'sales_start': 78,
        'sales_complete': 90,
        'merge_start': 92,
        'merge_complete': 98
    }
    
    try:
        # Check for early cancellation
        if progress_callback(5, "Initializing RP Data scraper...") is False:
            logger.info("Job cancelled before starting")
            return None

        # Default download directory if not specified
        if download_dir is None:
            download_dir = "downloads"
        
        # Default output directory if not specified
        if output_dir is None:
            output_dir = "merged_properties"
            
        # Ensure directories exist
        os.makedirs(download_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

        # Check if we're running in Azure App Service - if so, force headless mode
        is_azure = os.environ.get('WEBSITE_SITE_NAME') is not None
        if is_azure and not headless:
            logger.info("Running in Azure App Service, forcing headless mode")
            headless = True

        # Use default values if parameters are None
        if locations is None:
            locations = []
        
        if property_types is None:
            property_types = ["Business", "Commercial"]
        
        if business_type is None:
            business_type = "Vet"  # Default to Vet if not specified
        
        # Log the parameters
        logger.info("===== RP DATA SCRAPER AND PROCESSOR =====")
        logger.info(f"Locations: {locations}")
        logger.info(f"Property Types: {property_types}")
        logger.info(f"Floor Area: {min_floor_area} - {max_floor_area}")
        logger.info(f"Business Type: {business_type}")
        logger.info(f"Headless Mode: {headless}")
        logger.info(f"Download Directory: {download_dir}")
        logger.info(f"Output Directory: {output_dir}")
        
        # Create enhanced progress callback for scraping phase
        def scraping_progress_callback(percentage, message):
            # Map scraper progress to our milestones
            if 'login' in message.lower():
                if 'starting' in message.lower() or 'logging' in message.lower():
                    actual_percentage = PROGRESS_MILESTONES['login_start']
                else:
                    # Scale login progress between start and complete
                    actual_percentage = PROGRESS_MILESTONES['login_start'] + \
                        (percentage / 100) * (PROGRESS_MILESTONES['login_complete'] - PROGRESS_MILESTONES['login_start'])
            elif 'for rent' in message.lower():
                if 'starting' in message.lower():
                    actual_percentage = PROGRESS_MILESTONES['rent_start']
                else:
                    # Scale rent progress between start and complete
                    actual_percentage = PROGRESS_MILESTONES['rent_start'] + \
                        (percentage / 100) * (PROGRESS_MILESTONES['rent_complete'] - PROGRESS_MILESTONES['rent_start'])
            elif 'for sale' in message.lower():
                if 'starting' in message.lower():
                    actual_percentage = PROGRESS_MILESTONES['sale_start']
                else:
                    # Scale sale progress between start and complete
                    actual_percentage = PROGRESS_MILESTONES['sale_start'] + \
                        (percentage / 100) * (PROGRESS_MILESTONES['sale_complete'] - PROGRESS_MILESTONES['sale_start'])
            elif 'sales' in message.lower():
                if 'starting' in message.lower():
                    actual_percentage = PROGRESS_MILESTONES['sales_start']
                else:
                    # Scale sales progress between start and complete
                    actual_percentage = PROGRESS_MILESTONES['sales_start'] + \
                        (percentage / 100) * (PROGRESS_MILESTONES['sales_complete'] - PROGRESS_MILESTONES['sales_start'])
            else:
                # For other messages, distribute remaining percentage
                actual_percentage = max(percentage, 8)  # Never go below login start
            
            return progress_callback(int(actual_percentage), message)
        
        # Step 1: Scrape the data
        logger.info("\n===== STEP 1: SCRAPING DATA FROM RP DATA =====\n")
        result_files, global_scraper = scrape_rpdata(
            locations=locations,
            property_types=property_types,
            min_floor_area=min_floor_area,
            max_floor_area=max_floor_area,
            headless=headless,
            progress_callback=scraping_progress_callback,
            download_dir=download_dir
        )
        
        # Check for cancellation after scraping
        if progress_callback(PROGRESS_MILESTONES['sales_complete'], "Scraping completed, preparing to merge files...") is False:
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

        # Add delay to ensure files are completely written
        logger.info("Waiting for files to finalize...")
        time.sleep(3)  # 3 second delay
        
        # Check for cancellation again
        if progress_callback(PROGRESS_MILESTONES['merge_start'], "Starting merge process...") is False:
            logger.info("Job cancelled before merging")
            return None
        
        # Step 2: Process and merge the Excel files
        logger.info("\n===== STEP 2: PROCESSING AND MERGING FILES =====\n")
        
        # Create enhanced progress callback for merge phase
        def merge_progress_callback(percentage, message):
            # Map merge progress to our milestones
            actual_percentage = PROGRESS_MILESTONES['merge_start'] + \
                (percentage / 100) * (PROGRESS_MILESTONES['merge_complete'] - PROGRESS_MILESTONES['merge_start'])
            return progress_callback(int(actual_percentage), message)
        
        from merge_excel import process_excel_files
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
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.info(f"Total processing time: {elapsed_time:.2f} seconds")
        
        # Final cancellation check
        if progress_callback(98, "Processing complete, preparing final file...") is False:
            logger.info("Job cancelled at final stage")
            return None
        
        if success:
            # Return the output directory for further processing in app.py
            logger.info(f"Processing complete. Files saved to: {output_dir}")
            return output_dir
        else:
            logger.error("Failed to process and merge files")
            progress_callback(100, "Processing failed. Please check logs.")
            return None
    
    except Exception as e:
        logger.error(f"An error occurred in the main process: {e}")
        logger.error(traceback.format_exc())
        progress_callback(100, f"Error: {str(e)}")
        return None
    finally:
        # Ensure browser is closed if we have a global scraper instance
        if 'global_scraper' in locals() and global_scraper:
            try:
                global_scraper.close()
                logger.info("Closed global scraper instance in finally block")
            except Exception as e:
                logger.warning(f"Error closing global scraper in finally block: {e}")

# Function to allow testing this module directly
def test_main():
    """Run a test of the entire process with minimal data."""
    # Example usage with minimal data
    test_locations = ["Test Location"]
    property_types = ["Business", "Commercial"]
    min_floor = "Min"
    max_floor = "Max"
    business_type = "Vet"
    
    # Create job-specific directories for test
    test_job_id = "test_job"
    test_download_dir = os.path.join("downloads", test_job_id)
    test_output_dir = os.path.join("merged_properties", test_job_id)
    
    # Create directories
    os.makedirs(test_download_dir, exist_ok=True)
    os.makedirs(test_output_dir, exist_ok=True)
    
    # Run the main function with job-specific directories
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
    # Generate a test job ID
    test_job_id = f"test_{int(time.time())}"
    test_download_dir = os.path.join("downloads", test_job_id) 
    test_output_dir = os.path.join("merged_properties", test_job_id)
    
    # Create the job directories
    os.makedirs(test_download_dir, exist_ok=True)
    os.makedirs(test_output_dir, exist_ok=True)
    
    # Use actual locations for a real run
    locations = ["Hunters Hill NSW 2110", "Crows Nest NSW 2065"]
    property_types = ["Business", "Commercial"]
    min_floor = "Min"
    max_floor = "1250"
    business_type = "Vet"
    headless = True
    
    # Run the entire process with job-specific directories
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