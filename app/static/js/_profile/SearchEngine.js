/**
 * SearchEngine - Handles search and filter functionality for the preview table
 * Provides real-time search across all columns with highlighting and filtering
 */
class SearchEngine {
    constructor() {
        this.searchQuery = '';
        this.columnFilters = {};
        this.showAdvancedSearch = false;
        this.searchResults = {
            total: 0,
            filtered: 0
        };
        this.filteredConfigurations = [];
        this.originalConfigurations = [];
        
        // URL parameter support
        this.urlParams = new URLSearchParams(window.location.search);
        this.loadSearchStateFromURL();
    }

    /**
     * Initialize search functionality with configurations
     * @param {Array} configurations - Array of configuration objects
     */
    initialize(configurations) {
        this.originalConfigurations = configurations || [];
        this.searchResults.total = this.originalConfigurations.length;
        this.performSearch();
    }

    /**
     * Update configurations when data changes
     * @param {Array} configurations - Updated array of configuration objects
     */
    updateConfigurations(configurations) {
        this.originalConfigurations = configurations || [];
        this.searchResults.total = this.originalConfigurations.length;
        this.performSearch();
    }

    /**
     * Perform search and filtering across all configurations
     */
    performSearch() {
        let filtered = [...this.originalConfigurations];

        // Apply global search query
        if (this.searchQuery && this.searchQuery.trim()) {
            filtered = this.applyGlobalSearch(filtered, this.searchQuery.trim());
        }

        // Apply column-specific filters
        if (Object.keys(this.columnFilters).length > 0) {
            filtered = this.applyColumnFilters(filtered);
        }

        this.filteredConfigurations = filtered;
        this.searchResults.filtered = filtered.length;

        // Update URL parameters
        this.updateURLParams();

        console.log('🔍 [SEARCH] Search performed:', {
            query: this.searchQuery,
            columnFilters: this.columnFilters,
            total: this.searchResults.total,
            filtered: this.searchResults.filtered
        });
    }

    /**
     * Apply global search across all columns
     * @param {Array} configurations - Configurations to search
     * @param {string} query - Search query
     * @returns {Array} Filtered configurations
     */
    applyGlobalSearch(configurations, query) {
        const searchTerms = query.toLowerCase().split(/\s+/).filter(term => term.length > 0);
        
        return configurations.filter(config => {
            // Search across all fields in the configuration
            const searchableText = Object.values(config)
                .map(value => {
                    if (value === null || value === undefined) return '';
                    return String(value).toLowerCase();
                })
                .join(' ');

            // Check if all search terms are found
            return searchTerms.every(term => searchableText.includes(term));
        });
    }

    /**
     * Apply column-specific filters
     * @param {Array} configurations - Configurations to filter
     * @returns {Array} Filtered configurations
     */
    applyColumnFilters(configurations) {
        return configurations.filter(config => {
            return Object.entries(this.columnFilters).every(([header, filterValue]) => {
                if (!filterValue || !filterValue.trim()) return true;

                // The backend creates row data using header names as keys,
                // so we can directly use the header to access the config value
                const configValue = config[header];
                if (configValue === null || configValue === undefined) return false;

                const configText = String(configValue).toLowerCase();
                const filterText = filterValue.toLowerCase().trim();

                return configText.includes(filterText);
            });
        });
    }

    /**
     * Highlight search terms in text
     * @param {string} text - Text to highlight
     * @param {string} header - Column header (for column-specific highlighting)
     * @returns {string} HTML with highlighted terms
     */
    highlightSearchTerm(text, header) {
        if (!text || text === 'N/A') return text;

        let highlightedText = String(text);
        const termsToHighlight = new Set();

        // Add global search terms
        if (this.searchQuery && this.searchQuery.trim()) {
            const searchTerms = this.searchQuery.toLowerCase().split(/\s+/).filter(term => term.length > 0);
            searchTerms.forEach(term => termsToHighlight.add(term));
        }

        // Add column-specific filter terms
        if (this.columnFilters[header] && this.columnFilters[header].trim()) {
            const filterTerms = this.columnFilters[header].toLowerCase().split(/\s+/).filter(term => term.length > 0);
            filterTerms.forEach(term => termsToHighlight.add(term));
        }

        // Apply highlighting
        termsToHighlight.forEach(term => {
            const regex = new RegExp(`(${this.escapeRegExp(term)})`, 'gi');
            highlightedText = highlightedText.replace(regex, '<span class="search-term-highlight">$1</span>');
        });

        return highlightedText;
    }

