CREATE TABLE IF NOT EXISTS cluster_sets (
    id uuid PRIMARY KEY,
    project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    indexing_run_id uuid NOT NULL REFERENCES analysis_runs(id) ON DELETE RESTRICT,
    dataset_version_id uuid NOT NULL REFERENCES dataset_versions(id) ON DELETE RESTRICT,
    parent_cluster_set_id uuid REFERENCES cluster_sets(id) ON DELETE SET NULL,
    display_name text NOT NULL,
    status text NOT NULL DEFAULT 'queued',
    progress integer NOT NULL DEFAULT 0,
    phase text NOT NULL DEFAULT 'queued',
    derivation_type text NOT NULL DEFAULT 'root',
    vector_basis text NOT NULL,
    message_weight double precision NOT NULL DEFAULT 0.5,
    answer_weight double precision NOT NULL DEFAULT 0.5,
    algorithm text NOT NULL,
    parameters jsonb NOT NULL DEFAULT '{}'::jsonb,
    source_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
    llm_provider text,
    llm_model text,
    llm_parameters jsonb NOT NULL DEFAULT '{}'::jsonb,
    llm_sample_strategy jsonb NOT NULL DEFAULT '{}'::jsonb,
    error_code text,
    error_message text,
    diagnostics jsonb NOT NULL DEFAULT '{}'::jsonb,
    started_at timestamptz,
    completed_at timestamptz,
    cancel_requested_at timestamptz,
    deleted_at timestamptz,
    deleted_by_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
    created_by_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT cluster_sets_display_name_nonempty_check CHECK (
        length(btrim(display_name)) > 0
    ),
    CONSTRAINT cluster_sets_status_check CHECK (
        status IN ('queued', 'running', 'cancelling', 'completed', 'failed', 'cancelled')
    ),
    CONSTRAINT cluster_sets_progress_range_check CHECK (
        progress >= 0 AND progress <= 100
    ),
    CONSTRAINT cluster_sets_phase_nonempty_check CHECK (length(btrim(phase)) > 0),
    CONSTRAINT cluster_sets_derivation_type_check CHECK (
        derivation_type IN ('root', 'refinement', 'outlier_exclusion', 'manual_edit')
    ),
    CONSTRAINT cluster_sets_vector_basis_check CHECK (
        vector_basis IN ('message', 'answer', 'combined')
    ),
    CONSTRAINT cluster_sets_weights_check CHECK (
        message_weight >= 0 AND answer_weight >= 0 AND message_weight + answer_weight > 0
    ),
    CONSTRAINT cluster_sets_algorithm_nonempty_check CHECK (length(btrim(algorithm)) > 0),
    CONSTRAINT cluster_sets_parameters_object_check CHECK (
        jsonb_typeof(parameters) = 'object'
    ),
    CONSTRAINT cluster_sets_source_snapshot_object_check CHECK (
        jsonb_typeof(source_snapshot) = 'object'
    ),
    CONSTRAINT cluster_sets_llm_provider_check CHECK (
        llm_provider IS NULL OR llm_provider IN ('openai', 'ollama')
    ),
    CONSTRAINT cluster_sets_llm_parameters_object_check CHECK (
        jsonb_typeof(llm_parameters) = 'object'
    ),
    CONSTRAINT cluster_sets_llm_sample_strategy_object_check CHECK (
        jsonb_typeof(llm_sample_strategy) = 'object'
    ),
    CONSTRAINT cluster_sets_diagnostics_object_check CHECK (
        jsonb_typeof(diagnostics) = 'object'
    )
);

ALTER TABLE provider_configurations
    ADD COLUMN IF NOT EXISTS embedding_models jsonb NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS llm_models jsonb NOT NULL DEFAULT '[]'::jsonb;

UPDATE provider_configurations
SET embedding_models = manual_models
WHERE embedding_models = '[]'::jsonb
  AND manual_models <> '[]'::jsonb;

UPDATE provider_configurations
SET llm_models = manual_models
WHERE provider IN ('openai', 'ollama')
  AND llm_models = '[]'::jsonb
  AND manual_models <> '[]'::jsonb;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'provider_configurations_embedding_models_array_check'
    ) THEN
        ALTER TABLE provider_configurations
        ADD CONSTRAINT provider_configurations_embedding_models_array_check
        CHECK (jsonb_typeof(embedding_models) = 'array');
    END IF;
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'provider_configurations_llm_models_array_check'
    ) THEN
        ALTER TABLE provider_configurations
        ADD CONSTRAINT provider_configurations_llm_models_array_check
        CHECK (jsonb_typeof(llm_models) = 'array');
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS cluster_set_events (
    id uuid PRIMARY KEY,
    project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    cluster_set_id uuid NOT NULL REFERENCES cluster_sets(id) ON DELETE CASCADE,
    event_type text NOT NULL,
    actor_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT cluster_set_events_type_nonempty_check CHECK (
        length(btrim(event_type)) > 0
    ),
    CONSTRAINT cluster_set_events_metadata_object_check CHECK (
        jsonb_typeof(metadata) = 'object'
    )
);

ALTER TABLE clusters
    ADD COLUMN IF NOT EXISTS cluster_set_id uuid REFERENCES cluster_sets(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS auto_summary_question text,
    ADD COLUMN IF NOT EXISTS auto_summary_answer text;

ALTER TABLE cluster_memberships
    ADD COLUMN IF NOT EXISTS cluster_set_id uuid REFERENCES cluster_sets(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS metadata jsonb NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE cluster_memberships
    DROP CONSTRAINT IF EXISTS cluster_memberships_pair_unique;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'cluster_memberships_set_pair_unique'
    ) THEN
        ALTER TABLE cluster_memberships
        ADD CONSTRAINT cluster_memberships_set_pair_unique
        UNIQUE (cluster_set_id, message_pair_id);
    END IF;
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'cluster_memberships_metadata_object_check'
    ) THEN
        ALTER TABLE cluster_memberships
        ADD CONSTRAINT cluster_memberships_metadata_object_check
        CHECK (jsonb_typeof(metadata) = 'object');
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_cluster_sets_project_active_created
ON cluster_sets (project_id, deleted_at, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_cluster_sets_project_indexing
ON cluster_sets (project_id, indexing_run_id, deleted_at, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_cluster_sets_parent
ON cluster_sets (project_id, parent_cluster_set_id, created_at ASC);

CREATE INDEX IF NOT EXISTS idx_cluster_set_events_set
ON cluster_set_events (project_id, cluster_set_id, created_at ASC);

CREATE INDEX IF NOT EXISTS idx_clusters_project_set
ON clusters (project_id, cluster_set_id, is_outlier, score DESC);

CREATE INDEX IF NOT EXISTS idx_cluster_memberships_set
ON cluster_memberships (project_id, cluster_set_id, cluster_id);
