class FormHelpers {
    // Store dynamic headers and mappings
    static dynamicHeaders = null;
    static dynamicHeaderMapping = null;
    static fieldOptionsCache = new Map(); // Cache for field options

    static async setDynamicHeaders(headers, manufacturingTypeId, pageType = 'profile') {
        console.log('🦆 [FORMHELPERS] Setting dynamic headers:', headers);
        this.dynamicHeaders = headers;
        
        // Fetch the header mapping from backend instead of generating client-side
        this.dynamicHeaderMapping = await this.fetchHeaderMapping(manufacturingTypeId, pageType);
        console.log('🦆 [FORMHELPERS] Fetched dynamic header mapping from backend:', this.dynamicHeaderMapping);
    }

    static async fetchHeaderMapping(manufacturingTypeId, pageType = 'profile') {
        try {
            // Try to get JWT token from localStorage/sessionStorage
            const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
            
            // Prepare headers
            const headers = {
                'Content-Type': 'application/json'
            };
            
            // Add Authorization header only if token is available
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
            // If no token, rely on cookie-based authentication

            // Fetch header mapping from backend API
            const response = await fetch(
                `/api/v1/admin/entry/profile/header-mapping/${manufacturingTypeId}?page_type=${pageType}`,
                {
                    headers: headers,
                    credentials: 'include'  // Include cookies for authentication
                }
            );

            if (!response.ok) {
                console.warn(`🦆 [FORMHELPERS] Failed to fetch header mapping: ${response.status}`);
                return {};
            }

            const mapping = await response.json();
            console.log('🦆 [FORMHELPERS] Successfully fetched header mapping from backend:', mapping);
            return mapping;

        } catch (error) {
            console.error(`🦆 [FORMHELPERS] Error fetching header mapping:`, error);
            return {};
        }
    }

    static getUIComponent(field) {
        // First, check if the backend has already specified a ui_component
        if (field.ui_component) {
            return field.ui_component;
        }
        
        // Fallback to client-side logic if no ui_component is specified
        // Determine UI component based on field name and data type
        if (field.data_type === 'boolean') return 'checkbox';
        if (field.data_type === 'number' || field.data_type === 'float') return 'number';
        if (field.name.includes('percentage') || field.name.includes('discount')) return 'percentage';
        if (field.name.includes('price') || field.name.includes('cost')) return 'currency';
        if (field.name.includes('description') || field.name.includes('notes')) return 'textarea';

        // Field-specific UI components based on CSV analysis
        const dropdownFields = ['type', 'company', 'material', 'opening_system', 'system_series'];
        const multiSelectFields = [];
        const checkboxFields = ['renovation', 'builtin_flyscreen_track'];

        if (dropdownFields.includes(field.name)) return 'dropdown';
        if (multiSelectFields.includes(field.name)) return 'multi-select';
        if (checkboxFields.includes(field.name)) return 'checkbox';

        return 'text';  // DEFAULT: text input
    }

    static async getFieldOptions(fieldName, manufacturingTypeId, pageType = 'profile') {
        // Check cache first
        const cacheKey = `${manufacturingTypeId}_${pageType}_${fieldName}`;
        if (this.fieldOptionsCache.has(cacheKey)) {
            return this.fieldOptionsCache.get(cacheKey);
        }

        try {
            // Try to get JWT token from localStorage/sessionStorage
            const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
            
            // Prepare headers
            const headers = {
                'Content-Type': 'application/json'
            };
            
            // Add Authorization header only if token is available
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
            // If no token, rely on cookie-based authentication

            // Fetch schema from API to get field options
            const response = await fetch(
                `/api/v1/admin/entry/profile/schema/${manufacturingTypeId}?page_type=${pageType}`,
                {
                    headers: headers,
                    credentials: 'include'  // Include cookies for authentication
                }
            );

            if (!response.ok) {
                console.warn(`🦆 [FORMHELPERS] Failed to fetch schema: ${response.status}`);
                return [];
            }

            const schema = await response.json();
            
            // Find the field in the schema and extract its options
            let fieldOptions = [];
            for (const section of schema.sections || []) {
                for (const field of section.fields || []) {
                    if (field.name === fieldName && field.options) {
                        fieldOptions = field.options;
                        break;
                    }
                }
                if (fieldOptions.length > 0) break;
            }

            // Cache the result
            this.fieldOptionsCache.set(cacheKey, fieldOptions);
            
            console.log(`🦆 [FORMHELPERS] Fetched options for ${fieldName}:`, fieldOptions);
            return fieldOptions;

        } catch (error) {
            console.error(`🦆 [FORMHELPERS] Error fetching options for ${fieldName}:`, error);
            return [];
        }
    }

