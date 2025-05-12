from flask import Flask, render_template, request, jsonify, send_file, redirect
import os
import threading
import uuid
import json
import logging
import traceback
import shutil
import sys
from flask_cors import CORS
from dotenv import load_dotenv
from datetime import datetime
import time

# Add current directory to path to help with imports in Docker
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Load environment variables from .env file if it exists
load_dotenv()

# Determine containerized environment
is_containerized = os.environ.get('WEBSITE_SITE_NAME') is not None or 'DOCKER_CONTAINER' in os.environ or False

# Import main function from rpdata_scraper
from rpdata_scraper.main import main

app = Flask(__name__)
CORS(app)  # Enable CORS to fix 403 errors

log_dir = os.environ.get('HOME', '') + '/LogFiles'
os.makedirs(log_dir, exist_ok=True)

# Create timestamped log filename
log_filename = f"{log_dir}/rpdata_scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Configure more detailed logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed from INFO to DEBUG for more details
    format='%(asctime)s - %(levelname)s - %(name)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Log Docker/container environment information
logger.info(f"Running in containerized environment: {is_containerized}")
if is_containerized:
    logger.info("Container environment variables:")
    for key in ['WEBSITE_SITE_NAME', 'DOCKER_CONTAINER']:
        if key in os.environ:
            logger.info(f"  {key}: {os.environ[key]}")

# Ensure necessary directories exist
os.makedirs('downloads', exist_ok=True)
os.makedirs('merged_properties', exist_ok=True)
os.makedirs('tmp', exist_ok=True)

