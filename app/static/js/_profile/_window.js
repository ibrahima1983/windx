
// Image handling functions for profile entry
window.openImageModal = function(imageSrc) {
    // Create modal overlay
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50';
    modal.style.zIndex = '9999';

    // Create modal content
    modal.innerHTML = `
        <div class="relative max-w-4xl max-h-full p-4">
            <button class="absolute top-2 right-2 text-white text-2xl hover:text-gray-300 z-10" onclick="this.closest('.fixed').remove()">
                ×
            </button>
            <img src="${imageSrc}" alt="Preview" class="max-w-full max-h-full object-contain rounded shadow-lg">
        </div>
    `;

    // Close on click outside
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            modal.remove();
        }
    });

    // Close on escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            modal.remove();
        }
    }, { once: true });

    document.body.appendChild(modal);
};

window.handleInlineImageChange = function(rowId, field, event) {
    console.log('🦆 [UPLOAD DEBUG] ========================================');
    console.log('🦆 [UPLOAD DEBUG] handleInlineImageChange called');
    console.log('🦆 [UPLOAD DEBUG] rowId:', rowId);
    console.log('🦆 [UPLOAD DEBUG] field:', field);
    console.log('🦆 [UPLOAD DEBUG] event:', event);
    console.log('🦆 [UPLOAD DEBUG] event.target:', event.target);
    console.log('🦆 [UPLOAD DEBUG] event.target.files:', event.target.files);

    const file = event.target.files[0];
    console.log('🦆 [UPLOAD DEBUG] Selected file:', file);

    if (!file) {
        console.log('🦆 [UPLOAD DEBUG] ❌ No file selected');
        return;
    }

    console.log('🦆 [UPLOAD DEBUG] File details:');
    console.log('🦆 [UPLOAD DEBUG] - name:', file.name);
    console.log('🦆 [UPLOAD DEBUG] - size:', file.size);
    console.log('🦆 [UPLOAD DEBUG] - type:', file.type);
    console.log('🦆 [UPLOAD DEBUG] - lastModified:', file.lastModified);

    // Validate file type
    if (!file.type.startsWith('image/')) {
        console.log('🦆 [UPLOAD DEBUG] ❌ Invalid file type:', file.type);
        alert('Please select an image file');
        return;
    }
    console.log('🦆 [UPLOAD DEBUG] ✅ File type validation passed');

    // Validate file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
        console.log('🦆 [UPLOAD DEBUG] ❌ File too large:', file.size);
        alert('Image file must be smaller than 5MB');
        return;
    }
    console.log('🦆 [UPLOAD DEBUG] ✅ File size validation passed');

    // Create FormData for upload
    console.log('🦆 [UPLOAD DEBUG] Creating FormData...');
    const formData = new FormData();
    formData.append('file', file);

    console.log('🦆 [UPLOAD DEBUG] FormData created:');
    console.log('🦆 [UPLOAD DEBUG] - FormData entries:', [...formData.entries()]);

    // Show loading state
    const loadingText = 'Uploading...';
    console.log('🦆 [UPLOAD DEBUG] Starting upload...');

    // Upload the file with credentials for authentication
    fetch('/api/v1/admin/entry/upload-image', {
        method: 'POST',
        credentials: 'include',  // Include cookies for authentication
        body: formData
    })
    .then(response => {
        console.log('🦆 [UPLOAD DEBUG] Response received:');
        console.log('🦆 [UPLOAD DEBUG] - status:', response.status);
        console.log('🦆 [UPLOAD DEBUG] - statusText:', response.statusText);
        console.log('🦆 [UPLOAD DEBUG] - ok:', response.ok);
        console.log('🦆 [UPLOAD DEBUG] - headers:', Object.fromEntries(response.headers.entries()));

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('🦆 [UPLOAD DEBUG] Response data:', data);

        if (data.success) {
            console.log('🦆 [UPLOAD DEBUG] ✅ Upload successful!');
            console.log('🦆 [UPLOAD DEBUG] - filename:', data.filename);
            console.log('🦆 [UPLOAD DEBUG] - url:', data.url);
            console.log('🦆 [UPLOAD DEBUG] - message:', data.message);

            // Update the row data with the new filename or URL
            console.log('🦆 [UPLOAD DEBUG] Looking for Alpine app...');

            // Try multiple ways to get the Alpine app instance
            let app = null;

            // Method 1: Alpine store
            if (window.Alpine && window.Alpine.store) {
                app = window.Alpine.store('profileEntry');
                console.log('🦆 [UPLOAD DEBUG] Method 1 (Alpine.store):', app);
            }

            // Method 2: Global window reference
            if (!app && window.profileEntryApp) {
                app = window.profileEntryApp;
                console.log('🦆 [UPLOAD DEBUG] Method 2 (window.profileEntryApp):', app);
            }

            // Method 3: Try to find Alpine component in DOM
            if (!app) {
                const profileContainer = document.querySelector('[x-data*="profileEntryApp"]');
                console.log('🦆 [UPLOAD DEBUG] Profile container found:', profileContainer);

                if (profileContainer && profileContainer._x_dataStack) {
                    app = profileContainer._x_dataStack[0];
                    console.log('🦆 [UPLOAD DEBUG] Method 3 (DOM search):', app);
                } else if (profileContainer && window.Alpine) {
                    // Try Alpine.$data method
                    try {
                        app = window.Alpine.$data(profileContainer);
                        console.log('🦆 [UPLOAD DEBUG] Method 3b (Alpine.$data):', app);
                    } catch (e) {
                        console.log('🦆 [UPLOAD DEBUG] Alpine.$data failed:', e);
                    }
                }
            }

            // Method 4: Try to access Alpine component data directly
            if (!app) {
                const profileContainer = document.querySelector('[x-data*="profileEntryApp"]');
                if (profileContainer && profileContainer.__x) {
                    app = profileContainer.__x.$data;
                    console.log('🦆 [UPLOAD DEBUG] Method 4 (__x.$data):', app);
                }
            }

            console.log('🦆 [UPLOAD DEBUG] Final app:', app);
            console.log('🦆 [UPLOAD DEBUG] app type:', typeof app);
            console.log('🦆 [UPLOAD DEBUG] app.savedConfigurations:', app?.savedConfigurations);

            // If app is a function, it means we got the factory function, not the instance
            if (typeof app === 'function') {
                console.log('🦆 [UPLOAD DEBUG] App is a function, trying to find the actual instance...');

                // Try to find the actual Alpine.js instance in the DOM
                const profileContainer = document.querySelector('[x-data*="profileEntryApp"]');
                if (profileContainer) {
                    console.log('🦆 [UPLOAD DEBUG] Found profile container, checking for Alpine data...');

                    // Try different ways to access Alpine data
                    if (profileContainer._x_dataStack && profileContainer._x_dataStack[0]) {
                        app = profileContainer._x_dataStack[0];
                        console.log('🦆 [UPLOAD DEBUG] Found via _x_dataStack:', app);
                    } else if (profileContainer.__x && profileContainer.__x.$data) {
                        app = profileContainer.__x.$data;
                        console.log('🦆 [UPLOAD DEBUG] Found via __x.$data:', app);
                    } else {
                        console.log('🦆 [UPLOAD DEBUG] Could not find Alpine instance, will use DOM fallback');
                        app = null; // Force DOM fallback
                    }
                }
            }

            if (app && app.savedConfigurations) {
                console.log('🦆 [UPLOAD DEBUG] Searching for row with id:', rowId);
                console.log('🦆 [UPLOAD DEBUG] Available row IDs:', app.savedConfigurations.map(r => r.id));

                const row = app.savedConfigurations.find(r => r.id === rowId);
                console.log('🦆 [UPLOAD DEBUG] Found row:', row);

                if (row) {
                    console.log('🦆 [UPLOAD DEBUG] Row before update:', JSON.stringify(row));

                    // Use the URL for display if available, otherwise use filename
                    const displayValue = data.url || data.filename;
                    console.log('🦆 [UPLOAD DEBUG] Setting display value:', displayValue);
                    console.log('🦆 [UPLOAD DEBUG] Field to update:', field);

                    // Update the row data
                    row[field] = displayValue;

                    console.log('🦆 [UPLOAD DEBUG] Row after update:', JSON.stringify(row));

                    // Force Alpine.js reactivity by creating a new array reference
                    app.savedConfigurations = [...app.savedConfigurations];
                    console.log('🦆 [UPLOAD DEBUG] Forced Alpine reactivity update');

                    // Also update pending edits - use filename for database storage
                    if (!app.pendingEdits) {
                        app.pendingEdits = {};
                    }
                    if (!app.pendingEdits[rowId]) {
                        app.pendingEdits[rowId] = {};
                    }
                    app.pendingEdits[rowId][field] = data.filename; // Store filename in database
                    app.hasUnsavedEdits = true;

                    console.log('🦆 [UPLOAD DEBUG] Updated pending edits:', app.pendingEdits);
                    console.log('🦆 [UPLOAD DEBUG] hasUnsavedEdits set to:', app.hasUnsavedEdits);

                    // Force Alpine.js to detect the change
                    setTimeout(() => {
                        console.log('🦆 [UPLOAD DEBUG] Post-update hasUnsavedEdits check:', app.hasUnsavedEdits);
                    }, 100);
                } else {
                    console.log('🦆 [UPLOAD DEBUG] ❌ Row not found with id:', rowId);
                    console.log('🦆 [UPLOAD DEBUG] Available rows:', app.savedConfigurations);
                }

                // Cancel editing mode
                console.log('🦆 [UPLOAD DEBUG] Canceling editing mode...');
                app.cancelEditing();

                // Force a small delay to ensure Alpine.js processes the changes
                setTimeout(() => {
                    console.log('🦆 [UPLOAD DEBUG] Post-update check - editingCell:', app.editingCell);
                    console.log('🦆 [UPLOAD DEBUG] Post-update check - row data:', app.savedConfigurations.find(r => r.id === rowId));
                }, 100);

            } else {
                console.log('🦆 [UPLOAD DEBUG] ❌ App or savedConfigurations not available, trying manual DOM update...');

                // Fallback: Try to update the DOM directly
                const tableCell = document.querySelector(`[data-row-id="${rowId}"][data-field="${field}"]`);
                if (tableCell) {
                    console.log('🦆 [UPLOAD DEBUG] Found table cell, updating directly');
                    const displayValue = data.url || data.filename;

                    // Create image element
                    const img = document.createElement('img');
                    img.src = displayValue;
                    img.alt = `Image for ${field}`;
                    img.className = 'h-12 w-12 object-cover rounded border shadow-sm cursor-pointer hover:shadow-md transition-shadow';
                    img.onclick = () => window.openImageModal && window.openImageModal(displayValue);

                    // Replace cell content
                    tableCell.innerHTML = '';
                    tableCell.appendChild(img);
                } else {
                    console.log('🦆 [UPLOAD DEBUG] ❌ Could not find table cell to update');
                }

                // Try to set hasUnsavedEdits flag even if we don't have savedConfigurations
                if (app && typeof app === 'object' && app.hasUnsavedEdits !== undefined) {
                    console.log('🦆 [UPLOAD DEBUG] Setting hasUnsavedEdits flag on Alpine instance...');

                    // Initialize pendingEdits if it doesn't exist
                    if (!app.pendingEdits) {
                        app.pendingEdits = {};
                    }
                    if (!app.pendingEdits[rowId]) {
                        app.pendingEdits[rowId] = {};
                    }

                    // Store the filename for database commit
                    app.pendingEdits[rowId][field] = data.filename;
                    app.hasUnsavedEdits = true;

                    console.log('🦆 [UPLOAD DEBUG] Updated pendingEdits:', app.pendingEdits);
                    console.log('🦆 [UPLOAD DEBUG] hasUnsavedEdits set to:', app.hasUnsavedEdits);
                } else {
                    console.log('🦆 [UPLOAD DEBUG] Could not set hasUnsavedEdits - trying DOM manipulation...');

                    // Try to find and manipulate the Alpine component directly
                    const profileContainer = document.querySelector('[x-data*="profileEntryApp"]');
                    if (profileContainer) {
                        // Try to trigger Alpine.js reactivity by dispatching a custom event
                        const event = new CustomEvent('image-uploaded', {
                            detail: {
                                rowId,
                                field,
                                filename: data.filename,
                                url: data.url || data.filename
                            }
                        });
                        profileContainer.dispatchEvent(event);
                        console.log('🦆 [UPLOAD DEBUG] Dispatched image-uploaded event with URL:', data.url);
                    }
                }

                // Still try to cancel editing if we have an app
                if (app && app.cancelEditing) {
                    app.cancelEditing();
                }
            }

            if (window.showToast) {
                window.showToast('Image uploaded successfully', 'success');
            }
        } else {
            console.log('🦆 [UPLOAD DEBUG] ❌ Upload failed:', data.error);
            alert('Failed to upload image: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.log('🦆 [UPLOAD DEBUG] ❌ Upload error caught:', error);
        console.log('🦆 [UPLOAD DEBUG] Error details:', error.message);
        console.log('🦆 [UPLOAD DEBUG] Error stack:', error.stack);
        alert('Failed to upload image: ' + error.message);
    });

    console.log('🦆 [UPLOAD DEBUG] ========================================');
};