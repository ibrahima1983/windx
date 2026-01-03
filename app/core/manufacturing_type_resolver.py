"""Manufacturing Type Configuration and Resolution.

This module provides a robust, production-ready way to resolve manufacturing types
without hardcoding database IDs. It uses stable identifiers (names) and provides
fallback mechanisms for different environments.
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.manufacturing_type import ManufacturingType


class ManufacturingTypeResolver:
    """Resolves manufacturing types by stable identifiers instead of hardcoded IDs.
    
    This class provides a production-safe way to reference manufacturing types
    that works across different environments and database states.
    """
    
    # Stable identifiers for known manufacturing types
    WINDOW_PROFILE_ENTRY = "Window Profile Entry"
    CASEMENT_WINDOW = "Casement Window"
    SLIDING_DOOR = "Sliding Door"
    
    # Page type constants
    PAGE_TYPE_PROFILE = "profile"
    PAGE_TYPE_ACCESSORIES = "accessories"
    PAGE_TYPE_GLAZING = "glazing"
    
    # Valid page types
    VALID_PAGE_TYPES = {PAGE_TYPE_PROFILE, PAGE_TYPE_ACCESSORIES, PAGE_TYPE_GLAZING}
    
    # Cache for resolved IDs (per-session)
    _cache: dict[str, int] = {}
    
    @classmethod
    async def get_by_name(
        cls,
        db: AsyncSession,
        name: str,
        *,
        create_if_missing: bool = False,
    ) -> Optional[ManufacturingType]:
        """Get manufacturing type by name.
        
        Args:
            db: Database session
            name: Manufacturing type name (stable identifier)
            create_if_missing: If True, create the type if it doesn't exist
            
        Returns:
            ManufacturingType or None if not found
        """
        stmt = select(ManufacturingType).where(
            ManufacturingType.name == name,
            ManufacturingType.is_active == True,
        )
        result = await db.execute(stmt)
        mfg_type = result.scalar_one_or_none()
        
        if mfg_type:
            # Cache the ID for this session
            cls._cache[name] = mfg_type.id
            return mfg_type
            
        if create_if_missing:
            # This should only be used in development/setup
            # Production should have types pre-created
            raise NotImplementedError(
                f"Manufacturing type '{name}' not found. "
                "Run setup script to create it."
            )
            
        return None
    
    @classmethod
    async def get_id_by_name(
        cls,
        db: AsyncSession,
        name: str,
    ) -> Optional[int]:
        """Get manufacturing type ID by name.
        
        Args:
            db: Database session
            name: Manufacturing type name
            
        Returns:
            Manufacturing type ID or None if not found
        """
        # Check cache first
        if name in cls._cache:
            return cls._cache[name]
            
        mfg_type = await cls.get_by_name(db, name)
        return mfg_type.id if mfg_type else None
    
    @classmethod
    async def get_default_for_page_type(
        cls,
        db: AsyncSession,
        page_type: str,
        manufacturing_category: str = "window",
    ) -> Optional[ManufacturingType]:
        """Get the default manufacturing type for a specific page type.
        
        This method provides a fallback chain based on page type and category:
        1. Try specific page type + category combination
        2. Try first active type matching category
        3. Try any active manufacturing type
        
        Args:
            db: Database session
            page_type: Page type (profile, accessories, glazing)
            manufacturing_category: Category (window, door, etc.)
            
        Returns:
            ManufacturingType or None if no types exist
        """
        # Validate page type
        if page_type not in cls.VALID_PAGE_TYPES:
            raise ValueError(f"Invalid page_type '{page_type}'. Must be one of: {cls.VALID_PAGE_TYPES}")
        
        # For profile pages, use the existing logic
        if page_type == cls.PAGE_TYPE_PROFILE:
            return await cls.get_default_profile_entry_type(db)
        
        # For accessories and glazing, try to find appropriate manufacturing type
        # First try category-specific types
        stmt = select(ManufacturingType).where(
            ManufacturingType.base_category == manufacturing_category,
            ManufacturingType.is_active == True,
        ).limit(1)
        result = await db.execute(stmt)
        mfg_type = result.scalar_one_or_none()
        if mfg_type:
            return mfg_type
        
        # Fallback: Any active type
        stmt = select(ManufacturingType).where(
            ManufacturingType.is_active == True
        ).limit(1)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    @classmethod
    async def get_default_profile_entry_type(
        cls,
        db: AsyncSession,
    ) -> Optional[ManufacturingType]:
        """Get the default manufacturing type for profile entry.
        
        This method provides a robust fallback chain:
        1. Try "Window Profile Entry" (primary - has rich CSV structure)
        2. Try first active window type
        3. Try any active manufacturing type
        4. If none exist, log warning about setup
        
        Args:
            db: Database session
            
        Returns:
            ManufacturingType or None if no types exist
        """
        # Try primary profile entry type (has the rich 29-field CSV structure)
        mfg_type = await cls.get_by_name(db, cls.WINDOW_PROFILE_ENTRY)
        if mfg_type:
            return mfg_type
        
        # Log warning if primary type is missing
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            f"Primary manufacturing type '{cls.WINDOW_PROFILE_ENTRY}' not found. "
            "This type contains the rich profile structure with 29 CSV fields. "
            "Run 'python scripts/setup_profile_hierarchy.py' to create it."
        )
        
        # Fallback: Try any window type
        stmt = select(ManufacturingType).where(
            ManufacturingType.base_category == "window",
            ManufacturingType.is_active == True,
        ).limit(1)
        result = await db.execute(stmt)
        mfg_type = result.scalar_one_or_none()
        if mfg_type:
            logger.warning(
                f"Using fallback manufacturing type '{mfg_type.name}' (ID: {mfg_type.id}). "
                "This may not have the full profile structure. "
                "Consider running the profile hierarchy setup script."
            )
            return mfg_type
        
        # Last resort: Any active type
        stmt = select(ManufacturingType).where(
            ManufacturingType.is_active == True
        ).limit(1)
        result = await db.execute(stmt)
        fallback_type = result.scalar_one_or_none()
        
        if fallback_type:
            logger.warning(
                f"Using last resort manufacturing type '{fallback_type.name}' (ID: {fallback_type.id}). "
                "This likely does not have the profile structure. "
                "Run 'python manage.py setup_fresh_db' to set up the system properly."
            )
        else:
            logger.error(
                "No manufacturing types found in database! "
                "Run 'python manage.py setup_fresh_db' to initialize the system."
            )
        
        return fallback_type
    
    @classmethod
    def validate_page_type(cls, page_type: str | None) -> bool:
        """Validate if page_type is valid.
        
        Args:
            page_type: Page type to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if page_type is None:
            return False
        return page_type in cls.VALID_PAGE_TYPES
    
    @classmethod
    async def verify_profile_setup(
        cls,
        db: AsyncSession,
    ) -> dict[str, any]:
        """Verify that the profile system is properly set up.
        
        Args:
            db: Database session
            
        Returns:
            dict: Verification results with status and details
        """
        from app.models.attribute_node import AttributeNode
        
        results = {
            "status": "ok",
            "warnings": [],
            "errors": [],
            "manufacturing_type": None,
            "attribute_count": 0,
            "has_rich_structure": False,
        }
        
        # Check if Window Profile Entry exists
        mfg_type = await cls.get_by_name(db, cls.WINDOW_PROFILE_ENTRY)
        if not mfg_type:
            results["status"] = "error"
            results["errors"].append(
                f"Primary manufacturing type '{cls.WINDOW_PROFILE_ENTRY}' not found. "
                "Run 'python scripts/setup_profile_hierarchy.py' to create it."
            )
            return results
        
        results["manufacturing_type"] = {
            "id": mfg_type.id,
            "name": mfg_type.name,
            "base_category": mfg_type.base_category,
        }
        
        # Check attribute nodes count and structure
        stmt = select(AttributeNode).where(
            AttributeNode.manufacturing_type_id == mfg_type.id,
            AttributeNode.page_type == "profile"
        )
        result = await db.execute(stmt)
        attribute_nodes = result.scalars().all()
        
        results["attribute_count"] = len(attribute_nodes)
        
        # Check for meaningful structure (schema-driven approach)
        # Instead of hardcoding fields, check for structural indicators
        actual_fields = {node.name for node in attribute_nodes}
        
        # Check for minimum viable structure (essential for any profile system)
        critical_indicators = {
            "has_basic_info": any(field in actual_fields for field in ["name", "title", "product_name"]),
            "has_type_info": any(field in actual_fields for field in ["type", "category", "product_type"]),
            "has_material_info": any(field in actual_fields for field in ["material", "materials"]),
            "has_dimensions": any(field in actual_fields for field in ["width", "height", "length", "size"]),
            "has_pricing": any(field in actual_fields for field in ["price", "cost", "price_per_meter", "price_per_unit"]),
        }
        
        missing_critical = [key for key, present in critical_indicators.items() if not present]
        
        if missing_critical:
            results["status"] = "error"
            results["errors"].append(
                f"Missing critical profile capabilities: {', '.join(missing_critical)}. "
                "Profile page may not work correctly. Consider running setup scripts."
            )
        
        # Determine if we have a rich structure based on attribute count and diversity
        # A rich structure should have multiple sections and various field types
        sections = set()
        field_types = set()
        ui_components = set()
        
        for node in attribute_nodes:
            # Extract section from ltree_path (first part)
            if node.ltree_path and "." in node.ltree_path:
                sections.add(node.ltree_path.split(".")[0])
            
            if node.data_type:
                field_types.add(node.data_type)
            
            if node.ui_component:
                ui_components.add(node.ui_component)
        
        # Rich structure indicators
        rich_indicators = {
            "multiple_sections": len(sections) >= 3,  # At least 3 logical sections
            "diverse_field_types": len(field_types) >= 3,  # At least 3 different data types
            "varied_ui_components": len(ui_components) >= 3,  # At least 3 different UI components
            "sufficient_fields": len(attribute_nodes) >= 10,  # At least 10 fields for meaningful configuration
        }
        
        rich_score = sum(rich_indicators.values())
        results["has_rich_structure"] = rich_score >= 3  # At least 3 out of 4 indicators
        
        results["structure_details"] = {
            "sections": len(sections),
            "field_types": len(field_types),
            "ui_components": len(ui_components),
            "rich_score": f"{rich_score}/4",
            "section_names": sorted(sections) if sections else [],
        }
        
        # Provide helpful feedback without being prescriptive
        if not results["has_rich_structure"] and results["status"] == "ok":
            results["status"] = "warning"
            if len(attribute_nodes) < 10:
                results["warnings"].append(
                    f"Profile has only {len(attribute_nodes)} fields. "
                    "Consider adding more attributes for richer product configuration."
                )
            if len(sections) < 3:
                results["warnings"].append(
                    f"Profile has only {len(sections)} logical sections. "
                    "Consider organizing attributes into more sections (e.g., basic info, dimensions, pricing)."
                )
        
        return results
    
    @classmethod
    def clear_cache(cls):
        """Clear the ID cache. Useful for testing or after database changes."""
        cls._cache.clear()
