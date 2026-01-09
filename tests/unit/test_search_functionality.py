"""
Unit tests for search and filter functionality
Tests the SearchEngine JavaScript functionality through basic validation
"""

import pytest
import json
from pathlib import Path


class TestSearchFunctionality:
    """Test search and filter functionality implementation"""

    def test_search_engine_file_exists(self):
        """Test that SearchEngine.js file exists"""
        search_engine_path = Path("app/static/js/_profile/SearchEngine.js")
        assert search_engine_path.exists(), "SearchEngine.js file should exist"

    def test_search_engine_has_required_methods(self):
        """Test that SearchEngine.js contains required methods"""
        search_engine_path = Path("app/static/js/_profile/SearchEngine.js")
        content = search_engine_path.read_text(encoding="utf-8")

        required_methods = [
            "initialize",
            "performSearch",
            "applyGlobalSearch",
            "applyColumnFilters",
            "highlightSearchTerm",
            "clearSearch",
            "clearAllFilters",
            "toggleAdvancedSearch",
            "exportSearchResults",
            "updateURLParams",
            "loadSearchStateFromURL",
        ]

        for method in required_methods:
            assert method in content, f"SearchEngine should have {method} method"

    def test_template_has_search_controls(self):
        """Test that template includes search controls"""
        template_path = Path("app/templates/admin/entry/profile.html.jinja")
        content = template_path.read_text(encoding="utf-8")

        # Check for search input
        assert 'placeholder="Search across all columns..."' in content

        # Check for advanced search toggle
        assert "toggleAdvancedSearch()" in content

        # Check for export functionality
        assert "exportSearchResults()" in content

        # Check for clear search functionality
        assert "clearSearch()" in content

        # Check for column filters
        assert "Column-Specific Filters" in content

    def test_css_has_search_styles(self):
        """Test that CSS includes search-related styles"""
        css_path = Path("app/static/css/profile-entry.css")
        content = css_path.read_text()

        required_styles = [
            ".search-highlight",
            ".search-term-highlight",
            ".advanced-search-panel",
            ".search-input",
            ".column-filter",
            ".no-results-state",
        ]

        for style in required_styles:
            assert style in content, f"CSS should include {style} style"

    def test_profile_entry_has_search_integration(self):
        """Test that profile-entry.js integrates search functionality"""
        profile_entry_path = Path("app/static/js/profile-entry.js")
        content = profile_entry_path.read_text(encoding="utf-8")

        # Check for SearchEngine initialization
        assert "searchEngine: new SearchEngine()" in content

        # Check for search-related properties
        search_properties = [
            "searchQuery",
            "columnFilters",
            "showAdvancedSearch",
            "searchResults",
            "filteredConfigurations",
        ]

        for prop in search_properties:
            assert prop in content, f"Profile entry should have {prop} property"

        # Check for search methods
        search_methods = [
            "performSearch",
            "clearSearch",
            "toggleAdvancedSearch",
            "clearAllFilters",
            "highlightSearchTerm",
            "exportSearchResults",
        ]

        for method in search_methods:
            assert method in content, f"Profile entry should have {method} method"

    def test_template_uses_filtered_configurations(self):
        """Test that template uses filteredConfigurations instead of savedConfigurations"""
        template_path = Path("app/templates/admin/entry/profile.html.jinja")
        content = template_path.read_text(encoding="utf-8")

        # Check that table iterates over filteredConfigurations
        assert 'x-for="row in filteredConfigurations"' in content

        # Check for no results state
        assert "filteredConfigurations.length === 0" in content

        # Check for search highlighting
        assert "highlightSearchTerm" in content

    def test_search_engine_script_loaded(self):
        """Test that SearchEngine script is loaded in template"""
        template_path = Path("app/templates/admin/entry/profile.html.jinja")
        content = template_path.read_text(encoding="utf-8")

        assert "SearchEngine.js" in content, "Template should load SearchEngine.js"

    def test_search_functionality_requirements_coverage(self):
        """Test that implementation covers all task requirements"""
        template_path = Path("app/templates/admin/entry/profile.html.jinja")
        template_content = template_path.read_text(encoding="utf-8")

        search_engine_path = Path("app/static/js/_profile/SearchEngine.js")
        search_content = search_engine_path.read_text(encoding="utf-8")

        # Requirement 4.1: Real-time search across all columns
        assert "performSearch()" in template_content
        assert "applyGlobalSearch" in search_content

        # Requirement 4.2: Column-specific filtering
        assert "Column-Specific Filters" in template_content
        assert "applyColumnFilters" in search_content

        # Requirement 4.3: Search adapts to dynamic schema changes
        assert "previewHeaders" in template_content
        assert "FormHelpers.getHeaderMapping()" in search_content

        # Requirement 4.4: "No results" messaging
        assert "No results found" in template_content

        # Requirement 4.5: Works with any number of columns
        assert "headers.map" in search_content  # Dynamic header handling

        # URL parameter support
        assert "URLSearchParams" in search_content
        assert "updateURLParams" in search_content

        # Search highlighting
        assert "highlightSearchTerm" in search_content

        # Check CSS has search highlighting styles
        css_path = Path("app/static/css/profile-entry.css")
        css_content = css_path.read_text(encoding="utf-8")
        assert "search-term-highlight" in css_content

    def test_search_state_persistence(self):
        """Test that search state persistence is implemented"""
        search_engine_path = Path("app/static/js/_profile/SearchEngine.js")
        content = search_engine_path.read_text(encoding="utf-8")

        # Check for URL parameter handling
        assert "URLSearchParams" in content
        assert "loadSearchStateFromURL" in content
        assert "updateURLParams" in content

        # Check for state management
        assert "getSearchState" in content
        assert "setSearchQuery" in content
        assert "setColumnFilter" in content

    def test_export_functionality(self):
        """Test that export functionality is implemented"""
        search_engine_path = Path("app/static/js/_profile/SearchEngine.js")
        content = search_engine_path.read_text(encoding="utf-8")

        # Check for export methods
        assert "exportSearchResults" in content
        assert "generateCSV" in content

        # Check for CSV generation
        assert "text/csv" in content
        assert "createObjectURL" in content

    def test_search_performance_considerations(self):
        """Test that search implementation considers performance"""
        search_engine_path = Path("app/static/js/_profile/SearchEngine.js")
        content = search_engine_path.read_text(encoding="utf-8")

        # Check for efficient search implementation
        assert "filter(" in content  # Uses array filter for efficiency
        assert "toLowerCase()" in content  # Case-insensitive search

        # Check for search term splitting for better matching
        assert "split(" in content

    def test_accessibility_considerations(self):
        """Test that search implementation considers accessibility"""
        template_path = Path("app/templates/admin/entry/profile.html.jinja")
        content = template_path.read_text(encoding="utf-8")

        # Check for proper labels
        assert "placeholder=" in content

        # Check for keyboard navigation support
        assert "@keydown.escape" in content
        assert "@keydown.enter" in content

    def test_responsive_design_support(self):
        """Test that search functionality supports responsive design"""
        css_path = Path("app/static/css/profile-entry.css")
        content = css_path.read_text()

        # Check for responsive breakpoints
        assert "@media (max-width: 768px)" in content
        assert "@media (max-width: 1024px)" in content

        # Check for mobile-friendly search controls
        assert "search-controls" in content or "search-input" in content
