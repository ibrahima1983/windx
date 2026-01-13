// Profile Entry Application JavaScript
// This file uses modular classes loaded from separate files

console.log('%c🚀 profile-entry.js v40 LOADED', 'background: #00ff00; color: black; font-size: 16px; font-weight: bold; padding: 8px;');

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
        previewHeadersReady: false, // Add explicit flag for template reactivity

        // Initialization guard
        isInitialized: false,
        isInitializing: false,

        // Inline Editing & Table Preview
        canEdit: options.canEdit || false,
        canDelete: options.canDelete || false,
        savedConfigurations: [],
        editingCell: { rowId: null, field: null, value: null },
        pendingEdits: {}, // Track unsaved edits: { rowId: { field: value } }
        hasUnsavedEdits: false,
        committingChanges: false,

        // Bulk Selection & Delete
        selectedRows: new Set(), // Track selected row IDs
        selectAll: false, // Track select all state
        bulkDeleting: false, // Track bulk delete operation

        // Search and Filter functionality
        searchEngine: new SearchEngine(),
        searchQuery: '',
        columnFilters: {},
        showAdvancedSearch: false,
        searchResults: { total: 0, filtered: 0 },
        filteredConfigurations: [],

        // Dynamic options state
        showAddInput: {},  // Track which fields have add input visible: { fieldName: boolean }
        newOptionValue: {}, // Track new option values: { fieldName: string }
        addingOption: {},   // Track which fields are currently adding: { fieldName: boolean }
        
        // Remove options state
        showRemoveInput: {},  // Track which fields have remove input visible: { fieldName: boolean }
        removeOptionValue: {}, // Track remove option values: { fieldName: string }
        removingOption: {},   // Track which fields are currently removing: { fieldName: boolean }

        // System Series auto-population state
        loadingSystemSeriesData: false,
        systemSeriesData: null,
        autoPopulatedFields: new Set(), // Track which fields are auto-populated

        // System Series auto-population state
        loadingSystemSeriesData: false,
        autoPopulatedFields: new Set(), // Track which fields are auto-populated

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
            // Prevent multiple initializations
            if (this.isInitialized || this.isInitializing) {
                console.log('🦆 [INIT] Already initialized or initializing, skipping...');
                return;
            }
            
            this.isInitializing = true;
            
            // Initialize dynamic options state
            this.showAddInput = {};
            this.newOptionValue = {};
            this.addingOption = {};
            
            // Initialize System Series auto-population state
            this.loadingSystemSeriesData = false;
            this.autoPopulatedFields = new Set();
            
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
                console.log('🦆 [STEP 2] Manufacturing type ID found, loading data in proper order...');
                this.loading = true;
                try {
                    // Load headers FIRST to prevent preview table errors
                    console.log('🦆 [STEP 2a] Loading dynamic headers first...');
                    const headers = await this.loadDynamicHeaders();
                    console.log('🦆 [STEP 2a] Headers loaded successfully');
                    
                    // Then load schema and previews in parallel
                    console.log('🦆 [STEP 2b] Loading schema and previews...');
                    const [schema, previews] = await Promise.all([
                        DataLoader.loadSchema(this.manufacturingTypeId, this.pageType),
                        this.loadPreviews()
                    ]);
                    
                    this.schema = this.processSchema(schema);
                    console.log('🦆 [STEP 2] Data loading completed');
                    
                    // Initialize cascading options for relation fields
                    await this.initializeCascadingOptions();
                } catch (err) {
                    console.error('🦆 [ERROR] Failed to load data:', err);
                    this.error = err.message;
                    // Reset initialization flags on error
                    this.isInitializing = false;
                    this.isInitialized = false;
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
                fullSchema: this.schema,
                hasHeaders: this.dynamicHeaders?.length || 0
            });
            console.log('🦆 [DUCK DEBUG] ✨ LOUD DUCK DEBUG - Form data keys:', Object.keys(this.formData));
            console.log('🦆 [DUCK DEBUG] ✨ LOUD DUCK DEBUG - Field visibility:', this.fieldVisibility);
            console.log('🦆 [DUCK DEBUG] ========================================');
            
            // Mark initialization as complete
            this.isInitializing = false;
            this.isInitialized = true;
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
                
                console.log('🦆 [HEADERS] About to set this.dynamicHeaders to:', headers);
                this.dynamicHeaders = headers;
                console.log('🦆 [HEADERS] After setting - this.dynamicHeaders:', this.dynamicHeaders);
                console.log('🦆 [HEADERS] After setting - this.dynamicHeaders.length:', this.dynamicHeaders?.length);
                
                // Set flag for template reactivity
                this.previewHeadersReady = true;
                console.log('🦆 [HEADERS] Set previewHeadersReady to true');
                
                // Set the headers in FormHelpers for use throughout the application
                await FormHelpers.setDynamicHeaders(headers, this.manufacturingTypeId, this.pageType);
                
                console.log('🦆 [HEADERS] ✅ Dynamic headers loaded and set:', headers);
                return headers;
            } catch (err) {
                console.error('🦆 [HEADERS] ❌ Failed to load dynamic headers:', err);
                this.headersError = err.message;
                
                // No fallbacks allowed - throw error to prevent bugs
                throw new Error(`Failed to load dynamic headers: ${err.message}`);
            } finally {
                this.headersLoading = false;
            }
        },

        startEditing(rowId, field, value) {
            console.log('🦆 [EDITING DEBUG] ========================================');
            console.log('🦆 [EDITING DEBUG] startEditing called');
            console.log('🦆 [EDITING DEBUG] rowId:', rowId);
            console.log('🦆 [EDITING DEBUG] field (header):', field);
            console.log('🦆 [EDITING DEBUG] value:', value);
            console.log('🦆 [EDITING DEBUG] isImageField(field):', this.isImageField(field));
            
            // Debug field type detection
            const fieldInfo = this.getFieldInfoByHeader(field);
            console.log('🦆 [EDITING DEBUG] getFieldInfoByHeader result:', fieldInfo);
            console.log('🦆 [EDITING DEBUG] getFieldComponentType:', this.getFieldComponentType(field));
            console.log('🦆 [EDITING DEBUG] isDropdownField:', this.isDropdownField(field));
            console.log('🦆 [EDITING DEBUG] isNumberField:', this.isNumberField(field));
            console.log('🦆 [EDITING DEBUG] isCheckboxField:', this.isCheckboxField(field));
            console.log('🦆 [EDITING DEBUG] getFieldOptionsForHeader:', this.getFieldOptionsForHeader(field));
            
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
            // Prevent double-save (Enter key + blur can both fire)
            if (this.editingCell.rowId !== rowId || this.editingCell.field !== field) {
                console.log('🦆 [SAVE EDIT] Skipping - editingCell mismatch or already saved');
                return;
            }
            
            const newValue = this.editingCell.value;
            const originalValue = this.savedConfigurations.find(r => r.id === rowId)?.[field];
            
            console.log('🦆 [SAVE EDIT] Saving:', { rowId, field, newValue, originalValue });
            
            const result = TableEditor.saveInlineEdit(rowId, field, newValue, originalValue, this.pendingEdits, this.savedConfigurations);
            
            if (result.changed) {
                this.pendingEdits = result.pendingEdits;
                this.savedConfigurations = result.savedConfigurations;
                this.updateConfigurationsData(); // Update search engine
                this.hasUnsavedEdits = true;
                
                // Auto-calculate price fields for inline editing
                this.autoCalculateInlinePrice(rowId, field, newValue);
            }

            this.cancelEditing();
        },

        /**
         * Auto-calculate price fields when inline editing in Preview tab
         * Formula: price_per_beam = price_per_meter * length_of_beam
         */
        autoCalculateInlinePrice(rowId, fieldHeader, newValue) {
            console.log('🧮 [INLINE PRICE CALC] ========================================');
            console.log('🧮 [INLINE PRICE CALC] Starting calculation...');
            console.log('🧮 [INLINE PRICE CALC] rowId:', rowId);
            console.log('🧮 [INLINE PRICE CALC] fieldHeader:', fieldHeader);
            console.log('🧮 [INLINE PRICE CALC] newValue:', newValue);
            
            // Map header to field name
            const mapping = FormHelpers.getHeaderMapping();
            console.log('🧮 [INLINE PRICE CALC] Header mapping:', mapping);
            
            const fieldName = mapping[fieldHeader] || fieldHeader.toLowerCase().replace(/\s+/g, '_');
            console.log('🧮 [INLINE PRICE CALC] Mapped fieldName:', fieldName);
            
            // Only process relevant fields
            const priceFields = ['price_per_meter', 'price_per_beam', 'length_of_beam'];
            if (!priceFields.includes(fieldName)) {
                console.log('🧮 [INLINE PRICE CALC] Field not in priceFields, skipping');
                return;
            }
            
            // Find the row in savedConfigurations
            const row = this.savedConfigurations.find(r => r.id === rowId);
            if (!row) {
                console.log('🧮 [INLINE PRICE CALC] Row not found');
                return;
            }
            console.log('🧮 [INLINE PRICE CALC] Found row:', row);
            console.log('🧮 [INLINE PRICE CALC] Row keys:', Object.keys(row));
            
            // Get header names for the fields (reverse lookup)
            const reverseMapping = {};
            for (const [header, field] of Object.entries(mapping)) {
                reverseMapping[field] = header;
            }
            console.log('🧮 [INLINE PRICE CALC] Reverse mapping:', reverseMapping);
            
            // Find the actual header names used in the row data
            const lengthHeader = reverseMapping['length_of_beam'] || this.findHeaderInRow(row, ['Length of Beam', 'Length of beam', 'length_of_beam']);
            const pricePerMeterHeader = reverseMapping['price_per_meter'] || this.findHeaderInRow(row, ['Price/m', 'Price per meter', 'price_per_meter']);
            const pricePerBeamHeader = reverseMapping['price_per_beam'] || this.findHeaderInRow(row, ['Price per Beam', 'Price per/beam', 'price_per_beam']);
            
            console.log('🧮 [INLINE PRICE CALC] lengthHeader:', lengthHeader);
            console.log('🧮 [INLINE PRICE CALC] pricePerMeterHeader:', pricePerMeterHeader);
            console.log('🧮 [INLINE PRICE CALC] pricePerBeamHeader:', pricePerBeamHeader);
            
            // Get current values from the row
            const lengthOfBeam = this.parseDecimal(row[lengthHeader]);
            const pricePerMeter = this.parseDecimal(row[pricePerMeterHeader]);
            const pricePerBeam = this.parseDecimal(row[pricePerBeamHeader]);
            
            console.log('🧮 [INLINE PRICE CALC] Current values:', { lengthOfBeam, pricePerMeter, pricePerBeam });
            
            // Skip if length_of_beam is not set or is zero
            if (lengthOfBeam === null || lengthOfBeam === 0) {
                console.log('🧮 [INLINE PRICE CALC] length_of_beam is null or 0, skipping');
                return;
            }
            
            let targetHeader = null;
            let calculatedValue = null;
            
            if (fieldName === 'price_per_meter' && newValue !== null && newValue !== '') {
                // Calculate price_per_beam from price_per_meter
                const parsedValue = this.parseDecimal(newValue);
                if (parsedValue !== null) {
                    calculatedValue = this.roundToDecimals(parsedValue * lengthOfBeam, 2);
                    targetHeader = pricePerBeamHeader;
                    console.log(`🧮 [INLINE PRICE CALC] price_per_beam = ${parsedValue} × ${lengthOfBeam} = ${calculatedValue}`);
                }
            } else if (fieldName === 'price_per_beam' && newValue !== null && newValue !== '') {
                // Calculate price_per_meter from price_per_beam
                const parsedValue = this.parseDecimal(newValue);
                if (parsedValue !== null) {
                    calculatedValue = this.roundToDecimals(parsedValue / lengthOfBeam, 2);
                    targetHeader = pricePerMeterHeader;
                    console.log(`🧮 [INLINE PRICE CALC] price_per_meter = ${parsedValue} ÷ ${lengthOfBeam} = ${calculatedValue}`);
                }
            } else if (fieldName === 'length_of_beam' && pricePerMeter !== null) {
                // Recalculate price_per_beam when length changes
                const parsedLength = this.parseDecimal(newValue);
                if (parsedLength !== null && parsedLength !== 0) {
                    calculatedValue = this.roundToDecimals(pricePerMeter * parsedLength, 2);
                    targetHeader = pricePerBeamHeader;
                    console.log(`🧮 [INLINE PRICE CALC] length changed: price_per_beam = ${pricePerMeter} × ${parsedLength} = ${calculatedValue}`);
                }
            }
            
            // Update the calculated field
            if (targetHeader && calculatedValue !== null) {
                console.log(`🧮 [INLINE PRICE CALC] Updating ${targetHeader} to ${calculatedValue}`);
                
                // Update the row data
                row[targetHeader] = calculatedValue;
                
                // Add to pending edits
                if (!this.pendingEdits[rowId]) {
                    this.pendingEdits[rowId] = {};
                }
                this.pendingEdits[rowId][targetHeader] = calculatedValue;
                
                // Force reactivity
                this.savedConfigurations = [...this.savedConfigurations];
                
                // Highlight the auto-calculated cell with fade animation
                // Use longer setTimeout to ensure Alpine has finished re-rendering the DOM
                const self = this;
                const targetHeaderForHighlight = targetHeader;
                const rowIdForHighlight = rowId;
                setTimeout(() => {
                    self.highlightCalculatedCell(rowIdForHighlight, targetHeaderForHighlight);
                }, 250);
                
                console.log(`🧮 [INLINE PRICE CALC] ✅ Updated ${targetHeader} to ${calculatedValue}`);
                console.log('🧮 [INLINE PRICE CALC] pendingEdits:', this.pendingEdits);
            } else {
                console.log('🧮 [INLINE PRICE CALC] No update needed (targetHeader or calculatedValue is null)');
            }
            console.log('🧮 [INLINE PRICE CALC] ========================================');
        },

        /**
         * Highlight a cell that was auto-calculated with a fade animation
         */
        highlightCalculatedCell(rowId, header) {
            console.log('✨ [HIGHLIGHT] Attempting to highlight cell:', { rowId, header });
            
            // Find the cell by row ID and header
            // The data attributes are set by Alpine.js as :data-row-id and :data-field
            const selector = `td[data-row-id="${rowId}"][data-field="${header}"]`;
            console.log('✨ [HIGHLIGHT] Selector:', selector);
            
            // Search in the entire document since $el might not contain the table after re-render
            const cell = document.querySelector(selector);
            console.log('✨ [HIGHLIGHT] Found cell:', cell);
            
            if (cell) {
                console.log('✨ [HIGHLIGHT] Adding highlight class');
                cell.classList.add('auto-calculated-highlight');
                setTimeout(() => {
                    cell.classList.remove('auto-calculated-highlight');
                    console.log('✨ [HIGHLIGHT] Removed highlight class');
                }, 1500);
            } else {
                console.log('✨ [HIGHLIGHT] Cell not found, trying alternative approach');
                // Alternative: find by iterating through table rows
                const table = document.querySelector('#preview-tab table tbody');
                if (table) {
                    const rows = table.querySelectorAll('tr');
                    rows.forEach(row => {
                        const cells = row.querySelectorAll('td');
                        cells.forEach(td => {
                            const tdRowId = td.getAttribute('data-row-id');
                            const tdField = td.getAttribute('data-field');
                            if (tdRowId == rowId && tdField === header) {
                                console.log('✨ [HIGHLIGHT] Found cell via iteration!');
                                td.classList.add('auto-calculated-highlight');
                                setTimeout(() => {
                                    td.classList.remove('auto-calculated-highlight');
                                }, 1500);
                            }
                        });
                    });
                }
            }
        },

        /**
         * Helper to find a header in row data by trying multiple possible names
         */
        findHeaderInRow(row, possibleNames) {
            for (const name of possibleNames) {
                if (row.hasOwnProperty(name)) {
                    return name;
                }
            }
            return possibleNames[0]; // Return first as fallback
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

            // Clear form data for fields that become invisible
            for (const [fieldName, isVisible] of Object.entries(this.fieldVisibility)) {
                if (isVisible === false && this.formData[fieldName] !== undefined && this.formData[fieldName] !== null && this.formData[fieldName] !== '') {
                    console.log(`🧹 Clearing invisible field: ${fieldName} (was: ${this.formData[fieldName]})`);
                    this.formData[fieldName] = null;
                    // Also clear any field errors for the cleared field
                    if (this.fieldErrors[fieldName]) {
                        const updatedErrors = { ...this.fieldErrors };
                        delete updatedErrors[fieldName];
                        this.fieldErrors = updatedErrors;
                    }
                }
            }

            // Update UI field visibility
            if (this.$el) {
                BusinessRulesEngine.updateFieldVisibility(this.formData, this.$el);
            }
        },

        isFieldVisible(fieldName) {
            // Check business rules first
            const businessRulesVisibility = BusinessRulesEngine.evaluateFieldAvailability(this.formData);
            if (businessRulesVisibility.hasOwnProperty(fieldName)) {
                const isBusinessRuleVisible = businessRulesVisibility[fieldName];
                console.log(`🔍 Business rule for ${fieldName}: ${isBusinessRuleVisible} (type: ${this.formData.type})`);
                if (!isBusinessRuleVisible) {
                    return false;
                }
            }

            // If no conditional logic, field is visible by default
            if (!this.schema || !this.schema.conditional_logic[fieldName]) {
                return true;
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
            // This method is deprecated - options now come from schema
            console.warn('🦆 [PROFILE-ENTRY] getFieldOptions is deprecated, options come from schema');
            return [];
        },

        async getAllFieldOptions(fieldName) {
            // Get options from database via API
            if (!this.manufacturingTypeId) {
                console.warn('🦆 [PROFILE-ENTRY] No manufacturing type ID available');
                return [];
            }
            
            return await FormHelpers.getFieldOptions(fieldName, this.manufacturingTypeId, this.pageType);
        },

        getCustomOptions(fieldName) {
            // Custom options are now stored in database, not localStorage
            // This method is kept for backward compatibility but returns empty array
            return [];
        },

        async addNewOption(fieldName, optionValue) {
            if (!optionValue || optionValue.trim() === '') {
                showToast('Please enter a valid option value', 'warning');
                return;
            }

            if (!this.manufacturingTypeId) {
                showToast('No manufacturing type selected', 'error');
                return;
            }

            const trimmedValue = optionValue.trim();
            
            try {
                const result = await FormHelpers.addFieldOption(
                    fieldName, 
                    trimmedValue, 
                    this.manufacturingTypeId, 
                    this.pageType
                );
                
                if (result.success) {
                    showToast(result.message || `Added "${trimmedValue}" to ${fieldName} options`, 'success');
                    
                    // Reload the schema to get updated options
                    await this.loadSchema();
                    
                    // Force Alpine.js to re-render
                    this.$nextTick(() => {
                        this.fieldErrors = { ...this.fieldErrors };
                    });
                } else {
                    showToast(result.error || `Failed to add "${trimmedValue}"`, 'error');
                }
            } catch (error) {
                console.error('🦆 [PROFILE-ENTRY] Error adding option:', error);
                showToast(`Error adding option: ${error.message}`, 'error');
            }
        },

        async removeExistingOption(fieldName, optionValue) {
            if (!optionValue || optionValue.trim() === '') {
                showToast('Please enter a valid option value to remove', 'warning');
                return;
            }

            if (!this.manufacturingTypeId) {
                showToast('No manufacturing type selected', 'error');
                return;
            }

            const trimmedValue = optionValue.trim();
            
            // Confirm removal
            if (!confirm(`Are you sure you want to remove "${trimmedValue}" from ${fieldName} options?`)) {
                return;
            }
            
            try {
                const result = await FormHelpers.removeFieldOptionByName(
                    fieldName, 
                    trimmedValue, 
                    this.manufacturingTypeId, 
                    this.pageType
                );
                
                if (result.success) {
                    showToast(result.message || `Removed "${trimmedValue}" from ${fieldName} options`, 'success');
                    
                    // If the removed option was selected, clear the field value
                    if (this.formData[fieldName] === trimmedValue) {
                        this.updateField(fieldName, '');
                    }
                    
                    // Reload the schema to get updated options
                    await this.loadSchema();
                    
                    // Force Alpine.js to re-render
                    this.$nextTick(() => {
                        this.fieldErrors = { ...this.fieldErrors };
                    });
                } else {
                    showToast(result.error || `Failed to remove "${trimmedValue}"`, 'error');
                }
            } catch (error) {
                console.error('🦆 [PROFILE-ENTRY] Error removing option:', error);
                showToast(`Error removing option: ${error.message}`, 'error');
            }
        },

        async removeCustomOption(fieldName, optionValue, optionId) {
            if (!optionId) {
                showToast('Cannot remove option: missing option ID', 'error');
                return;
            }

            if (confirm(`Are you sure you want to remove "${optionValue}" from ${fieldName} options?`)) {
                try {
                    const result = await FormHelpers.removeFieldOption(optionId);
                    
                    if (result.success) {
                        showToast(result.message || `Removed "${optionValue}" from ${fieldName} options`, 'success');
                        
                        // If the removed option was selected, clear the field value
                        if (this.formData[fieldName] === optionValue) {
                            this.updateField(fieldName, '');
                        }
                        
                        // Reload the schema to get updated options
                        await this.loadSchema();
                        
                        // Force Alpine.js to re-render
                        this.$nextTick(() => {
                            this.fieldErrors = { ...this.fieldErrors };
                        });
                    } else {
                        showToast(result.error || `Failed to remove "${optionValue}"`, 'error');
                    }
                } catch (error) {
                    console.error('🦆 [PROFILE-ENTRY] Error removing option:', error);
                    showToast(`Error removing option: ${error.message}`, 'error');
                }
            }
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

        // Field type helpers for inline editing
        getFieldInfoByHeader(header) {
            console.log('🔍 [FIELD INFO] getFieldInfoByHeader called with header:', header);
            
            // Get field name from header mapping
            const mapping = FormHelpers.getHeaderMapping();
            console.log('🔍 [FIELD INFO] Header mapping:', mapping);
            
            const fieldName = mapping[header];
            console.log('🔍 [FIELD INFO] Mapped fieldName:', fieldName);
            
            if (!fieldName) {
                console.log('🔍 [FIELD INFO] ❌ No fieldName found for header:', header);
                return null;
            }
            
            // Find field in schema
            if (!this.schema?.sections) {
                console.log('🔍 [FIELD INFO] ❌ No schema sections available');
                return null;
            }
            
            console.log('🔍 [FIELD INFO] Searching schema sections for field:', fieldName);
            for (const section of this.schema.sections) {
                for (const field of section.fields) {
                    if (field.name === fieldName) {
                        const result = {
                            fieldName: field.name,
                            componentType: field.componentType || 'text',
                            options: field.options || [],
                            validation_rules: field.validation_rules || {},
                            data_type: field.data_type
                        };
                        console.log('🔍 [FIELD INFO] ✅ Found field:', result);
                        return result;
                    }
                }
            }
            console.log('🔍 [FIELD INFO] ❌ Field not found in schema:', fieldName);
            return null;
        },

        getFieldOptionsForHeader(header) {
            const fieldInfo = this.getFieldInfoByHeader(header);
            const options = fieldInfo?.options || [];
            console.log('🔍 [FIELD OPTIONS] Options for', header, ':', options);
            return options;
        },

        getFieldComponentType(header) {
            const fieldInfo = this.getFieldInfoByHeader(header);
            const componentType = fieldInfo?.componentType || 'text';
            console.log('🔍 [COMPONENT TYPE]', header, '→', componentType);
            return componentType;
        },

        getFieldValidationRules(header) {
            const fieldInfo = this.getFieldInfoByHeader(header);
            return fieldInfo?.validation_rules || {};
        },

        isDropdownField(header) {
            const componentType = this.getFieldComponentType(header);
            const result = componentType === 'dropdown';
            console.log('🔍 [IS DROPDOWN]', header, ':', result, '(componentType:', componentType, ')');
            return result;
        },

        isNumberField(header) {
            const componentType = this.getFieldComponentType(header);
            const result = ['number', 'percentage', 'currency'].includes(componentType);
            console.log('🔍 [IS NUMBER]', header, ':', result, '(componentType:', componentType, ')');
            return result;
        },

        isCheckboxField(header) {
            const componentType = this.getFieldComponentType(header);
            return componentType === 'checkbox';
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

        /**
         * Auto-calculate price fields based on length_of_beam
         * Formula: price_per_beam = price_per_meter * length_of_beam
         * 
         * Uses proper decimal arithmetic to avoid floating point precision issues
         */
        autoCalculatePriceFields(fieldName, value) {
            console.log('%c🧮 [PRICE CALC] autoCalculatePriceFields called', 'background: #ff6600; color: white; font-size: 14px; padding: 4px;');
            console.log('%c Field: ' + fieldName + ', Value: ' + value, 'background: #ff6600; color: white; font-size: 12px; padding: 2px;');
            
            // Only process relevant fields
            const priceFields = ['price_per_meter', 'price_per_beam', 'length_of_beam'];
            if (!priceFields.includes(fieldName)) {
                console.log(`🧮 [PRICE CALC] Field ${fieldName} is not a price field, skipping`);
                return;
            }

            // Get current values
            const lengthOfBeam = this.parseDecimal(this.formData.length_of_beam);
            const pricePerMeter = this.parseDecimal(this.formData.price_per_meter);
            const pricePerBeam = this.parseDecimal(this.formData.price_per_beam);

            console.log('%c🧮 [PRICE CALC] Current values', 'background: #0066ff; color: white; font-size: 12px; padding: 2px;');
            console.log('  lengthOfBeam:', lengthOfBeam);
            console.log('  pricePerMeter:', pricePerMeter);
            console.log('  pricePerBeam:', pricePerBeam);

            // Skip if length_of_beam is not set or is zero
            if (lengthOfBeam === null || lengthOfBeam === 0) {
                console.log(`🧮 [PRICE CALC] length_of_beam is null or 0, skipping calculation`);
                return;
            }

            let targetField = null;
            let calculatedValue = null;

            // Calculate based on which field was changed
            if (fieldName === 'price_per_meter' && pricePerMeter !== null) {
                // Calculate price_per_beam from price_per_meter
                calculatedValue = this.roundToDecimals(pricePerMeter * lengthOfBeam, 2);
                targetField = 'price_per_beam';
                this.formData.price_per_beam = calculatedValue;
                console.log(`🧮 [PRICE CALC] price_per_beam = ${pricePerMeter} × ${lengthOfBeam} = ${calculatedValue}`);
            } else if (fieldName === 'price_per_beam' && pricePerBeam !== null) {
                // Calculate price_per_meter from price_per_beam
                calculatedValue = this.roundToDecimals(pricePerBeam / lengthOfBeam, 2);
                targetField = 'price_per_meter';
                this.formData.price_per_meter = calculatedValue;
                console.log(`🧮 [PRICE CALC] price_per_meter = ${pricePerBeam} ÷ ${lengthOfBeam} = ${calculatedValue}`);
            } else if (fieldName === 'length_of_beam' && pricePerMeter !== null) {
                // Recalculate price_per_beam when length changes (if price_per_meter is set)
                calculatedValue = this.roundToDecimals(pricePerMeter * lengthOfBeam, 2);
                targetField = 'price_per_beam';
                this.formData.price_per_beam = calculatedValue;
                console.log(`🧮 [PRICE CALC] length changed: price_per_beam = ${pricePerMeter} × ${lengthOfBeam} = ${calculatedValue}`);
            } else {
                console.log(`🧮 [PRICE CALC] No calculation performed - conditions not met`);
                return;
            }

            // Update the DOM input element directly since :value is one-way binding
            if (targetField && calculatedValue !== null && this.$el) {
                const inputElement = this.$el.querySelector(`#${targetField}, [name="${targetField}"], input[id="${targetField}"]`);
                if (inputElement) {
                    inputElement.value = calculatedValue;
                    console.log(`🧮 [PRICE CALC] Updated DOM input #${targetField} to ${calculatedValue}`);
                } else {
                    console.log(`🧮 [PRICE CALC] Could not find input element for ${targetField}`);
                }
            }
        },

        /**
         * Parse a value to a decimal number, handling various input formats
         * Returns null if the value is empty, null, undefined, or not a valid number
         */
        parseDecimal(value) {
            if (value === null || value === undefined || value === '') {
                return null;
            }
            
            // Handle string values
            if (typeof value === 'string') {
                value = value.trim();
                if (value === '') {
                    return null;
                }
            }
            
            const num = parseFloat(value);
            return isNaN(num) ? null : num;
        },

        /**
         * Round a number to specified decimal places using proper decimal arithmetic
         * This avoids floating point precision issues like 0.1 + 0.2 = 0.30000000000000004
         */
        roundToDecimals(value, decimals) {
            if (value === null || value === undefined || isNaN(value)) {
                return null;
            }
            
            // Use the "multiply, round, divide" technique to avoid floating point issues
            // Adding Number.EPSILON helps with edge cases like 1.005 rounding to 1.00 instead of 1.01
            const multiplier = Math.pow(10, decimals);
            return Math.round((value + Number.EPSILON) * multiplier) / multiplier;
        },

        updateField(fieldName, value) {
            console.log('%c🔄 [UPDATE FIELD] updateField called', 'background: #222; color: #bada55; font-size: 14px; padding: 4px;');
            console.log('%c Field: ' + fieldName + ', Value: ' + value, 'background: #222; color: #00ff00; font-size: 12px; padding: 2px;');
            
            // Update form data
            this.formData[fieldName] = value;

            // Handle System Series auto-population
            if (fieldName === 'system_series') {
                this.handleSystemSeriesChange(value);
            }

            // Auto-calculate price fields
            this.autoCalculatePriceFields(fieldName, value);

            // Handle cascading dropdowns for relation fields
            this.handleCascadingOptions(fieldName, value);

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

        /**
         * Handle cascading dropdown options for relation fields
         * When a parent field changes, fetch and update child field options
         * 
         * Hierarchy: company → material → opening_system → system_series → colours
         */
        async handleCascadingOptions(fieldName, value) {
            // Define the cascading hierarchy
            // Note: Schema uses 'colours' but Relations API uses 'color'
            const cascadeHierarchy = ['company', 'material', 'opening_system', 'system_series', 'colours'];
            const apiFieldMapping = {
                'company': 'company',
                'material': 'material',
                'opening_system': 'opening_system',
                'system_series': 'system_series',
                'colours': 'color'  // Map schema field to API field
            };
            
            const fieldIndex = cascadeHierarchy.indexOf(fieldName);
            
            // Only process if this is a cascading field
            if (fieldIndex === -1) {
                console.log(`🔗 [CASCADE] Field ${fieldName} is not in cascade hierarchy, skipping`);
                return;
            }
            
            console.log(`🔗 [CASCADE] ========================================`);
            console.log(`🔗 [CASCADE] Field ${fieldName} changed to "${value}"`);
            console.log(`🔗 [CASCADE] Field index in hierarchy: ${fieldIndex}`);
            
            // Clear all child field values and options when parent changes
            for (let i = fieldIndex + 1; i < cascadeHierarchy.length; i++) {
                const childField = cascadeHierarchy[i];
                this.formData[childField] = '';
                
                // Also clear the options in the schema
                if (this.schema && this.schema.sections) {
                    for (const section of this.schema.sections) {
                        const field = section.fields.find(f => f.name === childField);
                        if (field) {
                            field.options = [];
                        }
                    }
                }
                console.log(`🔗 [CASCADE] Cleared child field: ${childField}`);
            }
            
            // If value is empty, clear children and return
            if (!value) {
                console.log(`🔗 [CASCADE] Value is empty, cleared children, done`);
                this.schema = { ...this.schema }; // Force reactivity
                return;
            }
            
            // Build parent selections for API call - get entity IDs for all selected parents
            const parentSelections = {};
            
            for (let i = 0; i <= fieldIndex; i++) {
                const schemaField = cascadeHierarchy[i];
                const apiField = apiFieldMapping[schemaField];
                const fieldValue = this.formData[schemaField];
                
                console.log(`🔗 [CASCADE] Processing parent ${schemaField}: "${fieldValue}"`);
                
                if (fieldValue) {
                    // Get entity ID by name
                    const entityId = await this.getEntityIdByName(apiField, fieldValue);
                    console.log(`🔗 [CASCADE] Got entity ID for ${apiField}="${fieldValue}": ${entityId}`);
                    
                    if (entityId) {
                        parentSelections[`${apiField}_id`] = entityId;
                    } else {
                        console.warn(`🔗 [CASCADE] Could not find entity ID for ${apiField}="${fieldValue}"`);
                    }
                }
            }
            
            console.log(`🔗 [CASCADE] Parent selections for API:`, parentSelections);
            
            // Fetch dependent options from Relations API
            try {
                const response = await fetch('/api/v1/admin/relations/options', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify(parentSelections)
                });
                
                console.log(`🔗 [CASCADE] API response status: ${response.status}`);
                
                if (!response.ok) {
                    console.warn(`🔗 [CASCADE] Failed to fetch options: ${response.status}`);
                    return;
                }
                
                const data = await response.json();
                const options = data.options || {};
                
                console.log(`🔗 [CASCADE] Received options from API:`, options);
                
                // Update schema options for child fields
                if (this.schema && this.schema.sections) {
                    for (const section of this.schema.sections) {
                        for (const field of section.fields) {
                            // Map schema field name to API field name
                            const apiFieldName = apiFieldMapping[field.name] || field.name;
                            
                            if (options[apiFieldName] && options[apiFieldName].length > 0) {
                                // Update field options with names from the API
                                field.options = options[apiFieldName].map(opt => opt.name);
                                console.log(`🔗 [CASCADE] ✅ Updated ${field.name} options:`, field.options);
                            }
                        }
                    }
                    
                    // Force Alpine.js reactivity
                    this.schema = { ...this.schema };
                    console.log(`🔗 [CASCADE] Schema updated, reactivity triggered`);
                }
                
            } catch (error) {
                console.error(`🔗 [CASCADE] Error fetching options:`, error);
            }
            
            console.log(`🔗 [CASCADE] ========================================`);
        },
        
        /**
         * Get entity ID by name from the Relations API
         */
        async getEntityIdByName(entityType, entityName) {
            console.log(`🔗 [CASCADE] getEntityIdByName called: type=${entityType}, name="${entityName}"`);
            try {
                const url = `/api/v1/admin/relations/entities/${entityType}`;
                console.log(`🔗 [CASCADE] Fetching: ${url}`);
                
                const response = await fetch(url, {
                    credentials: 'include'
                });
                
                console.log(`🔗 [CASCADE] Response status: ${response.status}`);
                
                if (!response.ok) {
                    console.warn(`🔗 [CASCADE] Failed to get entities: ${response.status}`);
                    return null;
                }
                
                const data = await response.json();
                const entities = data.entities || [];
                
                console.log(`🔗 [CASCADE] Found ${entities.length} entities:`, entities.map(e => e.name));
                
                const entity = entities.find(e => e.name === entityName);
                
                if (entity) {
                    console.log(`🔗 [CASCADE] ✅ Found entity: id=${entity.id}, name="${entity.name}"`);
                    return entity.id;
                } else {
                    console.warn(`🔗 [CASCADE] ❌ Entity not found: "${entityName}"`);
                    return null;
                }
                
            } catch (error) {
                console.error(`🔗 [CASCADE] Error getting entity ID:`, error);
                return null;
            }
        },

        /**
         * Initialize cascading options on page load
         * Loads initial options AND restores cascading state for draft values
         */
        async initializeCascadingOptions() {
            console.log('🔗 [CASCADE] Initializing cascading options...');
            
            const cascadeHierarchy = ['company', 'material', 'opening_system', 'system_series', 'colours'];
            const apiFieldMapping = {
                'company': 'company',
                'material': 'material',
                'opening_system': 'opening_system',
                'system_series': 'system_series',
                'colours': 'color'
            };
            
            try {
                // Load initial options for all relation fields
                const response = await fetch('/api/v1/admin/relations/options', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({})
                });
                
                if (!response.ok) {
                    console.warn('🔗 [CASCADE] Failed to fetch initial options, using schema defaults');
                    return;
                }
                
                const data = await response.json();
                const options = data.options || {};
                
                console.log('🔗 [CASCADE] Initial options loaded:', options);
                
                // Update schema options for all relation fields
                if (this.schema && this.schema.sections) {
                    for (const section of this.schema.sections) {
                        for (const field of section.fields) {
                            const apiFieldName = apiFieldMapping[field.name] || field.name;
                            
                            if (options[apiFieldName] && options[apiFieldName].length > 0) {
                                field.options = options[apiFieldName].map(opt => opt.name);
                                console.log(`🔗 [CASCADE] Updated ${field.name} options:`, field.options);
                            }
                        }
                    }
                }
                
                // Now restore cascading options for any pre-selected draft values
                // Go through each level of the hierarchy and load dependent options
                console.log('🔗 [CASCADE] Checking for draft values to restore...');
                console.log('🔗 [CASCADE] Current formData:', this.formData);
                
                const parentSelections = {};
                
                for (let i = 0; i < cascadeHierarchy.length; i++) {
                    const fieldName = cascadeHierarchy[i];
                    const fieldValue = this.formData[fieldName];
                    
                    if (!fieldValue) {
                        console.log(`🔗 [CASCADE] No draft value for ${fieldName}, stopping cascade restore`);
                        break;
                    }
                    
                    console.log(`🔗 [CASCADE] Restoring cascade for ${fieldName}="${fieldValue}"`);
                    
                    // Get entity ID for this value
                    const apiField = apiFieldMapping[fieldName];
                    const entityId = await this.getEntityIdByName(apiField, fieldValue);
                    
                    if (!entityId) {
                        console.warn(`🔗 [CASCADE] Could not find entity ID for ${fieldName}="${fieldValue}", stopping`);
                        break;
                    }
                    
                    parentSelections[`${apiField}_id`] = entityId;
                    
                    // Fetch options for the next level
                    if (i < cascadeHierarchy.length - 1) {
                        console.log(`🔗 [CASCADE] Fetching options with selections:`, parentSelections);
                        
                        const cascadeResponse = await fetch('/api/v1/admin/relations/options', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            credentials: 'include',
                            body: JSON.stringify(parentSelections)
                        });
                        
                        if (cascadeResponse.ok) {
                            const cascadeData = await cascadeResponse.json();
                            const cascadeOptions = cascadeData.options || {};
                            
                            console.log(`🔗 [CASCADE] Received options for level ${i}:`, cascadeOptions);
                            
                            // Update schema options for child fields
                            if (this.schema && this.schema.sections) {
                                for (const section of this.schema.sections) {
                                    for (const field of section.fields) {
                                        const fieldApiName = apiFieldMapping[field.name] || field.name;
                                        if (cascadeOptions[fieldApiName] && cascadeOptions[fieldApiName].length > 0) {
                                            field.options = cascadeOptions[fieldApiName].map(opt => opt.name);
                                            console.log(`🔗 [CASCADE] ✅ Restored ${field.name} options:`, field.options);
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                
                // Force Alpine.js reactivity
                this.schema = { ...this.schema };
                console.log('🔗 [CASCADE] Cascade initialization complete');
                
            } catch (error) {
                console.error('🔗 [CASCADE] Error initializing cascading options:', error);
            }
        },

        /**
         * Handle System Series selection change for auto-population
         * This is the master selector that auto-populates dependent fields
         */
        async handleSystemSeriesChange(systemSeriesName) {
            console.log('🎯 [SYSTEM SERIES] ========================================');
            console.log('🎯 [SYSTEM SERIES] handleSystemSeriesChange called with:', systemSeriesName);
            
            // Clear auto-populated fields first
            this.clearAutoPopulatedFields();
            
            if (!systemSeriesName) {
                console.log('🎯 [SYSTEM SERIES] Empty value, cleared auto-populated fields');
                return;
            }
            
            this.loadingSystemSeriesData = true;
            
            try {
                // Get system series ID by name
                const systemSeriesId = await this.getEntityIdByName('system_series', systemSeriesName);
                
                if (!systemSeriesId) {
                    console.warn('🎯 [SYSTEM SERIES] Could not find system series ID for:', systemSeriesName);
                    return;
                }
                
                console.log('🎯 [SYSTEM SERIES] Found system series ID:', systemSeriesId);
                
                // Call the relations API to get dependent options
                const response = await fetch('/api/v1/admin/relations/options', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({ system_series_id: systemSeriesId })
                });
                
                if (!response.ok) {
                    throw new Error(`Failed to fetch system series data: ${response.status}`);
                }
                
                const data = await response.json();
                console.log('🎯 [SYSTEM SERIES] Received data:', data);
                
                const options = data.options || {};
                
                // Auto-populate dependent fields
                this.autoPopulateFromSystemSeries(options);
                
                // Store the system series data for reference
                this.systemSeriesData = options;
                
                console.log('🎯 [SYSTEM SERIES] ✅ Auto-population complete');
                
            } catch (error) {
                console.error('🎯 [SYSTEM SERIES] ❌ Error:', error);
                showToast(`Failed to load system series data: ${error.message}`, 'error');
            } finally {
                this.loadingSystemSeriesData = false;
            }
            
            console.log('🎯 [SYSTEM SERIES] ========================================');
        },
        
        /**
         * Auto-populate fields based on system series selection
         */
        autoPopulateFromSystemSeries(options) {
            console.log('🎯 [AUTO-POPULATE] Starting auto-population with options:', options);
            
            // Map API field names to form field names
            const fieldMapping = {
                'company': 'company',
                'material': 'material', 
                'opening_system': 'opening_system',
                'color': 'colours' // Note: API uses 'color', form uses 'colours'
            };
            
            // Auto-populate single-select fields
            for (const [apiField, formField] of Object.entries(fieldMapping)) {
                if (options[apiField] && options[apiField].length > 0) {
                    if (formField === 'colours') {
                        // Handle colors as multi-select (take all colors)
                        const colorNames = options[apiField].map(opt => opt.name);
                        this.formData[formField] = colorNames;
                        this.autoPopulatedFields.add(formField);
                        console.log(`🎯 [AUTO-POPULATE] Set ${formField} to:`, colorNames);
                    } else {
                        // Handle single-select fields (take first option)
                        const selectedValue = options[apiField][0].name;
                        this.formData[formField] = selectedValue;
                        this.autoPopulatedFields.add(formField);
                        console.log(`🎯 [AUTO-POPULATE] Set ${formField} to:`, selectedValue);
                    }
                }
            }
            
            // Force Alpine.js reactivity
            this.formData = { ...this.formData };
            
            console.log('🎯 [AUTO-POPULATE] Auto-populated fields:', Array.from(this.autoPopulatedFields));
        },
        
        /**
         * Clear auto-populated fields when system series changes
         */
        clearAutoPopulatedFields() {
            console.log('🎯 [CLEAR] Clearing auto-populated fields:', Array.from(this.autoPopulatedFields));
            
            for (const fieldName of this.autoPopulatedFields) {
                this.formData[fieldName] = '';
            }
            
            this.autoPopulatedFields.clear();
            this.systemSeriesData = null;
            
            // Force Alpine.js reactivity
            this.formData = { ...this.formData };
        },
        
        /**
         * Check if a field is auto-populated (for UI styling)
         */
        isAutoPopulated(fieldName) {
            return this.autoPopulatedFields.has(fieldName);
        },

        /**
         * Add a color to the colors array (for manual selection)
         */
        addColor(colorName) {
            if (!colorName || this.isAutoPopulated('colours')) return;
            
            if (!this.formData.colours) {
                this.formData.colours = [];
            }
            
            if (!this.formData.colours.includes(colorName)) {
                this.formData.colours.push(colorName);
                this.formData = { ...this.formData }; // Force reactivity
                console.log('🎨 [COLORS] Added color:', colorName, 'Current colors:', this.formData.colours);
            }
        },
        
        /**
         * Remove a color from the colors array (for manual selection)
         */
        removeColor(colorName) {
            if (this.isAutoPopulated('colours')) return;
            
            if (this.formData.colours) {
                this.formData.colours = this.formData.colours.filter(c => c !== colorName);
                this.formData = { ...this.formData }; // Force reactivity
                console.log('🎨 [COLORS] Removed color:', colorName, 'Current colors:', this.formData.colours);
            }
        },

        /**
         * Handle System Series selection change and auto-populate related fields
         */
        async handleSystemSeriesChange(systemSeriesValue) {
            console.log('🎯 [SYSTEM SERIES] ========================================');
            console.log('🎯 [SYSTEM SERIES] System Series changed to:', systemSeriesValue);
            
            // Update the form data first
            this.updateField('system_series', systemSeriesValue);
            
            // Clear auto-populated fields if no system series selected
            if (!systemSeriesValue) {
                console.log('🎯 [SYSTEM SERIES] No system series selected, clearing auto-populated fields');
                this.clearAutoPopulatedFields();
                return;
            }
            
            this.loadingSystemSeriesData = true;
            
            try {
                // Get the system series entity ID
                const systemSeriesId = await this.getEntityIdByName('system_series', systemSeriesValue);
                
                if (!systemSeriesId) {
                    console.warn('🎯 [SYSTEM SERIES] Could not find system series ID for:', systemSeriesValue);
                    return;
                }
                
                console.log('🎯 [SYSTEM SERIES] Found system series ID:', systemSeriesId);
                
                // Call the relations API to get dependent options
                const response = await fetch('/api/v1/admin/relations/options', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({ system_series_id: systemSeriesId })
                });
                
                if (!response.ok) {
                    console.error('🎯 [SYSTEM SERIES] API call failed:', response.status);
                    return;
                }
                
                const data = await response.json();
                const options = data.options || {};
                
                console.log('🎯 [SYSTEM SERIES] Received auto-population data:', options);
                
                // Auto-populate the dependent fields
                this.autoPopulateFields(options);
                
            } catch (error) {
                console.error('🎯 [SYSTEM SERIES] Error during auto-population:', error);
            } finally {
                this.loadingSystemSeriesData = false;
            }
            
            console.log('🎯 [SYSTEM SERIES] ========================================');
        },

        /**
         * Auto-populate dependent fields from System Series selection
         */
        autoPopulateFields(options) {
            console.log('🎯 [AUTO-POPULATE] Starting auto-population with options:', options);
            
            // Clear previous auto-populated fields
            this.autoPopulatedFields.clear();
            
            // Map API field names to form field names
            const fieldMapping = {
                'company': 'company',
                'material': 'material', 
                'opening_system': 'opening_system',
                'color': 'colours'  // Note: API uses 'color', form uses 'colours'
            };
            
            // Auto-populate each field that has data
            for (const [apiField, formField] of Object.entries(fieldMapping)) {
                if (options[apiField] && options[apiField].length > 0) {
                    const firstOption = options[apiField][0];
                    const value = firstOption.name;
                    
                    console.log(`🎯 [AUTO-POPULATE] Setting ${formField} = "${value}"`);
                    
                    // Update form data
                    this.updateField(formField, value);
                    
                    // Mark as auto-populated
                    this.autoPopulatedFields.add(formField);
                    
                    // Update field options in schema to include the auto-populated value
                    this.updateFieldOptions(formField, options[apiField].map(opt => opt.name));
                }
            }
            
            console.log('🎯 [AUTO-POPULATE] Auto-populated fields:', Array.from(this.autoPopulatedFields));
        },

        /**
         * Update field options in the schema
         */
        updateFieldOptions(fieldName, newOptions) {
            if (!this.schema || !this.schema.sections) return;
            
            for (const section of this.schema.sections) {
                const field = section.fields.find(f => f.name === fieldName);
                if (field) {
                    field.options = newOptions;
                    console.log(`🎯 [AUTO-POPULATE] Updated ${fieldName} options:`, newOptions);
                    break;
                }
            }
            
            // Force Alpine.js reactivity
            this.schema = { ...this.schema };
        },

        /**
         * Clear auto-populated fields when System Series is deselected
         */
        clearAutoPopulatedFields() {
            console.log('🎯 [AUTO-POPULATE] Clearing auto-populated fields:', Array.from(this.autoPopulatedFields));
            
            for (const fieldName of this.autoPopulatedFields) {
                this.updateField(fieldName, '');
            }
            
            this.autoPopulatedFields.clear();
        },

        /**
         * Check if a field is auto-populated by System Series
         */
        isAutoPopulated(fieldName) {
            return this.autoPopulatedFields.has(fieldName);
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
            console.log('🦆 [PREVIEW HEADERS GETTER] Called - dynamicHeaders:', this.dynamicHeaders);
            console.log('🦆 [PREVIEW HEADERS GETTER] dynamicHeaders length:', this.dynamicHeaders?.length || 0);
            console.log('🦆 [PREVIEW HEADERS GETTER] dynamicHeaders type:', typeof this.dynamicHeaders);
            
            // Return empty array while loading to prevent errors
            if (!this.dynamicHeaders || this.dynamicHeaders.length === 0) {
                console.log('🦆 [PREVIEW HEADERS] Headers not yet loaded, returning empty array');
                return [];
            }
            console.log('🦆 [PREVIEW HEADERS] Returning headers:', this.dynamicHeaders);
            return this.dynamicHeaders;
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
        },

        // Bulk Selection Methods
        toggleRowSelection(rowId) {
            if (this.selectedRows.has(rowId)) {
                this.selectedRows.delete(rowId);
            } else {
                this.selectedRows.add(rowId);
            }
            
            // Update select all state
            this.selectAll = this.selectedRows.size === this.savedConfigurations.length && this.savedConfigurations.length > 0;
            
            console.log('🦆 [SELECTION] Row selection toggled:', rowId, 'Selected count:', this.selectedRows.size);
        },

        toggleSelectAll() {
            if (this.selectAll) {
                // Deselect all
                this.selectedRows.clear();
                this.selectAll = false;
            } else {
                // Select all visible configurations
                this.selectedRows.clear();
                this.filteredConfigurations.forEach(config => {
                    this.selectedRows.add(config.id);
                });
                this.selectAll = true;
            }
            
            console.log('🦆 [SELECTION] Select all toggled:', this.selectAll, 'Selected count:', this.selectedRows.size);
        },

        isRowSelected(rowId) {
            return this.selectedRows.has(rowId);
        },

        get hasSelectedRows() {
            return this.selectedRows.size > 0;
        },

        get selectedRowsCount() {
            return this.selectedRows.size;
        },

        clearSelection() {
            this.selectedRows.clear();
            this.selectAll = false;
        },

        async bulkDeleteSelected() {
            if (this.selectedRows.size === 0) {
                showToast('No rows selected for deletion', 'warning');
                return;
            }

            const selectedIds = Array.from(this.selectedRows);
            const confirmMessage = `Are you sure you want to delete ${selectedIds.length} configuration${selectedIds.length > 1 ? 's' : ''}? This action cannot be undone.`;
            
            if (!confirm(confirmMessage)) {
                return;
            }

            this.bulkDeleting = true;

            try {
                console.log('🦆 [BULK DELETE] Starting bulk delete for IDs:', selectedIds);
                
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
                
                const response = await fetch('/api/v1/admin/entry/profile/configurations/bulk', {
                    method: 'DELETE',
                    headers: headers,
                    credentials: 'include',  // Include cookies for authentication
                    body: JSON.stringify(selectedIds)
                });

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}));
                    throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
                }

                const result = await response.json();
                console.log('🦆 [BULK DELETE] Result:', result);

                // Update UI based on results
                if (result.success_count > 0) {
                    // Remove successfully deleted configurations from the list
                    this.savedConfigurations = this.savedConfigurations.filter(config => 
                        !selectedIds.includes(config.id) || result.errors.some(error => error.includes(config.id.toString()))
                    );
                    this.updateConfigurationsData();
                }

                // Clear selection
                this.clearSelection();

                // Show results
                if (result.error_count === 0) {
                    showToast(`Successfully deleted ${result.success_count} configuration${result.success_count > 1 ? 's' : ''}`, 'success');
                } else if (result.success_count > 0) {
                    showToast(`Deleted ${result.success_count} configurations, ${result.error_count} failed`, 'warning', 6000);
                    if (result.errors.length > 0) {
                        console.warn('🦆 [BULK DELETE] Errors:', result.errors);
                    }
                } else {
                    showToast(`Failed to delete configurations: ${result.errors.join(', ')}`, 'error', 8000);
                }

            } catch (err) {
                console.error('🦆 [BULK DELETE] Error:', err);
                showToast(`Bulk delete failed: ${err.message}`, 'error', 6000);
            } finally {
                this.bulkDeleting = false;
            }
        }
    };
}