    /**
     * Check if a row should be highlighted (contains search terms)
     * @param {Object} row - Configuration row
     * @returns {boolean} True if row should be highlighted
     */
    isRowHighlighted(row) {
        if (!this.searchQuery && Object.keys(this.columnFilters).length === 0) {
            return false;
        }

        // Check if any field contains search terms
        const searchableText = Object.values(row)
            .map(value => {
                if (value === null || value === undefined) return '';
                return String(value).toLowerCase();
            })
            .join(' ');

        // Check global search
        if (this.searchQuery && this.searchQuery.trim()) {
            const searchTerms = this.searchQuery.toLowerCase().split(/\s+/).filter(term => term.length > 0);
            if (searchTerms.some(term => searchableText.includes(term))) {
                return true;
            }
        }

        // Check column filters
        return Object.entries(this.columnFilters).some(([header, filterValue]) => {
            if (!filterValue || !filterValue.trim()) return false;

            // The backend creates row data using header names as keys,
            // so we can directly use the header to access the row value
            const configValue = row[header];
            
            if (configValue === null || configValue === undefined) return false;
            
            const configText = String(configValue).toLowerCase();
            const filterText = filterValue.toLowerCase().trim();
            
            return configText.includes(filterText);
        });
    }

    /**
     * Clear global search
     */
    clearSearch() {
        this.searchQuery = '';
        this.performSearch();
    }

    /**
     * Clear all column filters
     */
    clearAllFilters() {
        this.columnFilters = {};
        this.performSearch();
    }

    /**
     * Toggle advanced search panel
     */
    toggleAdvancedSearch() {
        this.showAdvancedSearch = !this.showAdvancedSearch;
        console.log('🔍 [SEARCH] Advanced search toggled:', this.showAdvancedSearch);
    }

    /**
     * Export search results to CSV
     * @param {Array} headers - Table headers
     */
    exportSearchResults(headers) {
        if (this.filteredConfigurations.length === 0) {
            if (window.showToast) {
                window.showToast('No results to export', 'warning');
            }
            return;
        }

        try {
            const csvContent = this.generateCSV(this.filteredConfigurations, headers);
            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
            const link = document.createElement('a');
            
            if (link.download !== undefined) {
                const url = URL.createObjectURL(blob);
                link.setAttribute('href', url);
                link.setAttribute('download', `search_results_${new Date().toISOString().split('T')[0]}.csv`);
                link.style.visibility = 'hidden';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                
                if (window.showToast) {
                    window.showToast(`Exported ${this.filteredConfigurations.length} records`, 'success');
                }
            }
        } catch (error) {
            console.error('🔍 [SEARCH] Export failed:', error);
            if (window.showToast) {
                window.showToast('Export failed: ' + error.message, 'error');
            }
        }
    }

    /**
     * Generate CSV content from configurations
     * @param {Array} configurations - Configurations to export
     * @param {Array} headers - Table headers
     * @returns {string} CSV content
     */
    generateCSV(configurations, headers) {
        // Create CSV header row
        const csvHeaders = headers.map(header => `"${header.replace(/"/g, '""')}"`);
        const csvRows = [csvHeaders.join(',')];

        // Create CSV data rows
        configurations.forEach(config => {
            const row = headers.map(header => {
                // The backend creates row data using header names as keys,
                // so we can directly use the header to access the config value
                let value = config[header];
                
                if (value === null || value === undefined) {
                    value = 'N/A';
                } else if (typeof value === 'object') {
                    value = JSON.stringify(value);
                } else {
                    value = String(value);
                }
                
                // Escape quotes and wrap in quotes
                return `"${value.replace(/"/g, '""')}"`;
            });
            csvRows.push(row.join(','));
        });

        return csvRows.join('\n');
    }

