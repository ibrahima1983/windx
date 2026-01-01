class FormHelpers {
    // Store dynamic headers and mappings
    static dynamicHeaders = null;
    static dynamicHeaderMapping = null;

    static setDynamicHeaders(headers) {
        console.log('🦆 [FORMHELPERS] Setting dynamic headers:', headers);
        this.dynamicHeaders = headers;
        this.dynamicHeaderMapping = this.generateHeaderMapping(headers);
        console.log('🦆 [FORMHELPERS] Generated dynamic header mapping:', this.dynamicHeaderMapping);
    }

    static generateHeaderMapping(headers) {
        // Generate mapping from headers to field names
        const mapping = {};
        
        for (const header of headers) {
            // Convert header to field name (lowercase, replace spaces with underscores)
            let fieldName = header.toLowerCase()
                .replace(/\s+/g, '_')
                .replace(/[^\w_]/g, '')
                .replace(/_+/g, '_')
                .replace(/^_|_$/g, '');
            
            // Handle special cases for consistency with existing field names
            const specialMappings = {
                'opening_system': 'opening_system',
                'system_series': 'system_series',
                'length_of_beam': 'length_of_beam',
                'builtin_flyscreen_track': 'builtin_flyscreen_track',
                'total_width': 'total_width',
                'flyscreen_track_height': 'flyscreen_track_height',
                'front_height': 'front_height',
                'rear_height': 'rear_height',
                'glazing_height': 'glazing_height',
                'renovation_height': 'renovation_height',
                'glazing_undercut_height': 'glazing_undercut_height',
                'sash_overlap': 'sash_overlap',
                'flying_mullion_horizontal_clearance': 'flying_mullion_horizontal_clearance',
                'flying_mullion_vertical_clearance': 'flying_mullion_vertical_clearance',
                'steel_material_thickness': 'steel_material_thickness',
                'weight_per_meter': 'weight_per_meter',
                'reinforcement_steel': 'reinforcement_steel',
                'price_per_meter': 'price_per_meter',
                'price_per_beam': 'price_per_beam',
                'upvc_profile_discount': 'upvc_profile_discount'
            };
            
            if (specialMappings[fieldName]) {
                fieldName = specialMappings[fieldName];
            }
            
            mapping[header] = fieldName;
        }
        
        return mapping;
    }
    static getUIComponent(field) {
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

    static getFieldOptions(fieldName) {
        // Return options based on CSV data analysis
        const optionsMap = {
            'type': ['Frame', 'sash', 'Mullion', 'Flying mullion', 'glazing bead', 'Interlock', 'Track', 'auxilary', 'coupling', 'tube'],
            'company': ['kompen', 'choose from database'],
            'material': ['UPVC', 'Choose'],
            'opening_system': ['Casement', 'All'],
            'system_series': ['Kom700', 'Kom701', 'Kom800', 'All'],
            'renovation': ['yes', 'no', 'n.a'],
        };

        return optionsMap[fieldName] || [];
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
        // Require dynamic header mapping - no fallbacks allowed
        if (!this.dynamicHeaderMapping) {
            console.error('🦆 [FORMHELPERS] ERROR: No dynamic header mapping available. Headers must be loaded from backend.');
            return 'ERROR: Headers not loaded';
        }

        const fieldName = this.dynamicHeaderMapping[header];
        if (!fieldName) {
            console.warn('🦆 [FORMHELPERS] WARNING: Header not found in mapping:', header);
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
        // Require dynamic header mapping - no fallbacks allowed
        if (!this.dynamicHeaderMapping) {
            console.error('🦆 [FORMHELPERS] ERROR: No dynamic header mapping available. Headers must be loaded from backend.');
            return {};
        }
        return this.dynamicHeaderMapping;
    }

    static getPreviewHeaders() {
        // Require dynamic headers - no fallbacks allowed
        if (!this.dynamicHeaders || this.dynamicHeaders.length === 0) {
            console.error('🦆 [FORMHELPERS] ERROR: No dynamic headers available. Headers must be loaded from backend.');
            return ['ERROR: Headers not loaded'];
        }
        
        console.log('🦆 [FORMHELPERS] Using dynamic headers:', this.dynamicHeaders);
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

        // Require dynamic header mapping - no fallbacks allowed
        if (!this.dynamicHeaderMapping) {
            console.error('🦆 [FORMHELPERS] ERROR: No dynamic header mapping available for isValueChanged.');
            return false;
        }

        const fieldName = this.dynamicHeaderMapping[header];
        if (!fieldName) {
            console.warn('🦆 [FORMHELPERS] WARNING: Header not found in mapping for isValueChanged:', header);
            return false;
        }

        return formData[fieldName] !== lastSavedData[fieldName];
    }
}