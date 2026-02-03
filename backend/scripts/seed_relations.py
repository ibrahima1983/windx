#!/usr/bin/env python
"""Seed Relations data for testing cascading dropdowns.

DEPRECATED: This script is deprecated in favor of the new scope-based architecture.
The profile seeding functionality has been moved to:
backend/scripts/product_definition/setup_profile.py

New Usage:
    python -m backend.scripts.product_definition.setup_profile

Legacy Usage (still supported):
    .venv\scripts\python scripts/seed_relations.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.scripts.product_definition.setup_profile import ProfileSetup


async def seed_relations():
    """Seed relations data for testing - delegates to new architecture."""
    print("⚠️  DEPRECATION WARNING:")
    print("   This script is deprecated. Please use:")
    print("   python -m backend.scripts.product_definition.setup_profile")
    print()
    print("🔄 Delegating to new profile setup...")
    print()
    
    setup = ProfileSetup()
    await setup.run_setup()


if __name__ == "__main__":
    asyncio.run(seed_relations())
