#!/usr/bin/env python3
# Main script to run the RP Data scraper and merger
# Updated for Docker compatibility with improved logging

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
from clear_folders import clear_folders

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("rpdata_scraper.log")
    ]
)
logger = logging.getLogger(__name__)

def main(locations=None, property_types=None, min_floor_area="Min", max_floor_area="Max", 
         business_type=None, headless=False, progress_callback=None):
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
    
    Returns:
        str: Path to the merged Excel file, or None if the process failed
    """
    start_time = time.time()
    
    # Default progress reporting function if none provided
    if progress_callback is None:
        def progress_callback(percentage, message):
            logger.info(f"Progress: {percentage}% - {message}")
    
    progress_callback(1, "Initializing RP Data scraper...")

    # Check if we're running in Docker - if so, force headless mode
    is_docker = os.environ.get('RUNNING_IN_DOCKER', 'false').lower() == 'true'
    if is_docker and not headless:
        logger.info("Running in Docker, forcing headless mode")
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
    
    try:
        # First clear all files in the downloads/ and merged_properties/ directories
        progress_callback(5, "Clearing existing files...")
        logger.info("Clearing all folders...")
        clear_folders()

        # Step 1: Scrape RP Data
        logger.info("\n===== STEP 1: SCRAPING RP DATA =====\n")
        progress_callback(10, "Setting up scraper...")
        
        result_files = scrape_rpdata(
            locations=locations,
            property_types=property_types,
            min_floor_area=min_floor_area,
            max_floor_area=max_floor_area,
            headless=headless,
            progress_callback=progress_callback
        )
        
        if not result_files:
            logger.error("No files were downloaded during scraping")
            return 'No files downloaded'
        
        logger.info(f"Downloaded files: {result_files}")

        # Add delay to ensure files are completely written
        logger.info("Waiting 3 seconds for files to finalize...")
        time.sleep(3)  # 3 second delay
        
        # Step 2: Process and merge the Excel files
        logger.info("\n===== STEP 2: PROCESSING AND MERGING FILES =====\n")
        progress_callback(45, "Starting to process files into complete merged file...")

        success = process_excel_files(
            files_dict=result_files,
            locations=locations,
            property_types=property_types,
            min_floor=min_floor_area,
            max_floor=max_floor_area,
            business_type=business_type,
            headless=headless,
            progress_callback=progress_callback
        )
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.info(f"Total processing time: {elapsed_time:.2f} seconds")
        
        if success:
            # Get the name of the most recently created file in merged_properties
            merged_dir = "merged_properties"
            
            if os.path.exists(merged_dir) and os.listdir(merged_dir):
                files = os.listdir(merged_dir)
                if files:
                    # Sort by modification time (newest first)
                    files.sort(key=lambda x: os.path.getmtime(os.path.join(merged_dir, x)), reverse=True)
                    newest_file = os.path.join(merged_dir, files[0])
                    logger.info(f"Processing complete. Merged file saved to: {newest_file}")
                    
                    progress_callback(100, f"Processing complete! File saved as {os.path.basename(newest_file)}")
                    return merged_dir
            
            logger.info(f"Processing complete. Merged file saved to merged_properties directory.")
            return "merged_properties"
        else:
            logger.error("Failed to process and merge files")
            progress_callback(100, "Processing failed. Please check logs.")
            return None
    
    except Exception as e:
        logger.error(f"An error occurred in the main process: {e}")
        logger.error(traceback.format_exc())
        progress_callback(100, f"Error: {str(e)}")
        return None

# Function to allow testing this module directly
def test_main():
    """Run a test of the entire process with minimal data."""
    # Example usage with minimal data
    test_locations = ["Test Location"]
    property_types = ["Business", "Commercial"]
    min_floor = "Min"
    max_floor = "Max"
    business_type = "Vet"
    
    # Create directories if they don't exist
    os.makedirs("downloads", exist_ok=True)
    os.makedirs("merged_properties", exist_ok=True)
    
    # Run the main function in test mode
    print("Running main() function in test mode...")
    result = main(
        locations=test_locations, 
        property_types=property_types,
        min_floor_area=min_floor,
        max_floor_area=max_floor,
        business_type=business_type,
        headless=True
    )
    
    print(f"Test result: {result}")
    return result is not None

if __name__ == "__main__":
    # Use actual locations for a real run
    locations = ["Hunters Hill NSW 2110", "Crows Nest NSW 2065"]
    property_types = ["Business", "Commercial"]
    min_floor = "Min"
    max_floor = "1250"
    business_type = "Vet"
    headless = False
    
    # Create merged_properties directory if it doesn't exist
    os.makedirs("merged_properties", exist_ok=True)
    
    # Run the entire process
    output_location = main(
        locations=locations,
        property_types=property_types,
        min_floor_area=min_floor,
        max_floor_area=max_floor,
        business_type=business_type,
        headless=headless
    )
    
    if output_location:
        logger.info(f"Success! Output saved to: {output_location}")
    else:
        logger.error("Process completed with errors")