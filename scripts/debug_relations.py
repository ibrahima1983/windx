#!/usr/bin/env python
"""Debug script to verify Relations data.

Shows all entities and paths in the Relations system.

Usage:
    .venv\scripts\python scripts/debug_relations.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_session_maker
from app.services.relations import RelationsService


async def debug_relations():
    """Debug and display all relations data."""
    print("=" * 70)
    print("🔍 RELATIONS DEBUG - Verifying Seeded Data")
    print("=" * 70)
    
    session_maker = get_session_maker()
    async with session_maker() as db:
        service = RelationsService(db)
        
        # Get all entities
        print("\n📦 ENTITIES BY TYPE:")
        print("-" * 70)
        
        entity_types = ["company", "material", "opening_system", "system_series", "color"]
        
        for entity_type in entity_types:
            entities = await service.get_entities_by_type(entity_type)
            print(f"\n🏷️  {entity_type.upper()} ({len(entities)} total):")
            for ent in entities:
                print(f"   ID: {ent.id:3d} | Name: {ent.name}")
        
        # Get all paths
        print("\n" + "=" * 70)
        print("🔗 DEPENDENCY PATHS:")
        print("-" * 70)
        
        paths = await service.get_all_paths()
        
        if not paths:
            print("\n⚠️  No paths found!")
        else:
            print(f"\nFound {len(paths)} paths:\n")
            for i, path in enumerate(paths, 1):
                print(f"{i}. {path.get('readable', 'N/A')}")
                print(f"   LTREE: {path.get('ltree_path', 'N/A')}")
                print()
        
        # Test cascading options
        print("=" * 70)
        print("🧪 TESTING CASCADING OPTIONS:")
        print("-" * 70)
        
        # Get company options (no parent)
        print("\n1️⃣  Companies (no parent selection):")
        options = await service.get_dependent_options({})
        companies = options.get("company", [])
        for c in companies:
            print(f"   - {c['name']} (ID: {c['id']})")
        
        if companies:
            # Get materials for first company
            company_id = companies[0]["id"]
            company_name = companies[0]["name"]
            print(f"\n2️⃣  Materials for '{company_name}':")
            options = await service.get_dependent_options({"company_id": company_id})
            materials = options.get("material", [])
            for m in materials:
                print(f"   - {m['name']} (ID: {m['id']})")
            
            if materials:
                # Get opening systems for first material
                material_id = materials[0]["id"]
                material_name = materials[0]["name"]
                print(f"\n3️⃣  Opening Systems for '{company_name}' → '{material_name}':")
                options = await service.get_dependent_options({
                    "company_id": company_id,
                    "material_id": material_id,
                })
                opening_systems = options.get("opening_system", [])
                for os in opening_systems:
                    print(f"   - {os['name']} (ID: {os['id']})")
                
                if opening_systems:
                    # Get system series
                    os_id = opening_systems[0]["id"]
                    os_name = opening_systems[0]["name"]
                    print(f"\n4️⃣  System Series for '{company_name}' → '{material_name}' → '{os_name}':")
                    options = await service.get_dependent_options({
                        "company_id": company_id,
                        "material_id": material_id,
                        "opening_system_id": os_id,
                    })
                    series = options.get("system_series", [])
                    for s in series:
                        print(f"   - {s['name']} (ID: {s['id']})")
                    
                    if series:
                        # Get colors
                        series_id = series[0]["id"]
                        series_name = series[0]["name"]
                        print(f"\n5️⃣  Colors for '{company_name}' → '{material_name}' → '{os_name}' → '{series_name}':")
                        options = await service.get_dependent_options({
                            "company_id": company_id,
                            "material_id": material_id,
                            "opening_system_id": os_id,
                            "system_series_id": series_id,
                        })
                        colors = options.get("color", [])
                        for c in colors:
                            print(f"   - {c['name']} (ID: {c['id']})")
        
        print("\n" + "=" * 70)
        print("✅ DEBUG COMPLETE!")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(debug_relations())
