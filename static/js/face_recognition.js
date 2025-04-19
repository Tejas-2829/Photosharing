/**
 * Face Recognition Settings
 * Handles UI interactions and API calls for face recognition settings
 */

document.addEventListener('DOMContentLoaded', function() {
    // Range input value display updaters
    function initRangeInputs() {
        const minConfidenceInput = document.getElementById('min_confidence');
        const minConfidenceValue = document.getElementById('min_confidence_value');
        if (minConfidenceInput && minConfidenceValue) {
            minConfidenceInput.addEventListener('input', function() {
                minConfidenceValue.textContent = parseFloat(this.value).toFixed(2);
            });
        }
        
        const recognitionToleranceInput = document.getElementById('recognition_tolerance');
        const recognitionToleranceValue = document.getElementById('recognition_tolerance_value');
        if (recognitionToleranceInput && recognitionToleranceValue) {
            recognitionToleranceInput.addEventListener('input', function() {
                recognitionToleranceValue.textContent = parseFloat(this.value).toFixed(2);
            });
        }
    }
    
    // Algorithm card selection
    function initAlgorithmCards() {
        const hogCard = document.getElementById('hog-card');
        const cnnCard = document.getElementById('cnn-card');
        const hogRadio = document.getElementById('hog');
        const cnnRadio = document.getElementById('cnn');
        
        if (hogCard && cnnCard && hogRadio && cnnRadio) {
            hogCard.addEventListener('click', function() {
                hogRadio.checked = true;
                hogCard.classList.add('selected');
                cnnCard.classList.remove('selected');
            });
            
            cnnCard.addEventListener('click', function() {
                cnnRadio.checked = true;
                cnnCard.classList.add('selected');
                hogCard.classList.remove('selected');
            });
        }
        
        // Model size card selection
        const smallCard = document.getElementById('small-card');
        const largeCard = document.getElementById('large-card');
        const smallRadio = document.getElementById('small');
        const largeRadio = document.getElementById('large');
        
        if (smallCard && largeCard && smallRadio && largeRadio) {
            smallCard.addEventListener('click', function() {
                smallRadio.checked = true;
                smallCard.classList.add('selected');
                largeCard.classList.remove('selected');
            });
            
            largeCard.addEventListener('click', function() {
                largeRadio.checked = true;
                largeCard.classList.add('selected');
                smallCard.classList.remove('selected');
            });
        }
    }
    
    // Initialize tooltips
    function initTooltips() {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function(tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
    
    // Fetch current settings from API
    function fetchCurrentSettings() {
        fetch('/api/face_recognition_settings')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(settings => {
                applySettingsToForm(settings);
            })
            .catch(error => {
                console.error('Error fetching face recognition settings:', error);
            });
    }
    
    // Apply fetched settings to the form
    function applySettingsToForm(settings) {
        // Update range inputs
        const minConfidenceInput = document.getElementById('min_confidence');
        const minConfidenceValue = document.getElementById('min_confidence_value');
        if (minConfidenceInput && minConfidenceValue && settings.min_confidence) {
            minConfidenceInput.value = settings.min_confidence;
            minConfidenceValue.textContent = parseFloat(settings.min_confidence).toFixed(2);
        }
        
        const recognitionToleranceInput = document.getElementById('recognition_tolerance');
        const recognitionToleranceValue = document.getElementById('recognition_tolerance_value');
        if (recognitionToleranceInput && recognitionToleranceValue && settings.recognition_tolerance) {
            recognitionToleranceInput.value = settings.recognition_tolerance;
            recognitionToleranceValue.textContent = parseFloat(settings.recognition_tolerance).toFixed(2);
        }
        
        // Update algorithm selection
        if (settings.detection_algorithm) {
            const algorithmRadio = document.getElementById(settings.detection_algorithm);
            if (algorithmRadio) {
                algorithmRadio.checked = true;
                document.getElementById(`${settings.detection_algorithm}-card`).classList.add('selected');
            }
        }
        
        // Update model size selection
        if (settings.face_encoding_model) {
            const modelRadio = document.getElementById(settings.face_encoding_model);
            if (modelRadio) {
                modelRadio.checked = true;
                document.getElementById(`${settings.face_encoding_model}-card`).classList.add('selected');
            }
        }
        
        // Update auto categorize switch
        const autoCategorizeSwitch = document.getElementById('auto_categorize');
        if (autoCategorizeSwitch && settings.auto_categorize !== undefined) {
            autoCategorizeSwitch.checked = settings.auto_categorize;
        }
    }
    
    // Add confirmation prompt for reprocessing
    function initReprocessButtons() {
        document.querySelectorAll('a[href*="process_all_photos"]').forEach(button => {
            button.addEventListener('click', function(e) {
                if (!confirm('This will reprocess all photos in the room using current face recognition settings. This may take some time. Continue?')) {
                    e.preventDefault();
                    return false;
                }
                return true;
            });
        });
    }
    
    // Add preview of how current settings would work
    function createSettingsPreview() {
        const previewContainer = document.querySelector('.settings-section:first-child');
        if (!previewContainer) return;
        
        const previewDiv = document.createElement('div');
        previewDiv.className = 'settings-preview mt-3 p-3 border rounded bg-dark';
        previewDiv.innerHTML = `
            <h6 class="mb-3">How these settings affect recognition</h6>
            <div class="row">
                <div class="col-md-4 text-center mb-3">
                    <div><strong>Low Confidence (0.3)</strong></div>
                    <div class="text-muted small">More faces detected, less accurate</div>
                    <div class="mt-2 border rounded p-2">
                        <i data-feather="user" class="me-1"></i> <i data-feather="user" class="me-1"></i> <i data-feather="user" class="me-1"></i> <i data-feather="user" class="me-1"></i>
                    </div>
                </div>
                <div class="col-md-4 text-center mb-3">
                    <div><strong>Medium Confidence (0.6)</strong></div>
                    <div class="text-muted small">Balanced detection</div>
                    <div class="mt-2 border rounded p-2">
                        <i data-feather="user" class="me-1"></i> <i data-feather="user" class="me-1"></i> <i data-feather="user" class="me-1"></i>
                    </div>
                </div>
                <div class="col-md-4 text-center mb-3">
                    <div><strong>High Confidence (0.8)</strong></div>
                    <div class="text-muted small">Fewer faces, more accurate</div>
                    <div class="mt-2 border rounded p-2">
                        <i data-feather="user" class="me-1"></i> <i data-feather="user" class="me-1"></i>
                    </div>
                </div>
            </div>
        `;
        
        // Insert after the existing sliders
        const insertAfter = document.querySelector('.settings-section:first-child .mb-3:last-child');
        if (insertAfter) {
            insertAfter.after(previewDiv);
            feather.replace();
        }
    }
    
    // Initialize the face recognition settings page
    function initFaceRecognitionSettings() {
        initRangeInputs();
        initAlgorithmCards();
        initTooltips();
        initReprocessButtons();
        createSettingsPreview();
        
        // Fetch current settings from API if the form exists
        if (document.querySelector('form[action*="face_recognition_settings"]')) {
            fetchCurrentSettings();
        }
    }
    
    // Run initialization
    initFaceRecognitionSettings();
});
