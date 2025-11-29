-- ============================================
-- Supabase License Management Table Setup
-- ============================================
-- Run this SQL in your Supabase SQL Editor
-- ============================================

-- Create the licenses table
CREATE TABLE IF NOT EXISTS licenses (
    id BIGSERIAL PRIMARY KEY,
    license_key UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    client_name TEXT NOT NULL,
    hwid TEXT UNIQUE,
    expiration_date DATE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    notes TEXT
);

-- Create an index on hwid for faster lookups
CREATE INDEX IF NOT EXISTS idx_licenses_hwid ON licenses(hwid);

-- Create an index on license_key for faster lookups
CREATE INDEX IF NOT EXISTS idx_licenses_license_key ON licenses(license_key);

-- Create an index on expiration_date for filtering
CREATE INDEX IF NOT EXISTS idx_licenses_expiration_date ON licenses(expiration_date);

-- Create a function to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create a trigger to automatically update updated_at
CREATE TRIGGER update_licenses_updated_at 
    BEFORE UPDATE ON licenses
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security (RLS)
ALTER TABLE licenses ENABLE ROW LEVEL SECURITY;

-- Grant necessary permissions
GRANT ALL ON licenses TO authenticated;
GRANT ALL ON licenses TO service_role;

-- Optional: Create a view for active licenses
CREATE OR REPLACE VIEW active_licenses AS
SELECT 
    license_key,
    client_name,
    hwid,
    expiration_date,
    is_active,
    created_at,
    CASE 
        WHEN expiration_date < CURRENT_DATE THEN 'Expired'
        WHEN expiration_date >= CURRENT_DATE AND is_active = TRUE THEN 'Active'
        ELSE 'Inactive'
    END AS status
FROM licenses
WHERE is_active = TRUE;

