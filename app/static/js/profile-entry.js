// Profile Entry Application JavaScript
// This file uses modular classes loaded from separate files

function profileEntryApp(options = {}) {
    return {
        // State
        manufacturingTypeId: window.INITIAL_MANUFACTURING_TYPE_ID || null,
        pageType: window.INITIAL_PAGE_TYPE || 'profile',
        manufacturingTypes: [],
        schema: null,
        formData: {},
        fieldVisibility: {},
        fieldErrors: {},
        activeTab: 'input', // Default to input tab
        imagePreviews: {}, // Store object URLs for image previews

        loading: false,
        saving: false,
        error: null,
        hasUnsavedData: false, // Track if session has uncommitted data
        lastSavedData: null,
        autoSaveInterval: null,

        // Dynamic headers state
        dynamicHeaders: null,
        headersLoading: false,
        headersError: null,

        // Inline Editing & Table Preview
        canEdit: options.canEdit || false,
        canDelete: options.canDelete || false,
        savedConfigurations: [],
        editingCell: { rowId: null, field: null, value: null },
        pendingEdits: {}, // Track unsaved edits: { rowId: { field: value } }
        hasUnsavedEdits: false,
        committingChanges: false,

        // Search and Filter functionality
        searchEngine: new SearchEngine(),
        searchQuery: '',
        columnFilters: {},
        showAdvancedSearch: false,
        searchResults: { total: 0, filtered: 0 },
        filteredConfigurations: [],

        // Computed
        get isFormValid() {
            return FormValidator.isFormValid(this.schema, this.formData, this.fieldVisibility, this.fieldErrors);
        },

        // Methods
        switchTab(tabName) {
            this.activeTab = tabName;
            this.updateUrlState();
            console.log('Switched to tab:', tabName);
        },

        updateUrlState() {
            // Update URL with current tab state only
            const url = new URL(window.location);
            url.searchParams.set('tab', this.activeTab);
            
            // Update URL without triggering page reload
            window.history.replaceState(
                { 
                    tab: this.activeTab,
                    pageType: this.pageType 
                }, 
                '', 
                url
            );
            
            // Store in session storage for persistence
            sessionStorage.setItem('entryPageState', JSON.stringify({
                tab: this.activeTab,
                pageType: this.pageType,
                timestamp: Date.now()
            }));
            
            console.log('🔗 URL state updated:', { tab: this.activeTab });
        },

        loadUrlState() {
            // Load state from URL parameters first
            const urlParams = new URLSearchParams(window.location.search);
            const urlTab = urlParams.get('tab');
            
            // Load from session storage as fallback
            const sessionState = sessionStorage.getItem('entryPageState');
            let sessionData = null;
            
            if (sessionState) {
                try {
                    sessionData = JSON.parse(sessionState);
                    // Check if session data is not too old (24 hours)
                    if (Date.now() - sessionData.timestamp > 24 * 60 * 60 * 1000) {
                        sessionData = null;
                        sessionStorage.removeItem('entryPageState');
                    }
                } catch (e) {
                    console.warn('Failed to parse session state:', e);
                    sessionStorage.removeItem('entryPageState');
                }
            }
            
            // Apply state with priority: URL > Session > Default
            if (urlTab && ['input', 'preview'].includes(urlTab)) {
                this.activeTab = urlTab;
            } else if (sessionData && sessionData.tab) {
                this.activeTab = sessionData.tab;
            }
            
            console.log('🔗 Loaded URL state:', { 
                tab: this.activeTab,
                source: urlTab ? 'URL' : sessionData ? 'Session' : 'Default'
            });
            
            // Update URL to reflect current state (in case we loaded from session)
            this.updateUrlState();
        },

        async init() {
            console.log('🦆 [DUCK DEBUG] ========================================');
            console.log('🦆 [DUCK DEBUG] ProfileEntryApp Initialization Started');
            console.log('🦆 [DUCK DEBUG] ========================================');
            console.log('🦆 [INIT] Alpine.js version:', typeof Alpine !== 'undefined' ? 'loaded' : 'NOT LOADED');
            console.log('🦆 [INIT] Window object keys:', Object.keys(window).filter(k => k.includes('INITIAL')));
            console.log('🦆 [INIT] manufacturingTypeId:', this.manufacturingTypeId);
            console.log('🦆 [INIT] Current state:', {
                loading: this.loading,
                schema: this.schema,
                formData: this.formData,
                error: this.error
            });

            // Add event listener for image uploads
            this.$el.addEventListener('image-uploaded', (event) => {
                console.log('🦆 [EVENT DEBUG] Image uploaded event received:', event.detail);
                const { rowId, field, filename, url } = event.detail;
                
                // Update the savedConfigurations data if it exists
                if (this.savedConfigurations && Array.isArray(this.savedConfigurations)) {
                    const row = this.savedConfigurations.find(r => r.id === rowId);
                    if (row) {
                        console.log('🦆 [EVENT DEBUG] Updating row data via event...');
                        console.log('🦆 [EVENT DEBUG] Row before update:', row[field]);
                        
                        // Use URL for display, filename for database
                        row[field] = url || filename;
                        
                        console.log('🦆 [EVENT DEBUG] Row after update:', row[field]);
                        
                        // Force Alpine.js reactivity
                        this.savedConfigurations = [...this.savedConfigurations];
                    }
                }
                
                // Initialize pendingEdits if it doesn't exist
                if (!this.pendingEdits) {
                    this.pendingEdits = {};
                }
                if (!this.pendingEdits[rowId]) {
                    this.pendingEdits[rowId] = {};
                }
                
                // Store the filename for database commit
                this.pendingEdits[rowId][field] = filename;
                this.hasUnsavedEdits = true;
                
                console.log('🦆 [EVENT DEBUG] Updated pendingEdits via event:', this.pendingEdits);
                console.log('🦆 [EVENT DEBUG] hasUnsavedEdits set to:', this.hasUnsavedEdits);
            });

            // Load from session storage first
            const sessionData = SessionManager.loadFromSession();
            this.formData = { ...this.formData, ...sessionData.data };
            this.hasUnsavedData = sessionData.hasUnsavedData;

            console.log('🦆 [STEP 1] Loading manufacturing types...');
            this.manufacturingTypes = await DataLoader.loadManufacturingTypes();
            console.log('🦆 [STEP 1] Manufacturing types loaded:', this.manufacturingTypes.length, 'types');

            if (this.manufacturingTypeId) {
                console.log('🦆 [STEP 2] Manufacturing type ID found, loading schema, headers, and previews...');
                this.loading = true;
                try {
                    const [schema, headers, previews] = await Promise.all([
                        DataLoader.loadSchema(this.manufacturingTypeId, this.pageType),
                        this.loadDynamicHeaders(),
                        this.loadPreviews()
                    ]);
                    
                    this.schema = this.processSchema(schema);
                    // previews are already loaded by this.loadPreviews()
                    console.log('🦆 [STEP 2] Data loading completed');
                } catch (err) {
                    console.error('🦆 [ERROR] Failed to load data:', err);
                    this.error = err.message;
                } finally {
                    this.loading = false;
                }
            } else {
                console.warn('🦆 [WARNING] No manufacturingTypeId provided - cannot load schema');
            }

            // Load URL state for tab and input view
            this.loadUrlState();

            // Setup navigation guards
            SessionManager.setupNavigationGuards(() => this.hasUnsavedData);

            console.log('🦆 [DUCK DEBUG] ========================================');
            console.log('🦆 [DUCK DEBUG] Initialization Complete');
            console.log('🦆 [DUCK DEBUG] ✨ LOUD DUCK DEBUG - Final state:', {
                loading: this.loading,
                hasSchema: !!this.schema,
                schemaSection: this.schema?.sections?.length || 0,
                error: this.error,
                schemaKeys: Object.keys(this.schema || {}),
                fullSchema: this.schema
            });
            console.log('🦆 [DUCK DEBUG] ✨ LOUD DUCK DEBUG - Form data keys:', Object.keys(this.formData));
            console.log('🦆 [DUCK DEBUG] ✨ LOUD DUCK DEBUG - Field visibility:', this.fieldVisibility);
            console.log('🦆 [DUCK DEBUG] ========================================');
        },

        processSchema(schema) {
            if (!schema || !schema.sections) {
                console.warn('🦆 [SCHEMA] ⚠️ LOUD DUCK DEBUG - Schema has no sections!');
                return schema;
            }

            // Force Alpine.js reactivity by triggering multiple updates
            const processedSchema = { ...schema };
            
            console.log('🦆 [SCHEMA] Pre-calculating component types...');
            processedSchema.sections.forEach((section, sectionIndex) => {
                console.log(`🦆 [SCHEMA] ✨ LOUD DUCK DEBUG - Section ${sectionIndex}:`, section.title, 'Fields:', section.fields?.length || 0);
                section.fields.forEach((field, fieldIndex) => {
                    console.log(`🦆 [SCHEMA] ✨ LOUD DUCK DEBUG - Field ${fieldIndex}:`, field.name, 'Type:', field.data_type);
                    field.componentType = FormHelpers.getUIComponent(field);
                    // Set default value if not in formData
                    if (this.formData[field.name] === undefined) {
                        this.formData[field.name] = FormHelpers.getDefaultValue(field);
                    }
                });
            });
            console.log('🦆 [SCHEMA] ✅ Schema processing complete');
            
            return processedSchema;
        },

        async loadManufacturingTypes() {
            try {
                this.manufacturingTypes = await DataLoader.loadManufacturingTypes();
            } catch (err) {
                this.error = err.message;
            }
        },

        async loadSchema() {
            this.loading = true;
            this.error = null;
            try {
                const schema = await DataLoader.loadSchema(this.manufacturingTypeId, this.pageType);
                this.schema = this.processSchema(schema);
            } catch (err) {
                this.error = err.message;
            } finally {
                this.loading = false;
            }
        },

        async loadPreviews() {
            console.log('🦆 [PREVIEWS] ========================================');
            console.log('🦆 [PREVIEWS] 🔥 CACHE BUSTED VERSION 3 - DEBUGGING DATA LOADING 🔥');
            console.log('🦆 [PREVIEWS] Starting to load previews...');
            console.log('🦆 [PREVIEWS] Manufacturing type ID:', this.manufacturingTypeId);
            
            try {
                this.savedConfigurations = await DataLoader.loadPreviews(this.manufacturingTypeId);
                
                console.log('🦆 [PREVIEWS] ✅ Loaded configurations:', this.savedConfigurations);
                console.log('🦆 [PREVIEWS] Configuration count:', this.savedConfigurations.length);
                console.log('🦆 [PREVIEWS] First configuration:', this.savedConfigurations[0]);
                
                // Initialize search engine with loaded configurations
                this.searchEngine.initialize(this.savedConfigurations);
                this.updateSearchState();
                
                console.log('🦆 [PREVIEWS] ✅ Search engine initialized');
                console.log('🦆 [PREVIEWS] Search state:', this.searchEngine.getSearchState());
                console.log('🦆 [PREVIEWS] 🎯 FINAL CHECK - this.savedConfigurations length:', this.savedConfigurations.length);
                console.log('🦆 [PREVIEWS] 🎯 FINAL CHECK - this.savedConfigurations:', this.savedConfigurations);
                
                return this.savedConfigurations;
                
            } catch (err) {
                console.error('🦆 [PREVIEWS] ❌ Failed to load previews:', err);
                this.savedConfigurations = [];
                this.searchEngine.initialize([]);
                this.updateSearchState();
            }
        },

        async loadDynamicHeaders() {
            if (!this.manufacturingTypeId) {
                console.warn('🦆 [HEADERS] No manufacturing type ID - cannot load headers');
                return;
            }

            this.headersLoading = true;
            this.headersError = null;

            try {
                console.log('🦆 [HEADERS] Loading dynamic headers for manufacturing type:', this.manufacturingTypeId, 'page type:', this.pageType);
                const headers = await DataLoader.loadDynamicHeaders(this.manufacturingTypeId, this.pageType);
                
                this.dynamicHeaders = headers;
                
                // Set the headers in FormHelpers for use throughout the application
                FormHelpers.setDynamicHeaders(headers);
                
                console.log('🦆 [HEADERS] ✅ Dynamic headers loaded and set:', headers);
                return headers;
            } catch (err) {
                console.error('🦆 [HEADERS] ❌ Failed to load dynamic headers:', err);
                this.headersError = err.message;
                
                // Fall back to hardcoded headers on error
                console.log('🦆 [HEADERS] Falling back to hardcoded headers');
                const fallbackHeaders = [
                    "Name", "Type", "Company", "Material", "opening system", "system series",
                    "Code", "Length of Beam\nm", "Renovation\nonly for frame", "width",
                    "builtin Flyscreen track only for sliding frame", "Total width\nonly for frame with builtin flyscreen",
                    "flyscreen track height\nonly for frame with builtin flyscreen", "front Height mm", "Rear heightt",
                    "Glazing height", "Renovation height mm\nonly for frame", "Glazing undercut heigth\nonly for glazing bead",
                    "Pic", "Sash overlap only for sashs", "flying mullion horizontal clearance",
                    "flying mullion vertical clearance", "Steel material thickness\nonly for reinforcement",
                    "Weight/m kg", "Reinforcement steel", "Colours", "Price/m", "Price per/beam", "UPVC Profile Discount%"
                ];
                
                this.dynamicHeaders = fallbackHeaders;
                FormHelpers.setDynamicHeaders(fallbackHeaders);
                
                return fallbackHeaders;
            } finally {
                this.headersLoading = false;
            }
        },

        startEditing(rowId, field, value) {
            console.log('🦆 [EDITING DEBUG] ========================================');
            console.log('🦆 [EDITING DEBUG] startEditing called');
            console.log('🦆 [EDITING DEBUG] rowId:', rowId);
            console.log('🦆 [EDITING DEBUG] field:', field);
            console.log('🦆 [EDITING DEBUG] value:', value);
            console.log('🦆 [EDITING DEBUG] isImageField(field):', this.isImageField(field));
            
            this.editingCell = {
                rowId: rowId,
                field: field,
                value: value === 'N/A' ? '' : value
            };
            
            console.log('🦆 [EDITING DEBUG] editingCell set to:', this.editingCell);
            console.log('🦆 [EDITING DEBUG] ========================================');
        },

        cancelEditing() {
            console.log('🦆 [CANCEL EDITING DEBUG] ========================================');
            console.log('🦆 [CANCEL EDITING DEBUG] cancelEditing called');
            console.log('🦆 [CANCEL EDITING DEBUG] Current editingCell:', this.editingCell);
            
            this.editingCell = { rowId: null, field: null, value: null };
            
            console.log('🦆 [CANCEL EDITING DEBUG] editingCell reset to:', this.editingCell);
            console.log('🦆 [CANCEL EDITING DEBUG] ========================================');
        },

        async saveInlineEdit(rowId, field) {
            const newValue = this.editingCell.value;
            const originalValue = this.savedConfigurations.find(r => r.id === rowId)?.[field];
            
            const result = TableEditor.saveInlineEdit(rowId, field, newValue, originalValue, this.pendingEdits, this.savedConfigurations);
            
            if (result.changed) {
                this.pendingEdits = result.pendingEdits;
                this.savedConfigurations = result.savedConfigurations;
                this.updateConfigurationsData(); // Update search engine
                this.hasUnsavedEdits = true;
            }

            this.cancelEditing();
        },

        async commitTableChanges() {
            if (Object.keys(this.pendingEdits).length === 0) {
                return;
            }

            this.committingChanges = true;

            try {
                const result = await TableEditor.commitTableChanges(this.pendingEdits);
                
                // Handle field-specific errors from inline editing
                if (result.fieldErrors && Object.keys(result.fieldErrors).length > 0) {
                    // Highlight cells with errors in the preview table
                    if (this.$el) {
                        TableEditor.highlightInlineEditErrors(result.fieldErrors, this.$el);
                    }
                    
                    // Show detailed error information
                    const errorCount = Object.keys(result.fieldErrors).length;
                    const errorMessages = Object.values(result.fieldErrors).join('; ');
                    showToast(
                        `${errorCount} field${errorCount > 1 ? 's' : ''} failed to save: ${errorMessages}`, 
                        'error', 
                        8000
                    );
                }
                
                // Clear pending edits and show results
                this.pendingEdits = {};
                this.hasUnsavedEdits = false;

                if (result.errorCount === 0) {
                    showToast(`Successfully committed ${result.successCount} changes`, 'success');
                } else if (result.successCount > 0) {
                    showToast(`Committed ${result.successCount} changes, ${result.errorCount} failed`, 'warning');
                } else {
                    showToast(`Failed to commit ${result.errorCount} changes`, 'error');
                }

                // Reload the preview data to ensure consistency
                await this.loadPreviews();

            } catch (err) {
                console.error('Error committing changes:', err);
                showToast('Failed to commit changes: ' + (err.message || 'Unknown error'), 'error');
            } finally {
                this.committingChanges = false;
            }
        },

        async deleteRow(rowId) {
            const result = await TableEditor.deleteRow(rowId);
            
            if (result.success) {
                this.savedConfigurations = this.savedConfigurations.filter(r => r.id !== rowId);
                this.updateConfigurationsData(); // Update search engine
                if (window.showToast) {
                    window.showToast('Deleted successfully', 'success');
                }
            } else if (!result.cancelled) {
                alert(result.error || 'Failed to delete');
            }
        },

        initializeFormData() {
            this.formData = {
                manufacturing_type_id: this.manufacturingTypeId,
                name: '',
                type: '',
                upvc_profile_discount: 20.0
            };

            // Initialize all fields with default values
            if (this.schema) {
                for (const section of this.schema.sections) {
                    for (const field of section.fields) {
                        if (!(field.name in this.formData)) {
                            this.formData[field.name] = FormHelpers.getDefaultValue(field);
                        }
                    }
                }
            }
        },

        getDefaultValue(field) {
            return FormHelpers.getDefaultValue(field);
        },

        updateFieldVisibility() {
            if (!this.schema || !this.schema.conditional_logic) return;

            // Evaluate all conditional logic
            for (const [fieldName, condition] of Object.entries(this.schema.conditional_logic)) {
                try {
                    this.fieldVisibility[fieldName] = ConditionEvaluator.evaluateCondition(condition, this.formData);
                } catch (err) {
                    console.error(`Error evaluating condition for ${fieldName}:`, err);
                    this.fieldVisibility[fieldName] = true; // Default to visible
                }
            }

            // Apply business rules for field availability
            const businessRulesVisibility = BusinessRulesEngine.evaluateFieldAvailability(this.formData);
            Object.assign(this.fieldVisibility, businessRulesVisibility);

            // Update UI field visibility
            if (this.$el) {
                BusinessRulesEngine.updateFieldVisibility(this.formData, this.$el);
            }
        },

        isFieldVisible(fieldName) {
            // If no conditional logic, check business rules
            if (!this.schema || !this.schema.conditional_logic[fieldName]) {
                return BusinessRulesEngine.isFieldValidForCurrentContext(fieldName, this.formData);
            }

            return this.fieldVisibility[fieldName] !== false;
        },

        /**
         * Check if a field is valid for the current context (replaces broken implementation)
         * @param {string} fieldName - Field name to check
         * @returns {boolean} True if field is valid for current context
         */
        isFieldValidForCurrentContext(fieldName) {
            return BusinessRulesEngine.isFieldValidForCurrentContext(fieldName, this.formData);
        },

        getUIComponent(field) {
            return FormHelpers.getUIComponent(field);
        },

        getFieldOptions(fieldName) {
            return FormHelpers.getFieldOptions(fieldName);
        },

        getFieldUnit(fieldName) {
            return FormHelpers.getFieldUnit(fieldName);
        },

        updateMultiSelectField(fieldName, selectElement) {
            const selectedOptions = Array.from(selectElement.selectedOptions).map(option => option.value);
            this.updateField(fieldName, selectedOptions);
        },

        handleFileChange(fieldName, event) {
            ImageHandler.handleFileChange(
                fieldName, 
                event, 
                (field, value) => this.updateField(field, value),
                this.imagePreviews,
                (previews) => { this.imagePreviews = previews; }
            );
        },

        clearFile(fieldName) {
            ImageHandler.clearFile(
                fieldName,
                (field, value) => this.updateField(field, value),
                this.imagePreviews,
                (previews) => { this.imagePreviews = previews; }
            );
        },

        // Image handling methods
        isImageField(fieldName) {
            return ImageHandler.isImageField(fieldName);
        },

        openImageModal(imageSrc) {
            window.openImageModal(imageSrc);
        },

        handleInlineImageChange(rowId, field, event) {
            window.handleInlineImageChange(rowId, field, event);
        },

        getImageUrl(filename) {
            return ImageHandler.getImageUrl(filename);
        },

        // Add debugging method to check template conditions
        debugImageField(header, rowValue) {
            return ImageHandler.debugImageField(header, rowValue);
        },

        updateField(fieldName, value) {
            // Update form data
            this.formData[fieldName] = value;

            // Save to session storage
            SessionManager.saveToSession(this.formData);
            this.hasUnsavedData = true;

            // Clear field error when user corrects the field
            if (this.fieldErrors[fieldName]) {
                this.fieldErrors = FormValidator.clearFieldError(this.fieldErrors, fieldName);
                
                // Remove visual error highlighting
                if (this.$el) {
                    const fieldElement = this.$el.querySelector(`#${fieldName}, [name="${fieldName}"], [data-field="${fieldName}"]`);
                    if (fieldElement) {
                        fieldElement.classList.remove('field-error-highlight');
                        const fieldContainer = fieldElement.closest('.field-container, .form-field, .input-group');
                        if (fieldContainer) {
                            fieldContainer.classList.remove('field-error-highlight');
                        }
                    }
                }
            }

            // Update field visibility based on new data
            this.updateFieldVisibility();

            // Validate field
            this.validateField(fieldName, value);
        },

        validateField(fieldName, value) {
            if (!this.schema) return;

            // Find field definition
            let field = null;
            for (const section of this.schema.sections) {
                field = section.fields.find(f => f.name === fieldName);
                if (field) break;
            }

            if (!field) return;

            const isVisible = this.isFieldVisible(fieldName);
            const fieldErrors = FormValidator.validateField(field, value, isVisible);
            
            // Add business rules validation
            const businessRuleErrors = BusinessRulesEngine.validateBusinessRules(this.formData);
            if (businessRuleErrors[fieldName]) {
                fieldErrors[fieldName] = businessRuleErrors[fieldName];
            }
            
            // Update field errors
            if (Object.keys(fieldErrors).length > 0) {
                this.fieldErrors = { ...this.fieldErrors, ...fieldErrors };
            } else {
                // Clear error if validation passes
                const updatedErrors = { ...this.fieldErrors };
                delete updatedErrors[fieldName];
                this.fieldErrors = updatedErrors;
            }
        },

        validateAllFields() {
            this.fieldErrors = FormValidator.validateAllFields(this.schema, this.formData, this.fieldVisibility);
            
            // Add business rules validation
            const businessRuleErrors = BusinessRulesEngine.validateBusinessRules(this.formData);
            Object.assign(this.fieldErrors, businessRuleErrors);
        },

        getPreviewValue(header) {
            const headerMapping = FormHelpers.getHeaderMapping();
            const fieldName = headerMapping[header] || header.toLowerCase().replace(/\s+/g, '_');
            const value = this.formData[fieldName];
            
            // Use business rules to determine display value
            return BusinessRulesEngine.getDisplayValue(fieldName, value, this.formData);
        },

        // Enhanced preview headers using dynamic headers from backend
        get previewHeaders() {
            // Use dynamic headers if available, otherwise fall back to FormHelpers
            if (this.dynamicHeaders && this.dynamicHeaders.length > 0) {
                return this.dynamicHeaders;
            }
            return FormHelpers.getPreviewHeaders();
        },

        async saveConfiguration() {
            // Validate all fields before saving
            this.validateAllFields();

            if (!this.isFormValid) {
                showToast('Please fix validation errors before saving', 'error');
                this.scrollToFirstError();
                return;
            }

            this.saving = true;
            this.error = null;

            try {
                const saveData = this.prepareSaveData();
                const result = await ConfigurationSaver.saveConfiguration(saveData, this.pageType);

                if (result.success) {
                    showToast('Configuration saved successfully!', 'success');
                    this.lastSavedData = { ...this.formData };

                    // Optionally redirect or update URL
                    if (result.configuration.id) {
                        const url = new URL(window.location);
                        url.searchParams.set('configuration_id', result.configuration.id);
                        window.history.replaceState({}, '', url);
                    }

                    console.log('Saved configuration:', result.configuration);
                    await this.loadPreviews();
                } else {
                    const errorInfo = ConfigurationSaver.handleSaveError(result.status, result.errorData);
                    
                    if (errorInfo.fieldErrors) {
                        this.fieldErrors = { ...this.fieldErrors, ...errorInfo.fieldErrors };
                        if (errorInfo.showFieldErrors) {
                            this.scrollToFirstError();
                        }
                    }
                    
                    if (errorInfo.redirect) {
                        showToast(errorInfo.message, 'error');
                        window.location.href = errorInfo.redirect;
                        return;
                    }
                    
                    throw new Error(errorInfo.message);
                }
            } catch (err) {
                console.error('Error saving configuration:', err);
                this.error = err.message || 'Failed to save configuration';
                showToast(err.message || 'Failed to save configuration', 'error');
            } finally {
                this.saving = false;
            }
        },

        prepareSaveData() {
            return FormHelpers.prepareSaveData(this.formData, this.manufacturingTypeId, this.schema, this.fieldVisibility);
        },

        scrollToFirstError() {
            FormValidator.scrollToFirstError(this.fieldErrors, this.activeTab, (tab) => { this.activeTab = tab; });
        },

        // Auto-save functionality (optional)
        startAutoSave() {
            if (this.autoSaveInterval) {
                clearInterval(this.autoSaveInterval);
            }

            this.autoSaveInterval = setInterval(() => {
                if (this.hasUnsavedChanges() && this.isFormValid) {
                    this.autoSave();
                }
            }, 30000); // Auto-save every 30 seconds
        },

        hasUnsavedChanges() {
            return JSON.stringify(this.formData) !== JSON.stringify(this.lastSavedData || {});
        },

        async autoSave() {
            if (this.saving) return;

            try {
                await this.saveConfiguration();
                console.log('Auto-saved configuration');
            } catch (err) {
                console.warn('Auto-save failed:', err);
            }
        },

        isValueChanged(header) {
            return FormHelpers.isValueChanged(header, this.formData, this.lastSavedData);
        },

        getCompletedFieldsCount() {
            return FormHelpers.getCompletedFieldsCount(this.schema, this.formData, this.fieldVisibility);
        },

        getTotalFieldsCount() {
            return FormHelpers.getTotalFieldsCount(this.schema, this.fieldVisibility);
        },

        // Session Storage Management - now handled by SessionManager
        loadFromSession() {
            const sessionData = SessionManager.loadFromSession();
            this.formData = { ...this.formData, ...sessionData.data };
            this.hasUnsavedData = sessionData.hasUnsavedData;
        },

        async recordConfiguration() {
            this.validateAllFields();
            if (!this.isFormValid) {
                showToast('Please fix validation errors before recording', 'error');
                this.scrollToFirstError();
                return;
            }
            
            this.saving = true;
            this.error = null;
            
            // Clear previous field errors and visual highlights
            this.fieldErrors = {};
            if (this.$el) {
                FormValidator.highlightInvalidFields({}, this.$el);
            }
            
            try {
                const saveData = this.prepareSaveData();
                console.log('🔄 Sending data to server:', saveData);
                
                const result = await ConfigurationSaver.saveConfiguration(saveData, this.pageType);
                console.log('📡 Server response:', result);
                
                if (result.success) {
                    console.log('✅ Configuration saved successfully:', result.configuration);
                    SessionManager.markAsCommitted();
                    this.hasUnsavedData = false;
                    showToast('Configuration recorded successfully!', 'success');
                    await this.loadPreviews();
                } else {
                    const errorInfo = ConfigurationSaver.handleSaveError(result.status, result.errorData);
                    
                    if (errorInfo.fieldErrors) {
                        // Update field errors with specific messages from server
                        this.fieldErrors = { ...this.fieldErrors, ...errorInfo.fieldErrors };
                        console.log('🎯 Updated field errors:', this.fieldErrors);
                        
                        // Highlight invalid fields in both input and preview tabs
                        if (this.$el) {
                            FormValidator.highlightInvalidFields(this.fieldErrors, this.$el);
                        }
                        
                        if (errorInfo.showFieldErrors) {
                            this.scrollToFirstError();
                            
                            // Show detailed error message with field count
                            const errorCount = Object.keys(this.fieldErrors).length;
                            const errorFields = Object.keys(this.fieldErrors).join(', ');
                            showToast(
                                `Please fix ${errorCount} validation error${errorCount > 1 ? 's' : ''}: ${errorFields}`, 
                                'error', 
                                8000
                            );
                            return;
                        }
                    }
                    
                    if (errorInfo.redirect) {
                        showToast(errorInfo.message, 'error');
                        window.location.href = errorInfo.redirect;
                        return;
                    }
                    
                    throw new Error(errorInfo.message);
                }
            } catch (err) {
                console.error('❌ Error recording configuration:', err);
                this.error = err.message;
                
                // Show user-friendly error message
                const userMessage = this.getUserFriendlyErrorMessage(err.message);
                showToast(userMessage, 'error', 6000);
                
                this.scrollToFirstError();
            } finally {
                this.saving = false;
            }
        },

        getUserFriendlyErrorMessage(errorMessage) {
            // Convert technical error messages to user-friendly ones
            if (errorMessage.includes('ValidationException')) {
                return 'Please check your input values and try again';
            } else if (errorMessage.includes('NotFoundException')) {
                return 'The requested resource was not found. Please refresh the page and try again';
            } else if (errorMessage.includes('network') || errorMessage.includes('fetch')) {
                return 'Network error. Please check your connection and try again';
            } else if (errorMessage.includes('timeout')) {
                return 'Request timed out. Please try again';
            } else if (errorMessage.includes('500')) {
                return 'Server error occurred. Please try again later or contact support';
            } else {
                return errorMessage || 'An unexpected error occurred. Please try again';
            }
        },

        setupNavigationGuards() {
            SessionManager.setupNavigationGuards(() => this.hasUnsavedData);
        },

        // Search and Filter Methods
        updateSearchState() {
            const searchState = this.searchEngine.getSearchState();
            this.searchQuery = searchState.searchQuery;
            this.columnFilters = searchState.columnFilters;
            this.showAdvancedSearch = searchState.showAdvancedSearch;
            this.searchResults = searchState.searchResults;
            this.filteredConfigurations = searchState.filteredConfigurations;
        },

        performSearch() {
            this.searchEngine.setSearchQuery(this.searchQuery);
            this.updateSearchState();
        },

        clearSearch() {
            this.searchEngine.clearSearch();
            this.updateSearchState();
        },

        toggleAdvancedSearch() {
            this.searchEngine.toggleAdvancedSearch();
            this.updateSearchState();
        },

        clearAllFilters() {
            this.searchEngine.clearAllFilters();
            this.updateSearchState();
        },

        setColumnFilter(header, value) {
            this.searchEngine.setColumnFilter(header, value);
            this.updateSearchState();
        },

        highlightSearchTerm(text, header) {
            return this.searchEngine.highlightSearchTerm(text, header);
        },

        isRowHighlighted(row) {
            return this.searchEngine.isRowHighlighted(row);
        },

        exportSearchResults() {
            this.searchEngine.exportSearchResults(this.previewHeaders);
        },

        // Update configurations when data changes
        updateConfigurationsData() {
            this.searchEngine.updateConfigurations(this.savedConfigurations);
            this.updateSearchState();
        }
    };
}