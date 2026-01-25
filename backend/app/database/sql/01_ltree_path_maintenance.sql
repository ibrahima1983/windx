-- LTREE Path Maintenance Trigger
-- Automatically updates ltree_path when parent_node_id changes
-- Also updates all descendant paths when a node is moved

CREATE OR REPLACE FUNCTION update_attribute_node_ltree_path()
RETURNS TRIGGER AS $$
DECLARE
    parent_path LTREE;
    old_path LTREE;
    new_path LTREE;
BEGIN
    -- Handle INSERT or UPDATE
    IF TG_OP = 'INSERT' OR (TG_OP = 'UPDATE' AND (NEW.parent_node_id IS DISTINCT FROM OLD.parent_node_id OR NEW.name IS DISTINCT FROM OLD.name)) THEN
        
        -- If node has no parent, it's a root node
        IF NEW.parent_node_id IS NULL THEN
            -- Root node: path is just the node's name (sanitized)
            NEW.ltree_path = text2ltree(regexp_replace(lower(NEW.name), '[^a-z0-9_]', '_', 'g'));
        ELSE
            -- Get parent's path
            SELECT ltree_path INTO parent_path
            FROM attribute_nodes
            WHERE id = NEW.parent_node_id;
            
            IF parent_path IS NULL THEN
                RAISE EXCEPTION 'Parent node % does not exist or has no ltree_path', NEW.parent_node_id;
            END IF;
            
            -- Child node: parent_path + sanitized node name
            NEW.ltree_path = parent_path || text2ltree(regexp_replace(lower(NEW.name), '[^a-z0-9_]', '_', 'g'));
        END IF;
        
        -- If this is an UPDATE and the path changed, update all descendants
        IF TG_OP = 'UPDATE' AND OLD.ltree_path IS DISTINCT FROM NEW.ltree_path THEN
            old_path := OLD.ltree_path;
            new_path := NEW.ltree_path;
            
            -- Update all descendant paths
            UPDATE attribute_nodes
            SET ltree_path = new_path || subltree(ltree_path, nlevel(old_path), nlevel(ltree_path))
            WHERE ltree_path <@ old_path AND id != NEW.id;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for INSERT and UPDATE
DROP TRIGGER IF EXISTS trigger_update_attribute_node_ltree_path ON attribute_nodes;
CREATE TRIGGER trigger_update_attribute_node_ltree_path
    BEFORE INSERT OR UPDATE ON attribute_nodes
    FOR EACH ROW
    EXECUTE FUNCTION update_attribute_node_ltree_path();

-- Add comment for documentation
COMMENT ON FUNCTION update_attribute_node_ltree_path() IS 
'Automatically maintains ltree_path field based on parent_node_id and name. 
When a node is moved (parent_node_id changes), all descendant paths are updated recursively.';
