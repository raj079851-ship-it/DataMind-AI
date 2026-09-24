--
-- PostgreSQL database dump
--

\restrict nc7nU5sSBq0bOHtJCWWT8DOyq5BUpyUyMDDMoPelDAV3cwvBRN8Wu6iJQN76hvh

-- Dumped from database version 18.6
-- Dumped by pg_dump version 18.6

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

DROP POLICY IF EXISTS user_dataset_isolation_policy ON public.datasets;
DROP POLICY IF EXISTS user_dashboard_isolation_policy ON public.dashboards;
ALTER TABLE IF EXISTS ONLY public.datasets DROP CONSTRAINT IF EXISTS datasets_user_id_fkey;
ALTER TABLE IF EXISTS ONLY public.dataset_columns DROP CONSTRAINT IF EXISTS dataset_columns_dataset_id_fkey;
ALTER TABLE IF EXISTS ONLY public.data_cleaning_operations DROP CONSTRAINT IF EXISTS data_cleaning_operations_user_id_fkey;
ALTER TABLE IF EXISTS ONLY public.data_cleaning_operations DROP CONSTRAINT IF EXISTS data_cleaning_operations_dataset_id_fkey;
ALTER TABLE IF EXISTS ONLY public.dashboards DROP CONSTRAINT IF EXISTS dashboards_user_id_fkey;
ALTER TABLE IF EXISTS ONLY public.dashboards DROP CONSTRAINT IF EXISTS dashboards_dataset_id_fkey;
ALTER TABLE IF EXISTS ONLY public.audit_logs DROP CONSTRAINT IF EXISTS audit_logs_user_id_fkey;
ALTER TABLE IF EXISTS ONLY public.analysis_results DROP CONSTRAINT IF EXISTS analysis_results_job_id_fkey;
ALTER TABLE IF EXISTS ONLY public.analysis_results DROP CONSTRAINT IF EXISTS analysis_results_dataset_id_fkey;
ALTER TABLE IF EXISTS ONLY public.analysis_jobs DROP CONSTRAINT IF EXISTS analysis_jobs_user_id_fkey;
ALTER TABLE IF EXISTS ONLY public.analysis_jobs DROP CONSTRAINT IF EXISTS analysis_jobs_dataset_id_fkey;
ALTER TABLE IF EXISTS ONLY public.ai_insights DROP CONSTRAINT IF EXISTS ai_insights_user_id_fkey;
ALTER TABLE IF EXISTS ONLY public.ai_insights DROP CONSTRAINT IF EXISTS ai_insights_dataset_id_fkey;
ALTER TABLE IF EXISTS ONLY public.ai_insights DROP CONSTRAINT IF EXISTS ai_insights_analysis_id_fkey;
DROP TRIGGER IF EXISTS update_users_modtime ON public.users;
DROP TRIGGER IF EXISTS update_datasets_modtime ON public.datasets;
DROP TRIGGER IF EXISTS update_dashboards_modtime ON public.dashboards;
DROP INDEX IF EXISTS public.idx_users_role;
DROP INDEX IF EXISTS public.idx_users_email;
DROP INDEX IF EXISTS public.idx_insights_user_dataset;
DROP INDEX IF EXISTS public.idx_datasets_user_id;
DROP INDEX IF EXISTS public.idx_datasets_user_created;
DROP INDEX IF EXISTS public.idx_datasets_created_at;
DROP INDEX IF EXISTS public.idx_dataset_columns_lookup;
DROP INDEX IF EXISTS public.idx_dataset_columns_dataset_id;
DROP INDEX IF EXISTS public.idx_dashboards_user_id;
DROP INDEX IF EXISTS public.idx_dashboards_user_created;
DROP INDEX IF EXISTS public.idx_dashboards_dataset_id;
DROP INDEX IF EXISTS public.idx_cleaning_user_id;
DROP INDEX IF EXISTS public.idx_cleaning_dataset_id;
DROP INDEX IF EXISTS public.idx_audit_logs_user_id;
DROP INDEX IF EXISTS public.idx_audit_logs_user_created;
DROP INDEX IF EXISTS public.idx_audit_logs_created_at;
DROP INDEX IF EXISTS public.idx_audit_logs_action_created;
DROP INDEX IF EXISTS public.idx_analysis_results_job_id;
DROP INDEX IF EXISTS public.idx_analysis_results_dataset_id;
DROP INDEX IF EXISTS public.idx_analysis_jobs_user_status;
DROP INDEX IF EXISTS public.idx_analysis_jobs_user_id;
DROP INDEX IF EXISTS public.idx_analysis_jobs_dataset_id;
DROP INDEX IF EXISTS public.idx_ai_insights_user_id;
DROP INDEX IF EXISTS public.idx_ai_insights_dataset_id;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_pkey;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_email_key;
ALTER TABLE IF EXISTS ONLY public.datasets DROP CONSTRAINT IF EXISTS datasets_pkey;
ALTER TABLE IF EXISTS ONLY public.dataset_columns DROP CONSTRAINT IF EXISTS dataset_columns_pkey;
ALTER TABLE IF EXISTS ONLY public.data_cleaning_operations DROP CONSTRAINT IF EXISTS data_cleaning_operations_pkey;
ALTER TABLE IF EXISTS ONLY public.dashboards DROP CONSTRAINT IF EXISTS dashboards_pkey;
ALTER TABLE IF EXISTS ONLY public.audit_logs DROP CONSTRAINT IF EXISTS audit_logs_pkey;
ALTER TABLE IF EXISTS ONLY public.analysis_results DROP CONSTRAINT IF EXISTS analysis_results_pkey;
ALTER TABLE IF EXISTS ONLY public.analysis_jobs DROP CONSTRAINT IF EXISTS analysis_jobs_pkey;
ALTER TABLE IF EXISTS ONLY public.alembic_version DROP CONSTRAINT IF EXISTS alembic_version_pkc;
ALTER TABLE IF EXISTS ONLY public.ai_insights DROP CONSTRAINT IF EXISTS ai_insights_pkey;
DROP TABLE IF EXISTS public.users;
DROP TABLE IF EXISTS public.datasets;
DROP TABLE IF EXISTS public.dataset_columns;
DROP TABLE IF EXISTS public.data_cleaning_operations;
DROP TABLE IF EXISTS public.dashboards;
DROP TABLE IF EXISTS public.audit_logs;
DROP TABLE IF EXISTS public.analysis_results;
DROP TABLE IF EXISTS public.analysis_jobs;
DROP TABLE IF EXISTS public.alembic_version;
DROP TABLE IF EXISTS public.ai_insights;
DROP FUNCTION IF EXISTS public.update_timestamp_column();
DROP EXTENSION IF EXISTS "uuid-ossp";
DROP EXTENSION IF EXISTS pgcrypto;
--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: update_timestamp_column(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_timestamp_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: ai_insights; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ai_insights (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    dataset_id uuid NOT NULL,
    analysis_id uuid,
    insight_type character varying(100) NOT NULL,
    title character varying(255) NOT NULL,
    content text NOT NULL,
    recommendations jsonb DEFAULT '[]'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: analysis_jobs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.analysis_jobs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    dataset_id uuid NOT NULL,
    user_id uuid NOT NULL,
    job_type character varying(100) NOT NULL,
    status character varying(50) DEFAULT 'pending'::character varying NOT NULL,
    started_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    completed_at timestamp with time zone,
    error_message text,
    result_location text,
    CONSTRAINT check_job_status CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'running'::character varying, 'completed'::character varying, 'failed'::character varying, 'cancelled'::character varying])::text[])))
);


