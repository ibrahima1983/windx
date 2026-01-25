class ImageHandler {
    static isImageField(fieldName) {
        console.log('🦆 [IMAGE FIELD DEBUG] isImageField called with:', fieldName);
        
        if (!fieldName) {
            console.log('🦆 [IMAGE FIELD DEBUG] ❌ No fieldName provided');
            return false;
        }
        
        const imageFields = ['pic', 'image', 'photo', 'picture', 'img', 'thumbnail', 'avatar', 'logo'];
        const fieldNameLower = fieldName.toLowerCase();
        
        console.log('🦆 [IMAGE FIELD DEBUG] fieldNameLower:', fieldNameLower);
        console.log('🦆 [IMAGE FIELD DEBUG] imageFields:', imageFields);
        
        const isImage = imageFields.some(imgField => {
            const matches = fieldNameLower.includes(imgField);
            console.log(`🦆 [IMAGE FIELD DEBUG] Checking "${imgField}" in "${fieldNameLower}":`, matches);
            return matches;
        });
        
        console.log('🦆 [IMAGE FIELD DEBUG] Final result:', isImage);
        return isImage;
    }

    static getImageUrl(filename) {
        console.log('🦆 [IMAGE URL DEBUG] getImageUrl called with:', filename);
        
        // Handle both full URLs and relative filenames
        if (!filename || filename === 'N/A') {
            console.log('🦆 [IMAGE URL DEBUG] No filename or N/A, returning empty string');
            return '';
        }
        
        // If it's already a full URL (starts with http), return as-is
        if (filename.startsWith('http')) {
            console.log('🦆 [IMAGE URL DEBUG] Full URL detected, returning as-is:', filename);
            return filename;
        }
        
        // If it starts with a path separator, it's a relative URL
        if (filename.startsWith('/')) {
            console.log('🦆 [IMAGE URL DEBUG] Relative URL detected, adding cache buster');
            // Add cache-busting parameter
            const cacheBuster = `?t=${Date.now()}`;
            const urlWithCache = filename + cacheBuster;
            console.log('🦆 [IMAGE URL DEBUG] URL with cache buster:', urlWithCache);
            return urlWithCache;
        }
        
        // Otherwise, assume it's a filename and construct the URL
        const constructedUrl = `/static/uploads/${filename}?t=${Date.now()}`;
        console.log('🦆 [IMAGE URL DEBUG] Constructed URL with cache buster:', constructedUrl);
        return constructedUrl;
    }

    static handleFileChange(fieldName, event, updateFieldCallback, imagePreviews, setImagePreviewsCallback) {
        console.log('🦆 [MAIN FORM UPLOAD DEBUG] ========================================');
        console.log('🦆 [MAIN FORM UPLOAD DEBUG] handleFileChange called');
        console.log('🦆 [MAIN FORM UPLOAD DEBUG] fieldName:', fieldName);
        console.log('🦆 [MAIN FORM UPLOAD DEBUG] event:', event);
        console.log('🦆 [MAIN FORM UPLOAD DEBUG] event.target:', event.target);
        console.log('🦆 [MAIN FORM UPLOAD DEBUG] event.target.files:', event.target.files);
        
        const file = event.target.files[0];
        console.log('🦆 [MAIN FORM UPLOAD DEBUG] Selected file:', file);
        
        if (!file) {
            console.log('🦆 [MAIN FORM UPLOAD DEBUG] ❌ No file selected');
            return;
        }
        
        console.log('🦆 [MAIN FORM UPLOAD DEBUG] File details:');
        console.log('🦆 [MAIN FORM UPLOAD DEBUG] - name:', file.name);
        console.log('🦆 [MAIN FORM UPLOAD DEBUG] - size:', file.size);
        console.log('🦆 [MAIN FORM UPLOAD DEBUG] - type:', file.type);

        // Update form data with filename
        console.log('🦆 [MAIN FORM UPLOAD DEBUG] Updating form data with filename:', file.name);
        updateFieldCallback(fieldName, file.name);

        // Create image preview if it's an image
        if (file.type.startsWith('image/')) {
            console.log('🦆 [MAIN FORM UPLOAD DEBUG] Creating image preview...');
            const reader = new FileReader();
            reader.onload = (e) => {
                console.log('🦆 [MAIN FORM UPLOAD DEBUG] FileReader loaded, creating preview');
                // Force Alpine.js reactivity using spread
                const updatedPreviews = {
                    ...imagePreviews,
                    [fieldName]: e.target.result
                };
                setImagePreviewsCallback(updatedPreviews);
                console.log('🦆 [MAIN FORM UPLOAD DEBUG] Image preview created for:', fieldName);
            };
            reader.readAsDataURL(file);
        } else {
            console.log('🦆 [MAIN FORM UPLOAD DEBUG] Not an image file, skipping preview');
        }
        
        console.log('🦆 [MAIN FORM UPLOAD DEBUG] ========================================');
    }

    static clearFile(fieldName, updateFieldCallback, imagePreviews, setImagePreviewsCallback) {
        updateFieldCallback(fieldName, '');
        // Create a copy and delete to trigger reactivity
        const updatedPreviews = { ...imagePreviews };
        delete updatedPreviews[fieldName];
        setImagePreviewsCallback(updatedPreviews);

        // Clear the file input element if it exists
        const input = document.getElementById(fieldName);
        if (input) {
            input.value = '';
        }
    }

    static debugImageField(header, rowValue) {
        console.log('🦆 [TEMPLATE DEBUG] debugImageField called');
        console.log('🦆 [TEMPLATE DEBUG] - header:', header);
        console.log('🦆 [TEMPLATE DEBUG] - rowValue:', rowValue);
        console.log('🦆 [TEMPLATE DEBUG] - header.toLowerCase():', header.toLowerCase());
        console.log('🦆 [TEMPLATE DEBUG] - header.toLowerCase() === "pic":', header.toLowerCase() === 'pic');
        console.log('🦆 [TEMPLATE DEBUG] - rowValue exists:', !!rowValue);
        console.log('🦆 [TEMPLATE DEBUG] - rowValue !== "N/A":', rowValue !== 'N/A');
        console.log('🦆 [TEMPLATE DEBUG] - should show image:', header.toLowerCase() === 'pic' && rowValue && rowValue !== 'N/A');
        return header.toLowerCase() === 'pic' && rowValue && rowValue !== 'N/A';
    }
}