-- Enable PostgreSQL LTREE extension for hierarchical data
-- This script should be run once during database initialization

-- Create LTREE extension if it doesn't exist
-- LTREE provides data types and functions for representing labels of data
-- stored in a hierarchical tree-like structure
CREATE EXTENSION IF NOT EXISTS ltree;

-- Verify extension is installed
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_extension WHERE extname = 'ltree'
    ) THEN
        RAISE EXCEPTION 'LTREE extension failed to install';
    END IF;
END $$;

-- Display success message
DO $$
BEGIN
    RAISE NOTICE 'LTREE extension enabled successfully';
END $$;
