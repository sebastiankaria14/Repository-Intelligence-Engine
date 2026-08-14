-- ─────────────────────────────────────────────────
-- RIE PostgreSQL Initialization
-- ─────────────────────────────────────────────────

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- The main database and user are created by Docker env vars.
-- This script runs additional setup inside the already-created DB.

-- Grant full privileges
GRANT ALL PRIVILEGES ON DATABASE rie TO rie;