--
-- Name: analysis_results; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.analysis_results (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    job_id uuid NOT NULL,
    dataset_id uuid NOT NULL,
    result_type character varying(100) NOT NULL,
    result_data jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_logs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    action character varying(100) NOT NULL,
    resource_type character varying(100) NOT NULL,
    resource_id character varying(255),
    ip_address character varying(45),
    user_agent text,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: dashboards; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dashboards (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    dataset_id uuid,
    dashboard_name character varying(255) NOT NULL,
    description text,
    configuration jsonb DEFAULT '{}'::jsonb NOT NULL,
    is_public boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: data_cleaning_operations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.data_cleaning_operations (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    dataset_id uuid NOT NULL,
    user_id uuid NOT NULL,
    operation_type character varying(100) NOT NULL,
    column_name character varying(255),
    operation_details jsonb DEFAULT '{}'::jsonb NOT NULL,
    rows_affected integer DEFAULT 0 NOT NULL,
    status character varying(50) DEFAULT 'completed'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: dataset_columns; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dataset_columns (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    dataset_id uuid NOT NULL,
    column_name character varying(255) NOT NULL,
    data_type character varying(100) NOT NULL,
    null_count integer DEFAULT 0 NOT NULL,
    unique_count integer DEFAULT 0 NOT NULL,
    min_value text,
    max_value text,
    mean_value double precision,
    median_value double precision,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: datasets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.datasets (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    dataset_name character varying(255) NOT NULL,
    original_filename character varying(255) NOT NULL,
    file_type character varying(50) NOT NULL,
    file_size bigint DEFAULT 0 NOT NULL,
    storage_path character varying(512) NOT NULL,
    row_count integer DEFAULT 0 NOT NULL,
    column_count integer DEFAULT 0 NOT NULL,
    description text,
    status character varying(50) DEFAULT 'active'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT check_dataset_col_count_non_negative CHECK ((column_count >= 0)),
    CONSTRAINT check_dataset_file_size_non_negative CHECK ((file_size >= 0)),
    CONSTRAINT check_dataset_row_count_non_negative CHECK ((row_count >= 0))
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    full_name character varying(255) NOT NULL,
    email character varying(255) NOT NULL,
    password_hash character varying(255) NOT NULL,
    role character varying(50) DEFAULT 'user'::character varying NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_login timestamp with time zone,
    CONSTRAINT check_user_role CHECK (((role)::text = ANY ((ARRAY['admin'::character varying, 'user'::character varying, 'analyst'::character varying, 'engineer'::character varying, 'viewer'::character varying])::text[])))
);


--
-- Data for Name: ai_insights; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.ai_insights (id, user_id, dataset_id, analysis_id, insight_type, title, content, recommendations, created_at) FROM stdin;
585a77de-6c25-4444-9f7f-71039676b177	a7607514-0838-4878-b90b-2abd54a72e1b	fd3f3a5f-fd11-4f54-8ecf-1f56936c9d58	\N	Risk Advisory	Early Lifecycle Churn Spike	Customers with tenure under 6 months show a 48.2% churn likelihood when enrolled in month-to-month contracts.	["Offer long-term contract discounts during months 1-3.", "Automate high-touch onboarding check-ins for new signups."]	2026-09-24 05:16:59.17957-07
0effd029-ee26-4291-8209-1c1cbc2cd326	a7607514-0838-4878-b90b-2abd54a72e1b	fd3f3a5f-fd11-4f54-8ecf-1f56936c9d58	\N	Revenue Optimization	Electronic Check Payment Friction	Electronic check payment users experience 2.1x higher voluntary attrition compared to credit card auto-pay subscribers.	["Incentivize automatic credit card billing with a 5% monthly rebate.", "Audit payment failure retry logic for ACH and bank transfers."]	2026-09-24 05:16:59.17957-07
\.


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.alembic_version (version_num) FROM stdin;
001_initial_schema
\.


--
-- Data for Name: analysis_jobs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.analysis_jobs (id, dataset_id, user_id, job_type, status, started_at, completed_at, error_message, result_location) FROM stdin;
74a3a86d-08b2-4ad4-9cf2-e0d18e6475ca	fd3f3a5f-fd11-4f54-8ecf-1f56936c9d58	a7607514-0838-4878-b90b-2abd54a72e1b	EXPLORATORY_DATA_ANALYSIS	completed	2026-09-24 17:36:59.144811-07	2026-09-24 17:37:59.144811-07	\N	database:analysis_results
\.


--
-- Data for Name: analysis_results; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.analysis_results (id, job_id, dataset_id, result_type, result_data, created_at) FROM stdin;
e1963e1e-c5a4-4444-9e3a-30ce075dc567	74a3a86d-08b2-4ad4-9cf2-e0d18e6475ca	fd3f3a5f-fd11-4f54-8ecf-1f56936c9d58	EDA_SUMMARY	{"total_records": 608, "total_features": 12, "numeric_features": ["tenure", "MonthlyCharges", "TotalCharges"], "top_correlations": {"tenure_vs_Churn": -0.352, "MonthlyCharges_vs_Churn": 0.193}, "churn_rate_percent": 26.54, "avg_monthly_charges": 64.76}	2026-09-24 05:16:59.154993-07
\.


--
-- Data for Name: audit_logs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.audit_logs (id, user_id, action, resource_type, resource_id, ip_address, user_agent, metadata, created_at) FROM stdin;
3137508d-f5fb-4b2c-babb-f42d9367c6fd	a7607514-0838-4878-b90b-2abd54a72e1b	INITIALIZE_SEED_DATA	system	\N	127.0.0.1	SeedRunner/1.0	{"status": "complete", "environment": "production-ready"}	2026-09-24 05:16:59.199339-07
\.


--
-- Data for Name: dashboards; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.dashboards (id, user_id, dataset_id, dashboard_name, description, configuration, is_public, created_at, updated_at) FROM stdin;
dff83bc3-2acf-435c-bc4d-761c4871f6a2	a7607514-0838-4878-b90b-2abd54a72e1b	fd3f3a5f-fd11-4f54-8ecf-1f56936c9d58	Executive Churn Overview	High-level retention metrics and tenure cohort breakdown.	{"theme": "navy", "layout": "grid", "widgets": [{"type": "metric_card", "title": "Overall Churn Rate", "trend": "-1.4%", "value": "26.5%"}, {"x": "Contract", "y": "ChurnRate", "type": "bar_chart", "title": "Churn by Contract Type"}, {"type": "histogram", "field": "MonthlyCharges", "title": "Monthly Charges Distribution"}]}	t	2026-09-24 05:16:59.167833-07	2026-09-24 05:16:59.167833-07
\.


--
-- Data for Name: data_cleaning_operations; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.data_cleaning_operations (id, dataset_id, user_id, operation_type, column_name, operation_details, rows_affected, status, created_at) FROM stdin;
97f37b6e-0267-4e63-bebf-29c458faa076	fd3f3a5f-fd11-4f54-8ecf-1f56936c9d58	a7607514-0838-4878-b90b-2abd54a72e1b	impute_missing_values	TotalCharges	{"strategy": "median", "fallback_value": 0.0}	11	completed	2026-09-24 05:16:59.124395-07
\.


--
-- Data for Name: dataset_columns; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.dataset_columns (id, dataset_id, column_name, data_type, null_count, unique_count, min_value, max_value, mean_value, median_value, created_at) FROM stdin;
d816f4fc-34e1-4937-ad2b-713782b12d4b	fd3f3a5f-fd11-4f54-8ecf-1f56936c9d58	CustomerID	categorical	0	600	CUST-1000	CUST-1599	\N	\N	2026-09-24 05:16:59.051458-07
71966b2d-d317-4572-8509-42572fc2add3	fd3f3a5f-fd11-4f54-8ecf-1f56936c9d58	SignupDate	categorical	0	71	2018-02-03	2023-12-02	\N	\N	2026-09-24 05:16:59.051458-07
3f145531-fa7f-48d6-8a9f-4de80659c86f	fd3f3a5f-fd11-4f54-8ecf-1f56936c9d58	Gender	categorical	0	3	Female	Prefer not to say	\N	\N	2026-09-24 05:16:59.051458-07
4b7377cc-cbcc-433d-9a2e-e9cb575d4317	fd3f3a5f-fd11-4f54-8ecf-1f56936c9d58	SeniorCitizen	numeric	0	2	0.0	1.0	0.18	0	2026-09-24 05:16:59.051458-07
fca614df-4eab-4993-b479-ee1129294134	fd3f3a5f-fd11-4f54-8ecf-1f56936c9d58	Partner	categorical	19	2	No	Yes	\N	\N	2026-09-24 05:16:59.051458-07
7d6c65b8-96a5-4f4c-8bf5-cf5f55aef837	fd3f3a5f-fd11-4f54-8ecf-1f56936c9d58	TenureMonths	numeric	0	71	1.0	71.0	35.41	35	2026-09-24 05:16:59.051458-07
76bbec43-0bff-4d7b-9068-7003b860a0e6	fd3f3a5f-fd11-4f54-8ecf-1f56936c9d58	Contract	categorical	0	3	Month-to-month	Two year	\N	\N	2026-09-24 05:16:59.051458-07
717145a0-3a33-4b24-abde-366adbdbf02d	fd3f3a5f-fd11-4f54-8ecf-1f56936c9d58	PaperlessBilling	categorical	0	2	No	Yes	\N	\N	2026-09-24 05:16:59.051458-07
ff42a5eb-8153-4c58-838b-53d0e8108fc0	fd3f3a5f-fd11-4f54-8ecf-1f56936c9d58	PaymentMethod	categorical	0	8	  Bank transfer 	Mailed check	\N	\N	2026-09-24 05:16:59.051458-07
98f94926-7112-4990-b220-f8028253cf5e	fd3f3a5f-fd11-4f54-8ecf-1f56936c9d58	MonthlyCharges	numeric	29	520	18.0	125.0	65.27	64.99	2026-09-24 05:16:59.051458-07
496f978e-57d4-46a1-8357-074114d1acb3	fd3f3a5f-fd11-4f54-8ecf-1f56936c9d58	TotalCharges	numeric	44	556	18.0	7896.1	2312.88	1985.29	2026-09-24 05:16:59.051458-07
2e247b96-aa67-49da-a0f6-9d0953db585e	fd3f3a5f-fd11-4f54-8ecf-1f56936c9d58	Churn	categorical	0	2	No	Yes	\N	\N	2026-09-24 05:16:59.051458-07
\.


--
-- Data for Name: datasets; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.datasets (id, user_id, dataset_name, original_filename, file_type, file_size, storage_path, row_count, column_count, description, status, created_at, updated_at) FROM stdin;
fd3f3a5f-fd11-4f54-8ecf-1f56936c9d58	a7607514-0838-4878-b90b-2abd54a72e1b	Customer Churn Analytics	telecom_customer_churn.csv	csv	51025	C:\\Users\\admin\\Downloads\\AI-Powered Data Anlytics Platform\\storage\\datasets\\fd3f3a5f-fd11-4f54-8ecf-1f56936c9d58_telecom_customer_churn.csv	608	12	Telecom customer churn records with tenure, contract type, charges, and churn status.	active	2026-09-24 05:16:58.904512-07	2026-09-24 05:16:58.904512-07
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.users (id, full_name, email, password_hash, role, is_active, created_at, updated_at, last_login) FROM stdin;
a7607514-0838-4878-b90b-2abd54a72e1b	Super Administrator	raj079851@gmail.com	$2b$12$fY8gJievfn5i7hBLqcTo5u1GTF.ZWJuPA.lTzmBOgLk8h0hhreOyW	admin	t	2026-09-24 05:16:57.970859-07	2026-09-24 05:16:57.970859-07	2026-09-24 17:46:58.274546-07
79ac2cd4-eb27-47f3-aa01-37edc0c0931d	Sarah Connor	sarah.connor@datamind.ai	$2b$12$bqNvBOzMa6IX99mMOkJZLOeatlUSItwZaT/5hdtrw4HIvineQHJAy	user	t	2026-09-24 05:16:58.29078-07	2026-09-24 05:16:58.29078-07	2026-09-24 17:46:58.584483-07
44a9e6da-cbb1-4eba-8394-3e1c9c750ec7	Alex Mercer	alex.analyst@datamind.ai	$2b$12$GsFOrGet4ebBp.RMrSIK4OX3pnuKVl2OdTfWOqOBaRa2Tzjo7OHM6	analyst	t	2026-09-24 05:16:58.598908-07	2026-09-24 05:16:58.598908-07	2026-09-24 17:46:58.900636-07
\.


--
-- Name: ai_insights ai_insights_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_insights
    ADD CONSTRAINT ai_insights_pkey PRIMARY KEY (id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: analysis_jobs analysis_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.analysis_jobs
    ADD CONSTRAINT analysis_jobs_pkey PRIMARY KEY (id);


--
-- Name: analysis_results analysis_results_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.analysis_results
    ADD CONSTRAINT analysis_results_pkey PRIMARY KEY (id);


--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (id);


--
-- Name: dashboards dashboards_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dashboards
    ADD CONSTRAINT dashboards_pkey PRIMARY KEY (id);


--
-- Name: data_cleaning_operations data_cleaning_operations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_cleaning_operations
    ADD CONSTRAINT data_cleaning_operations_pkey PRIMARY KEY (id);


--
-- Name: dataset_columns dataset_columns_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dataset_columns
    ADD CONSTRAINT dataset_columns_pkey PRIMARY KEY (id);


--
-- Name: datasets datasets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.datasets
    ADD CONSTRAINT datasets_pkey PRIMARY KEY (id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: idx_ai_insights_dataset_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ai_insights_dataset_id ON public.ai_insights USING btree (dataset_id);


--
-- Name: idx_ai_insights_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ai_insights_user_id ON public.ai_insights USING btree (user_id);


--
-- Name: idx_analysis_jobs_dataset_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_analysis_jobs_dataset_id ON public.analysis_jobs USING btree (dataset_id);


--
-- Name: idx_analysis_jobs_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_analysis_jobs_user_id ON public.analysis_jobs USING btree (user_id);


--
-- Name: idx_analysis_jobs_user_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_analysis_jobs_user_status ON public.analysis_jobs USING btree (user_id, status);


--
-- Name: idx_analysis_results_dataset_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_analysis_results_dataset_id ON public.analysis_results USING btree (dataset_id);


--
-- Name: idx_analysis_results_job_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_analysis_results_job_id ON public.analysis_results USING btree (job_id);


--
-- Name: idx_audit_logs_action_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_logs_action_created ON public.audit_logs USING btree (action, created_at);


--
-- Name: idx_audit_logs_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_logs_created_at ON public.audit_logs USING btree (created_at);


--
-- Name: idx_audit_logs_user_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_logs_user_created ON public.audit_logs USING btree (user_id, created_at);


--
-- Name: idx_audit_logs_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_logs_user_id ON public.audit_logs USING btree (user_id);


--
-- Name: idx_cleaning_dataset_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cleaning_dataset_id ON public.data_cleaning_operations USING btree (dataset_id);


--
-- Name: idx_cleaning_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cleaning_user_id ON public.data_cleaning_operations USING btree (user_id);


--
-- Name: idx_dashboards_dataset_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_dashboards_dataset_id ON public.dashboards USING btree (dataset_id);


--
-- Name: idx_dashboards_user_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_dashboards_user_created ON public.dashboards USING btree (user_id, created_at);


--
-- Name: idx_dashboards_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_dashboards_user_id ON public.dashboards USING btree (user_id);


--
-- Name: idx_dataset_columns_dataset_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_dataset_columns_dataset_id ON public.dataset_columns USING btree (dataset_id);


--
-- Name: idx_dataset_columns_lookup; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_dataset_columns_lookup ON public.dataset_columns USING btree (dataset_id, column_name);


--
-- Name: idx_datasets_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_datasets_created_at ON public.datasets USING btree (created_at);


--
-- Name: idx_datasets_user_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_datasets_user_created ON public.datasets USING btree (user_id, created_at);


--
-- Name: idx_datasets_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_datasets_user_id ON public.datasets USING btree (user_id);


--
-- Name: idx_insights_user_dataset; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_insights_user_dataset ON public.ai_insights USING btree (user_id, dataset_id);


--
-- Name: idx_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_email ON public.users USING btree (email);


--
-- Name: idx_users_role; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_role ON public.users USING btree (role);


--
-- Name: dashboards update_dashboards_modtime; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_dashboards_modtime BEFORE UPDATE ON public.dashboards FOR EACH ROW EXECUTE FUNCTION public.update_timestamp_column();


--
-- Name: datasets update_datasets_modtime; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_datasets_modtime BEFORE UPDATE ON public.datasets FOR EACH ROW EXECUTE FUNCTION public.update_timestamp_column();


--
-- Name: users update_users_modtime; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_users_modtime BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.update_timestamp_column();


--
-- Name: ai_insights ai_insights_analysis_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_insights
    ADD CONSTRAINT ai_insights_analysis_id_fkey FOREIGN KEY (analysis_id) REFERENCES public.analysis_jobs(id) ON DELETE SET NULL;


--
-- Name: ai_insights ai_insights_dataset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_insights
    ADD CONSTRAINT ai_insights_dataset_id_fkey FOREIGN KEY (dataset_id) REFERENCES public.datasets(id) ON DELETE CASCADE;


--
-- Name: ai_insights ai_insights_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_insights
    ADD CONSTRAINT ai_insights_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: analysis_jobs analysis_jobs_dataset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.analysis_jobs
    ADD CONSTRAINT analysis_jobs_dataset_id_fkey FOREIGN KEY (dataset_id) REFERENCES public.datasets(id) ON DELETE CASCADE;


--
-- Name: analysis_jobs analysis_jobs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.analysis_jobs
    ADD CONSTRAINT analysis_jobs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: analysis_results analysis_results_dataset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.analysis_results
    ADD CONSTRAINT analysis_results_dataset_id_fkey FOREIGN KEY (dataset_id) REFERENCES public.datasets(id) ON DELETE CASCADE;


--
-- Name: analysis_results analysis_results_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.analysis_results
    ADD CONSTRAINT analysis_results_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.analysis_jobs(id) ON DELETE CASCADE;


--
-- Name: audit_logs audit_logs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: dashboards dashboards_dataset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dashboards
    ADD CONSTRAINT dashboards_dataset_id_fkey FOREIGN KEY (dataset_id) REFERENCES public.datasets(id) ON DELETE SET NULL;


--
-- Name: dashboards dashboards_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dashboards
    ADD CONSTRAINT dashboards_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: data_cleaning_operations data_cleaning_operations_dataset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_cleaning_operations
    ADD CONSTRAINT data_cleaning_operations_dataset_id_fkey FOREIGN KEY (dataset_id) REFERENCES public.datasets(id) ON DELETE CASCADE;


--
-- Name: data_cleaning_operations data_cleaning_operations_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_cleaning_operations
    ADD CONSTRAINT data_cleaning_operations_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: dataset_columns dataset_columns_dataset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dataset_columns
    ADD CONSTRAINT dataset_columns_dataset_id_fkey FOREIGN KEY (dataset_id) REFERENCES public.datasets(id) ON DELETE CASCADE;


--
-- Name: datasets datasets_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.datasets
    ADD CONSTRAINT datasets_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: ai_insights; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.ai_insights ENABLE ROW LEVEL SECURITY;

--
-- Name: dashboards; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.dashboards ENABLE ROW LEVEL SECURITY;

--
-- Name: datasets; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.datasets ENABLE ROW LEVEL SECURITY;

--
-- Name: dashboards user_dashboard_isolation_policy; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY user_dashboard_isolation_policy ON public.dashboards USING ((((user_id)::text = current_setting('app.current_user_id'::text, true)) OR (is_public = true) OR (current_setting('app.is_admin'::text, true) = 'true'::text)));


--
-- Name: datasets user_dataset_isolation_policy; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY user_dataset_isolation_policy ON public.datasets USING ((((user_id)::text = current_setting('app.current_user_id'::text, true)) OR (current_setting('app.is_admin'::text, true) = 'true'::text)));


--
-- PostgreSQL database dump complete
--

\unrestrict nc7nU5sSBq0bOHtJCWWT8DOyq5BUpyUyMDDMoPelDAV3cwvBRN8Wu6iJQN76hvh

