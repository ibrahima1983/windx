"""Test configuration loading."""

import os
import sys
from pathlib import Path

# Get project root and change to it
project_root = Path(__file__).parent.parent.parent
os.chdir(project_root)
sys.path.insert(0, str(project_root))

# Print current directory
print(f"Current directory: {os.getcwd()}")
print(f"Script location: {Path(__file__).parent}")
print(f"Project root: {project_root}")

# Check if .env exists
env_path = Path(".env")
print(f"\n.env exists: {env_path.exists()}")
if env_path.exists():
    print(f".env path: {env_path.absolute()}")
    print("\n.env contents:")
    print(env_path.read_text()[:500])

# Try to load settings
print("\n" + "=" * 50)
print("Attempting to load settings...")
print("=" * 50)

try:
    from app.core.config import get_settings

    settings = get_settings()
    print("✓ Settings loaded successfully!")
    print(f"\nApp Name: {settings.app_name}")
    print(f"Debug: {settings.debug}")
    print(f"Database Provider: {settings.database.provider}")
    print(f"Database Host: {settings.database.host}")
    print(f"Database User: {settings.database.user}")
    print(f"Database Name: {settings.database.name}")
except Exception as e:
    print(f"✗ Failed to load settings: {e}")
    import traceback

    traceback.print_exc()
