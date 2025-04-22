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
    const cancelBtn = document.getElementById('cancelBtn');
    const backBtn = document.getElementById('backBtn');
    const locationsInput = document.getElementById('locations');
    
    // Create modal instances
    const confirmModal = new bootstrap.Modal(document.getElementById('confirmationModal'));
    const confirmBtn = document.getElementById('confirmBtn');
    
    const cancelModal = new bootstrap.Modal(document.getElementById('cancelModal'));
    const confirmCancelBtn = document.getElementById('confirmCancelBtn');
    
    const backModal = new bootstrap.Modal(document.getElementById('backModal'));
    const confirmBackBtn = document.getElementById('confirmBackBtn');
    
    // Current job ID and status check interval
    let currentJobId = null;
    let statusInterval = null;
    let isProcessing = false;
    
    // Function to validate locations input
    function validateLocations(locationsText) {
        if (!locationsText.trim()) {
            return { isValid: false, message: "Please enter at least one location." };
        }
        
        const locations = locationsText.split(',').map(loc => loc.trim());
        const validStates = ['NSW', 'QLD', 'VIC', 'TAS', 'WA', 'SA', 'ACT', 'NT'];
        
        for (let i = 0; i < locations.length; i++) {
            const location = locations[i];
            const parts = location.split(' ');
            
            // Check if we have at least 3 parts (suburb, state, postcode)
            if (parts.length < 3) {
                return { 
                    isValid: false, 
                    message: `Location "${location}" is invalid. Format should be "Suburb State Postcode".` 
                };
            }
            
            // The last part should be the postcode
            const postcode = parts[parts.length - 1];
            // The second last part should be the state
            const state = parts[parts.length - 2];
            // Everything else is the suburb
            const suburb = parts.slice(0, parts.length - 2).join(' ');
            
            // Check if postcode is a 4-digit number
            if (!/^\d{4}$/.test(postcode)) {
                return { 
                    isValid: false, 
                    message: `Invalid postcode "${postcode}" in "${location}". Postcode must be a 4-digit number.` 
                };
            }

            // Check if state is valid
            if (!validStates.includes(state)) {
                return { 
                    isValid: false, 
                    message: `Invalid state "${state}" in "${location}". State must be one of: NSW, QLD, VIC, TAS, WA, SA, ACT, NT.` 
                };
            }

            // Check if suburb is present
            if (!suburb) {
                return { 
                    isValid: false, 
                    message: `Missing suburb in "${location}". Format should be "Suburb State Postcode".` 
                };
            }
            
        }
        
        return { isValid: true };
    }
    
    // Function to show location validation error message
    function showLocationError(message) {
        // Create or update error message element
        let errorElement = document.getElementById('locations-error');
        if (!errorElement) {
            errorElement = document.createElement('div');
            errorElement.id = 'locations-error';
            errorElement.className = 'alert alert-danger mt-2';
            locationsInput.parentNode.appendChild(errorElement);
        }
        
        errorElement.textContent = message;
        
        // Highlight the input
        locationsInput.classList.add('is-invalid');
        
        // Remove error after user starts typing again
        locationsInput.addEventListener('input', function() {
            const errorElement = document.getElementById('locations-error');
            if (errorElement) {
                errorElement.remove();
            }
            locationsInput.classList.remove('is-invalid');
        }, { once: true });
    }
    
    // Form submission with validation
    searchForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Validate locations
        const locationsValidation = validateLocations(locationsInput.value);
        
        if (!locationsValidation.isValid) {
            // Show error message
            showLocationError(locationsValidation.message);
            return;
        }
        
        // If validation passes, show confirmation modal
        confirmModal.show();
    });
    
    // Confirmation button click
    confirmBtn.addEventListener('click', function() {
        confirmModal.hide();
        startProcessing();
    });
    
    // Reset button click - only works on main form page
    resetBtn.addEventListener('click', function() {
        // Only allow reset if not currently processing
        if (!isProcessing) {
            searchForm.reset();
            
            // Clear any location validation errors
            const errorElement = document.getElementById('locations-error');
            if (errorElement) {
                errorElement.remove();
            }
            locationsInput.classList.remove('is-invalid');
        }
    });
    
    // Back button click - shows confirmation dialog
    if (backBtn) {
        backBtn.addEventListener('click', function() {
            // If we're not processing or if we have results ready, go back without confirmation
            if (!isProcessing || downloadContainer.classList.contains('d-none') === false) {
                resetUI();
            } else {
                // Otherwise show confirmation modal
                backModal.show();
            }
        });
    }
    
    // Confirm back button click
    if (confirmBackBtn) {
        confirmBackBtn.addEventListener('click', function() {
            backModal.hide();
            cancelCurrentJob();
        });
    }
    
    // Cancel button click - shows confirmation modal
    if (cancelBtn) {
        cancelBtn.addEventListener('click', function() {
            cancelModal.show();
        });
    }
    
    // Confirm cancel button click
    if (confirmCancelBtn) {
        confirmCancelBtn.addEventListener('click', function() {
            cancelModal.hide();
            cancelCurrentJob();
        });
    }
    
    // Function to cancel the current job
    function cancelCurrentJob() {
        if (!currentJobId) return;
        
        // Show cancelling message
        statusMessage.textContent = 'Cancelling job...';
        
        // Send cancel request to server
        fetch('/api/cancel', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ job_id: currentJobId })
        })
        .then(response => response.json())
        .then(data => {
            clearInterval(statusInterval);
            statusInterval = null;
            
            // Reset UI after cancellation
            resetUI();
        })
        .catch(error => {
            console.error('Error cancelling job:', error);
            // Still try to reset UI
            resetUI();
        });
    }
    
    // Start processing function
    function startProcessing() {
        // Mark as processing
        isProcessing = true;
        
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
            isProcessing = false;
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
            
            // Check if cancelled
            if (data.status === 'cancelled') {
                clearInterval(statusInterval);
                statusInterval = null;
                resetUI();
                return;
            }
            
            // Check if completed
            if (data.status === 'completed' && data.result_file) {
                clearInterval(statusInterval);
                statusInterval = null;
                downloadBtn.href = `/api/download/${currentJobId}`;
                downloadContainer.classList.remove('d-none');
                isProcessing = false; // No longer processing once complete
            }
            
            // Check if error
            if (data.status === 'error') {
                clearInterval(statusInterval);
                statusInterval = null;
                showError(data.message);
                isProcessing = false;
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
        
        // Set processing state to false
        isProcessing = false;
        
        // Show form, hide progress
        formContainer.classList.remove('d-none');
        progressContainer.classList.add('d-none');
        
        // Hide download and error containers
        downloadContainer.classList.add('d-none');
        errorContainer.classList.add('d-none');
        
        // Clear any location validation errors
        const errorElement = document.getElementById('locations-error');
        if (errorElement) {
            errorElement.remove();
        }
        locationsInput.classList.remove('is-invalid');
    }
});