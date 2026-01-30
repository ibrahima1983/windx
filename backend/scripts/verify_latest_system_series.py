"""
Script to verify the metadata of the most recently created System Series entity.
Use this to check if the Frontend fix is correctly saving metadata.
"""

import asyncio
import sys
from pathlib import Path
from sqlalchemy import select, desc

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import get_db
from app.models.attribute_node import AttributeNode

async def check_latest_series():
    print("Checking latest System Series entity...")
    
    async for session in get_db():
        # Get the most recently created system_series
        result = await session.execute(
            select(AttributeNode)
            .where(AttributeNode.node_type == "system_series")
            .order_by(desc(AttributeNode.created_at)) # Assuming created_at exists, or use ID desc
            .limit(1)
        )
        series: AttributeNode | None = result.scalar_one_or_none()
        
        if not series:
            print("No System Series found in database.")
            return

        print(f"\nLast Created Series: '{series.name}' (ID: {series.id})")
        print("-" * 50)
        
        metadata = series.metadata_ or {}
        print("Metadata Content:")
        for k, v in metadata.items():
            print(f"  {k}: {v}")
            
        print("-" * 50)
        
        # Verify specific fields
        missing = []
        if 'opening_system_id' not in metadata: missing.append('opening_system_id')
        if 'linked_company_material' not in metadata: missing.append('linked_company_material')
        if 'linked_material_id' not in metadata: missing.append('linked_material_id')
        
        if missing:
            print(f"❌ FAIL: Missing critical dependency metadata: {', '.join(missing)}")
        else:
            print("✅ SUCCES: All dependency metadata fields are present!")
            print(f"   Opening System: {metadata['opening_system_id']}")
            print(f"   Company: {metadata['linked_company_material']}")
            print(f"   Material: {metadata['linked_material_id']}")
            
        break

if __name__ == "__main__":
    asyncio.run(check_latest_series())
