from flask import Flask, render_template, request, jsonify, send_file
import os
import threading
import time
import uuid
import json
from werkzeug.utils import secure_filename

# Import main function from rpdata_scraper
from rpdata_scraper.main import main

app = Flask(__name__)

# Ensure necessary directory exists
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
    
    # Always use headless mode
    headless = True
    
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

def run_job(job_id, locations, property_types, min_floor_area, max_floor_area, business_type, headless):
    """Run the main processing job in a background thread"""
    try:
        update_job_status(job_id, 'running', 5, 'Initializing search...')
        
        # Call main function from rpdata_scraper
        result = main(
            locations=locations,
            property_types=property_types,
            min_floor_area=min_floor_area,
            max_floor_area=max_floor_area,
            business_type=business_type,
            headless=headless
        )
        
        # Check if processing was successful
        if result:
            # Get the file from rpdata_scraper/merged_properties folder
            merged_dir = os.path.join('rpdata_scraper', 'merged_properties')
            files = os.listdir(merged_dir)
            if files:
                # Should only be one file in the folder
                result_file = os.path.join(merged_dir, files[0])
                update_job_status(job_id, 'completed', 100, 'Processing complete!', result_file)
            else:
                update_job_status(job_id, 'error', 0, 'Processing completed but no file was generated')
        else:
            update_job_status(job_id, 'error', 0, 'Processing failed')
    
    except Exception as e:
        update_job_status(job_id, 'error', 0, f'An error occurred: {str(e)}')

def update_job_status(job_id, status, progress, message, result_file=None):
    """Update the status of a job"""
    jobs[job_id] = {
        'status': status,
        'progress': progress,
        'message': message,
        'result_file': result_file
    }
    
    # Save to file in case server restarts
    with open(f'tmp/{job_id}.json', 'w') as f:
        json.dump(jobs[job_id], f)

@app.route('/api/status/<job_id>')
def job_status(job_id):
    """Get the status of a job"""
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
    except:
        return jsonify({'error': 'Job not found'}), 404

@app.route('/api/download/<job_id>')
def download_file(job_id):
    """Download the generated Excel file"""
    # Get job status
    status = None
    if job_id in jobs:
        status = jobs[job_id]
    else:
        # Try to load from disk
        try:
            with open(f'tmp/{job_id}.json', 'r') as f:
                status = json.load(f)
        except:
            pass
    
    if not status or status.get('status') != 'completed' or not status.get('result_file'):
        return jsonify({'error': 'File not ready or does not exist'}), 404
    
    # Get the file path
    file_path = status.get('result_file')
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    
    # Send the file
    return send_file(
        file_path,
        as_attachment=True,
        download_name=os.path.basename(file_path)
    )

@app.route('/api/reset', methods=['POST'])
def reset():
    """Reset the job (just for UI state, doesn't cancel running jobs)"""
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True)