    static async addFieldOption(fieldName, optionValue, manufacturingTypeId, pageType = 'profile') {
        try {
            // Try to get JWT token from localStorage/sessionStorage
            const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
            
            // Prepare headers
            const headers = {
                'Content-Type': 'application/json'
            };
            
            // Add Authorization header only if token is available
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
            // If no token, rely on cookie-based authentication (browser will send cookies automatically)

            // Call API to add option
            const response = await fetch(
                `/api/v1/admin/entry/profile/add-option?manufacturing_type_id=${manufacturingTypeId}&field_name=${fieldName}&option_value=${encodeURIComponent(optionValue)}&page_type=${pageType}`,
                {
                    method: 'POST',
                    headers: headers,
                    credentials: 'include'  // Include cookies for authentication
                }
            );

            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.detail?.message || result.message || 'Failed to add option');
            }

            if (result.success) {
                // Clear cache for this field
                const cacheKey = `${manufacturingTypeId}_${pageType}_${fieldName}`;
                this.fieldOptionsCache.delete(cacheKey);
                
                console.log(`🦆 [FORMHELPERS] Successfully added option: ${optionValue}`);
                return { success: true, message: result.message };
            } else {
                throw new Error(result.error || 'Failed to add option');
            }

        } catch (error) {
            console.error(`🦆 [FORMHELPERS] Error adding option:`, error);
            return { success: false, error: error.message };
        }
    }

    static async removeFieldOption(optionId) {
        try {
            // Try to get JWT token from localStorage/sessionStorage
            const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
            
            // Prepare headers
            const headers = {
                'Content-Type': 'application/json'
            };
            
            // Add Authorization header only if token is available
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
            // If no token, rely on cookie-based authentication (browser will send cookies automatically)

            // Call API to remove option
            const response = await fetch(
                `/api/v1/admin/entry/profile/remove-option/${optionId}`,
                {
                    method: 'DELETE',
                    headers: headers,
                    credentials: 'include'  // Include cookies for authentication
                }
            );

            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.detail?.message || result.message || 'Failed to remove option');
            }

            if (result.success) {
                // Clear all cache since we don't know which field this option belonged to
                this.fieldOptionsCache.clear();
                
                console.log(`🦆 [FORMHELPERS] Successfully removed option: ${result.option_value}`);
                return { success: true, message: result.message };
            } else {
                throw new Error(result.error || 'Failed to remove option');
            }

        } catch (error) {
            console.error(`🦆 [FORMHELPERS] Error removing option:`, error);
            return { success: false, error: error.message };
        }
    }

    static async removeFieldOptionByName(fieldName, optionValue, manufacturingTypeId, pageType = 'profile') {
        try {
            // Try to get JWT token from localStorage/sessionStorage
            const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
            
            // Prepare headers
            const headers = {
                'Content-Type': 'application/json'
            };
            
            // Add Authorization header only if token is available
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
            // If no token, rely on cookie-based authentication (browser will send cookies automatically)

            // Call API to remove option by name
            const response = await fetch(
                `/api/v1/admin/entry/profile/remove-option-by-name?manufacturing_type_id=${manufacturingTypeId}&field_name=${fieldName}&option_value=${encodeURIComponent(optionValue)}&page_type=${pageType}`,
                {
                    method: 'DELETE',
                    headers: headers,
                    credentials: 'include'  // Include cookies for authentication
                }
            );

            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.detail?.message || result.message || 'Failed to remove option');
            }

            if (result.success) {
                // Clear cache for this field
                const cacheKey = `${manufacturingTypeId}_${pageType}_${fieldName}`;
                this.fieldOptionsCache.delete(cacheKey);
                
                console.log(`🦆 [FORMHELPERS] Successfully removed option: ${optionValue}`);
                return { success: true, message: result.message };
            } else {
                throw new Error(result.error || 'Failed to remove option');
            }

        } catch (error) {
            console.error(`🦆 [FORMHELPERS] Error removing option:`, error);
            return { success: false, error: error.message };
        }
    }

    static getFieldUnit(fieldName) {
        // Return appropriate unit based on field name
        const unitMap = {
            'length_of_beam': 'm',
            'width': 'mm',
            'total_width': 'mm',
            'flyscreen_track_height': 'mm',
            'front_height': 'mm',
            'rear_height': 'mm',
            'glazing_height': 'mm',
            'renovation_height': 'mm',
            'glazing_undercut_height': 'mm',
            'sash_overlap': 'mm',
            'flying_mullion_horizontal_clearance': 'mm',
            'flying_mullion_vertical_clearance': 'mm',
            'steel_material_thickness': 'mm',
            'weight_per_meter': 'kg',
            'price_per_meter': '$',
            'price_per_beam': '$',
            'upvc_profile_discount': '%'
        };

        return unitMap[fieldName] || '';
    }

    static getDefaultValue(field) {
        switch (field.data_type) {
            case 'boolean':
                return false;
            case 'number':
            case 'float':
                return null;
            case 'array':
                return [];
            default:
                return '';
        }
    }

    static getPreviewValue(header, formData, fieldVisibility) {
        // Return N/A while headers are loading to prevent errors
        if (!this.dynamicHeaderMapping) {
            console.log('🦆 [FORMHELPERS] Header mapping not yet loaded, returning N/A');
            return 'N/A';
        }

        const fieldName = this.dynamicHeaderMapping[header];
        if (!fieldName) {
            console.warn('🦆 [FORMHELPERS] WARNING: Header not found in backend mapping:', header);
            return 'N/A';
        }

        const value = formData[fieldName];

        // Handle conditional field visibility - if field is hidden, show N/A
        if (fieldVisibility[fieldName] === false) {
            return 'N/A';
        }

        // Use BusinessRulesEngine if available to determine display value
        if (typeof BusinessRulesEngine !== 'undefined') {
            return BusinessRulesEngine.getDisplayValue(fieldName, value, formData);
        }

        // Fallback to original logic if BusinessRulesEngine is not available
        if (value === null || value === undefined || value === '') {
            return 'N/A';
        }

        // Format different data types to match CSV format
        if (typeof value === 'boolean') {
            return value ? 'yes' : 'no';
        } else if (Array.isArray(value)) {
            return value.length > 0 ? value.join(', ') : 'N/A';
        } else if (typeof value === 'number') {
            // Format numbers appropriately
            if (fieldName.includes('price')) {
                return value.toFixed(2);
            } else if (fieldName.includes('percentage') || fieldName.includes('discount')) {
                return value + '%';
            } else {
                return String(value);
            }
        } else {
            return String(value);
        }
    }

    static getHeaderMapping() {
        // Return empty object while headers are loading to prevent errors
        if (!this.dynamicHeaderMapping) {
            console.log('🦆 [FORMHELPERS] Header mapping not yet loaded, returning empty object');
            return {};
        }
        return this.dynamicHeaderMapping;
    }

    static getPreviewHeaders() {
        // Return empty array while loading to prevent errors
        if (!this.dynamicHeaders || this.dynamicHeaders.length === 0) {
            console.log('🦆 [FORMHELPERS] Headers not yet loaded, returning empty array');
            return [];
        }
        
        console.log('🦆 [FORMHELPERS] Using dynamic headers from backend:', this.dynamicHeaders);
        return this.dynamicHeaders;
    }

    static prepareSaveData(formData, manufacturingTypeId, schema, fieldVisibility) {
        const saveData = {
            ...formData,
            manufacturing_type_id: manufacturingTypeId
        };

        // Remove fields that are not visible (conditional logic)
        if (schema) {
            for (const section of schema.sections) {
                for (const field of section.fields) {
                    if (fieldVisibility[field.name] === false) {
                        delete saveData[field.name];
                    }
                }
            }
        }

        // Convert empty strings to null for optional fields
        Object.keys(saveData).forEach(key => {
            if (saveData[key] === '') {
                saveData[key] = null;
            }
        });

        return saveData;
    }

    static getCompletedFieldsCount(schema, formData, fieldVisibility) {
        if (!schema) return 0;

        let completed = 0;
        for (const section of schema.sections) {
            for (const field of section.fields) {
                if (fieldVisibility[field.name] !== false) {
                    const value = formData[field.name];
                    if (value !== null && value !== undefined && value !== '' &&
                        !(Array.isArray(value) && value.length === 0)) {
                        completed++;
                    }
                }
            }
        }
        return completed;
    }

    static getTotalFieldsCount(schema, fieldVisibility) {
        if (!schema) return 0;

        let total = 0;
        for (const section of schema.sections) {
            for (const field of section.fields) {
                if (fieldVisibility[field.name] !== false) {
                    total++;
                }
            }
        }
        return total;
    }

    static isValueChanged(header, formData, lastSavedData) {
        if (!lastSavedData) return false;

        // Return false while headers are loading to prevent errors
        if (!this.dynamicHeaderMapping) {
            console.log('🦆 [FORMHELPERS] Header mapping not yet loaded for isValueChanged, returning false');
            return false;
        }

        const fieldName = this.dynamicHeaderMapping[header];
        if (!fieldName) {
            console.warn('🦆 [FORMHELPERS] WARNING: Header not found in backend mapping for isValueChanged:', header);
            return false;
        }

        return formData[fieldName] !== lastSavedData[fieldName];
    }
}