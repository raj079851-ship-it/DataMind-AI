-- =====================================================================
-- DataMind AI - Production PostgreSQL Database Migration (001_initial_schema.sql)
-- Target Engine: PostgreSQL 18+ / 17 / 16 / 15
-- Features: UUID v4, JSONB, FK Cascades, Composite Indexes, RLS Policies, Triggers
-- =====================================================================

-- 1. Enable Cryptographic & UUID Extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Create Reusable Timestamp Auto-Update Trigger Function
CREATE OR REPLACE FUNCTION update_timestamp_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- =====================================================================
-- TABLE 1: USERS
-- =====================================================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_login TIMESTAMP WITH TIME ZONE,
    login_count INTEGER DEFAULT 0 NOT NULL,
    last_login_ip VARCHAR(100),
    last_login_user_agent TEXT,
    last_login_method VARCHAR(50),
    last_login_status VARCHAR(50) DEFAULT 'SUCCESS',
    last_login_details TEXT,
    login_history JSONB DEFAULT '[]'::jsonb NOT NULL,
    CONSTRAINT check_user_role CHECK (role IN ('admin', 'user', 'analyst', 'engineer', 'viewer'))
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

CREATE TRIGGER update_users_modtime
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp_column();

-- =====================================================================
-- TABLE 2: DATASETS
-- =====================================================================
CREATE TABLE IF NOT EXISTS datasets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    dataset_name VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    file_size BIGINT NOT NULL DEFAULT 0,
    storage_path VARCHAR(512) NOT NULL,
    row_count INTEGER NOT NULL DEFAULT 0,
    column_count INTEGER NOT NULL DEFAULT 0,
    description TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT check_dataset_file_size_non_negative CHECK (file_size >= 0),
    CONSTRAINT check_dataset_row_count_non_negative CHECK (row_count >= 0),
    CONSTRAINT check_dataset_col_count_non_negative CHECK (column_count >= 0)
);

CREATE INDEX IF NOT EXISTS idx_datasets_user_id ON datasets(user_id);
CREATE INDEX IF NOT EXISTS idx_datasets_created_at ON datasets(created_at);
CREATE INDEX IF NOT EXISTS idx_datasets_user_created ON datasets(user_id, created_at);

CREATE TRIGGER update_datasets_modtime
    BEFORE UPDATE ON datasets
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp_column();

-- =====================================================================
-- TABLE 3: DATASET COLUMNS (Profiling & Metadata)
-- =====================================================================
CREATE TABLE IF NOT EXISTS dataset_columns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id UUID NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    column_name VARCHAR(255) NOT NULL,
    data_type VARCHAR(100) NOT NULL,
    null_count INTEGER NOT NULL DEFAULT 0,
    unique_count INTEGER NOT NULL DEFAULT 0,
    min_value TEXT,
    max_value TEXT,
    mean_value DOUBLE PRECISION,
    median_value DOUBLE PRECISION,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dataset_columns_dataset_id ON dataset_columns(dataset_id);
CREATE INDEX IF NOT EXISTS idx_dataset_columns_lookup ON dataset_columns(dataset_id, column_name);

-- =====================================================================
-- TABLE 4: DATA CLEANING OPERATIONS (Audit Trail of Transformations)
-- =====================================================================
CREATE TABLE IF NOT EXISTS data_cleaning_operations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id UUID NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    operation_type VARCHAR(100) NOT NULL,
    column_name VARCHAR(255),
    operation_details JSONB NOT NULL DEFAULT '{}'::jsonb,
    rows_affected INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(50) NOT NULL DEFAULT 'completed',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cleaning_dataset_id ON data_cleaning_operations(dataset_id);
CREATE INDEX IF NOT EXISTS idx_cleaning_user_id ON data_cleaning_operations(user_id);

-- =====================================================================
-- TABLE 5: ANALYSIS JOBS (Asynchronous ML & Analytical Tasks)
-- =====================================================================
CREATE TABLE IF NOT EXISTS analysis_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id UUID NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    result_location TEXT,
    CONSTRAINT check_job_status CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled'))
);

CREATE INDEX IF NOT EXISTS idx_analysis_jobs_dataset_id ON analysis_jobs(dataset_id);
CREATE INDEX IF NOT EXISTS idx_analysis_jobs_user_id ON analysis_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_analysis_jobs_user_status ON analysis_jobs(user_id, status);

-- =====================================================================
-- TABLE 6: ANALYSIS RESULTS (Empirical Findings & Metrics in JSONB)
-- =====================================================================
CREATE TABLE IF NOT EXISTS analysis_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES analysis_jobs(id) ON DELETE CASCADE,
    dataset_id UUID NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    result_type VARCHAR(100) NOT NULL,
    result_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_analysis_results_job_id ON analysis_results(job_id);
CREATE INDEX IF NOT EXISTS idx_analysis_results_dataset_id ON analysis_results(dataset_id);

-- =====================================================================
-- TABLE 7: DASHBOARDS (User Interactive BI Dashboards)
-- =====================================================================
CREATE TABLE IF NOT EXISTS dashboards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    dataset_id UUID REFERENCES datasets(id) ON DELETE SET NULL,
    dashboard_name VARCHAR(255) NOT NULL,
    description TEXT,
    configuration JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_public BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dashboards_user_id ON dashboards(user_id);
CREATE INDEX IF NOT EXISTS idx_dashboards_dataset_id ON dashboards(dataset_id);
CREATE INDEX IF NOT EXISTS idx_dashboards_user_created ON dashboards(user_id, created_at);

CREATE TRIGGER update_dashboards_modtime
    BEFORE UPDATE ON dashboards
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp_column();

-- =====================================================================
-- TABLE 8: AI INSIGHTS (Synthesized Machine Intelligence)
-- =====================================================================
CREATE TABLE IF NOT EXISTS ai_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    dataset_id UUID NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    analysis_id UUID REFERENCES analysis_jobs(id) ON DELETE SET NULL,
    insight_type VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    recommendations JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ai_insights_user_id ON ai_insights(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_insights_dataset_id ON ai_insights(dataset_id);
CREATE INDEX IF NOT EXISTS idx_insights_user_dataset ON ai_insights(user_id, dataset_id);

-- =====================================================================
-- TABLE 9: AUDIT LOGS (Immutable Activity Log)
-- =====================================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id VARCHAR(255),
    ip_address VARCHAR(45),
    user_agent TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_created ON audit_logs(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action_created ON audit_logs(action, created_at);

-- =====================================================================
-- ROW-LEVEL SECURITY (RLS) POLICIES
-- =====================================================================
-- Enable RLS on Datasets, Dashboards, and AI Insights
ALTER TABLE datasets ENABLE ROW LEVEL SECURITY;
ALTER TABLE dashboards ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_insights ENABLE ROW LEVEL SECURITY;

-- Note: RLS policies allow session variable `app.current_user_id` or superuser bypass
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'datasets' AND policyname = 'user_dataset_isolation_policy'
    ) THEN
        CREATE POLICY user_dataset_isolation_policy ON datasets
            FOR ALL
            USING (
                user_id::text = current_setting('app.current_user_id', true)
                OR current_setting('app.is_admin', true) = 'true'
            );
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'dashboards' AND policyname = 'user_dashboard_isolation_policy'
    ) THEN
        CREATE POLICY user_dashboard_isolation_policy ON dashboards
            FOR ALL
            USING (
                user_id::text = current_setting('app.current_user_id', true)
                OR is_public = true
                OR current_setting('app.is_admin', true) = 'true'
            );
    END IF;
END $$;
