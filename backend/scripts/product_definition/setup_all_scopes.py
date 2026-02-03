"""Setup all product definition scopes.

This script sets up all available product definition scopes in the correct order.
It provides a convenient way to initialize the entire product definition system.
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Tuple

# Fix Windows CMD encoding issues
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from .base import run_async_script
from .setup_profile import ProfileSetup
from .setup_glazing import GlazingSetup


class AllScopesSetup:
    """Setup all product definition scopes."""
    
    def __init__(self):
        # Define scopes in setup order (dependencies first)
        self.scopes = [
            ("profile", ProfileSetup),
            ("glazing", GlazingSetup),
        ]
    
    async def setup_all_scopes(self) -> None:
        """Setup all available scopes."""
        print("=" * 80)
        print("🚀 SETTING UP ALL PRODUCT DEFINITION SCOPES")
        print("=" * 80)
        
        success_count = 0
        total_scopes = len(self.scopes)
        
        for scope_name, setup_class in self.scopes:
            print(f"\n{'='*60}")
            print(f"Setting up {scope_name.title()} scope...")
            print('='*60)
            
            try:
                setup = setup_class()
                await setup.run_setup()
                success_count += 1
                print(f"✅ {scope_name.title()} scope setup completed successfully!")
                
            except Exception as e:
                print(f"❌ Error setting up {scope_name} scope: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"\n{'='*80}")
        print(f"📊 SETUP SUMMARY")
        print('='*80)
        print(f"Successfully set up: {success_count}/{total_scopes} scopes")
        
        if success_count == total_scopes:
            print("🎉 All scopes set up successfully!")
        else:
            print(f"⚠️  {total_scopes - success_count} scopes failed to set up")
            sys.exit(1)
    
    async def setup_specific_scope(self, scope_name: str) -> bool:
        """Setup a specific scope by name."""
        print(f"🚀 Setting up {scope_name.title()} scope...")
        print("=" * 60)
        
        # Find the scope setup class
        setup_class = None
        for name, cls in self.scopes:
            if name == scope_name.lower():
                setup_class = cls
                break
        
        if not setup_class:
            available_scopes = [name for name, _ in self.scopes]
            print(f"❌ Unknown scope: {scope_name}")
            print(f"Available scopes: {', '.join(available_scopes)}")
            return False
        
        try:
            setup = setup_class()
            await setup.run_setup()
            print(f"✅ {scope_name.title()} scope setup completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Error setting up {scope_name} scope: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def list_available_scopes(self) -> None:
        """List all available scopes."""
        print("📋 Available Product Definition Scopes:")
        print("=" * 50)
        
        for scope_name, setup_class in self.scopes:
            setup = setup_class()
            print(f"  • {scope_name.title()}")
            print(f"    Description: {setup.__class__.__doc__.strip() if setup.__class__.__doc__ else 'No description'}")
        
        print(f"\nTotal: {len(self.scopes)} scopes available")


async def main():
    """Main setup function."""
    setup_manager = AllScopesSetup()
    
    if len(sys.argv) == 1:
        # No arguments - setup all scopes
        await setup_manager.setup_all_scopes()
        
    elif sys.argv[1] == "--list":
        # List available scopes
        setup_manager.list_available_scopes()
        
    elif sys.argv[1] == "--help":
        # Show help
        print("Product Definition Scopes Setup")
        print("=" * 40)
        print("Usage:")
        print("  python setup_all_scopes.py                 # Setup all scopes")
        print("  python setup_all_scopes.py <scope_name>    # Setup specific scope")
        print("  python setup_all_scopes.py --list          # List available scopes")
        print("  python setup_all_scopes.py --help          # Show this help")
        print()
        setup_manager.list_available_scopes()
        
    else:
        # Setup specific scope
        scope_name = sys.argv[1].lower()
        success = await setup_manager.setup_specific_scope(scope_name)
        if not success:
            sys.exit(1)


if __name__ == "__main__":
    run_async_script(main())