# Database SQL Scripts

This directory contains PostgreSQL SQL scripts for database triggers and functions used by the Windx configurator system.

## Scripts Overview

### 01_ltree_path_maintenance.sql
**Purpose**: Automatically maintains the `ltree_path` field in the `attribute_nodes` table.

**Features**:
- Generates LTREE paths based on `parent_node_id` and node `name`
- Sanitizes node names for LTREE compatibility (lowercase, alphanumeric + underscore)
- Automatically updates all descendant paths when a node is moved
- Handles both INSERT and UPDATE operations

**Example**:
```sql
-- When inserting a node:
INSERT INTO attribute_nodes (name, parent_node_id, manufacturing_type_id, node_type)
VALUES ('Frame Material', NULL, 1, 'category');
-- ltree_path is automatically set to: 'frame_material'

-- When inserting a child node:
INSERT INTO attribute_nodes (name, parent_node_id, manufacturing_type_id, node_type)
VALUES ('Aluminum', 5, 1, 'option');
-- ltree_path is automatically set to: 'frame_material.aluminum'

-- When moving a node (changing parent_node_id):
UPDATE attribute_nodes SET parent_node_id = 10 WHERE id = 5;
-- ltree_path is updated for the node AND all its descendants
```

### 02_depth_calculation.sql
**Purpose**: Automatically calculates the `depth` field from the `ltree_path`.

**Features**:
- Calculates depth as the number of levels in the hierarchy
- Root nodes have depth 0
- Updates automatically on INSERT and UPDATE

**Example**:
```sql
-- Root node: 'frame_material' → depth = 0
-- Child node: 'frame_material.aluminum' → depth = 1
-- Grandchild: 'frame_material.aluminum.color' → depth = 2
```

### 03_price_history.sql
**Purpose**: Logs price and weight changes for configurations.

**Features**:
- Tracks changes to `total_price`, `base_price`, and `calculated_weight`
- Records old and new values for audit trail
- Includes timestamp and user information
- Gracefully handles missing history table (for phased implementation)

**Note**: The `configuration_price_history` table is optional. Uncomment the CREATE TABLE statement in the script to enable full price history tracking.

## Installation

### Option 1: Manual Execution
Execute the scripts in order using psql or your database client:

```bash
psql -U your_user -d your_database -f app/database/sql/01_ltree_path_maintenance.sql
psql -U your_user -d your_database -f app/database/sql/02_depth_calculation.sql
psql -U your_user -d your_database -f app/database/sql/03_price_history.sql
```

### Option 2: Python Script
Create a database initialization script:

```python
from sqlalchemy import text
from app.core.database import engine
import os

async def install_triggers():
    sql_dir = "app/database/sql"
    scripts = [
        "01_ltree_path_maintenance.sql",
        "02_depth_calculation.sql",
        "03_price_history.sql"
    ]
    
    async with engine.begin() as conn:
        for script in scripts:
            script_path = os.path.join(sql_dir, script)
            with open(script_path, 'r') as f:
                sql = f.read()
                await conn.execute(text(sql))
            print(f"Installed: {script}")
```

### Option 3: Alembic Migration
Include in an Alembic migration:

```python
from alembic import op
import os

def upgrade():
    sql_dir = "app/database/sql"
    scripts = [
        "01_ltree_path_maintenance.sql",
        "02_depth_calculation.sql",
        "03_price_history.sql"
    ]
    
    for script in scripts:
        script_path = os.path.join(sql_dir, script)
        with open(script_path, 'r') as f:
            sql = f.read()
            op.execute(sql)

def downgrade():
    # Drop triggers and functions
    op.execute("DROP TRIGGER IF EXISTS trigger_update_attribute_node_ltree_path ON attribute_nodes")
    op.execute("DROP FUNCTION IF EXISTS update_attribute_node_ltree_path()")
    op.execute("DROP TRIGGER IF EXISTS trigger_calculate_attribute_node_depth ON attribute_nodes")
    op.execute("DROP FUNCTION IF EXISTS calculate_attribute_node_depth()")
    op.execute("DROP TRIGGER IF EXISTS trigger_log_configuration_price_change ON configurations")
    op.execute("DROP FUNCTION IF EXISTS log_configuration_price_change()")
```

## Testing

### Test LTREE Path Maintenance
```sql
-- Create a root node
INSERT INTO attribute_nodes (name, manufacturing_type_id, node_type)
VALUES ('Test Root', 1, 'category')
RETURNING id, ltree_path, depth;
-- Expected: ltree_path = 'test_root', depth = 0

-- Create a child node
INSERT INTO attribute_nodes (name, parent_node_id, manufacturing_type_id, node_type)
VALUES ('Test Child', <root_id>, 1, 'attribute')
RETURNING id, ltree_path, depth;
-- Expected: ltree_path = 'test_root.test_child', depth = 1

-- Move the child to a different parent
UPDATE attribute_nodes SET parent_node_id = <new_parent_id> WHERE id = <child_id>
RETURNING ltree_path;
-- Expected: ltree_path updated to reflect new parent
```

### Test Depth Calculation
```sql
-- Check depth values
SELECT id, name, ltree_path, depth 
FROM attribute_nodes 
ORDER BY ltree_path;
-- Verify depth matches the number of dots in ltree_path
```

### Test Price History
```sql
-- Update configuration price
UPDATE configurations 
SET total_price = 999.99 
WHERE id = 1;

-- Check history (if table exists)
SELECT * FROM configuration_price_history 
WHERE configuration_id = 1 
ORDER BY changed_at DESC;
```

## Troubleshooting

### LTREE Extension Not Enabled
If you get an error about LTREE not being available:
```sql
CREATE EXTENSION IF NOT EXISTS ltree;
```

### Trigger Not Firing
Check if triggers are enabled:
```sql
SELECT tgname, tgenabled 
FROM pg_trigger 
WHERE tgrelid = 'attribute_nodes'::regclass;
```

### Path Not Updating
Verify the trigger function exists:
```sql
SELECT proname, prosrc 
FROM pg_proc 
WHERE proname = 'update_attribute_node_ltree_path';
```

## Performance Considerations

### LTREE Path Maintenance
- Moving a node with many descendants can be slow (updates all descendant paths)
- Consider batching large hierarchy changes
- GiST index on `ltree_path` helps with query performance

### Depth Calculation
- Very fast (simple calculation)
- No performance concerns

### Price History
- Adds overhead to every configuration UPDATE
- Consider disabling if not needed
- History table can grow large over time (implement archiving strategy)

## Maintenance

### Rebuilding LTREE Paths
If paths become inconsistent, rebuild them:
```sql
-- Disable trigger temporarily
ALTER TABLE attribute_nodes DISABLE TRIGGER trigger_update_attribute_node_ltree_path;

-- Rebuild paths (requires recursive CTE or application logic)
-- This is a manual process - contact DBA

-- Re-enable trigger
ALTER TABLE attribute_nodes ENABLE TRIGGER trigger_update_attribute_node_ltree_path;
```

### Monitoring Trigger Performance
```sql
-- Check trigger execution time (requires pg_stat_statements)
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
WHERE query LIKE '%update_attribute_node_ltree_path%';
```

## References

- [PostgreSQL LTREE Documentation](https://www.postgresql.org/docs/current/ltree.html)
- [PostgreSQL Triggers Documentation](https://www.postgresql.org/docs/current/triggers.html)
- [Windx Integration Plan](../../../.kiro/specs/windx-integration/windx-integration-plan.md)
