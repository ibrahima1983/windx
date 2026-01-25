-- Price History Trigger
-- Automatically logs price changes for configurations
-- Tracks changes to total_price, base_price, and calculated_weight

CREATE OR REPLACE FUNCTION log_configuration_price_change()
RETURNS TRIGGER AS $$
BEGIN
    -- Only log if price or weight actually changed
    IF (OLD.total_price IS DISTINCT FROM NEW.total_price) OR 
       (OLD.base_price IS DISTINCT FROM NEW.base_price) OR 
       (OLD.calculated_weight IS DISTINCT FROM NEW.calculated_weight) THEN
        
        -- Insert into audit/history table (if it exists)
        -- Note: This assumes a configuration_price_history table exists
        -- If not, this will fail gracefully and can be created later
        BEGIN
            INSERT INTO configuration_price_history (
                configuration_id,
                old_base_price,
                new_base_price,
                old_total_price,
                new_total_price,
                old_calculated_weight,
                new_calculated_weight,
                change_reason,
                changed_at,
                changed_by
            ) VALUES (
                NEW.id,
                OLD.base_price,
                NEW.base_price,
                OLD.total_price,
                NEW.total_price,
                OLD.calculated_weight,
                NEW.calculated_weight,
                'Automatic update from configuration change',
                NOW(),
                CURRENT_USER
            );
        EXCEPTION
            WHEN undefined_table THEN
                -- Table doesn't exist yet, skip logging
                -- This allows the trigger to be created before the history table
                NULL;
        END;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for UPDATE only (not INSERT)
DROP TRIGGER IF EXISTS trigger_log_configuration_price_change ON configurations;
CREATE TRIGGER trigger_log_configuration_price_change
    AFTER UPDATE ON configurations
    FOR EACH ROW
    EXECUTE FUNCTION log_configuration_price_change();

-- Add comment for documentation
COMMENT ON FUNCTION log_configuration_price_change() IS 
'Automatically logs price and weight changes for configurations. 
Records old and new values in configuration_price_history table for audit trail.';

-- Optional: Create the history table if it doesn't exist
-- This can be uncommented when ready to enable full price history tracking
/*
CREATE TABLE IF NOT EXISTS configuration_price_history (
    id SERIAL PRIMARY KEY,
    configuration_id INTEGER NOT NULL REFERENCES configurations(id) ON DELETE CASCADE,
    old_base_price NUMERIC(12,2),
    new_base_price NUMERIC(12,2),
    old_total_price NUMERIC(12,2),
    new_total_price NUMERIC(12,2),
    old_calculated_weight NUMERIC(10,2),
    new_calculated_weight NUMERIC(10,2),
    change_reason TEXT,
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    changed_by VARCHAR(255)
);

CREATE INDEX idx_config_price_history_config_id ON configuration_price_history(configuration_id);
CREATE INDEX idx_config_price_history_changed_at ON configuration_price_history(changed_at);
*/
