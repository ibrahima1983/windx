class ConfigurationSaver {
    static async saveConfiguration(saveData, pageType = 'profile') {
        try {
            const url = `/api/v1/admin/entry/profile/save?page_type=${encodeURIComponent(pageType)}`;
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',  // Include cookies for admin authentication
                body: JSON.stringify(saveData)
            });

            if (!response.ok) {
                const errorData = await response.json();
                return {
                    success: false,
                    status: response.status,
                    errorData
                };
            }

            const configuration = await response.json();
            return {
                success: true,
                configuration
            };
        } catch (err) {
            console.error('Error saving configuration:', err);
            return {
                success: false,
                error: err.message || 'Failed to save configuration'
            };
        }
    }

    static handleSaveError(status, errorData) {
        const errors = {};
        let message = 'Failed to save configuration';

        if (status === 422) {
            if (errorData.detail) {
                // If detail is an array (standard FastAPI validation error)
                if (Array.isArray(errorData.detail)) {
                    const fieldErrorsFromServer = {};
                    const messages = errorData.detail.map(e => {
                        const field = e.loc ? e.loc[e.loc.length - 1] : 'Unknown field';
                        const msg = e.msg || 'Invalid value';
                        fieldErrorsFromServer[field] = msg;
                        return `${field}: ${msg}`;
                    });
                    
                    return {
                        fieldErrors: fieldErrorsFromServer,
                        message: 'Please fix the highlighted validation errors',
                        showFieldErrors: true
                    };
                }
                // If detail is an object with specific field_errors (EntryService custom validation)
                else if (errorData.detail.field_errors) {
                    return {
                        fieldErrors: errorData.detail.field_errors,
                        message: 'Please fix the highlighted validation errors',
                        showFieldErrors: true
                    };
                }
                // If detail is a string with ValidationException message
                else if (typeof errorData.detail === 'string' && errorData.detail.includes('field_errors')) {
                    try {
                        // Try to extract field errors from ValidationException string
                        const match = errorData.detail.match(/field_errors=({.*})/);
                        if (match) {
                            const fieldErrorsStr = match[1].replace(/'/g, '"');
                            const fieldErrors = JSON.parse(fieldErrorsStr);
                            return {
                                fieldErrors: fieldErrors,
                                message: 'Please fix the highlighted validation errors',
                                showFieldErrors: true
                            };
                        }
                    } catch (parseError) {
                        console.warn('Failed to parse field errors from ValidationException:', parseError);
                    }
                }
                // Generic detail message
                else {
                    message = errorData.detail.message || errorData.detail || 'Validation failed';
                }
            }
            // Handle ValidationException with field_errors attribute
            else if (errorData.field_errors) {
                return {
                    fieldErrors: errorData.field_errors,
                    message: 'Please fix the highlighted validation errors',
                    showFieldErrors: true
                };
            }
        } else if (status === 401) {
            return {
                redirect: '/api/v1/admin/login',
                message: 'Authentication session expired'
            };
        } else if (status === 500) {
            message = 'Server Error: ' + (errorData.detail?.message || 'Internal server error occurred');
        } else {
            message = errorData.message || errorData.detail || `Server returned ${status}`;
        }

        return { message, showFieldErrors: false };
    }
}