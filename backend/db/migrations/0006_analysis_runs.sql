CREATE TABLE IF NOT EXISTS analysis_runs (
    id uuid PRIMARY KEY,
    project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    dataset_version_id uuid NOT NULL REFERENCES dataset_versions(id) ON DELETE RESTRICT,
    analysis_profile_id uuid NOT NULL REFERENCES analysis_profiles(id) ON DELETE RESTRICT,
    status text NOT NULL,
    progress integer NOT NULL DEFAULT 0,
    profile_snapshot jsonb NOT NULL,
    provider text NOT NULL,
    model text NOT NULL,
    parameters jsonb NOT NULL DEFAULT '{}'::jsonb,
    error_message text,
    diagnostics jsonb NOT NULL DEFAULT '{}'::jsonb,
    started_at timestamptz,
    completed_at timestamptz,
    created_by_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT analysis_runs_status_check CHECK (
        status IN ('queued', 'running', 'completed', 'failed', 'cancelled')
    ),
    CONSTRAINT analysis_runs_progress_range_check CHECK (
        progress >= 0 AND progress <= 100
    ),
    CONSTRAINT analysis_runs_provider_check CHECK (
        provider IN ('openai', 'ollama', 'vllm')
    ),
    CONSTRAINT analysis_runs_profile_snapshot_object_check CHECK (
        jsonb_typeof(profile_snapshot) = 'object'
    ),
    CONSTRAINT analysis_runs_parameters_object_check CHECK (
        jsonb_typeof(parameters) = 'object'
    ),
    CONSTRAINT analysis_runs_diagnostics_object_check CHECK (
        jsonb_typeof(diagnostics) = 'object'
    )
);

CREATE TABLE IF NOT EXISTS embeddings (
    id uuid PRIMARY KEY,
    project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    analysis_run_id uuid NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    dataset_version_id uuid NOT NULL REFERENCES dataset_versions(id) ON DELETE CASCADE,
    analysis_profile_id uuid NOT NULL REFERENCES analysis_profiles(id) ON DELETE RESTRICT,
    source_object_type text NOT NULL,
    source_object_id uuid NOT NULL,
    text_variant text NOT NULL,
    model text NOT NULL,
    dimensions integer NOT NULL,
    embedding vector,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT embeddings_dimensions_positive_check CHECK (dimensions > 0),
    CONSTRAINT embeddings_source_object_type_check CHECK (
        source_object_type IN ('message_pair')
    ),
    CONSTRAINT embeddings_text_variant_check CHECK (
        text_variant IN ('message', 'answer')
    )
);

CREATE INDEX IF NOT EXISTS idx_analysis_runs_project_created
ON analysis_runs (project_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_analysis_runs_project_status
ON analysis_runs (project_id, status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_embeddings_project_run
ON embeddings (project_id, analysis_run_id);

CREATE INDEX IF NOT EXISTS idx_embeddings_source
ON embeddings (source_object_type, source_object_id, text_variant);
