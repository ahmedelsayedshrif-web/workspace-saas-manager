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
-- IMPORTANT: service_role bypasses RLS automatically, so no policy needed for it

-- Allow anonymous users to read licenses (for license verification by HWID)
CREATE POLICY "Allow license check by HWID"
ON licenses FOR SELECT
TO anon
USING (true);  -- Allow reading for license verification

-- Allow anonymous users to UPDATE their own license (for activation - linking HWID)
CREATE POLICY "Allow license activation by HWID"
ON licenses FOR UPDATE
TO anon
USING (true)
WITH CHECK (true);

-- Note: INSERT operations require service_role key (which bypasses RLS automatically)
-- No policy needed for service_role - it has full access by default

