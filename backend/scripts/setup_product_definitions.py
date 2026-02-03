#!/usr/bin/env python3
"""Setup script for creating product definition scopes.

DEPRECATED: This script is deprecated in favor of the new scope-based architecture.
Please use the scripts in backend/scripts/product_definition/ instead.

New Usage:
    python -m backend.scripts.product_definition.setup_all_scopes     # Setup all scopes
    python -m backend.scripts.product_definition.setup_profile        # Setup profile only
    python -m backend.scripts.product_definition.setup_glazing        # Setup glazing only

Legacy Usage (still supported):
    python setup_product_definitions.py                    # Setup all scopes
    python setup_product_definitions.py profile            # Setup profile scope only
    python setup_product_definitions.py glazing            # Setup glazing scope only
"""

import asyncio
import sys
from pathlib import Path

# Fix Windows CMD encoding issues
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import new scope-based setup
from backend.scripts.product_definition.setup_all_scopes import AllScopesSetup


async def main():
    """Main setup function - delegates to new scope-based architecture."""
    print("⚠️  DEPRECATION WARNING:")
    print("   This script is deprecated. Please use the new scope-based scripts:")
    print("   - backend/scripts/product_definition/setup_all_scopes.py")
    print("   - backend/scripts/product_definition/setup_profile.py")
    print("   - backend/scripts/product_definition/setup_glazing.py")
    print()
    print("🔄 Delegating to new architecture...")
    print()
    
    setup_manager = AllScopesSetup()
    
    if len(sys.argv) > 1:
        # Setup specific scope
        scope = sys.argv[1].lower()
        success = await setup_manager.setup_specific_scope(scope)
        if not success:
            sys.exit(1)
    else:
        # Setup all scopes
        await setup_manager.setup_all_scopes()


if __name__ == "__main__":
    asyncio.run(main())