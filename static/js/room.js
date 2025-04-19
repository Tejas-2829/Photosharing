/**
 * Room.js
 * Handles interactive features for the room view page
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize lightbox for photos if the library is available
    if (typeof lightbox !== 'undefined') {
        lightbox.option({
            'resizeDuration': 200,
            'wrapAround': true,
            'albumLabel': 'Photo %1 of %2',
            'fadeDuration': 300,
            'imageFadeDuration': 300
        });
    }
    
    // Initialize dropzone for photo uploads if available and if on upload page
    if (typeof Dropzone !== 'undefined' && document.querySelector('.dropzone')) {
        // Extract CSRF token
        const csrfToken = document.querySelector('input[name="csrf_token"]').value;
        const roomId = window.location.pathname.split('/')[2]; // Extract from URL
        
        Dropzone.autoDiscover = false;
        
        const myDropzone = new Dropzone(".dropzone", {
            url: `/room/${roomId}/upload`,
            paramName: "photo",
            maxFilesize: 10, // MB
            acceptedFiles: "image/*",
            addRemoveLinks: true,
            headers: {
                'X-CSRF-TOKEN': csrfToken
            },
            init: function() {
                this.on("sending", function(file, xhr, formData) {
                    formData.append("csrf_token", csrfToken);
                    
                    // Get description from form if available
                    const description = document.getElementById('photo-description');
                    if (description) {
                        formData.append("description", description.value);
                    }
                });
                
                this.on("success", function(file, response) {
                    file.previewElement.classList.add("dz-success");
                });
                
                this.on("error", function(file, errorMessage) {
                    file.previewElement.classList.add("dz-error");
                    
                    // Display the error message
                    let errorDisplay = file.previewElement.querySelector(".dz-error-message");
                    if (errorDisplay) {
                        errorDisplay.textContent = errorMessage;
                    }
                });
                
                this.on("queuecomplete", function() {
                    // Redirect to room page or show success message
                    setTimeout(() => {
                        window.location.href = `/room/${roomId}`;
                    }, 1500);
                });
            }
        });
    }
    
    // Enable filtering photos by tag
    function initPhotoFiltering() {
        const tagFilters = document.querySelectorAll('.tag-filter');
        if (!tagFilters.length) return;
        
        tagFilters.forEach(filter => {
            filter.addEventListener('click', function() {
                const tagName = this.getAttribute('data-tag');
                if (!tagName) return;
                
                // Toggle active state on filter button
                this.classList.toggle('active');
                
                // Get all active filters
                const activeFilters = Array.from(document.querySelectorAll('.tag-filter.active'))
                    .map(el => el.getAttribute('data-tag'));
                
                // Filter photos based on active tags
                const photoCards = document.querySelectorAll('.photo-card');
                
                if (activeFilters.length === 0) {
                    // If no active filters, show all photos
                    photoCards.forEach(card => {
                        card.style.display = '';
                    });
                } else {
                    // Filter photos
                    photoCards.forEach(card => {
                        const photoTags = Array.from(card.querySelectorAll('.badge'))
                            .map(badge => badge.textContent.trim());
                        
                        // Check if photo has at least one of the active tags
                        const hasTag = activeFilters.some(tag => photoTags.includes(tag));
                        card.style.display = hasTag ? '' : 'none';
                    });
                }
            });
        });
    }
    
    // Enable photo tagging functionality
    function initPhotoTagging() {
        const photoContainer = document.querySelector('.photo-container');
        const tagForm = document.getElementById('tag-form');
        if (!photoContainer || !tagForm) return;
        
        let tagBox = null;
        let startX, startY;
        let currentX, currentY;
        let isDrawing = false;
        
        // Create tag box on mousedown
        photoContainer.addEventListener('mousedown', function(e) {
            // Only allow tagging if the form is visible
            if (!tagForm.classList.contains('d-block')) return;
            
            const rect = photoContainer.getBoundingClientRect();
            startX = e.clientX - rect.left;
            startY = e.clientY - rect.top;
            
            tagBox = document.createElement('div');
            tagBox.className = 'tag-box';
            tagBox.style.left = `${startX}px`;
            tagBox.style.top = `${startY}px`;
            tagBox.style.width = '0';
            tagBox.style.height = '0';
            
            photoContainer.appendChild(tagBox);
            isDrawing = true;
            
            // Prevent text selection
            e.preventDefault();
        });
        
        // Resize tag box on mousemove
        document.addEventListener('mousemove', function(e) {
            if (!isDrawing || !tagBox) return;
            
            const rect = photoContainer.getBoundingClientRect();
            currentX = e.clientX - rect.left;
            currentY = e.clientY - rect.top;
            
            // Ensure coordinates are within the container
            currentX = Math.max(0, Math.min(currentX, rect.width));
            currentY = Math.max(0, Math.min(currentY, rect.height));
            
            // Calculate width and height
            const width = Math.abs(currentX - startX);
            const height = Math.abs(currentY - startY);
            
            // Calculate top-left position
            const left = Math.min(startX, currentX);
            const top = Math.min(startY, currentY);
            
            // Update tag box
            tagBox.style.left = `${left}px`;
            tagBox.style.top = `${top}px`;
            tagBox.style.width = `${width}px`;
            tagBox.style.height = `${height}px`;
            
            // Update form inputs
            document.getElementById('x').value = left / rect.width;
            document.getElementById('y').value = top / rect.height;
            document.getElementById('width').value = width / rect.width;
            document.getElementById('height').value = height / rect.height;
        });
        
        // Finalize tag box on mouseup
        document.addEventListener('mouseup', function() {
            if (isDrawing) {
                isDrawing = false;
                
                // Show the tag input if we have a reasonable size box
                const width = parseFloat(tagBox.style.width);
                const height = parseFloat(tagBox.style.height);
                
                if (width > 20 && height > 20) {
                    // Position the tag form near the tag box
                    tagForm.style.display = 'block';
                    document.getElementById('tag_name').focus();
                } else {
                    // Remove small tag boxes
                    if (tagBox && tagBox.parentNode) {
                        tagBox.parentNode.removeChild(tagBox);
                    }
                    tagBox = null;
                }
            }
        });
        
        // Cancel tagging operation
        document.getElementById('cancel-tag-button').addEventListener('click', function() {
            if (tagBox && tagBox.parentNode) {
                tagBox.parentNode.removeChild(tagBox);
            }
            tagBox = null;
            tagForm.style.display = 'none';
        });
        
        // Show tag form when "Tag Photo" button is clicked
        const tagPhotoButton = document.getElementById('tag-photo-button');
        if (tagPhotoButton) {
            tagPhotoButton.addEventListener('click', function() {
                tagForm.classList.toggle('d-block');
                this.classList.toggle('active');
                
                if (!tagForm.classList.contains('d-block')) {
                    // If hiding the form, also remove any in-progress tag box
                    if (tagBox && tagBox.parentNode) {
                        tagBox.parentNode.removeChild(tagBox);
                    }
                    tagBox = null;
                }
            });
        }
    }
    
    // Enable album selection dropdown
    function initAlbumSelection() {
        const albumSelect = document.getElementById('album_id');
        if (!albumSelect) return;
        
        albumSelect.addEventListener('change', function() {
            const selectedAlbum = this.options[this.selectedIndex].text;
            document.getElementById('selected-album-name').textContent = selectedAlbum;
        });
    }
    
    // Initialize room features based on current tab
    function initRoomTabs() {
        // Handle tab switching
        const tabs = document.querySelectorAll('button[data-bs-toggle="tab"]');
        tabs.forEach(tab => {
            tab.addEventListener('shown.bs.tab', function(e) {
                // You could load tab-specific content here via AJAX if needed
                const targetTab = e.target.getAttribute('aria-controls');
                
                // Example: load albums content when switching to albums tab
                if (targetTab === 'albums' && !document.querySelector('.albums-loaded')) {
                    // This would typically be an AJAX call in a real app
                    console.log('Albums tab activated - could load content dynamically');
                }
            });
        });
    }
    
    // Display existing tag boxes on photo
    function showExistingTags() {
        const photoContainer = document.querySelector('.photo-container');
        const tags = document.querySelectorAll('.photo-tag[data-coordinates]');
        if (!photoContainer || !tags.length) return;
        
        const photoWidth = photoContainer.offsetWidth;
        const photoHeight = photoContainer.offsetHeight;
        
        tags.forEach(tag => {
            try {
                const coordinates = JSON.parse(tag.getAttribute('data-coordinates'));
                if (!coordinates) return;
                
                const tagBox = document.createElement('div');
                tagBox.className = 'tag-box';
                tagBox.style.left = `${coordinates.x * photoWidth}px`;
                tagBox.style.top = `${coordinates.y * photoHeight}px`;
                tagBox.style.width = `${coordinates.width * photoWidth}px`;
                tagBox.style.height = `${coordinates.height * photoHeight}px`;
                
                // Add tag name as tooltip
                tagBox.title = tag.getAttribute('data-name');
                
                photoContainer.appendChild(tagBox);
            } catch (e) {
                console.error('Error parsing tag coordinates:', e);
            }
        });
    }
    
    // Initialize the room page
    function initRoomPage() {
        initPhotoFiltering();
        initPhotoTagging();
        initAlbumSelection();
        initRoomTabs();
        showExistingTags();
    }
    
    // Run initialization
    initRoomPage();
});
