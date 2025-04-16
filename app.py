from flask import Flask, render_template, request, jsonify, send_file
import os
import threading
import uuid
import json
import logging
import traceback
from flask_cors import CORS

# Import main function from rpdata_scraper
from rpdata_scraper.main import main

app = Flask(__name__)
CORS(app)  # Enable CORS to fix 403 errors

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("rpdata_scraper.log")
    ]
)
logger = logging.getLogger(__name__)

# Ensure necessary directories exist
os.makedirs('downloads', exist_ok=True)  # For downloaded Excel files
os.makedirs('merged_properties', exist_ok=True)  # For merged output
os.makedirs('tmp', exist_ok=True)  # For job status tracking

# Store running jobs
jobs = {}

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
        
        # Use headless mode based on environment
        # In production Docker container, always use headless
        is_docker = os.environ.get('RUNNING_IN_DOCKER', 'false').lower() == 'true'
        headless = True if is_docker else False
        
        logger.info(f"Starting new job {job_id} with parameters: business_type={business_type}, "
                    f"locations={locations}, floor_area={min_floor_area}-{max_floor_area}, headless={headless}")
        
        # Set property types to both Business and Commercial as specified
        property_types = ["Business", "Commercial"]
        
        # Initialize job status
        jobs[job_id] = {
            'status': 'running',
            'progress': 0,
            'message': 'Starting property search...',
            'result_file': None
        }
        
        # Save status to file
        with open(f'tmp/{job_id}.json', 'w') as f:
            json.dump(jobs[job_id], f)
        
        # Run the job in a background thread
        thread = threading.Thread(
            target=run_job,
            args=(job_id, locations, property_types, min_floor_area, max_floor_area, business_type, headless)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({'job_id': job_id})
    except Exception as e:
        logger.error(f"Error in process endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

def run_job(job_id, locations, property_types, min_floor_area, max_floor_area, business_type, headless):
    """Run the main processing job in a background thread"""
    try:
        update_job_status(job_id, 'running', 5, 'Initializing search...')
        
        # Create progress callback function
        def progress_callback(percentage, message):
            update_job_status(job_id, 'running', percentage, message)

        # Call main function from rpdata_scraper
        result = main(
            locations=locations,
            property_types=property_types,
            min_floor_area=min_floor_area,
            max_floor_area=max_floor_area,
            business_type=business_type,
            headless=headless,
            progress_callback=progress_callback
        )

        if result == 'No files downloaded':
            logger.error("No files downloaded during scraping")
            update_job_status(job_id, 'error', 0, 'No results found. Please check your search criteria.')
            return
        
        # Check if processing was successful
        if result:
            # The merged_properties folder is in the root directory
            merged_dir = 'merged_properties'
            
            if os.path.exists(merged_dir):
                files = os.listdir(merged_dir)
                if files:
                    # Sort by modification time (newest first)
                    files.sort(key=lambda x: os.path.getmtime(os.path.join(merged_dir, x)), reverse=True)
                    result_file = os.path.join(merged_dir, files[0])
                    
                    # Log file details for debugging
                    logger.info(f"Found result file: {result_file}")
                    logger.info(f"File exists: {os.path.exists(result_file)}")
                    logger.info(f"File size: {os.path.getsize(result_file) if os.path.exists(result_file) else 'N/A'}")
                    
                    # Ensure the file path is absolute
                    result_file = os.path.abspath(result_file)
                    logger.info(f"Absolute file path: {result_file}")
                    
                    update_job_status(job_id, 'completed', 100, 'Processing complete!', result_file)
                else:
                    logger.error(f"No files found in {merged_dir}")
                    update_job_status(job_id, 'error', 0, 'No files found in merged_properties directory')
            else:
                logger.error(f"Directory not found: {merged_dir}")
                update_job_status(job_id, 'error', 0, 'merged_properties directory not found')
        else:
            logger.error("Processing failed - main() returned falsy value")
            update_job_status(job_id, 'error', 0, 'Processing failed')
    
    except Exception as e:
        logger.error(f"Exception in run_job: {str(e)}")
        logger.error(traceback.format_exc())
        update_job_status(job_id, 'error', 0, f'An error occurred: {str(e)}')

def update_job_status(job_id, status, progress, message, result_file=None):
    """Update the status of a job"""
    jobs[job_id] = {
        'status': status,
        'progress': progress,
        'message': message,
        'result_file': result_file
    }
    
    # Log status updates
    logger.info(f"Job {job_id} updated: {status}, {progress}%, {message}")
    if result_file:
        logger.info(f"Result file: {result_file}")
    
    # Save to file in case server restarts
    with open(f'tmp/{job_id}.json', 'w') as f:
        json.dump(jobs[job_id], f)

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
            # Try looking in the merged_properties directory
            merged_dir = 'merged_properties'
            if os.path.exists(merged_dir):
                files = os.listdir(merged_dir)
                if files:
                    # Sort by modification time (newest first)
                    files.sort(key=lambda x: os.path.getmtime(os.path.join(merged_dir, x)), reverse=True)
                    alt_file_path = os.path.join(merged_dir, files[0])
                    logger.info(f"Original file not found, trying alternative: {alt_file_path}")
                    
                    if os.path.exists(alt_file_path):
                        file_path = alt_file_path
                        # Update job status with correct path
                        update_job_status(job_id, 'completed', 100, 'Processing complete!', file_path)
                    else:
                        logger.error(f"Alternative file not found: {alt_file_path}")
                        return jsonify({'error': 'File not found at specified path'}), 404
                else:
                    logger.error(f"No files in {merged_dir}")
                    return jsonify({'error': 'No files in merged_properties directory'}), 404
            else:
                logger.error(f"Directory not found: {merged_dir}")
                return jsonify({'error': 'File not found at specified path'}), 404
        
        # Try to send the file
        try:
            logger.info(f"Sending file: {file_path}")
            return send_file(
                file_path,
                as_attachment=True,
                download_name=os.path.basename(file_path)
            )
        except Exception as e:
            logger.error(f"Error sending file: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({'error': f'Error sending file: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"Error in download_file endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/reset', methods=['POST'])
def reset():
    """Reset the job (just for UI state, doesn't cancel running jobs)"""
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
        files = os.listdir(merged_dir)
        if not files:
            return "Error: No files found in merged_properties directory"
        
        # Get the most recent file
        files.sort(key=lambda x: os.path.getmtime(os.path.join(merged_dir, x)), reverse=True)
        file_path = os.path.abspath(os.path.join(merged_dir, files[0]))
        
        # Create test job ID
        test_job_id = 'test-job-123'
        
        # Set up job status
        jobs[test_job_id] = {
            'status': 'completed',
            'progress': 100,
            'message': 'Processing complete!',
            'result_file': file_path
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
        'version': '1.0.0'
    })

if __name__ == '__main__':
    # Make sure necessary directories exist
    os.makedirs('downloads', exist_ok=True)
    os.makedirs('merged_properties', exist_ok=True)
    os.makedirs('tmp', exist_ok=True)
    
    # Print working directory for debugging
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"Python executable: {os.path.abspath(os.__file__)}")
    
    # Check if running in Docker
    is_docker = os.environ.get('RUNNING_IN_DOCKER', 'false').lower() == 'true'
    
    # Set debug mode and host based on environment
    debug_mode = not is_docker
    host = '0.0.0.0' if is_docker else '127.0.0.1'
    
    logger.info(f"Starting application with debug={debug_mode}, host={host}")
    app.run(host=host, port=5000, debug=debug_mode)