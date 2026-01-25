-- Test Script for Database Triggers
-- This script tests the LTREE path maintenance, depth calculation, and price history triggers

-- Prerequisites: Run this after installing triggers and creating tables

BEGIN;

-- Test 1: LTREE Path Maintenance - Root Node
-- Expected: ltree_path = 'test_root', depth = 0
INSERT INTO attribute_nodes (name, manufacturing_type_id, node_type)
VALUES ('Test Root', 1, 'category')
RETURNING id, name, ltree_path, depth;

-- Store the root ID for next test
-- Replace <root_id> below with the actual ID from the previous INSERT

-- Test 2: LTREE Path Maintenance - Child Node
-- Expected: ltree_path = 'test_root.test_child', depth = 1
INSERT INTO attribute_nodes (name, parent_node_id, manufacturing_type_id, node_type)
VALUES ('Test Child', <root_id>, 1, 'attribute')
RETURNING id, name, ltree_path, depth;

-- Test 3: LTREE Path Maintenance - Grandchild Node
-- Expected: ltree_path = 'test_root.test_child.test_grandchild', depth = 2
INSERT INTO attribute_nodes (name, parent_node_id, manufacturing_type_id, node_type)
VALUES ('Test Grandchild', <child_id>, 1, 'option')
RETURNING id, name, ltree_path, depth;

-- Test 4: Verify Depth Calculation
-- All nodes should have correct depth values
SELECT id, name, ltree_path, depth, nlevel(ltree_path) - 1 as calculated_depth
FROM attribute_nodes
WHERE name LIKE 'Test%'
ORDER BY ltree_path;

-- Test 5: Move Node (Update Parent)
-- This should update the node's path AND all descendant paths
UPDATE attribute_nodes 
SET parent_node_id = NULL 
WHERE id = <child_id>
RETURNING id, name, ltree_path, depth;

-- Verify descendants were updated
SELECT id, name, ltree_path, depth
FROM attribute_nodes
WHERE name LIKE 'Test%'
ORDER BY ltree_path;

-- Test 6: Price History Trigger
-- Update configuration price and verify history is logged
UPDATE configurations 
SET total_price = total_price + 100.00
WHERE id = 1
RETURNING id, total_price;

-- Check if history was logged (if table exists)
-- SELECT * FROM configuration_price_history 
-- WHERE configuration_id = 1 
-- ORDER BY changed_at DESC LIMIT 1;

-- Cleanup test data
DELETE FROM attribute_nodes WHERE name LIKE 'Test%';

ROLLBACK;

-- Summary of Expected Results:
-- 1. Root node: ltree_path = 'test_root', depth = 0
-- 2. Child node: ltree_path = 'test_root.test_child', depth = 1
-- 3. Grandchild: ltree_path = 'test_root.test_child.test_grandchild', depth = 2
-- 4. After moving child to root: ltree_path = 'test_child', depth = 0
-- 5. Grandchild path updated: ltree_path = 'test_child.test_grandchild', depth = 1
-- 6. Price history logged (if table exists)
