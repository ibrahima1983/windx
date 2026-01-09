import asyncio
from sqlalchemy import text
from app.core.database import get_db


async def update_display_conditions():
    print("Starting display condition updates...")

    updates = [
        # Renovation field (only for frames or sash) - adjusted based on checking "Frame" types broadly
        {
            "name": "renovation",
            "condition": {"operator": "contains", "field": "type", "value": "frame"},
        },
        # Width field (not for flying mullion)
        {
            "name": "width",
            "condition": {"operator": "not_equals", "field": "type", "value": "Flying mullion"},
        },
        # Builtin flyscreen track (only for sliding frames)
        {
            "name": "builtin_flyscreen_track",
            "condition": {
                "operator": "and",
                "conditions": [
                    {"operator": "contains", "field": "type", "value": "sliding"},
                    {"operator": "contains", "field": "type", "value": "frame"},
                ],
            },
        },
        # Total width (only when flyscreen is enabled)
        {
            "name": "total_width",
            "condition": {
                "operator": "or",
                "conditions": [
                    {"operator": "equals", "field": "builtin_flyscreen_track", "value": True},
                    {"operator": "contains", "field": "builtin_flyscreen_track", "value": "yes"},
                    {"operator": "equals", "field": "builtin_flyscreen_track", "value": "on"},
                ],
            },
        },
        # Flyscreen track height (only when flyscreen is enabled)
        {
            "name": "flyscreen_track_height",
            "condition": {
                "operator": "or",
                "conditions": [
                    {"operator": "equals", "field": "builtin_flyscreen_track", "value": True},
                    {"operator": "contains", "field": "builtin_flyscreen_track", "value": "yes"},
                    {"operator": "equals", "field": "builtin_flyscreen_track", "value": "on"},
                ],
            },
        },
        # Sash overlap (only for sash types)
        {
            "name": "sash_overlap",
            "condition": {"operator": "contains", "field": "type", "value": "sash"},
        },
        # Flying mullion clearances (only for flying mullion type)
        {
            "names": ["flying_mullion_horizontal_clearance", "flying_mullion_vertical_clearance"],
            "condition": {"operator": "equals", "field": "type", "value": "Flying mullion"},
        },
        # Steel material thickness (only when reinforcement is specified)
        {
            "name": "steel_material_thickness",
            "condition": {
                "operator": "is_not_empty",
                "field": "reinforcement_steel",
                "value": None,
            },
        },
        # Glazing undercut height (only for glazing bead)
        {
            "name": "glazing_undercut_height",
            "condition": {"operator": "contains", "field": "type", "value": "glazing bead"},
        },
        # Renovation height (only for frames)
        {
            "name": "renovation_height",
            "condition": {"operator": "contains", "field": "type", "value": "frame"},
        },
        # Front/Rear/Glazing heights usually go with frames/sashes
        {
            "names": ["front_height", "rear_height", "glazing_height"],
            "condition": {
                "operator": "or",
                "conditions": [
                    {"operator": "contains", "field": "type", "value": "frame"},
                    {"operator": "contains", "field": "type", "value": "sash"},
                    {"operator": "contains", "field": "type", "value": "mullion"},
                ],
            },
        },
    ]

    async for session in get_db():
        for update in updates:
            import json

            condition_json = json.dumps(update["condition"])

            names = update.get("names", [update.get("name")])

            for name in names:
                query = text("""
                    UPDATE attribute_nodes 
                    SET display_condition = :condition,
                        updated_at = NOW()
                    WHERE name = :name AND manufacturing_type_id = 475
                """)

                result = await session.execute(query, {"condition": condition_json, "name": name})
                print(f"Updated {name}: {result.rowcount} rows")

        await session.commit()
        print("All updates committed.")
        break


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(update_display_conditions())
