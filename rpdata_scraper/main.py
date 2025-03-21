#!/usr/bin/env python3
# Main script to run the RP Data scraper and merger
# pip install selenium undetected-chromedriver pandas openpyxl webdriver-manager

'''
Overall Workflow of RPData Site Scraper:
1) main.py runs taking in input
2) scrape_rpdata.py scrapes RP Data and downloads files (utilises setup_rpdata_scraper.py and rpdata_base.py to do this)
3) merge_excel.py runs
    a) get_image_and_agent_phone.py runs to get the images and agent phones
    b) lanchecker.py runs to get zoning data
    c) check_zoning.py runs to check if each property has allowable use in the zone (uses 'Allowable Use in the Zone - TABLE.xlsx')
    d) merge_excel_files.py finishes running and merged all 3 files into one
4) Finaly merged file saved (final merged file is in perfect format for data entry from other sources such as realcommercial.com)

* TAKES ROUGHLY 5 MINS ALL UP *
'''

import os
import logging
import time

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from scraper.scrape_rpdata import scrape_rpdata
from merge_excel import process_excel_files
from clear_folders import clear_folders

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main(locations=None, property_types=None, min_floor_area="Min", max_floor_area="Max", business_type=None, headless=False, progress_callback=None):
    """
    Main function to scrape RP Data and process the results.
    
    Args:
        locations (list): List of locations to search
        property_types (list): List of property types to filter for
        min_floor_area (str): Minimum floor area
        max_floor_area (str): Maximum floor area
        business_type (str): Type of business to search for (either Vet or Health)
        headless (bool): Whether to run in headless mode
        progress_callback (function): Optional callback for progress updates
    
    Returns:
        str: Path to the merged Excel file, or None if the process failed
    """
    # Default progress reporting function if none provided
    if progress_callback is None:
        def progress_callback(percentage, message):
            pass  # No-op if no callback provided
    progress_callback(10, "Starting RP Data scraper...")

    # First clear all files in the downloads/ and merged_properties/ directories
    print("\nCLEARING ALL FOLDERS\n")
    clear_folders()

    if locations is None:
        locations = []
    
    if property_types is None:
        property_types = ["Business", "Commercial"]
    
    logger.info("===== RP DATA SCRAPER AND PROCESSOR =====")
    logger.info(f"Locations: {locations}")
    logger.info(f"Property Types: {property_types}")
    logger.info(f"Floor Area: {min_floor_area} - {max_floor_area}")
    
    try:
        # Step 1: Scrape RP Data
        logger.info("\n===== STEP 1: SCRAPING RP DATA =====\n")
        progress_callback(13, "Setting up scraper...")
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
            return None
        

        logger.info(f"Downloaded files: {result_files}")

        # Add delay to ensure files are completely written
        import time
        logger.info("Waiting 3 seconds for files to finalize...")
        time.sleep(3)  # 3 second delay
        
        # Step 2: Process and merge the Excel files
        logger.info("\n===== STEP 2: PROCESSING AND MERGING FILES =====\n")
        
        # Now pass parameters to process_excel_files for proper filename generation
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
        
        if success:
            # Since the output file is now dynamically named and stored in merged_properties directory,
            # we need to specify the directory in the success message
            logger.info(f"Processing complete. Merged file saved to merged_properties directory.")
            # Return the directory where files are saved
            return "merged_properties"
        else:
            logger.error("Failed to process and merge files")
            return None
    
    except Exception as e:
        logger.error(f"An error occurred in the main process: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

if __name__ == "__main__":
    start_time = time.time()

    # Example usage - modify these parameters as needed
    locations = ["Hunters Hill NSW 2110", "Crows Nest NSW 2065"]#, "Drummoyne NSW 2047"]
    property_types = ["Business", "Commercial"]
    min_floor = "Min"
    max_floor = "1250"
    business_type = "Vet" # Either Vet or Health
    headless = False # True means we can't see the browser, False means we can see the browser
    '''
    Acceptable Values for Min and Max Floor Area:
    Min: "Min", "100", "200", "300", "400", "500", "600", "700", "800", "900", "1000", "1250", "1500", "1750", "2000"
    Max: "Max", "100", "200", "300", "400", "500", "600", "700", "800", "900", "1000", "1250", "1500", "1750", "2000"
    '''
    
    # Create merged_properties directory if it doesn't exist
    os.makedirs("merged_properties", exist_ok=True)
    
    #############################
    ### RUNNING ENTIRE THING ###
    #############################
    output_location = main(
        locations=locations,
        property_types=property_types,
        min_floor_area=min_floor,
        max_floor_area=max_floor,
        business_type=business_type,
        headless=headless  # Set to True for headless mode
    )
    #############################
    
    if output_location:
        logger.info(f"Success! Output saved to: {output_location}")
    else:
        logger.error("Process completed with errors")
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    logger.info(f"\nTotal time taken: {elapsed_time:.2f} seconds")

