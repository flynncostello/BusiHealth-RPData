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
import fcntl  # For file locking on Unix systems

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

# At the top of app.py
is_azure = os.environ.get('WEBSITE_SITE_NAME') is not None
if is_azure:
    logger.info(f"Running in Azure: {os.environ.get('WEBSITE_SITE_NAME')}")
    # Adjust timeouts for Azure
    FILE_OPERATION_TIMEOUT = 2.0  # Increased timeout for file operations
else:
    FILE_OPERATION_TIMEOUT = 0.5  # Faster locally

# Store running jobs
jobs = {}
# Store running job threads to allow termination
job_threads = {}
# Add a lock for job status updates to prevent race conditions
job_status_lock = threading.Lock()

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
        
        # Initialize job status with thread safety
        with job_status_lock:
            jobs[job_id] = {
                'status': 'initializing',
                'progress': 0,
                'message': 'Starting property search...',
                'result_file': None,
                'download_dir': job_download_dir,
                'merged_dir': job_merged_dir,
                'cancelled': False,  # Flag to mark job as cancelled
                'file_verified': False,  # New flag to track file verification
                'created_at': time.time()
            }
        
        # Save status to file with proper locking
        save_job_status_to_file(job_id, jobs[job_id])
        
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


def save_job_status_to_file(job_id, job_status):
    """
    Save job status to file with proper locking to prevent race conditions.
    """
    status_file = f'tmp/{job_id}.json'
    temp_file = f'{status_file}.tmp.{os.getpid()}'
    
    try:
        # Write to temporary file first
        with open(temp_file, 'w') as f:
            json.dump(job_status, f, indent=2)
            f.flush()
            os.fsync(f.fileno())  # Force write to disk
        
        # Atomic rename (most reliable across platforms)
        if os.name == 'nt':  # Windows
            # Windows requires removing existing file first
            if os.path.exists(status_file):
                os.remove(status_file)
        os.rename(temp_file, status_file)
        
        logger.debug(f"Successfully saved status for job {job_id}")
    except Exception as e:
        logger.error(f"Error saving job status for {job_id}: {e}")
        # Clean up temp file if it exists
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass


