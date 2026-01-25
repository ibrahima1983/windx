#!/usr/bin/env python
"""Seed Relations data for testing cascading dropdowns.

Creates the following paths:
1. Komben → UPVC → Casement → K700 → White
2. Komben → UPVC → Casement → K600 → Red
3. Komben → Aluminum → Casement → K701 → Green
4. Komben → Aluminum → Sliding → K800 → Blue

Usage:
    .venv\scripts\python scripts/seed_relations.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_session_maker
from app.services.relations import RelationsService


async def seed_relations():
    """Seed relations data for testing."""
    print("=" * 60)
    print("🌱 SEEDING RELATIONS DATA")
    print("=" * 60)
    
    session_maker = get_session_maker()
    async with session_maker() as db:
        service = RelationsService(db)
        
        # Define entities to create
        entities_to_create = {
            "company": ["Komben"],
            "material": ["UPVC", "Aluminum"],
            "opening_system": ["Casement", "Sliding"],
            "system_series": ["K700", "K600", "K701", "K800"],
            "color": ["White", "Red", "Green", "Blue"],
        }
        
        # Store created entity IDs
        entity_ids = {}
        
        # Create entities
        for entity_type, names in entities_to_create.items():
            entity_ids[entity_type] = {}
            print(f"\n📦 Creating {entity_type} entities...")
            
            for name in names:
                try:
                    entity = await service.create_entity(
                        entity_type=entity_type,
                        name=name,
                    )
                    entity_ids[entity_type][name] = entity.id
                    print(f"   ✅ Created: {name} (ID: {entity.id})")
                except ValueError as e:
                    # Entity might already exist, try to find it
                    print(f"   ⚠️  {name}: {e}")
                    existing = await service.get_entities_by_type(entity_type)
                    for ent in existing:
                        if ent.name == name:
                            entity_ids[entity_type][name] = ent.id
                            print(f"   📌 Found existing: {name} (ID: {ent.id})")
                            break
        
        print("\n" + "=" * 60)
        print("🔗 CREATING DEPENDENCY PATHS")
        print("=" * 60)
        
        # Define paths to create
        # Format: (company, material, opening_system, system_series, color)
        paths_to_create = [
            ("Komben", "UPVC", "Casement", "K700", "White"),
            ("Komben", "UPVC", "Casement", "K600", "Red"),
            ("Komben", "Aluminum", "Casement", "K701", "Green"),
            ("Komben", "Aluminum", "Sliding", "K800", "Blue"),
        ]
        
        for path in paths_to_create:
            company, material, opening_system, system_series, color = path
            path_str = f"{company} → {material} → {opening_system} → {system_series} → {color}"
            
            try:
                # Get IDs
                company_id = entity_ids["company"].get(company)
                material_id = entity_ids["material"].get(material)
                opening_system_id = entity_ids["opening_system"].get(opening_system)
                system_series_id = entity_ids["system_series"].get(system_series)
                color_id = entity_ids["color"].get(color)
                
                if not all([company_id, material_id, opening_system_id, system_series_id, color_id]):
                    print(f"\n❌ Missing entity IDs for path: {path_str}")
                    continue
                
                path_node = await service.create_dependency_path(
                    company_id=company_id,
                    material_id=material_id,
                    opening_system_id=opening_system_id,
                    system_series_id=system_series_id,
                    color_id=color_id,
                )
                print(f"\n✅ Created path: {path_str}")
                print(f"   LTREE: {path_node.ltree_path}")
                
            except ValueError as e:
                print(f"\n⚠️  Path exists or error: {path_str}")
                print(f"   {e}")
        
        print("\n" + "=" * 60)
        print("✅ SEEDING COMPLETE!")
        print("=" * 60)
        
        # Print summary
        print("\n📊 SUMMARY:")
        for entity_type, ids in entity_ids.items():
            print(f"   {entity_type}: {list(ids.keys())}")


if __name__ == "__main__":
    asyncio.run(seed_relations())
