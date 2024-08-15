CREATE TYPE eventtype AS ENUM (
    'user_account_creation',
    'user_delete_account',
    'user_shop_create',
    'user_shop_delete',
    'user_deactivate_account'
);

CREATE TABLE IF NOT EXISTS global_events (
    event_id UUID,
    event_time TIMESTAMP WITH TIME ZONE NOT NULL,
    event_type eventtype NOT NULL,
    event_metadata JSONB,
    partition_key VARCHAR(16) NOT NULL,
    PRIMARY KEY (event_id, partition_key)
) PARTITION BY LIST (partition_key);