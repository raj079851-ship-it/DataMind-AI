"""001_initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-24 17:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Users
    op.execute("""
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
            CONSTRAINT check_user_role CHECK (role IN ('admin', 'user', 'analyst', 'engineer', 'viewer'))
        );
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
    """)

    # 2. Datasets
    op.execute("""
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
    """)

    # 3. Dataset Columns
    op.execute("""
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
    """)

    # 4. Data Cleaning Operations
    op.execute("""
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
    """)

    # 5. Analysis Jobs
    op.execute("""
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
    """)

    # 6. Analysis Results
    op.execute("""
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
    """)

    # 7. Dashboards
    op.execute("""
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
    """)

    # 8. AI Insights
    op.execute("""
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
    """)

    # 9. Audit Logs
    op.execute("""
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
    """)


def downgrade() -> None:
    op.execute("""
        DROP TABLE IF EXISTS audit_logs CASCADE;
        DROP TABLE IF EXISTS ai_insights CASCADE;
        DROP TABLE IF EXISTS dashboards CASCADE;
        DROP TABLE IF EXISTS analysis_results CASCADE;
        DROP TABLE IF EXISTS analysis_jobs CASCADE;
        DROP TABLE IF EXISTS data_cleaning_operations CASCADE;
        DROP TABLE IF EXISTS dataset_columns CASCADE;
        DROP TABLE IF EXISTS datasets CASCADE;
        DROP TABLE IF EXISTS users CASCADE;
    """)
