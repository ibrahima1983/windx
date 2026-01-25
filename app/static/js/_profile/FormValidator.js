class FormValidator {
    static validateField(field, value, isVisible) {
        const errors = {};

        // Skip validation for hidden fields
        if (!isVisible) {
            return errors;
        }

        // Required validation
        if (field.required && (!value || value === '' || (Array.isArray(value) && value.length === 0))) {
            errors[field.name] = `${field.label} is required`;
            return errors;
        }

        // Skip further validation if field is empty and not required
        if (!value || value === '') {
            return errors;
        }

        // Validation rules
        if (field.validation_rules) {
            const rules = field.validation_rules;

            // Range validation for numbers
            if ((rules.min !== undefined || rules.max !== undefined) && !isNaN(value)) {
                const numValue = parseFloat(value);
                if (rules.min !== undefined && numValue < rules.min) {
                    errors[field.name] = `${field.label} must be at least ${rules.min}`;
                    return errors;
                }
                if (rules.max !== undefined && numValue > rules.max) {
                    errors[field.name] = `${field.label} must be at most ${rules.max}`;
                    return errors;
                }
            }

            // Pattern validation for strings
            if (rules.pattern && typeof value === 'string') {
                try {
                    if (!new RegExp(rules.pattern).test(value)) {
                        errors[field.name] = rules.message || `${field.label} format is invalid`;
                        return errors;
                    }
                } catch (e) {
                    console.warn(`Invalid regex pattern for ${field.name}:`, rules.pattern);
                }
            }

            // Length validation for strings
            if (typeof value === 'string') {
                if (rules.min_length && value.length < rules.min_length) {
                    errors[field.name] = `${field.label} must be at least ${rules.min_length} characters`;
                    return errors;
                }
                if (rules.max_length && value.length > rules.max_length) {
                    errors[field.name] = `${field.label} must be at most ${rules.max_length} characters`;
                    return errors;
                }
            }

            // Custom validation rules
            if (rules.rule_type) {
                switch (rules.rule_type) {
                    case 'email':
                        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                        if (!emailRegex.test(value)) {
                            errors[field.name] = `${field.label} must be a valid email address`;
                            return errors;
                        }
                        break;
                    case 'positive_number':
                        if (isNaN(value) || parseFloat(value) <= 0) {
                            errors[field.name] = `${field.label} must be a positive number`;
                            return errors;
                        }
                        break;
                }
            }
        }

        return errors;
    }

    static validateAllFields(schema, formData, fieldVisibility) {
        if (!schema) return {};

        let allErrors = {};

        // Validate all visible fields
        for (const section of schema.sections) {
            for (const field of section.fields) {
                const isVisible = fieldVisibility[field.name] !== false;
                if (isVisible) {
                    const fieldErrors = FormValidator.validateField(field, formData[field.name], isVisible);
                    allErrors = { ...allErrors, ...fieldErrors };
                }
            }
        }

        return allErrors;
    }

    static isFormValid(schema, formData, fieldVisibility, fieldErrors) {
        if (!schema) return false;

        // Check required fields
        for (const section of schema.sections) {
            for (const field of section.fields) {
                const isVisible = fieldVisibility[field.name] !== false;
                if (field.required && isVisible) {
                    const value = formData[field.name];
                    if (!value || value === '') {
                        return false;
                    }
                }
            }
        }

        // Check for validation errors
        return Object.keys(fieldErrors).length === 0;
    }

    static scrollToFirstError(fieldErrors, activeTab, switchTabCallback) {
        const firstErrorField = Object.keys(fieldErrors)[0];
        console.log('🎯 Scrolling to first error field:', firstErrorField, 'All errors:', fieldErrors);
        
        if (firstErrorField) {
            // Switch to input tab if we're not already there
            if (activeTab !== 'input') {
                switchTabCallback('input');
                console.log('🔄 Switched to input tab to show error');
            }
            
            // Wait a bit for tab switch to complete, then scroll
            setTimeout(() => {
                const element = document.getElementById(firstErrorField);
                console.log('🔍 Found error element:', element);
                
                if (element) {
                    // Scroll to element
                    element.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    element.focus();
                    
                    // Add a temporary highlight effect
                    element.classList.add('error-highlight');
                    setTimeout(() => {
                        element.classList.remove('error-highlight');
                    }, 3000);
                    
                    console.log('✅ Scrolled to and focused error field:', firstErrorField);
                } else {
                    console.warn('⚠️ Could not find element for field:', firstErrorField);
                    
                    // Try to find the field by name attribute or data-field attribute
                    const alternativeElement = document.querySelector(`[name="${firstErrorField}"], [data-field="${firstErrorField}"]`);
                    if (alternativeElement) {
                        alternativeElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        alternativeElement.focus();
                        console.log('✅ Found and scrolled to alternative element for:', firstErrorField);
                    }
                }
            }, 100);
        }
    }

    static clearFieldError(fieldErrors, fieldName) {
        const updatedErrors = { ...fieldErrors };
        delete updatedErrors[fieldName];
        return updatedErrors;
    }

    static highlightInvalidFields(fieldErrors, containerElement) {
        if (!containerElement) return;

        // Clear previous highlights
        const previouslyHighlighted = containerElement.querySelectorAll('.field-error-highlight');
        previouslyHighlighted.forEach(el => el.classList.remove('field-error-highlight'));

        // Highlight current invalid fields
        Object.keys(fieldErrors).forEach(fieldName => {
            const fieldElement = containerElement.querySelector(`#${fieldName}, [name="${fieldName}"], [data-field="${fieldName}"]`);
            if (fieldElement) {
                fieldElement.classList.add('field-error-highlight');
                
                // Also highlight the parent field container
                const fieldContainer = fieldElement.closest('.field-container, .form-field, .input-group');
                if (fieldContainer) {
                    fieldContainer.classList.add('field-error-highlight');
                }
            }
        });
    }
}