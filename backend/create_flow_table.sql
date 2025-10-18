-- Create flow table for SQLite
-- Run this SQL in your database if the migration doesn't run automatically

CREATE TABLE IF NOT EXISTS flow (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    nodes JSON NOT NULL,
    edges JSON NOT NULL,
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL,
    meta JSON DEFAULT '{}'
);

-- Create indexes
CREATE INDEX IF NOT EXISTS flow_user_id_idx ON flow(user_id);
CREATE INDEX IF NOT EXISTS flow_updated_at_idx ON flow(updated_at);
CREATE INDEX IF NOT EXISTS flow_user_id_updated_at_idx ON flow(user_id, updated_at);

-- Verify the table was created
SELECT 'Flow table created successfully!' as status;
