/**
 * Relations Manager
 * 
 * JavaScript module for managing hierarchical option dependencies.
 * Handles entity CRUD and image uploads.
 */

const RelationsManager = {
    // API base URL
    API_BASE: '/api/v1/admin/relations',
    
    // Image data storage (base64)
    imageData: {},
    
    /**
     * Initialize the Relations Manager
     */
    init() {
        this.setupDragAndDrop();
        console.log('RelationsManager initialized');
    },
    
    /**
     * Setup drag and drop for image containers
     */
    setupDragAndDrop() {
        document.querySelectorAll('.image-upload-box').forEach(container => {
            container.addEventListener('dragover', (e) => {
                e.preventDefault();
                container.style.borderColor = 'var(--primary)';
                container.style.backgroundColor = '#eff6ff';
            });
            
            container.addEventListener('dragleave', (e) => {
                e.preventDefault();
                container.style.borderColor = '';
                container.style.backgroundColor = '';
            });
            
            container.addEventListener('drop', (e) => {
                e.preventDefault();
                container.style.borderColor = '';
                container.style.backgroundColor = '';
                
                const entityType = container.closest('.entity-card').dataset.entityType;
                const file = e.dataTransfer.files[0];
                
                if (file && file.type.startsWith('image/')) {
                    this.processImageFile(file, entityType);
                }
            });
        });
    },
    
    /**
     * Trigger image upload input
     */
    triggerImageUpload(entityType) {
        const input = document.getElementById(`${entityType}_file`);
        if (input) {
            input.click();
        }
    },
    
    /**
     * Handle image file selection
     */
    handleImageSelect(event, entityType) {
        const file = event.target.files[0];
        if (file && file.type.startsWith('image/')) {
            this.processImageFile(file, entityType);
        }
    },
    
    /**
     * Process image file and show preview
     */
    processImageFile(file, entityType) {
        const reader = new FileReader();
        
        reader.onload = (event) => {
            const base64 = event.target.result;
            this.imageData[entityType] = base64;
            
            // Update preview
            const preview = document.getElementById(`${entityType}_preview`);
            const placeholder = document.getElementById(`${entityType}_placeholder`);
            const overlay = document.getElementById(`${entityType}_overlay`);
            
            if (preview && placeholder && overlay) {
                preview.src = base64;
                preview.classList.remove('hidden');
                placeholder.classList.add('hidden');
                overlay.classList.remove('hidden');
            }
        };
        
        reader.readAsDataURL(file);
    },
    
    /**
     * Record all entities - main save action
     */
    async recordAll() {
        const entityTypes = ['company', 'material', 'opening_system', 'system_series', 'color', 'unit_type'];
        let savedCount = 0;
        let errors = [];
        
        for (const entityType of entityTypes) {
            const card = document.querySelector(`.entity-card[data-entity-type="${entityType}"]`);
            if (!card) continue;
            
            // Get form data
            const nameInput = card.querySelector(`[name="${entityType}_name"]`);
            const name = nameInput?.value?.trim();
            
            // Skip if no name entered
            if (!name) continue;
            
            // Build data object
            const data = {
                entity_type: entityType,
                name: name,
                metadata: {}
            };
            
            // Get entity ID if editing
            const entityIdInput = card.querySelector(`[name="${entityType}_entity_id"]`);
            const entityId = entityIdInput?.value;
            
            // Add optional fields
            const priceInput = card.querySelector(`[name="${entityType}_price_from"]`);
            if (priceInput?.value) {
                data.price_from = parseFloat(priceInput.value);
            }
            
            const descInput = card.querySelector(`[name="${entityType}_description"]`);
            if (descInput?.value) {
                data.description = descInput.value;
            }
            
            // Add image URL if available
            if (this.imageData[entityType]) {
                data.image_url = this.imageData[entityType];
            }
            
            // Add metadata fields
            card.querySelectorAll('[name^="' + entityType + '_metadata."]').forEach(input => {
                const key = input.name.replace(`${entityType}_metadata.`, '');
                if (input.type === 'checkbox') {
                    data.metadata[key] = input.checked;
                } else if (input.value !== '') {
                    data.metadata[key] = isNaN(parseFloat(input.value)) ? input.value : parseFloat(input.value);
                }
            });
            
            try {
                let response;
                if (entityId) {
                    // Update existing entity
                    response = await fetch(`${this.API_BASE}/entities/${entityId}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(data)
                    });
                } else {
                    // Create new entity
                    response = await fetch(`${this.API_BASE}/entities`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(data)
                    });
                }
                
                const result = await response.json();
                
                if (response.ok) {
                    savedCount++;
                    this.resetCardForm(entityType);
                } else {
                    errors.push(`${entityType}: ${result.detail || 'Error'}`);
                }
            } catch (error) {
                console.error(`Error saving ${entityType}:`, error);
                errors.push(`${entityType}: Network error`);
            }
        }
        
        // Show result
        if (savedCount > 0) {
            showToast(`${savedCount} entity(s) saved successfully`, 'success');
        }
        if (errors.length > 0) {
            showToast(`Errors: ${errors.join(', ')}`, 'error');
        }
        if (savedCount === 0 && errors.length === 0) {
            showToast('No data to save. Please fill in at least one entity.', 'info');
        }
    },
    
    /**
     * Reset a single card form
     */
    resetCardForm(entityType) {
        const card = document.querySelector(`.entity-card[data-entity-type="${entityType}"]`);
        if (!card) return;
        
        // Reset all inputs
        card.querySelectorAll('input:not([type="file"]), textarea').forEach(input => {
            if (input.type === 'checkbox') {
                input.checked = false;
            } else {
                input.value = '';
            }
        });
        
        // Reset image
        delete this.imageData[entityType];
        
        const preview = document.getElementById(`${entityType}_preview`);
        const placeholder = document.getElementById(`${entityType}_placeholder`);
        const overlay = document.getElementById(`${entityType}_overlay`);
        
        if (preview) {
            preview.src = '';
            preview.classList.add('hidden');
        }
        if (placeholder) placeholder.classList.remove('hidden');
        if (overlay) overlay.classList.add('hidden');
    }
};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    RelationsManager.init();
});
