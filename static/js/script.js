document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const searchForm = document.getElementById('search-form');
    const formContainer = document.getElementById('form-container');
    const progressContainer = document.getElementById('progress-container');
    const progressBar = document.getElementById('progress-bar');
    const statusMessage = document.getElementById('status-message');
    const downloadContainer = document.getElementById('download-container');
    const downloadBtn = document.getElementById('download-btn');
    const errorContainer = document.getElementById('error-container');
    const errorMessage = document.getElementById('error-message');
    const resetBtn = document.getElementById('resetBtn');
    
    // Create modal instance
    const confirmModal = new bootstrap.Modal(document.getElementById('confirmationModal'));
    const confirmBtn = document.getElementById('confirmBtn');
    
    // Current job ID and status check interval
    let currentJobId = null;
    let statusInterval = null;
    
    // Form submission
    searchForm.addEventListener('submit', function(e) {
        e.preventDefault();
        confirmModal.show();
    });
    
    // Confirmation button click
    confirmBtn.addEventListener('click', function() {
        confirmModal.hide();
        startProcessing();
    });
    
    // Reset button click
    resetBtn.addEventListener('click', function() {
        resetUI();
        fetch('/api/reset', { method: 'POST' });
    });
    
    // Start processing function
    function startProcessing() {
        // Show progress, hide form
        formContainer.classList.add('d-none');
        progressContainer.classList.remove('d-none');
        
        // Hide download and error containers
        downloadContainer.classList.add('d-none');
        errorContainer.classList.add('d-none');
        
        // Initialize progress
        progressBar.style.width = '5%';
        statusMessage.textContent = 'Submitting request...';
        
        // Prepare form data
        const formData = new FormData(searchForm);
        
        // Submit request
        fetch('/api/process', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            currentJobId = data.job_id;
            
            // Start checking status
            statusInterval = setInterval(checkStatus, 2000);
        })
        .catch(error => {
            console.error('Error:', error);
            showError('Failed to submit request. Please try again.');
        });
    }
    
    // Check job status
    function checkStatus() {
        if (!currentJobId) return;
        
        fetch(`/api/status/${currentJobId}`)
        .then(response => response.json())
        .then(data => {
            // Update progress
            progressBar.style.width = `${data.progress}%`;
            statusMessage.textContent = data.message;
            
            // Check if completed
            if (data.status === 'completed' && data.result_file) {
                clearInterval(statusInterval);
                downloadBtn.href = `/api/download/${currentJobId}`;
                downloadContainer.classList.remove('d-none');
            }
            
            // Check if error
            if (data.status === 'error') {
                clearInterval(statusInterval);
                showError(data.message);
            }
        })
        .catch(error => {
            console.error('Error checking status:', error);
            // Don't show error, just keep checking
        });
    }
    
    // Show error message
    function showError(message) {
        errorMessage.textContent = message;
        errorContainer.classList.remove('d-none');
    }
    
    // Reset UI
    function resetUI() {
        // Clear interval if running
        if (statusInterval) {
            clearInterval(statusInterval);
            statusInterval = null;
        }
        
        // Reset job ID
        currentJobId = null;
        
        // Show form, hide progress
        formContainer.classList.remove('d-none');
        progressContainer.classList.add('d-none');
        
        // Hide download and error containers
        downloadContainer.classList.add('d-none');
        errorContainer.classList.add('d-none');
        
        // Reset form
        searchForm.reset();
    }
});