# Store running jobs
jobs = {}
# Store running job threads to allow termination
job_threads = {}

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/api/process', methods=['POST'])
def process():
    """Process the form data and start the scraping job"""
    try:
        # Generate a unique job ID
        job_id = str(uuid.uuid4())
        
        # Parse form data
        data = request.form
        business_type = data.get('business_type')
        
        # Parse locations string into a list
        locations_str = data.get('locations', '')
        locations = [loc.strip() for loc in locations_str.split(',') if loc.strip()]
        
        # Get floor area values
        min_floor_area = data.get('min_floor_area', 'Min')
        max_floor_area = data.get('max_floor_area', 'Max')
        
        # Create job-specific directories
        job_download_dir = os.path.join('downloads', job_id)
        job_merged_dir = os.path.join('merged_properties', job_id)
        
        os.makedirs(job_download_dir, exist_ok=True)
        os.makedirs(job_merged_dir, exist_ok=True)
        
        # Set directory permissions for Docker
        if is_containerized:
            try:
                os.chmod(job_download_dir, 0o777)
                os.chmod(job_merged_dir, 0o777)
                logger.info(f"Set directory permissions for Docker environment")
            except Exception as e:
                logger.warning(f"Could not set directory permissions: {e}")
        
        logger.info(f"Created job directories for {job_id}: {job_download_dir}, {job_merged_dir}")
        
        # Determine headless mode
        # In containerized environments, always use headless mode
        headless = True if is_containerized else False
        
        logger.info(f"Starting new job {job_id} with parameters: business_type={business_type}, "
                    f"locations={locations}, floor_area={min_floor_area}-{max_floor_area}, headless={headless}")
        
        # Set property types to both Business and Commercial as specified
        property_types = ["Business", "Commercial"]
        
        # Initialize job status
        jobs[job_id] = {
            'status': 'running',
            'progress': 0,
            'message': 'Starting property search...',
            'result_file': None,
            'download_dir': job_download_dir,
            'merged_dir': job_merged_dir,
            'cancelled': False  # Flag to mark job as cancelled
        }
        
        # Save status to file
        with open(f'tmp/{job_id}.json', 'w') as f:
            json.dump(jobs[job_id], f)
        
        # Run the job in a background thread
        thread = threading.Thread(
            target=run_job,
            args=(job_id, locations, property_types, min_floor_area, max_floor_area, 
                  business_type, headless, job_download_dir, job_merged_dir)
        )
        thread.daemon = True
        thread.start()
        
        # Store the thread for possible cancellation
        job_threads[job_id] = thread
        
        return jsonify({'job_id': job_id})
    except Exception as e:
        logger.error(f"Error in process endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

def run_job(job_id, locations, property_types, min_floor_area, max_floor_area, 
            business_type, headless, download_dir, output_dir):
    """Run the main processing job in a background thread with job-specific directories"""
    try:
        # Define progress milestones with smoother progression
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
            'merge_complete': 98,
            'file_ready': 100
        }
        
        # Create smooth progress callback with meaningful messages
        def progress_callback(percentage, message):
            # Clean up the message - remove cancellation check messages  
            if 'cancelled' in message.lower() or 'checking' in message.lower():
                return True  # Skip these messages
                
            # Don't let progress go backwards, but allow natural progression
            current_progress = jobs[job_id].get('progress', 0)
            if percentage < current_progress:
                # Only use current progress if the new percentage is significantly lower
                if current_progress - percentage > 5:
                    percentage = current_progress
            
            update_job_status(job_id, 'running', percentage, message)
            
            # Check for cancellation
            return not check_if_cancelled(job_id)
        
        update_job_status(job_id, 'running', PROGRESS_MILESTONES['start'], 'Initializing search environment...')
        
        # Check if job is cancelled before starting
        if check_if_cancelled(job_id):
            logger.info(f"Job {job_id} was cancelled before starting")
            cleanup_job_files(job_id)
            return
        
        # Call main function from rpdata_scraper
        logger.info(f"Starting main scraper, headless={headless}")
        result = main(
            locations=locations,
            property_types=property_types,
            min_floor_area=min_floor_area,
            max_floor_area=max_floor_area,
            business_type=business_type,
            headless=headless,
            progress_callback=progress_callback,
            download_dir=download_dir,
            output_dir=output_dir
        )

        # Check if job was cancelled during processing
        if check_if_cancelled(job_id):
            logger.info(f"Job {job_id} was cancelled after main processing")
            cleanup_job_files(job_id)
            return

        if result == 'No files downloaded':
            logger.error(f"No files downloaded during scraping for job {job_id}")
            update_job_status(job_id, 'error', 0, 'No results found. Please check your search criteria.')
            return
        
        # Update progress to merge phase
        progress_callback(PROGRESS_MILESTONES['merge_start'], "Processing files into final merged file...")
        
        # Verify the result directory exists and has files
        if result and os.path.exists(result):
            files = os.listdir(result)
            if files:
                # Sort by modification time (newest first)
                files.sort(key=lambda x: os.path.getmtime(os.path.join(result, x)), reverse=True)
                result_file = os.path.join(result, files[0])
                result_file = os.path.abspath(result_file)
                
                # Update progress but don't mark as complete yet
                progress_callback(PROGRESS_MILESTONES['merge_complete'], "Verifying file is ready for download...")
                
                # Enhanced file verification - ensure it's completely written and accessible
                logger.info(f"Verifying file is ready: {result_file}")
                file_ready = False
                
                # More robust verification with multiple checks
                for attempt in range(10):  # Increased from 5 to 10 attempts
                    if check_if_cancelled(job_id):
                        return
                        
                    if os.path.exists(result_file) and os.access(result_file, os.R_OK):
                        try:
                            # Test file accessibility comprehensively
                            file_size = os.path.getsize(result_file)
                            if file_size > 0:  # Ensure file is not empty
                                with open(result_file, 'rb') as test_file:
                                    # Read chunks to verify file integrity
                                    test_file.read(1024)
                                    test_file.seek(0, 2)  # Seek to end
                                    actual_size = test_file.tell()
                                    if actual_size == file_size:  # File size matches
                                        file_ready = True
                                        logger.info(f"File verified as ready after {attempt+1} attempts")
                                        break
                        except Exception as e:
                            logger.warning(f"File verification attempt {attempt+1} failed: {e}")
                    
                    # Exponential backoff with longer delays
                    time.sleep(min(2 ** attempt, 8))  # Max 8 seconds between attempts
                
                if not file_ready:
                    logger.error("File verification failed after all attempts")
                    update_job_status(job_id, 'error', 0, 'File verification failed. Please try again.')
                    return
                
                # Only now mark as complete when file is truly ready
                logger.info(f"File is ready, marking job {job_id} as completed")
                update_job_status(job_id, 'completed', PROGRESS_MILESTONES['file_ready'], 'File ready for download!', result_file)
            else:
                logger.error(f"No files found in {result}")
                update_job_status(job_id, 'error', 0, 'No files found in output directory')
        else:
            logger.error(f"Result directory not found: {result}")
            update_job_status(job_id, 'error', 0, 'Output directory not found')
    
    except Exception as e:
        logger.error(f"Exception in run_job for job {job_id}: {str(e)}")
        logger.error(traceback.format_exc())
        update_job_status(job_id, 'error', 0, f'An error occurred: {str(e)}')
    finally:
        # Clean up job thread reference
        if job_id in job_threads:
            del job_threads[job_id]

def check_if_cancelled(job_id):
    """Check if a job has been marked for cancellation"""
    if job_id not in jobs:
        try:
            # Try to load from disk if not in memory
            with open(f'tmp/{job_id}.json', 'r') as f:
                job_status = json.load(f)
                jobs[job_id] = job_status
        except Exception:
            # If we can't load the status, assume not cancelled
            return False
    
    # Return cancellation status
    return jobs[job_id].get('cancelled', False)

