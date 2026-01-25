/**
 * Search Engine - Composable for search and filter functionality
 * 
 * Provides real-time search across table data with column-specific filtering
 * 
 * Note: This is converted to a Vue composable pattern instead of a class.
 * URL parameter handling should be done via Vue Router instead.
 */

import { ref, computed } from 'vue'

export interface SearchResults {
    total: number
    filtered: number
}

export interface ColumnFilters {
    [header: string]: string
}

export function useSearch<T extends Record<string, any>>() {
    const searchQuery = ref('')
    const columnFilters = ref<ColumnFilters>({})
    const showAdvancedSearch = ref(false)
    const originalConfigurations = ref<T[]>([]) as unknown as any

    const searchResults = computed<SearchResults>(() => ({
        total: originalConfigurations.value.length,
        filtered: filteredConfigurations.value.length
    }))

    const filteredConfigurations = computed<T[]>(() => {
        let filtered = [...originalConfigurations.value]

        // Apply global search query
        if (searchQuery.value && searchQuery.value.trim()) {
            filtered = applyGlobalSearch(filtered, searchQuery.value.trim())
        }

        // Apply column-specific filters
        if (Object.keys(columnFilters.value).length > 0) {
            filtered = applyColumnFilters(filtered)
        }

        return filtered
    })

    function applyGlobalSearch(configurations: T[], query: string): T[] {
        const searchTerms = query.toLowerCase().split(/\s+/).filter(term => term.length > 0)

        return configurations.filter(config => {
            // Search across all fields in the configuration
            const searchableText = Object.values(config)
                .map(value => {
                    if (value === null || value === undefined) return ''
                    return String(value).toLowerCase()
                })
                .join(' ')

            // Check if all search terms are found
            return searchTerms.every((term: string) => searchableText.includes(term))
        })
    }

    function applyColumnFilters(configurations: T[]): T[] {
        return configurations.filter(config => {
            return Object.entries(columnFilters.value).every(([header, filterValue]) => {
                if (typeof filterValue !== 'string' || !filterValue.trim()) return true

                const configValue = config[header]
                if (configValue === null || configValue === undefined) return false

                const configText = String(configValue).toLowerCase()
                const filterText = filterValue.toLowerCase().trim()

                return configText.includes(filterText)
            })
        })
    }

    function isRowHighlighted(row: T): boolean {
        if (!searchQuery.value && Object.keys(columnFilters.value).length === 0) {
            return false
        }

        // Check if any field contains search terms
        const searchableText = Object.values(row)
            .map(value => {
                if (value === null || value === undefined) return ''
                return String(value).toLowerCase()
            })
            .join(' ')

        // Check global search
        if (searchQuery.value && searchQuery.value.trim()) {
            const searchTerms = searchQuery.value.toLowerCase().split(/\s+/).filter(term => term.length > 0)
            if (searchTerms.some((term: string) => searchableText.includes(term))) {
                return true
            }
        }

        // Check column filters
        return Object.entries(columnFilters.value).some(([header, filterValue]) => {
            if (typeof filterValue !== 'string' || !filterValue.trim()) return false

            const configValue = row[header]
            if (configValue === null || configValue === undefined) return false

            const configText = String(configValue).toLowerCase()
            const filterText = filterValue.toLowerCase().trim()

            return configText.includes(filterText)
        })
    }

    function clearSearch() {
        searchQuery.value = ''
    }

    function clearAllFilters() {
        columnFilters.value = {}
    }

    function toggleAdvancedSearch() {
        showAdvancedSearch.value = !showAdvancedSearch.value
    }

    function setSearchQuery(query: string) {
        searchQuery.value = query || ''
    }

    function setColumnFilter(header: string, value: string) {
        if (value && value.trim()) {
            columnFilters.value[header] = value
        } else {
            delete columnFilters.value[header]
        }
    }

    function isSearchActive(): boolean {
        // Check global search
        if (searchQuery.value && searchQuery.value.trim()) return true

        // Check column filters
        return Object.values(columnFilters.value).some((filter: string) => filter && filter.trim())
    }

    function getSearchStats() {
        // Count active filters safely
        const activeFiltersCount = Object.values(columnFilters.value).filter((filter: string) => filter && filter.trim()).length

        return {
            totalRecords: searchResults.value.total,
            filteredRecords: searchResults.value.filtered,
            hiddenRecords: searchResults.value.total - searchResults.value.filtered,
            searchActive: isSearchActive(),
            globalSearchActive: !!(searchQuery.value && searchQuery.value.trim()),
            columnFiltersActive: activeFiltersCount > 0,
            activeFiltersCount
        }
    }

    function exportSearchResults(headers: string[]) {
        if (filteredConfigurations.value.length === 0) {
            console.warn('No results to export')
            return
        }

        try {
            const csvContent = generateCSV(filteredConfigurations.value, headers)
            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
            const link = document.createElement('a')

            const url = URL.createObjectURL(blob)
            link.setAttribute('href', url)
            link.setAttribute('download', `search_results_${new Date().toISOString().split('T')[0]}.csv`)
            link.style.visibility = 'hidden'
            document.body.appendChild(link)
            link.click()
            document.body.removeChild(link)

            console.log(`Exported ${filteredConfigurations.value.length} records`)
        } catch (error) {
            console.error('Export failed:', error)
        }
    }

    function generateCSV(configurations: T[], headers: string[]): string {
        // Create CSV header row
        const csvHeaders = headers.map(header => `"${header.replace(/"/g, '""')}"`)
        const csvRows = [csvHeaders.join(',')]

        // Create CSV data rows
        configurations.forEach(config => {
            const row = headers.map(header => {
                let value = config[header]

                if (value === null || value === undefined) {
                    value = 'N/A'
                } else if (typeof value === 'object') {
                    value = JSON.stringify(value)
                } else {
                    value = String(value)
                }

                // Escape quotes and wrap in quotes
                return `"${value.replace(/"/g, '""')}"`
            })
            csvRows.push(row.join(','))
        })

        return csvRows.join('\n')
    }

    function initialize(configurations: T[]) {
        originalConfigurations.value = configurations || []
    }

    function updateConfigurations(configurations: T[]) {
        originalConfigurations.value = configurations || []
    }

    return {
        // State
        searchQuery,
        columnFilters,
        showAdvancedSearch,
        searchResults,
        filteredConfigurations,

        // Methods
        initialize,
        updateConfigurations,
        clearSearch,
        clearAllFilters,
        toggleAdvancedSearch,
        setSearchQuery,
        setColumnFilter,
        isSearchActive,
        isRowHighlighted,
        getSearchStats,
        exportSearchResults
    }
}
