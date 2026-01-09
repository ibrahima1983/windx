#!/usr/bin/env python3
"""
Seed script to create sample profile configuration data.

This script creates sample profile configurations using the proper
ManufacturingTypeResolver approach instead of hardcoded IDs.
"""

import asyncio
from decimal import Decimal
from typing import Any

from app.core.config import get_settings
from app.database import get_db
from app.models.manufacturing_type import ManufacturingType
from app.models.user import User
from app.schemas.entry import ProfileEntryData
from app.services.entry import EntryService


async def seed_profile_data():
    """Seed dummy profile data for testing."""
    print("[SEED] Starting profile data seeding...")

    settings = get_settings()
    print(f"[INFO] Database: {settings.database.provider}")

    async for session in get_db():
        try:
            # Use ManufacturingTypeResolver to get the default profile entry type
            from app.core.manufacturing_type_resolver import ManufacturingTypeResolver
            from sqlalchemy import select, text

            manufacturing_type = await ManufacturingTypeResolver.get_default_for_page_type(
                session, "profile", "window"
            )

            if not manufacturing_type:
                print("[ERROR] No manufacturing types found for profile page.")
                print("   Please run the setup script first:")
                print("   .venv\\scripts\\python scripts/setup_profile_hierarchy.py")
                return

            print(
                f"[OK] Found manufacturing type: {manufacturing_type.name} (ID: {manufacturing_type.id})"
            )
            print(f"   Base category: {manufacturing_type.base_category}")
            print(f"   Base price: ${manufacturing_type.base_price}")

            # Get any admin user for the seeding
            result = await session.execute(select(User).where(User.is_superuser == True).limit(1))
            admin_user = result.scalar_one_or_none()

            if not admin_user:
                print("[ERROR] No admin user found. Please create one first.")
                return

            print(f"[OK] Found admin user: {admin_user.email}")

            # Create EntryService
            entry_service = EntryService(session)

            # Sample profile data - simplified and valid
            sample_profiles = [
                # Simple Frame - Basic valid data
                {
                    "manufacturing_type_id": manufacturing_type.id,
                    "name": "Standard Frame",
                    "type": "Frame",
                    "company": "kompen",
                    "material": "UPVC",
                    "opening_system": "Casement",
                    "system_series": "Kom700",
                    "code": "STD-001",
                    "length_of_beam": Decimal("6.0"),
                    "width": Decimal("60.0"),
                    "front_height": Decimal("30.0"),
                    "rear_height": Decimal("30.0"),
                    "glazing_height": Decimal("20.0"),
                    "weight_per_meter": Decimal("2.5"),
                    "colours": "White",
                    "price_per_meter": Decimal("50.0"),
                    "price_per_beam": Decimal("300.0"),  # 50 * 6 = 300
                    "upvc_profile_discount": Decimal("10.0"),
                },
                # Sash Type - Valid sash data
                {
                    "manufacturing_type_id": manufacturing_type.id,
                    "name": "Standard Sash",
                    "type": "sash",
                    "company": "kompen",
                    "material": "UPVC",
                    "opening_system": "Casement",
                    "system_series": "Kom700",
                    "code": "SASH-001",
                    "length_of_beam": Decimal("5.0"),
                    "width": Decimal("55.0"),
                    "front_height": Decimal("25.0"),
                    "rear_height": Decimal("25.0"),
                    "glazing_height": Decimal("18.0"),
                    "sash_overlap": Decimal("8.0"),  # Only for sash types
                    "weight_per_meter": Decimal("2.0"),
                    "colours": "White",
                    "price_per_meter": Decimal("45.0"),
                    "price_per_beam": Decimal("225.0"),  # 45 * 5 = 225
                    "upvc_profile_discount": Decimal("15.0"),
                },
                # Sliding Frame - With flyscreen track
                {
                    "manufacturing_type_id": manufacturing_type.id,
                    "name": "Sliding Frame with Flyscreen",
                    "type": "Frame",
                    "company": "kompen",
                    "material": "UPVC",
                    "opening_system": "sliding",  # This allows flyscreen track
                    "system_series": "Kom800",
                    "code": "SLIDE-001",
                    "length_of_beam": Decimal("6.0"),
                    "width": Decimal("70.0"),
                    "builtin_flyscreen_track": True,  # Valid for sliding frames
                    "total_width": Decimal("105.0"),
                    "flyscreen_track_height": Decimal("35.0"),
                    "front_height": Decimal("45.0"),
                    "glazing_height": Decimal("25.0"),
                    "weight_per_meter": Decimal("3.0"),
                    "colours": "White",
                    "price_per_meter": Decimal("65.0"),
                    "price_per_beam": Decimal("390.0"),  # 65 * 6 = 390
                    "upvc_profile_discount": Decimal("12.0"),
                },
                # Mullion - Simple mullion
                {
                    "manufacturing_type_id": manufacturing_type.id,
                    "name": "Standard Mullion",
                    "type": "Mullion",
                    "company": "kompen",
                    "material": "UPVC",
                    "opening_system": "Casement",
                    "system_series": "Kom700",
                    "code": "MUL-001",
                    "length_of_beam": Decimal("6.0"),
                    "width": Decimal("60.0"),
                    "front_height": Decimal("40.0"),
                    "rear_height": Decimal("80.0"),  # Different heights for mullion
                    "glazing_height": Decimal("20.0"),
                    "weight_per_meter": Decimal("1.5"),
                    "colours": "White",
                    "price_per_meter": Decimal("35.0"),
                    "price_per_beam": Decimal("210.0"),  # 35 * 6 = 210
                    "upvc_profile_discount": Decimal("20.0"),
                },
                # Glazing Bead - Simple glazing bead
                {
                    "manufacturing_type_id": manufacturing_type.id,
                    "name": "Standard Glazing Bead",
                    "type": "glazing bead",
                    "company": "kompen",
                    "material": "UPVC",
                    "opening_system": "Casement",
                    "system_series": "Kom701",
                    "code": "GLAZE-001",
                    "length_of_beam": Decimal("6.0"),
                    "front_height": Decimal("26.0"),
                    "glazing_undercut_height": Decimal("3.0"),
                    "weight_per_meter": Decimal("0.5"),
                    "colours": "White",
                    "price_per_meter": Decimal("15.0"),
                    "price_per_beam": Decimal("90.0"),  # 15 * 6 = 90
                    "upvc_profile_discount": Decimal("25.0"),
                },
            ]

            print(f"[INFO] Creating {len(sample_profiles)} sample profiles...")

            created_count = 0
            for i, profile_data in enumerate(sample_profiles, 1):
                try:
                    print(f"  {i}. Creating '{profile_data['name']}'...")

                    # Convert dict to ProfileEntryData model
                    profile_entry = ProfileEntryData(**profile_data)

                    # Use the EntryService to save the profile with page_type
                    configuration = await entry_service.save_profile_configuration(
                        profile_entry, admin_user, page_type="profile"
                    )

                    print(f"     [OK] Created configuration ID: {configuration.id}")
                    created_count += 1

                except Exception as e:
                    print(f"     [ERROR] Failed to create '{profile_data['name']}': {e}")
                    print(f"         Error type: {type(e).__name__}")
                    if hasattr(e, "field_errors"):
                        print(f"         Field errors: {e.field_errors}")
                    continue

            await session.commit()
            print(
                f"\n[SUCCESS] Successfully created {created_count}/{len(sample_profiles)} profile configurations!"
            )

            # Show summary
            from sqlalchemy import text

            total_configs = await session.scalar(
                text("SELECT COUNT(*) FROM configurations WHERE manufacturing_type_id = :mfg_id"),
                {"mfg_id": manufacturing_type.id},
            )
            print(f"[INFO] Total configurations for '{manufacturing_type.name}': {total_configs}")

            # Show what page types are available
            print(f"\n[INFO] Available page types for this manufacturing type:")
            from app.models.attribute_node import AttributeNode

            stmt = (
                select(AttributeNode.page_type)
                .where(AttributeNode.manufacturing_type_id == manufacturing_type.id)
                .distinct()
            )
            result = await session.execute(stmt)
            page_types = [row[0] for row in result.fetchall()]
            for page_type in page_types:
                print(f"   - {page_type}")

        except Exception as e:
            print(f"[ERROR] Error during seeding: {e}")
            await session.rollback()
            raise
        finally:
            # Don't close the session here as it's managed by get_db()
            pass

        # Break after first session (get_db() yields one session)
        break


async def main():
    """Main entry point."""
    print("Profile Data Seeding Script")
    print("=" * 40)

    try:
        await seed_profile_data()
        print("\n[SUCCESS] Seeding completed successfully!")
        print("\nYou can now:")
        print("1. Visit the profile page: http://localhost:8000/api/v1/admin/entry/profile")
        print("2. Switch to Preview tab to see the seeded data")
        print("3. Test the search and filtering functionality")

    except Exception as e:
        print(f"\n[ERROR] Seeding failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