def update_job_status(job_id, status, progress, message, result_file=None):
    """Update the status of a job"""
    if job_id in jobs:
        current_job = jobs[job_id]
        cancelled = current_job.get('cancelled', False)
        
        # If cancelled, don't update status further
        if cancelled and status != 'cancelled':
            return
        
        jobs[job_id] = {
            'status': 'cancelled' if cancelled else status,
            'progress': progress,
            'message': 'Job was cancelled' if cancelled else message,
            'result_file': result_file,
            'cancelled': cancelled,
            # Preserve the directory paths
            'download_dir': current_job.get('download_dir'),
            'merged_dir': current_job.get('merged_dir')
        }
    else:
        # Create new job status if it doesn't exist in memory
        jobs[job_id] = {
            'status': status,
            'progress': progress,
            'message': message,
            'result_file': result_file,
            'cancelled': False,
            'download_dir': None,
            'merged_dir': None
        }
    
    # Log status updates
    logger.info(f"Job {job_id} updated: {status}, {progress}%, {message}")
    if result_file:
        logger.info(f"Result file: {result_file}")
    
    # Save to file in case server restarts
    with open(f'tmp/{job_id}.json', 'w') as f:
        json.dump(jobs[job_id], f)

def cleanup_job_files(job_id):
    """Clean up job-specific directories after successful download"""
    # Don't cleanup immediately - allow time for download
    def delayed_cleanup():
        time.sleep(30)  # Wait 30 seconds for download to complete
        logger.info(f"Cleaning up job files for {job_id}")

        try:
            if job_id not in jobs:
                logger.warning(f"Cannot cleanup job {job_id}: job not found in memory")
                # Try to load from disk
                try:
                    with open(f'tmp/{job_id}.json', 'r') as f:
                        jobs[job_id] = json.load(f)
                except Exception as e:
                    logger.warning(f"Could not load job {job_id} from disk: {e}")
                    return
            
            download_dir = jobs[job_id].get('download_dir')
            merged_dir = jobs[job_id].get('merged_dir')
            
            # Clean up download directory
            if download_dir and os.path.exists(download_dir):
                try:
                    shutil.rmtree(download_dir)
                    logger.info(f"Removed download directory for job {job_id}")
                except Exception as e:
                    logger.error(f"Error removing download directory: {e}")
                
            # Clean up merged directory
            if merged_dir and os.path.exists(merged_dir):
                try:
                    shutil.rmtree(merged_dir)
                    logger.info(f"Removed merged directory for job {job_id}")
                except Exception as e:
                    logger.error(f"Error removing merged directory: {e}")

                    
            # Remove status file
            status_file = f'tmp/{job_id}.json'
            if os.path.exists(status_file):
                try:
                    os.remove(status_file)
                    logger.info(f"Removed status file for job {job_id}")
                except Exception as e:
                    logger.error(f"Error removing status file: {e}")
                
            logger.info(f"Cleanup completed for job {job_id}")
            
            # Remove from memory
            if job_id in jobs:
                del jobs[job_id]
                
        except Exception as e:
            logger.error(f"Error cleaning up job {job_id}: {str(e)}")
            logger.error(traceback.format_exc())
    
    # Run cleanup in a separate thread to not block the main process
    cleanup_thread = threading.Thread(target=delayed_cleanup)
    cleanup_thread.daemon = True
    cleanup_thread.start()

