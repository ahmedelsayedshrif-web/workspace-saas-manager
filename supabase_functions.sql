-- ============================================
-- Additional Supabase Functions
-- ============================================
-- Run this SQL in your Supabase SQL Editor AFTER creating the licenses table
-- ============================================

-- Function to get server date (for license verification)
CREATE OR REPLACE FUNCTION get_server_date()
RETURNS DATE AS $$
BEGIN
    RETURN CURRENT_DATE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION get_server_date() TO anon, authenticated;

-- Row Level Security Policy for licenses table
-- Allow anonymous users to read their own license (by HWID)
CREATE POLICY "Allow license check by HWID"
ON licenses FOR SELECT
TO anon
USING (true);  -- Allow reading for license verification

-- Allow authenticated users full access (for admin panel)
CREATE POLICY "Full access for authenticated users"
ON licenses FOR ALL
TO authenticated
USING (true)
WITH CHECK (true);

-- Allow service role full access
CREATE POLICY "Full access for service role"
ON licenses FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

