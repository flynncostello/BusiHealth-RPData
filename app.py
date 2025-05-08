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
        update_job_status(job_id, 'running', 5, 'Initializing search...')
        
        # Check if job is cancelled before starting
        if check_if_cancelled(job_id):
            logger.info(f"Job {job_id} was cancelled before starting")
            cleanup_job_files(job_id)
            return
        
        # Create progress callback function
        def progress_callback(percentage, message):
            update_job_status(job_id, 'running', percentage, message)
            # Check for cancellation during each callback
            if check_if_cancelled(job_id):
                logger.info(f"Job {job_id} cancelled during progress callback")
                return False  # Signal to stop processing
            return True  # Signal to continue processing
        
        # Call main function from rpdata_scraper with job-specific directories
        logger.info(f"About to start MAIN, headless={headless}")
        result = main(
            locations=locations,
            property_types=property_types,
            min_floor_area=min_floor_area,
            max_floor_area=max_floor_area,
            business_type=business_type,
            headless=headless,# Should be headless=headless, normally
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
        
        # Check if processing was successful
        if result:
            # Find the most recent file in the job's merged directory
            if os.path.exists(output_dir):
                files = os.listdir(output_dir)
                if files:
                    # Sort by modification time (newest first)
                    files.sort(key=lambda x: os.path.getmtime(os.path.join(output_dir, x)), reverse=True)
                    result_file = os.path.join(output_dir, files[0])
                    
                    # Log file details for debugging
                    logger.info(f"Found result file for job {job_id}: {result_file}")
                    logger.info(f"File exists: {os.path.exists(result_file)}")
                    logger.info(f"File size: {os.path.getsize(result_file) if os.path.exists(result_file) else 'N/A'}")
                    
                    # Ensure the file path is absolute
                    result_file = os.path.abspath(result_file)
                    logger.info(f"Absolute file path: {result_file}")
                    
                    # Add a delay to ensure file is fully written and accessible
                    import time
                    logger.info(f"Ensuring file is ready before marking job as complete...")
                    for attempt in range(5):  # Try up to 5 times
                        if os.path.exists(result_file) and os.access(result_file, os.R_OK):
                            try:
                                # Test if file can be opened
                                with open(result_file, 'rb') as test_file:
                                    test_file.read(1024)  # Try to read some data
                                logger.info(f"File is confirmed ready after {attempt} attempts")
                                break
                            except Exception as e:
                                logger.warning(f"File not yet ready (attempt {attempt+1}): {e}")
                                time.sleep(2)  # Wait 2 seconds before trying again
                        else:
                            logger.warning(f"File not yet accessible (attempt {attempt+1})")
                            time.sleep(2)  # Wait 2 seconds before trying again

                    # Now update job status with local file path
                    update_job_status(job_id, 'completed', 100, 'Processing complete!', result_file)
                else:
                    logger.error(f"No files found in {output_dir} for job {job_id}")
                    update_job_status(job_id, 'error', 0, 'No files found in merged_properties directory')
            else:
                logger.error(f"Directory not found: {output_dir} for job {job_id}")
                update_job_status(job_id, 'error', 0, 'merged_properties directory not found')
        else:
            logger.error(f"Processing failed for job {job_id} - main() returned falsy value")
            update_job_status(job_id, 'error', 0, 'Processing failed')
    
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
    
    # If job was cancelled, ensure immediate cleanup happens
    if jobs[job_id].get('cancelled', False):
        logger.info(f"Job {job_id} has been marked as cancelled")
        return True
    
    return False


def update_job_status(job_id, status, progress, message, result_file=None):
    """Update the status of a job"""
    if job_id in jobs:
        current_job = jobs[job_id]
        cancelled = current_job.get('cancelled', False)
        
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
    import time
    time.sleep(20)  # Give browser time to complete download
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
            
        # Clean up merged directory (excluding the downloaded file)
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

@app.route('/api/status/<job_id>')
def job_status(job_id):
    """Get the status of a job"""
    try:
        # Check memory cache first
        if job_id in jobs:
            return jsonify(jobs[job_id])
        
        # Try to load from disk if not in memory
        try:
            with open(f'tmp/{job_id}.json', 'r') as f:
                status = json.load(f)
                # Cache in memory
                jobs[job_id] = status
                return jsonify(status)
        except Exception as e:
            logger.error(f"Error loading job status for {job_id}: {str(e)}")
            return jsonify({'error': 'Job not found'}), 404
    except Exception as e:
        logger.error(f"Error in job_status endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/<job_id>')
def download_file(job_id):
    """Download the generated Excel file"""
    try:
        logger.info(f"Download requested for job {job_id}")
        
        # Get job status
        status = None
        if job_id in jobs:
            status = jobs[job_id]
            logger.info(f"Found job status in memory")
        else:
            # Try to load from disk
            try:
                with open(f'tmp/{job_id}.json', 'r') as f:
                    status = json.load(f)
                    logger.info(f"Loaded job status from disk")
            except Exception as e:
                logger.error(f"Failed to load job status: {str(e)}")
                return jsonify({'error': 'Job status not found'}), 404
        
        if not status:
            logger.error(f"No status found for job {job_id}")
            return jsonify({'error': 'Job status not found'}), 404
            
        logger.info(f"Job status: {status}")
        
        if status.get('status') != 'completed':
            logger.error(f"Job not completed: {status.get('status')}")
            return jsonify({'error': 'Job not completed'}), 400
            
        file_path = status.get('result_file')
        if not file_path:
            logger.error("No result file path in job status")
            return jsonify({'error': 'No result file path in job status'}), 400
        
        logger.info(f"Attempting to download file: {file_path}")
        logger.info(f"File exists: {os.path.exists(file_path)}")
        
        if not os.path.exists(file_path):
            # Try looking in the job's merged directory
            job_merged_dir = status.get('merged_dir')
            if job_merged_dir and os.path.exists(job_merged_dir):
                files = os.listdir(job_merged_dir)
                if files:
                    # Sort by modification time (newest first)
                    files.sort(key=lambda x: os.path.getmtime(os.path.join(job_merged_dir, x)), reverse=True)
                    alt_file_path = os.path.join(job_merged_dir, files[0])
                    logger.info(f"Original file not found, trying alternative: {alt_file_path}")
                    
                    if os.path.exists(alt_file_path):
                        file_path = alt_file_path
                        # Update job status with correct path
                        status['result_file'] = file_path
                        jobs[job_id] = status
                        # Save to file
                        with open(f'tmp/{job_id}.json', 'w') as f:
                            json.dump(status, f)
                    else:
                        logger.error(f"Alternative file not found: {alt_file_path}")
                        return jsonify({'error': 'File not found at specified path'}), 404
                else:
                    logger.error(f"No files in {job_merged_dir}")
                    return jsonify({'error': 'No files in merged_properties directory'}), 404
            else:
                logger.error(f"Directory not found: {job_merged_dir}")
                return jsonify({'error': 'File not found at specified path'}), 404
        
        # Try to send the file
        try:
            logger.info(f"Verifying file is ready before sending: {file_path}")
            file_ready = False
            for attempt in range(3):  # Try up to 3 times
                if os.path.exists(file_path) and os.access(file_path, os.R_OK):
                    try:
                        # Test if file can be opened and read
                        with open(file_path, 'rb') as test_file:
                            test_file.read(1024)  # Try to read some data
                        file_ready = True
                        logger.info(f"File verified as ready after {attempt} attempts")
                        break
                    except Exception as e:
                        logger.warning(f"File not yet ready for download (attempt {attempt+1}): {e}")
                        time.sleep(2)  # Wait 2 seconds before trying again
                else:
                    logger.warning(f"File not accessible for download (attempt {attempt+1})")
                    time.sleep(2)  # Wait before trying again
            
            if not file_ready:
                return jsonify({'error': 'File exists but is not ready for download. Please try again.'}), 503
                
            logger.info(f"Sending file: {file_path}")
            response = send_file(
                file_path,
                as_attachment=True,
                download_name=os.path.basename(file_path)
            )
            
            # Clean up job files after successful download with longer delay
            # Increase the delay in cleanup_job_files to give browser more time
            def delayed_cleanup(job_id):
                time.sleep(15)  # Wait longer before cleanup
                cleanup_job_files(job_id)

            cleanup_thread = threading.Thread(target=delayed_cleanup, args=(job_id,))
            cleanup_thread.daemon = True
            cleanup_thread.start()
            
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
        
        # Save to disk - this is critical for the background process to detect cancellation
        with open(f'tmp/{job_id}.json', 'w') as f:
            json.dump(jobs[job_id], f)
        
        # IMPORTANT: Do NOT call cleanup_job_files() here!
        # Let the background process detect cancellation and clean itself up
        # This prevents the race condition where we delete the file before the process can see it
        
        # Schedule a delayed cleanup only if the job doesn't clean up after itself
        def delayed_cleanup():
            time.sleep(30)  # Wait 30 seconds
            # Check if job still exists
            if job_id in jobs:
                logger.info(f"Performing delayed cleanup for job {job_id}")
                cleanup_job_files(job_id)
        
        # Start delayed cleanup thread
        cleanup_thread = threading.Thread(target=delayed_cleanup)
        cleanup_thread.daemon = True
        cleanup_thread.start()
        
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

@app.route('/test-download')
def test_download():
    """Simple test route to download an existing file from merged_properties"""
    try:
        # Check if merged_properties exists
        merged_dir = 'merged_properties'
        if not os.path.exists(merged_dir):
            return "Error: merged_properties directory doesn't exist"
        
        # Get files in directory
        files = []
        # Look in job subdirectories
        for job_dir in os.listdir(merged_dir):
            job_path = os.path.join(merged_dir, job_dir)
            if os.path.isdir(job_path):
                for file in os.listdir(job_path):
                    files.append((os.path.join(job_path, file), 
                                 os.path.getmtime(os.path.join(job_path, file))))
        
        if not files:
            return "Error: No files found in any merged_properties subdirectory"
        
        # Get the most recent file
        files.sort(key=lambda x: x[1], reverse=True)
        file_path = files[0][0]
        
        # Create test job ID
        test_job_id = 'test-job-123'
        
        # Set up job status
        jobs[test_job_id] = {
            'status': 'completed',
            'progress': 100,
            'message': 'Processing complete!',
            'result_file': file_path,
            'download_dir': os.path.join('downloads', test_job_id),
            'merged_dir': os.path.dirname(file_path),
            'cancelled': False
        }
        
        # Save job status
        with open(f'tmp/{test_job_id}.json', 'w') as f:
            json.dump(jobs[test_job_id], f)
        
        # Simple HTML
        return f"""
        <h1>Test Download</h1>
        <p>File: {os.path.basename(file_path)}</p>
        <a href="/api/download/{test_job_id}">Download File</a>
        """
    except Exception as e:
        logger.error(f"Error in test_download endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return f"Error: {str(e)}"

@app.route('/healthcheck')
def healthcheck():
    """Health check endpoint for Azure monitoring"""
    return jsonify({
        'status': 'healthy',
        'version': '1.0.0',
        'environment': 'containerized' if is_containerized else 'standard'
    })

@app.route('/container-info')
def container_info():
    """Provide information about the container environment for debugging"""
    if not is_containerized:
        return jsonify({
            'is_containerized': False,
            'message': 'Not running in a container environment'
        })
    
    try:
        # Get Chrome version
        chrome_version = "Unknown"
        try:
            import subprocess
            chrome_version = subprocess.check_output(['google-chrome', '--version']).decode().strip()
        except Exception as e:
            chrome_version = f"Error checking Chrome: {str(e)}"
        
        # Check directory permissions
        dir_info = {}
        for dir_name in ['downloads', 'merged_properties', 'tmp']:
            if os.path.exists(dir_name):
                dir_info[dir_name] = {
                    'exists': True,
                    'writable': os.access(dir_name, os.W_OK),
                    'files': len(os.listdir(dir_name))
                }
            else:
                dir_info[dir_name] = {'exists': False}
        
        return jsonify({
            'is_containerized': True,
            'chrome_version': chrome_version,
            'directories': dir_info,
            'env_variables': {k: v for k, v in os.environ.items() if k in [
                'WEBSITE_SITE_NAME', 'DOCKER_CONTAINER', 'PYTHONPATH', 'PATH', 'DISPLAY'
            ]}
        })
    except Exception as e:
        return jsonify({
            'is_containerized': True,
            'error': str(e)
        })

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