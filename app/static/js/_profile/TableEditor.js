class TableEditor {
    static async commitTableChanges(pendingEdits) {
        if (Object.keys(pendingEdits).length === 0) {
            return { success: true, successCount: 0, errorCount: 0, fieldErrors: {} };
        }

        let successCount = 0;
        let errorCount = 0;
        const fieldErrors = {};

        try {
            // Process each row's edits
            for (const [rowId, edits] of Object.entries(pendingEdits)) {
                for (const [field, value] of Object.entries(edits)) {
                    try {
                        console.log(`🦆 [COMMIT DEBUG] Saving ${field} for row ${rowId} with value:`, value);
                        
                        const response = await fetch(`/api/v1/admin/entry/profile/preview/${rowId}/update-cell`, {
                            method: 'PATCH',
                            headers: { 'Content-Type': 'application/json' },
                            credentials: 'include',
                            body: JSON.stringify({ field: field, value: value })
                        });

                        console.log(`🦆 [COMMIT DEBUG] Response status for ${field}:`, response.status);

                        if (response.ok) {
                            successCount++;
                            console.log(`✅ Successfully saved ${field} for row ${rowId}`);
                        } else {
                            errorCount++;
                            const error = await response.json();
                            console.error(`❌ Failed to save ${field} for row ${rowId}:`, error);
                            
                            // Store field-specific error for UI display
                            const fieldKey = `${rowId}_${field}`;
                            if (error.detail && typeof error.detail === 'string') {
                                fieldErrors[fieldKey] = error.detail;
                            } else if (error.message) {
                                fieldErrors[fieldKey] = error.message;
                            } else {
                                fieldErrors[fieldKey] = `Failed to save ${field}`;
                            }
                        }
                    } catch (err) {
                        errorCount++;
                        console.error(`❌ Network error saving ${field} for row ${rowId}:`, err);
                        
                        // Store network error for UI display
                        const fieldKey = `${rowId}_${field}`;
                        fieldErrors[fieldKey] = 'Network error occurred';
                    }
                }
            }

            return { success: true, successCount, errorCount, fieldErrors };
        } catch (err) {
            console.error('Error committing changes:', err);
            return { success: false, error: err.message, successCount, errorCount, fieldErrors };
        }
    }

    static async deleteRow(rowId) {
        if (!confirm('Are you sure you want to delete this configuration?')) {
            return { success: false, cancelled: true };
        }

        try {
            const response = await fetch(`/api/v1/admin/entry/profile/configuration/${rowId}`, {
                method: 'DELETE',
                credentials: 'include'
            });

            if (response.ok) {
                return { success: true };
            } else {
                const error = await response.json();
                const errorMessage = error.detail || error.message || 'Failed to delete';
                return { success: false, error: errorMessage };
            }
        } catch (err) {
            console.error('Delete error:', err);
            return { success: false, error: 'Network error occurred while deleting' };
        }
    }

    static saveInlineEdit(rowId, field, newValue, originalValue, pendingEdits, savedConfigurations) {
        console.log('Saving inline edit:', rowId, field, newValue, 'Original:', originalValue);

        // If value hasn't changed, just return
        if (newValue === originalValue || (newValue === '' && originalValue === 'N/A')) {
            return { changed: false, pendingEdits, savedConfigurations };
        }

        // Basic client-side validation for inline edits
        const validationError = this.validateInlineEdit(field, newValue);
        if (validationError) {
            // Show immediate validation error
            if (window.showToast) {
                window.showToast(`${field}: ${validationError}`, 'error', 4000);
            }
            return { changed: false, pendingEdits, savedConfigurations, validationError };
        }

        // Store the edit in pending edits (don't save to server yet)
        const updatedPendingEdits = { ...pendingEdits };
        if (!updatedPendingEdits[rowId]) {
            updatedPendingEdits[rowId] = {};
        }
        updatedPendingEdits[rowId][field] = newValue || 'N/A';

        // Update local display immediately
        const updatedConfigurations = [...savedConfigurations];
        const row = updatedConfigurations.find(r => r.id === rowId);
        if (row) {
            row[field] = newValue || 'N/A';
        }

        console.log('Edit stored locally. Pending edits:', updatedPendingEdits);
        
        return { 
            changed: true, 
            pendingEdits: updatedPendingEdits, 
            savedConfigurations: updatedConfigurations 
        };
    }

    static validateInlineEdit(field, value) {
        // Basic validation for common field types
        const fieldLower = field.toLowerCase();
        
        // Numeric fields validation
        if (fieldLower.includes('width') || fieldLower.includes('height') || 
            fieldLower.includes('length') || fieldLower.includes('thickness') ||
            fieldLower.includes('clearance') || fieldLower.includes('overlap')) {
            
            if (value && value !== 'N/A') {
                const numValue = parseFloat(value);
                if (isNaN(numValue)) {
                    return 'Must be a valid number';
                }
                if (numValue < 0) {
                    return 'Must be a positive number';
                }
                if (numValue > 10000) {
                    return 'Value seems too large';
                }
            }
        }
        
        // Percentage fields validation
        if (fieldLower.includes('discount') && fieldLower.includes('%')) {
            if (value && value !== 'N/A') {
                const numValue = parseFloat(value);
                if (isNaN(numValue)) {
                    return 'Must be a valid percentage';
                }
                if (numValue < 0 || numValue > 100) {
                    return 'Must be between 0 and 100';
                }
            }
        }
        
        // String length validation
        if (typeof value === 'string' && value.length > 255) {
            return 'Value is too long (max 255 characters)';
        }
        
        return null; // No validation error
    }

    static highlightInlineEditErrors(fieldErrors, containerElement) {
        if (!containerElement) return;

        // Clear previous error highlights
        const previouslyHighlighted = containerElement.querySelectorAll('.inline-edit-error');
        previouslyHighlighted.forEach(el => el.classList.remove('inline-edit-error'));

        // Highlight cells with errors
        Object.keys(fieldErrors).forEach(fieldKey => {
            const [rowId, field] = fieldKey.split('_');
            const cell = containerElement.querySelector(`[data-row-id="${rowId}"][data-field="${field}"]`);
            if (cell) {
                cell.classList.add('inline-edit-error');
                
                // Add error tooltip
                cell.title = fieldErrors[fieldKey];
            }
        });
    }
}