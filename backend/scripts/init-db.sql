-- ============================================================================
-- Nexus AI Database Initialization Script
-- Runs automatically when PostgreSQL container starts for the first time
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create custom types
DO $$ BEGIN
    CREATE TYPE tenant_type AS ENUM ('agency', 'saas_subscriber');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE integration_platform AS ENUM ('meta', 'google', 'tiktok', 'twitter', 'linkedin', 'youtube', 'pinterest');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE approval_status AS ENUM ('pending', 'approved', 'rejected', 'failed');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE campaign_status AS ENUM ('draft', 'active', 'paused', 'completed', 'archived');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE nexus_ai TO postgres;

-- Create schema notification
DO $$
BEGIN
    RAISE NOTICE 'Nexus AI database initialized successfully';
END $$;