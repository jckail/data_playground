-- Create eventtype ENUM if not exists
CREATE TYPE eventtype AS ENUM (
    'user_account_creation',
    'user_delete_account',
    'user_shop_create',
    'user_shop_delete',
    'user_deactivate_account'
);

-- Create global_events table if not exists
CREATE TABLE IF NOT EXISTS global_events (
    event_id UUID,
    event_time TIMESTAMP WITH TIME ZONE NOT NULL,
    event_type eventtype NOT NULL,
    event_metadata JSONB,
    partition_key VARCHAR(16) NOT NULL,
    PRIMARY KEY (event_id, partition_key)
) PARTITION BY LIST (partition_key);

-- Create users table with partitioning by date
CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    status BOOLEAN NOT NULL DEFAULT TRUE,
    created_time TIMESTAMP WITH TIME ZONE NOT NULL,
    deactivated_time TIMESTAMP WITH TIME ZONE,
    partition_key DATE GENERATED ALWAYS AS (created_time::date) STORED
) PARTITION BY RANGE (partition_key);

-- Create shops table
CREATE TABLE IF NOT EXISTS shops (
    shop_id UUID PRIMARY KEY,
    shop_owner_id UUID REFERENCES users(user_id),
    shop_name VARCHAR(255) NOT NULL,
    created_time TIMESTAMP WITH TIME ZONE NOT NULL,
    deactivated_time TIMESTAMP WITH TIME ZONE,
    partition_key DATE GENERATED ALWAYS AS (created_time::date) STORED
) PARTITION BY RANGE (partition_key);

-- Create user_invoices table with partitioning by date
CREATE TABLE IF NOT EXISTS user_invoices (
    invoice_id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(user_id),
    shop_id UUID REFERENCES shops(shop_id),
    invoice_amount FLOAT NOT NULL,
    event_time TIMESTAMP WITH TIME ZONE NOT NULL,
    partition_key DATE GENERATED ALWAYS AS (event_time::date) STORED
) PARTITION BY RANGE (partition_key);

-- Create payments table with partitioning by date
CREATE TABLE IF NOT EXISTS payments (
    payment_id UUID PRIMARY KEY,
    invoice_id UUID REFERENCES user_invoices(invoice_id),
    payment_amount FLOAT NOT NULL,
    event_time TIMESTAMP WITH TIME ZONE NOT NULL,
    partition_key DATE GENERATED ALWAYS AS (event_time::date) STORED
) PARTITION BY RANGE (partition_key);

-- Example of creating a partition for a specific day for user_invoices
-- CREATE TABLE IF NOT EXISTS user_invoices_2024_08_16 PARTITION OF user_invoices
-- FOR VALUES FROM ('2024-08-16') TO ('2024-08-17');

-- Example of creating a partition for a specific day for payments
-- CREATE TABLE IF NOT EXISTS payments_2024_08_16 PARTITION OF payments
-- FOR VALUES FROM ('2024-08-16') TO ('2024-08-17');

-- Indexes for optimized querying

CREATE INDEX IF NOT EXISTS idx_user_invoices_user_id ON user_invoices(user_id);
CREATE INDEX IF NOT EXISTS idx_user_invoices_shop_id ON user_invoices(shop_id);
CREATE INDEX IF NOT EXISTS idx_user_invoices_event_time ON user_invoices(event_time);

CREATE INDEX IF NOT EXISTS idx_payments_invoice_id ON payments(invoice_id);
CREATE INDEX IF NOT EXISTS idx_payments_event_time ON payments(event_time);

CREATE INDEX IF NOT EXISTS idx_users_created_time ON users(created_time);
CREATE INDEX IF NOT EXISTS idx_users_deactivated_time ON users(deactivated_time);

CREATE INDEX IF NOT EXISTS idx_shops_created_time ON shops(created_time);
CREATE INDEX IF NOT EXISTS idx_shops_deactivated_time ON shops(deactivated_time);