def load_job_status_from_file(job_id):
    """
    Load job status from file with retry logic for Azure.
    """
    status_file = f'tmp/{job_id}.json'
    
    for attempt in range(3):
        try:
            if not os.path.exists(status_file):
                return None
                
            # Wait a bit for file to be ready
            if attempt > 0:
                time.sleep(0.01 * (2 ** attempt))
            
            with open(status_file, 'r') as f:
                # Try to acquire a shared lock if available
                if hasattr(fcntl, 'flock'):
                    try:
                        fcntl.flock(f.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
                    except IOError:
                        if attempt < 2:
                            continue
                
                job_status = json.load(f)
                return job_status
                
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Error reading job status for {job_id} (attempt {attempt+1}): {e}")
            if attempt < 2:
                time.sleep(0.01 * (2 ** attempt))
                continue
            else:
                raise
    
    return None


def run_job(job_id, locations, property_types, min_floor_area, max_floor_area, 
            business_type, headless, download_dir, output_dir):
    """Run the main processing job with robust race condition protection and file verification"""
    try:
        # Define clear progress milestones
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
        
        # Enhanced cancellation check with more robust detection
        def is_cancelled():
            """Enhanced cancellation check with multiple strategies for Azure."""
            try:
                # Strategy 1: Check in-memory cache first (fastest)
                with job_status_lock:
                    if job_id in jobs and jobs[job_id].get('cancelled', False):
                        logger.info(f"Cancellation detected in memory for job {job_id}")
                        return True
                
                # Strategy 2: Check file with retry logic
                job_status = load_job_status_from_file(job_id)
                if job_status:
                    # Update in-memory cache
                    with job_status_lock:
                        jobs[job_id] = job_status
                    
                    if job_status.get('cancelled', False):
                        logger.info(f"Cancellation detected in file for job {job_id}")
                        return True
                
                return False
            except Exception as e:
                logger.warning(f"Error checking cancellation for {job_id}: {e}")
                return False
        
        # Enhanced progress callback with race condition protection
        def progress_callback(percentage, message):
            """Enhanced progress callback with race condition prevention."""
            if message is None or (message and 'cancel' in message.lower()):
                # Still do the cancellation check even for skipped messages
                return not is_cancelled()
            
            try:
                with job_status_lock:
                    if job_id not in jobs:
                        # Try to reload from file
                        job_status = load_job_status_from_file(job_id)
                        if job_status:
                            jobs[job_id] = job_status
                        else:
                            logger.warning(f"Job {job_id} not found for progress update")
                            return not is_cancelled()
                    
                    current_job = jobs[job_id]
                    
                    # Check if job is cancelled
                    if current_job.get('cancelled', False):
                        return False
                    
                    # Prevent significant backwards progress (race condition protection)
                    current_progress = current_job.get('progress', 0)
                    if isinstance(percentage, (int, float)) and isinstance(current_progress, (int, float)):
                        if percentage < current_progress - 5:  # Allow small backwards movement for accuracy
                            logger.debug(f"Prevented backwards progress for {job_id}: {current_progress} -> {percentage}")
                            percentage = current_progress
                    
                    # Update status with validation
                    jobs[job_id]['status'] = 'running'
                    jobs[job_id]['progress'] = max(0, min(100, percentage))  # Clamp between 0-100
                    jobs[job_id]['message'] = message
                    jobs[job_id]['last_updated'] = time.time()
                
                # Save to file
                save_job_status_to_file(job_id, jobs[job_id])
                
                logger.debug(f"Progress update for job {job_id}: {percentage}% - {message}")
                
                # Check cancellation after update
                return not is_cancelled()
                
            except Exception as e:
                logger.error(f"Error in progress callback for {job_id}: {e}")
                return not is_cancelled()
        
        # Initial progress update
        update_job_status(job_id, 'running', PROGRESS_MILESTONES['start'], 'Initializing search environment...')
        
        # Check cancellation before starting
        if is_cancelled():
            logger.info(f"Job {job_id} was cancelled before starting")
            cleanup_job_files(job_id)
            return
        
        # Call main function with the enhanced cancellation check
        logger.info(f"Starting main scraper, headless={headless}")
        result = main(
            locations=locations,
            property_types=property_types,
            min_floor_area=min_floor_area,
            max_floor_area=max_floor_area,
            business_type=business_type,
            headless=headless,
            progress_callback=progress_callback,
            is_cancelled=is_cancelled,
            download_dir=download_dir,
            output_dir=output_dir
        )

        # Check cancellation after processing
        if is_cancelled():
            logger.info(f"Job {job_id} was cancelled during processing")
            cleanup_job_files(job_id)
            return

        if result == 'No files downloaded':
            update_job_status(job_id, 'error', 0, 'No Results Found on RPData for this search. Please go back to form and try again.')
            return

        # Enhanced file verification process
        if result and os.path.exists(result):
            # Progress update for verification start
            progress_callback(PROGRESS_MILESTONES['merge_complete'], "Processing complete. Verifying output files...")
            
            files = os.listdir(result)
            if files:
                files.sort(key=lambda x: os.path.getmtime(os.path.join(result, x)), reverse=True)
                result_file = os.path.join(result, files[0])
                result_file = os.path.abspath(result_file)
                
                progress_callback(PROGRESS_MILESTONES['file_verification'], "Verifying file integrity and accessibility...")
                
                # Enhanced file verification with multiple checks
                logger.info(f"Starting comprehensive file verification: {result_file}")
                
                file_verification_successful = False
                max_verification_attempts = 15  # Increased for Azure
                
                for attempt in range(max_verification_attempts):
                    if is_cancelled():
                        logger.info(f"Job {job_id} cancelled during file verification")
                        return
                    
                    logger.debug(f"File verification attempt {attempt + 1}/{max_verification_attempts}")
                    
                    # Check 1: File exists
                    if not os.path.exists(result_file):
                        logger.warning(f"File does not exist on attempt {attempt + 1}")
                        time.sleep(min(2 ** (attempt // 3), 4))  # Exponential backoff
                        continue
                    
                    # Check 2: File is accessible
                    if not os.access(result_file, os.R_OK):
                        logger.warning(f"File not readable on attempt {attempt + 1}")
                        time.sleep(min(2 ** (attempt // 3), 4))
                        continue
                    
                    try:
                        # Check 3: File size is reasonable
                        file_size = os.path.getsize(result_file)
                        if file_size == 0:
                            logger.warning(f"File is empty on attempt {attempt + 1}")
                            time.sleep(min(2 ** (attempt // 3), 4))
                            continue
                        
                        # Check 4: File can be opened and read
                        with open(result_file, 'rb') as test_file:
                            # Read file in chunks to verify integrity
                            chunk_size = 8192
                            bytes_read = 0
                            while True:
                                chunk = test_file.read(chunk_size)
                                if not chunk:
                                    break
                                bytes_read += len(chunk)
                            
                            # Verify all bytes were read
                            test_file.seek(0, 2)
                            actual_size = test_file.tell()
                            
                            if bytes_read == actual_size == file_size:
                                logger.info(f"File verification successful after {attempt + 1} attempts")
                                logger.info(f"File size: {file_size} bytes, verified: {bytes_read} bytes")
                                
                                # Final check: ensure Excel file is valid by reading header
                                with open(result_file, 'rb') as excel_check:
                                    header = excel_check.read(512)
                                    # Check for Excel file signatures
                                    if (header.startswith(b'PK\x03\x04') or  # XLSX
                                        header.startswith(b'\xd0\xcf\x11\xe0') or  # XLS
                                        b'xl/' in header):  # Additional XLSX check
                                        file_verification_successful = True
                                        break
                                    else:
                                        logger.warning(f"File doesn't appear to be a valid Excel file on attempt {attempt + 1}")
                            else:
                                logger.warning(f"File size mismatch on attempt {attempt + 1}: expected {file_size}, got {actual_size}")
                    
                    except Exception as e:
                        logger.warning(f"File verification attempt {attempt + 1} failed: {e}")
                    
                    # Wait before retry, with exponential backoff
                    time.sleep(min(2 ** (attempt // 3), 4))
                
                if not file_verification_successful:
                    logger.error(f"File verification failed after {max_verification_attempts} attempts")
                    update_job_status(job_id, 'error', 0, 'File verification failed. The output file may be corrupted or inaccessible.')
                    return
                
                # File is verified - mark job as completed with file verification flag
                logger.info(f"File verification completed successfully. Marking job {job_id} as completed")
                
                # Additional delay to ensure file system is fully consistent
                time.sleep(1)
                
                # Final status update with atomic operation
                with job_status_lock:
                    if job_id in jobs and not jobs[job_id].get('cancelled', False):
                        jobs[job_id]['status'] = 'completed'
                        jobs[job_id]['progress'] = PROGRESS_MILESTONES['file_ready']
                        jobs[job_id]['message'] = 'File ready for download!'
                        jobs[job_id]['result_file'] = result_file
                        jobs[job_id]['file_verified'] = True  # Important flag
                        jobs[job_id]['last_updated'] = time.time()
                
                save_job_status_to_file(job_id, jobs[job_id])
                logger.info(f"Job {job_id} marked as completed with verified file")
            else:
                update_job_status(job_id, 'error', 0, 'No files found in output directory')
        else:
            update_job_status(job_id, 'error', 0, 'Output directory not found')
    
    except Exception as e:
        logger.error(f"Exception in run_job for job {job_id}: {str(e)}")
        logger.error(traceback.format_exc())
        update_job_status(job_id, 'error', 0, f'An error occurred: {str(e)}')
    finally:
        if job_id in job_threads:
            del job_threads[job_id]


def check_if_cancelled(job_id):
    """
    Robust cancellation check that works reliably in Azure.
    Uses multiple strategies to ensure cancellation is detected quickly.
    """
    try:
        # Strategy 1: Check in-memory cache first (fastest)
        with job_status_lock:
            if job_id in jobs:
                cancelled = jobs[job_id].get('cancelled', False)
                if cancelled:
                    logger.info(f"Cancellation detected in memory for job {job_id}")
                    return True
        
        # Strategy 2: Check file
        job_status = load_job_status_from_file(job_id)
        if job_status:
            # Update in-memory cache
            with job_status_lock:
                jobs[job_id] = job_status
            
            cancelled = job_status.get('cancelled', False)
            if cancelled:
                logger.info(f"Cancellation detected in file for job {job_id}")
                return True
        
        return False
    except Exception as e:
        logger.warning(f"Error checking cancellation for {job_id}: {e}")
        return False


def update_job_status(job_id, status, progress, message, result_file=None):
    """
    Enhanced job status update with thread safety and race condition prevention.
    """
    try:
        with job_status_lock:
            # Load current status if not in memory
            if job_id not in jobs:
                job_status = load_job_status_from_file(job_id)
                if job_status:
                    jobs[job_id] = job_status
                else:
                    logger.warning(f"Cannot update job {job_id}: job not found")
                    return
            
            current_job = jobs[job_id]
            cancelled = current_job.get('cancelled', False)
            
            # If cancelled, preserve cancellation state unless explicitly setting to cancelled
            if cancelled and status != 'cancelled':
                return  # Don't overwrite cancellation
            
            # Prevent backwards progress unless it's a reset or error
            if status not in ['error', 'cancelled', 'initializing']:
                current_progress = current_job.get('progress', 0)
                if isinstance(progress, (int, float)) and isinstance(current_progress, (int, float)):
                    if progress < current_progress - 5:  # Allow small backwards movement
                        progress = current_progress
            
            # Update status
            jobs[job_id] = {
                'status': 'cancelled' if cancelled else status,
                'progress': max(0, min(100, progress)) if isinstance(progress, (int, float)) else progress,
                'message': 'Job was cancelled' if cancelled else message,
                'result_file': result_file,
                'cancelled': cancelled,
                'download_dir': current_job.get('download_dir'),
                'merged_dir': current_job.get('merged_dir'),
                'file_verified': current_job.get('file_verified', False),
                'created_at': current_job.get('created_at', time.time()),
                'last_updated': time.time()
            }
        
        # Save to file
        save_job_status_to_file(job_id, jobs[job_id])
        
        # Log status updates with more detail
        logger.info(f"Job {job_id} updated: {status}, {progress}%, {message}")
        if result_file:
            logger.info(f"Result file: {result_file}")
    
    except Exception as e:
        logger.error(f"Error updating job status for {job_id}: {e}")
        logger.error(traceback.format_exc())


def cleanup_job_files(job_id):
    """Clean up job-specific directories after successful download"""
    # Don't cleanup immediately - allow time for download
    def delayed_cleanup():
        time.sleep(30)  # Wait 30 seconds for download to complete
        logger.info(f"Cleaning up job files for {job_id}")

        try:
            # Load job status from file if not in memory
            with job_status_lock:
                if job_id not in jobs:
                    logger.warning(f"Cannot cleanup job {job_id}: job not found in memory")
                    job_status = load_job_status_from_file(job_id)
                    if job_status:
                        jobs[job_id] = job_status
                    else:
                        logger.warning(f"Could not load job {job_id} from disk")
                        return
                
                current_job = jobs[job_id]
            
            download_dir = current_job.get('download_dir')
            merged_dir = current_job.get('merged_dir')
            
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
            with job_status_lock:
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
    """Get the status of a job with enhanced verification"""
    try:
        status = None
        
        # Check memory cache first with proper locking
        with job_status_lock:
            if job_id in jobs:
                status = jobs[job_id].copy()  # Make a copy to avoid modifying the original
        
        # Load from disk if not in memory
        if not status:
            status = load_job_status_from_file(job_id)
            if status:
                # Cache in memory
                with job_status_lock:
                    jobs[job_id] = status
            else:
                logger.error(f"Job {job_id} not found")
                return jsonify({'error': 'Job not found'}), 404
        
        # Enhanced download readiness check
        download_ready = False
        
        if (status.get('status') == 'completed' and 
            status.get('result_file') and 
            status.get('file_verified', False)):  # New verification flag
            
            result_file = status.get('result_file')
            
            # Double-check file still exists and is readable
            if os.path.exists(result_file) and os.access(result_file, os.R_OK):
                try:
                    # Quick file verification
                    file_size = os.path.getsize(result_file)
                    if file_size > 0:
                        download_ready = True
                        status['file_size'] = file_size  # Include file size in response
                    else:
                        logger.warning(f"File exists but is empty: {result_file}")
                except Exception as e:
                    logger.warning(f"Error verifying file for download: {e}")
            else:
                logger.warning(f"File not accessible: {result_file}")
        
        status['download_ready'] = download_ready
        
        # Add debug information for troubleshooting
        if not download_ready and status.get('status') == 'completed':
            debug_info = {
                'has_result_file': bool(status.get('result_file')),
                'file_verified': status.get('file_verified', False),
                'file_exists': bool(status.get('result_file') and os.path.exists(status.get('result_file'))),
                'file_accessible': bool(status.get('result_file') and os.path.exists(status.get('result_file')) 
                                      and os.access(status.get('result_file'), os.R_OK))
            }
            status['debug_info'] = debug_info
            logger.debug(f"Download not ready for job {job_id}: {debug_info}")
            
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error in job_status endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@app.route('/api/download/<job_id>')
def download_file(job_id):
    """Download the generated Excel file with enhanced verification"""
    try:
        logger.info(f"Download requested for job {job_id}")
        
        # Get job status
        status = None
        
        with job_status_lock:
            if job_id in jobs:
                status = jobs[job_id]
                logger.info(f"Found job status in memory: {status.get('status')}")
        
        if not status:
            # Try to load from disk
            status = load_job_status_from_file(job_id)
            if status:
                logger.info(f"Loaded job status from disk: {status.get('status')}")
                # Cache in memory
                with job_status_lock:
                    jobs[job_id] = status
            else:
                logger.error(f"Failed to load job status for {job_id}")
                return jsonify({'error': 'Job status not found'}), 404
        
        # Enhanced completion check
        if status.get('status') != 'completed':
            logger.error(f"Job not completed: {status.get('status')}")
            return jsonify({
                'error': 'Job not completed', 
                'status': status.get('status'),
                'message': f'Job status is {status.get("status")}. Please wait for completion.'
            }), 400
        
        # Check file verification flag
        if not status.get('file_verified', False):
            logger.error(f"File not verified for job {job_id}")
            return jsonify({
                'error': 'File not verified', 
                'message': 'File verification is still in progress. Please wait a moment and try again.'
            }), 400
        
        # Get file path
        file_path = status.get('result_file')
        if not file_path:
            logger.error("No result file path in job status")
            return jsonify({'error': 'No result file found'}), 404
        
        # Final file verification before download
        logger.info(f"Performing final verification before download: {file_path}")
        
        if not os.path.exists(file_path):
            logger.error(f"File does not exist: {file_path}")
            return jsonify({'error': 'File not found'}), 404
        
        if not os.access(file_path, os.R_OK):
            logger.error(f"File not readable: {file_path}")
            return jsonify({'error': 'File not accessible'}), 403
        
        # Verify file is not empty and is readable
        try:
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                logger.error(f"File is empty: {file_path}")
                return jsonify({'error': 'File is empty'}), 500
            
            # Quick read test
            with open(file_path, 'rb') as test_file:
                test_file.read(1024)  # Read first 1KB to ensure file is accessible
                test_file.seek(0, 2)  # Go to end
                actual_size = test_file.tell()
                
                if actual_size != file_size:
                    logger.error(f"File size mismatch: {file_path}")
                    return jsonify({'error': 'File corruption detected'}), 500
                
            logger.info(f"Final verification passed: {file_path} (size: {file_size} bytes)")
        except Exception as e:
            logger.error(f"Final file verification failed: {str(e)}")
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
    """Enhanced cancellation with Azure-specific debugging and atomic operations."""
    try:
        job_id = request.json.get('job_id')
        if not job_id:
            return jsonify({'error': 'No job ID provided'}), 400
            
        logger.info(f"Cancellation requested for job {job_id}")
        
        # Check if job exists with thread safety
        job_found = False
        
        with job_status_lock:
            if job_id in jobs:
                job_found = True
        
        if not job_found:
            # Try to load from file
            job_status = load_job_status_from_file(job_id)
            if job_status:
                with job_status_lock:
                    jobs[job_id] = job_status
                    job_found = True
        
        if not job_found:
            logger.error(f"Job {job_id} not found for cancellation")
            return jsonify({'error': 'Job not found'}), 404
        
        # Update status atomically
        with job_status_lock:
            current_job = jobs[job_id]
            old_status = current_job.get('status', 'unknown')
            
            # Update all cancellation-related fields
            jobs[job_id]['cancelled'] = True
            jobs[job_id]['status'] = 'cancelled'
            jobs[job_id]['message'] = 'Job cancelled by user'
            jobs[job_id]['last_updated'] = time.time()
            
            logger.info(f"Job {job_id} status changed from {old_status} to cancelled")
        
        # Save to disk with retry logic
        save_successful = False
        for attempt in range(3):
            try:
                save_job_status_to_file(job_id, jobs[job_id])
                save_successful = True
                logger.info(f"Successfully saved cancellation status for job {job_id} (attempt {attempt+1})")
                break
            except Exception as e:
                logger.warning(f"Failed to save cancellation status (attempt {attempt+1}): {e}")
                if attempt < 2:
                    time.sleep(0.1)  # Brief wait before retry
        
        if not save_successful:
            logger.error(f"Failed to save cancellation status after 3 attempts for job {job_id}")
            return jsonify({'error': 'Failed to save cancellation status'}), 500
        
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