-- Depth Calculation Trigger
-- Automatically calculates depth from ltree_path
-- Depth is the number of levels in the hierarchy (0 for root nodes)

CREATE OR REPLACE FUNCTION calculate_attribute_node_depth()
RETURNS TRIGGER AS $$
BEGIN
    -- Calculate depth from ltree_path
    -- nlevel() returns the number of labels in the path
    -- Subtract 1 to make root nodes have depth 0
    IF NEW.ltree_path IS NOT NULL THEN
        NEW.depth = nlevel(NEW.ltree_path) - 1;
    ELSE
        NEW.depth = 0;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for INSERT and UPDATE
DROP TRIGGER IF EXISTS trigger_calculate_attribute_node_depth ON attribute_nodes;
CREATE TRIGGER trigger_calculate_attribute_node_depth
    BEFORE INSERT OR UPDATE ON attribute_nodes
    FOR EACH ROW
    EXECUTE FUNCTION calculate_attribute_node_depth();

-- Add comment for documentation
COMMENT ON FUNCTION calculate_attribute_node_depth() IS 
'Automatically calculates the depth field from ltree_path. 
Depth represents the nesting level in the hierarchy (0 for root nodes).';