    /**
     * Load search state from URL parameters
     */
    loadSearchStateFromURL() {
        const query = this.urlParams.get('search');
        if (query) {
            this.searchQuery = query;
        }

        const filters = this.urlParams.get('filters');
        if (filters) {
            try {
                this.columnFilters = JSON.parse(decodeURIComponent(filters));
            } catch (error) {
                console.warn('🔍 [SEARCH] Failed to parse filters from URL:', error);
                this.columnFilters = {};
            }
        }

        const advanced = this.urlParams.get('advanced');
        if (advanced === 'true') {
            this.showAdvancedSearch = true;
        }
    }

    /**
     * Update URL parameters with current search state
     */
    updateURLParams() {
        const url = new URL(window.location);

        if (this.searchQuery && this.searchQuery.trim()) {
            url.searchParams.set('search', this.searchQuery);
        } else {
            url.searchParams.delete('search');
        }

        if (Object.keys(this.columnFilters).length > 0) {
            const hasActiveFilters = Object.values(this.columnFilters).some(filter => filter && filter.trim());
            if (hasActiveFilters) {
                url.searchParams.set('filters', encodeURIComponent(JSON.stringify(this.columnFilters)));
            } else {
                url.searchParams.delete('filters');
            }
        } else {
            url.searchParams.delete('filters');
        }

        if (this.showAdvancedSearch) {
            url.searchParams.set('advanced', 'true');
        } else {
            url.searchParams.delete('advanced');
        }

        // Update URL without triggering page reload
        window.history.replaceState({}, '', url);
    }

    /**
     * Escape special regex characters
     * @param {string} string - String to escape
     * @returns {string} Escaped string
     */
    escapeRegExp(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    /**
     * Get current search state for external access
     * @returns {Object} Current search state
     */
    getSearchState() {
        return {
            searchQuery: this.searchQuery,
            columnFilters: { ...this.columnFilters },
            showAdvancedSearch: this.showAdvancedSearch,
            searchResults: { ...this.searchResults },
            filteredConfigurations: [...this.filteredConfigurations]
        };
    }

    /**
     * Set search query and perform search
     * @param {string} query - Search query
     */
    setSearchQuery(query) {
        this.searchQuery = query || '';
        this.performSearch();
    }

    /**
     * Set column filter and perform search
     * @param {string} header - Column header
     * @param {string} value - Filter value
     */
    setColumnFilter(header, value) {
        if (value && value.trim()) {
            this.columnFilters[header] = value;
        } else {
            delete this.columnFilters[header];
        }
        this.performSearch();
    }

    /**
     * Check if search is active
     * @returns {boolean} True if any search/filter is active
     */
    isSearchActive() {
        return (this.searchQuery && this.searchQuery.trim()) || 
               Object.values(this.columnFilters).some(filter => filter && filter.trim());
    }

    /**
     * Get search statistics
     * @returns {Object} Search statistics
     */
    getSearchStats() {
        return {
            totalRecords: this.searchResults.total,
            filteredRecords: this.searchResults.filtered,
            hiddenRecords: this.searchResults.total - this.searchResults.filtered,
            searchActive: this.isSearchActive(),
            globalSearchActive: !!(this.searchQuery && this.searchQuery.trim()),
            columnFiltersActive: Object.values(this.columnFilters).some(filter => filter && filter.trim()),
            activeFiltersCount: Object.values(this.columnFilters).filter(filter => filter && filter.trim()).length
        };
    }
}

// Export for use in other modules
if (typeof window !== 'undefined') {
    window.SearchEngine = SearchEngine;
}