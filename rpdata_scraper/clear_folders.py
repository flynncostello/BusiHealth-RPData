#!/usr/bin/env python3
# Clear folders utility - updated to support both full clearing and job-specific clearing
import os
import shutil
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

def clear_folders(job_id=None):
    """
    Clears contents of the 'downloads' and 'merged_properties' folders.
    If job_id is provided, only clears the job-specific subdirectories.
    
    Args:
        job_id (str, optional): Specific job ID to clear. If None, clears all contents.
    """
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Get parent directory (one level up)
    parent_dir = os.path.dirname(script_dir)
    
    # Define the paths to the folders in the parent directory
    downloads_path = os.path.join(parent_dir, 'downloads')
    merged_properties_path = os.path.join(parent_dir, 'merged_properties')
    tmp_path = os.path.join(parent_dir, 'tmp')
    
    folders_to_clear = [downloads_path, merged_properties_path]
    
    if job_id is not None:
        # Job-specific clearing - only clear the job's subdirectories
        logger.info(f"Clearing job-specific directories for job ID: {job_id}")
        
        job_downloads_path = os.path.join(downloads_path, job_id)
        job_merged_path = os.path.join(merged_properties_path, job_id)
        job_tmp_path = os.path.join(tmp_path, f"{job_id}.json")
        
        # Clear job's download directory
        if os.path.exists(job_downloads_path):
            try:
                shutil.rmtree(job_downloads_path)
                logger.info(f"Cleared job download directory: {job_downloads_path}")
            except Exception as e:
                logger.error(f"Error clearing job download directory: {e}")
        
        # Clear job's merged properties directory
        if os.path.exists(job_merged_path):
            try:
                shutil.rmtree(job_merged_path)
                logger.info(f"Cleared job merged properties directory: {job_merged_path}")
            except Exception as e:
                logger.error(f"Error clearing job merged properties directory: {e}")
        
        # Remove job's status file
        if os.path.exists(job_tmp_path):
            try:
                os.remove(job_tmp_path)
                logger.info(f"Removed job status file: {job_tmp_path}")
            except Exception as e:
                logger.error(f"Error removing job status file: {e}")
    else:
        # Full clearing - clear all contents of both directories
        logger.info("Clearing all contents of downloads and merged_properties directories")
        
        for folder_path in folders_to_clear:
            if os.path.exists(folder_path):
                # Check if it's a directory
                if os.path.isdir(folder_path):
                    logger.info(f"Clearing contents of {folder_path}...")
                    
                    # List all files and directories in the folder
                    for item in os.listdir(folder_path):
                        item_path = os.path.join(folder_path, item)
                        
                        try:
                            if os.path.isfile(item_path):
                                # Remove file
                                os.unlink(item_path)
                            elif os.path.isdir(item_path):
                                # Remove directory and all its contents
                                shutil.rmtree(item_path)
                        except Exception as e:
                            logger.error(f"Error while deleting {item_path}: {e}")
                    
                    logger.info(f"Finished clearing {folder_path}")
                else:
                    logger.warning(f"Warning: {folder_path} exists but is not a directory")
            else:
                logger.warning(f"Warning: {folder_path} does not exist")
        
        # Also clear tmp directory (except for .gitkeep if it exists)
        if os.path.exists(tmp_path) and os.path.isdir(tmp_path):
            logger.info(f"Clearing contents of {tmp_path}...")
            for item in os.listdir(tmp_path):
                if item == ".gitkeep":
                    continue  # Skip .gitkeep file
                
                item_path = os.path.join(tmp_path, item)
                try:
                    if os.path.isfile(item_path):
                        os.unlink(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                except Exception as e:
                    logger.error(f"Error while deleting {item_path}: {e}")

def cleanup_expired_jobs(max_age_hours=24):
    """
    Cleans up job files that are older than the specified age.
    
    Args:
        max_age_hours (int): Maximum age in hours before cleaning up job files
    """
    import time
    
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Get parent directory (one level up)
    parent_dir = os.path.dirname(script_dir)
    
    # Define the paths
    downloads_path = os.path.join(parent_dir, 'downloads')
    merged_properties_path = os.path.join(parent_dir, 'merged_properties')
    tmp_path = os.path.join(parent_dir, 'tmp')
    
    # Current time in seconds
    current_time = time.time()
    max_age_seconds = max_age_hours * 3600
    
    # Check tmp directory for job status files
    if os.path.exists(tmp_path) and os.path.isdir(tmp_path):
        for item in os.listdir(tmp_path):
            if item.endswith('.json'):
                item_path = os.path.join(tmp_path, item)
                
                # Get file modification time
                try:
                    mtime = os.path.getmtime(item_path)
                    age_seconds = current_time - mtime
                    
                    # If file is older than max age, clean up the job
                    if age_seconds > max_age_seconds:
                        job_id = item.split('.')[0]  # Remove .json extension
                        logger.info(f"Cleaning up expired job: {job_id} (age: {age_seconds/3600:.1f} hours)")
                        clear_folders(job_id)
                except Exception as e:
                    logger.error(f"Error checking file age for {item_path}: {e}")

# Example usage - uncomment to run the function when script is executed directly
if __name__ == "__main__":
    # Regular clearing of all folders
    clear_folders()
    
    # Also clean up expired jobs
    cleanup_expired_jobs()