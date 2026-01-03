#!/usr/bin/env python3
"""Production Entry System Setup Script.

This script ensures that entry pages have the necessary data to function
in production by creating manufacturing types and attribute nodes.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import get_settings
from app.database.connection import get_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy import select, text
from app.models.manufacturing_type import ManufacturingType
from app.models.attribute_node import AttributeNode


async def check_entry_system_readiness():
    """Check if entry system has necessary data for production."""
    print("=== Entry System Production Readiness Check ===\n")
    
    settings = get_settings()
    engine = get_engine()
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    issues_found = []
    
    async with session_maker() as session:
        try:
            # Check 1: Manufacturing Types
            print("1. Checking Manufacturing Types...")
            result = await session.execute(select(ManufacturingType))
            mfg_types = result.scalars().all()
            
            if not mfg_types:
                issues_found.append("No manufacturing types found")
                print("   Error: No manufacturing types found")
            else:
                print(f"   OK: Found {len(mfg_types)} manufacturing types:")
                for mfg in mfg_types:
                    print(f"      - {mfg.name} (ID: {mfg.id})")
            
            # Check 2: Attribute Nodes for Entry Pages
            print("\n2. Checking Attribute Nodes for Entry Pages...")
            
            page_types = ["profile", "accessories", "glazing"]
            for page_type in page_types:
                result = await session.execute(
                    select(AttributeNode).where(AttributeNode.page_type == page_type)
                )
                nodes = result.scalars().all()
                
                if not nodes:
                    issues_found.append(f"No attribute nodes found for page_type '{page_type}'")
                    print(f"   Error: No attribute nodes for '{page_type}' page")
                else:
                    print(f"   OK: Found {len(nodes)} attribute nodes for '{page_type}' page")
            
            # Check 3: LTREE Extension
            print("\n3. Checking LTREE Extension...")
            result = await session.execute(
                text("SELECT 1 FROM pg_extension WHERE extname = 'ltree'")
            )
            if result.scalar():
                print("   OK: LTREE extension is installed")
            else:
                issues_found.append("LTREE extension not installed")
                print("   Error: LTREE extension not installed")
            
            # Check 4: Entry Page Functionality
            print("\n4. Checking Entry Page Data Structure...")
            if mfg_types:
                # Test with first manufacturing type
                mfg_type = mfg_types[0]
                result = await session.execute(
                    select(AttributeNode).where(
                        AttributeNode.manufacturing_type_id == mfg_type.id,
                        AttributeNode.page_type == "profile"
                    )
                )
                profile_nodes = result.scalars().all()
                
                if not profile_nodes:
                    issues_found.append(f"Manufacturing type '{mfg_type.name}' has no profile page attributes")
                    print(f"   Error: Manufacturing type '{mfg_type.name}' has no profile page attributes")
                else:
                    print(f"   OK: Manufacturing type '{mfg_type.name}' has {len(profile_nodes)} profile attributes")
            
        except Exception as e:
            issues_found.append(f"Database error: {e}")
            print(f"   Error: Database error: {e}")
        finally:
            await session.close()
    
    await engine.dispose()
    
    # Summary
    print("\n" + "=" * 60)
    if not issues_found:
        print("SUCCESS: ENTRY SYSTEM IS PRODUCTION READY!")
        print("\nEntry pages should work correctly with existing data.")
        return True
    else:
        print("WARNING: ENTRY SYSTEM NEEDS SETUP!")
        print("\nIssues found:")
        for issue in issues_found:
            print(f"   • {issue}")
        
        print("\nRecommended Actions:")
        print("1. Create manufacturing types and attribute nodes:")
        print("   python manage.py create_factory_mfg --depth 3 --leaves 4")
        print("\n2. Or create custom manufacturing types manually via admin panel")
        print("\n3. Verify setup:")
        print("   python production_entry_setup.py")
        
        return False


async def create_minimal_entry_data():
    """Create minimal data needed for entry pages to work."""
    print("=== Creating Minimal Entry Data ===\n")
    
    engine = get_engine()
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with session_maker() as session:
        try:
            # Create a basic manufacturing type
            print("Creating basic manufacturing type...")
            
            basic_mfg = ManufacturingType(
                name="Basic Window",
                description="Basic window configuration for entry system",
                base_category="window",
                base_price=200.00,
                base_weight=25.0,
                is_active=True
            )
            session.add(basic_mfg)
            await session.flush()
            
            # Create basic attribute nodes for profile page
            print("Creating basic attribute nodes...")
            
            basic_attributes = [
                {
                    "name": "name",
                    "node_type": "attribute",
                    "data_type": "string",
                    "required": True,
                    "ltree_path": "basic.name",
                    "depth": 1,
                    "sort_order": 1,
                    "ui_component": "text",
                    "description": "Product name"
                },
                {
                    "name": "type",
                    "node_type": "attribute", 
                    "data_type": "string",
                    "required": True,
                    "ltree_path": "basic.type",
                    "depth": 1,
                    "sort_order": 2,
                    "ui_component": "select",
                    "description": "Product type"
                },
                {
                    "name": "width",
                    "node_type": "attribute",
                    "data_type": "number",
                    "required": False,
                    "ltree_path": "dimensions.width",
                    "depth": 1,
                    "sort_order": 3,
                    "ui_component": "number",
                    "description": "Width in mm"
                },
                {
                    "name": "height",
                    "node_type": "attribute",
                    "data_type": "number", 
                    "required": False,
                    "ltree_path": "dimensions.height",
                    "depth": 1,
                    "sort_order": 4,
                    "ui_component": "number",
                    "description": "Height in mm"
                }
            ]
            
            for attr_data in basic_attributes:
                attr_node = AttributeNode(
                    manufacturing_type_id=basic_mfg.id,
                    page_type="profile",  # Default to profile page
                    **attr_data
                )
                session.add(attr_node)
            
            await session.commit()
            
            print("OK: Minimal entry data created successfully!")
            print(f"   Manufacturing Type: {basic_mfg.name} (ID: {basic_mfg.id})")
            print(f"   Attribute Nodes: {len(basic_attributes)} created")
            
        except Exception as e:
            await session.rollback()
            print(f"Error creating minimal entry data: {e}")
            raise
        finally:
            await session.close()
    
    await engine.dispose()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--create-minimal":
        asyncio.run(create_minimal_entry_data())
    else:
        asyncio.run(check_entry_system_readiness())