@app.route('/api/status/<job_id>')
def job_status(job_id):
    """Get the status of a job"""
    try:
        # Check memory cache first
        status = None
        if job_id in jobs:
            status = jobs[job_id].copy()  # Make a copy to avoid modifying the original
        else:
            # Try to load from disk if not in memory
            try:
                with open(f'tmp/{job_id}.json', 'r') as f:
                    status = json.load(f)
                    # Cache in memory
                    jobs[job_id] = status
            except Exception as e:
                logger.error(f"Error loading job status for {job_id}: {str(e)}")
                return jsonify({'error': 'Job not found'}), 404
        
        # Add a download_ready flag to clearly indicate when download is truly available
        if status.get('status') == 'completed' and status.get('result_file') and os.path.exists(status.get('result_file')):
            status['download_ready'] = True
        else:
            status['download_ready'] = False
            
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error in job_status endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/<job_id>')
def download_file(job_id):
    """Download the generated Excel file with enhanced verification"""
    try:
        logger.info(f"Download requested for job {job_id}")
        
        # Get job status
        status = None
        if job_id in jobs:
            status = jobs[job_id]
            logger.info(f"Found job status in memory: {status.get('status')}")
        else:
            # Try to load from disk
            try:
                with open(f'tmp/{job_id}.json', 'r') as f:
                    status = json.load(f)
                    logger.info(f"Loaded job status from disk: {status.get('status')}")
                    # Cache in memory
                    jobs[job_id] = status
            except Exception as e:
                logger.error(f"Failed to load job status: {str(e)}")
                return jsonify({'error': 'Job status not found'}), 404
        
        if not status:
            logger.error(f"No status found for job {job_id}")
            return jsonify({'error': 'Job status not found'}), 404
            
        # Verify job is completed
        if status.get('status') != 'completed':
            logger.error(f"Job not completed: {status.get('status')}")
            return jsonify({
                'error': 'Job not completed', 
                'status': status.get('status'),
                'message': 'File is not ready yet. Please wait...'
            }), 400
        
        # Get file path
        file_path = status.get('result_file')
        if not file_path:
            logger.error("No result file path in job status")
            return jsonify({'error': 'No result file found'}), 404
        
        # Enhanced file verification before download
        logger.info(f"Verifying file before download: {file_path}")
        
        # Multiple verification steps
        if not os.path.exists(file_path):
            logger.error(f"File does not exist: {file_path}")
            return jsonify({'error': 'File not found'}), 404
        
        # Verify file is readable and not empty
        try:
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                logger.error(f"File is empty: {file_path}")
                return jsonify({'error': 'File is empty'}), 500
                
            # Attempt to read the file to verify it's not corrupted
            with open(file_path, 'rb') as test_file:
                # Read a chunk to verify file integrity
                test_file.read(1024)
                
            logger.info(f"File verified successfully: {file_path} (size: {file_size} bytes)")
        except Exception as e:
            logger.error(f"File verification failed: {str(e)}")
            return jsonify({'error': f'File verification failed: {str(e)}'}), 500
        
        try:
            # Send the file
            response = send_file(
                file_path,
                as_attachment=True,
                download_name=os.path.basename(file_path)
            )
            
            logger.info(f"Successfully initiated download for job {job_id}")
            
            # Schedule cleanup after download
            cleanup_job_files(job_id)
            
            return response
            
        except Exception as e:
            logger.error(f"Error sending file: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({'error': f'Error sending file: {str(e)}'}), 500
            
    except Exception as e:
        logger.error(f"Error in download_file endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/cancel', methods=['POST'])
def cancel_job():
    """Cancel a running job and clean up resources"""
    try:
        job_id = request.json.get('job_id')
        if not job_id:
            return jsonify({'error': 'No job ID provided'}), 400
            
        logger.info(f"Cancellation requested for job {job_id}")
        
        # Check if job exists
        if job_id not in jobs and not os.path.exists(f'tmp/{job_id}.json'):
            logger.error(f"Job {job_id} not found for cancellation")
            return jsonify({'error': 'Job not found'}), 404
            
        # Load job from disk if not in memory
        if job_id not in jobs:
            try:
                with open(f'tmp/{job_id}.json', 'r') as f:
                    jobs[job_id] = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load job status for cancellation: {str(e)}")
                return jsonify({'error': 'Failed to load job status'}), 500
        
        # Mark job as cancelled
        jobs[job_id]['cancelled'] = True
        jobs[job_id]['status'] = 'cancelled'
        jobs[job_id]['message'] = 'Job cancelled by user'
        
        # Save to disk immediately
        with open(f'tmp/{job_id}.json', 'w') as f:
            json.dump(jobs[job_id], f)
        
        # Schedule cleanup
        cleanup_job_files(job_id)
        
        return jsonify({'success': True, 'message': 'Job cancelled successfully'})
    except Exception as e:
        logger.error(f"Error in cancel_job endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500
    

@app.route('/api/reset', methods=['POST'])
def reset():
    """Reset the job (just for UI state, cleanup is handled after download)"""
    # This endpoint now only handles UX reset, not cancellation
    return jsonify({'success': True})


if __name__ == '__main__':
    # Make sure necessary directories exist
    os.makedirs('downloads', exist_ok=True)
    os.makedirs('merged_properties', exist_ok=True)
    os.makedirs('tmp', exist_ok=True)
    
    # Set Docker environment variable if not already set
    if is_containerized and 'DOCKER_CONTAINER' not in os.environ:
        os.environ['DOCKER_CONTAINER'] = 'true'
    
    # Print working directory for debugging
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"Python executable: {os.path.abspath(os.__file__)}")
    
    # Set debug mode and host based on environment
    debug_mode = not is_containerized
    host = '0.0.0.0'  # Always bind to all interfaces in Docker
    
    logger.info(f"Starting application with debug={debug_mode}, host={host}")
    app.run(host=host, port=8000, debug=debug_mode)