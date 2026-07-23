CREATE TABLE IF NOT EXISTS candidates (
    id uuid PRIMARY KEY,
    project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    dataset_version_id uuid NOT NULL REFERENCES dataset_versions(id) ON DELETE CASCADE,
    analysis_run_id uuid REFERENCES analysis_runs(id) ON DELETE SET NULL,
    source_cluster_id uuid REFERENCES clusters(id) ON DELETE SET NULL,
    candidate_type text NOT NULL,
    auto_status text NOT NULL DEFAULT 'unreviewed',
    manual_status text,
    language text NOT NULL DEFAULT 'de',
    auto_category_path text,
    manual_category_path text,
    auto_title text NOT NULL,
    manual_title text,
    auto_canonical_question text NOT NULL,
    manual_canonical_question text,
    auto_canonical_answer text NOT NULL,
    manual_canonical_answer text,
    auto_alternative_questions jsonb NOT NULL DEFAULT '[]'::jsonb,
    manual_alternative_questions jsonb,
    auto_parameters jsonb NOT NULL DEFAULT '{}'::jsonb,
    manual_parameters jsonb,
    auto_external_data_dependencies jsonb NOT NULL DEFAULT '[]'::jsonb,
    manual_external_data_dependencies jsonb,
    quality_score double precision NOT NULL DEFAULT 0,
    faq_suitability_score double precision NOT NULL DEFAULT 0,
    dynamicity_score double precision NOT NULL DEFAULT 0,
    contradiction_score double precision NOT NULL DEFAULT 0,
    notes text,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_by_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT candidates_type_check CHECK (
        candidate_type IN (
            'static_faq',
            'parameterized_faq',
            'dynamic_case',
            'text_block',
            'single_case',
            'not_usable'
        )
    ),
    CONSTRAINT candidates_auto_status_check CHECK (
        auto_status IN ('unreviewed', 'in_progress', 'reviewed', 'rejected', 'export_ready')
    ),
    CONSTRAINT candidates_manual_status_check CHECK (
        manual_status IS NULL OR manual_status IN (
            'unreviewed',
            'in_progress',
            'reviewed',
            'rejected',
            'export_ready'
        )
    ),
    CONSTRAINT candidates_auto_title_nonempty_check CHECK (length(btrim(auto_title)) > 0),
    CONSTRAINT candidates_question_nonempty_check CHECK (
        length(btrim(auto_canonical_question)) > 0
    ),
    CONSTRAINT candidates_answer_nonempty_check CHECK (
        length(btrim(auto_canonical_answer)) > 0
    ),
    CONSTRAINT candidates_auto_alt_questions_array_check CHECK (
        jsonb_typeof(auto_alternative_questions) = 'array'
    ),
    CONSTRAINT candidates_manual_alt_questions_array_check CHECK (
        manual_alternative_questions IS NULL
        OR jsonb_typeof(manual_alternative_questions) = 'array'
    ),
    CONSTRAINT candidates_auto_parameters_object_check CHECK (
        jsonb_typeof(auto_parameters) = 'object'
    ),
    CONSTRAINT candidates_manual_parameters_object_check CHECK (
        manual_parameters IS NULL OR jsonb_typeof(manual_parameters) = 'object'
    ),
    CONSTRAINT candidates_auto_dependencies_array_check CHECK (
        jsonb_typeof(auto_external_data_dependencies) = 'array'
    ),
    CONSTRAINT candidates_manual_dependencies_array_check CHECK (
        manual_external_data_dependencies IS NULL
        OR jsonb_typeof(manual_external_data_dependencies) = 'array'
    ),
    CONSTRAINT candidates_source_cluster_unique UNIQUE (project_id, source_cluster_id)
);

CREATE TABLE IF NOT EXISTS candidate_source_assignments (
    id uuid PRIMARY KEY,
    project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    candidate_id uuid NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    cluster_id uuid REFERENCES clusters(id) ON DELETE SET NULL,
    message_pair_id uuid NOT NULL REFERENCES message_pairs(id) ON DELETE CASCADE,
    dataset_version_id uuid NOT NULL REFERENCES dataset_versions(id) ON DELETE CASCADE,
    analysis_run_id uuid REFERENCES analysis_runs(id) ON DELETE SET NULL,
    message_segment_id text,
    source_language text NOT NULL DEFAULT 'unknown',
    normalized_customer_message text,
    normalized_support_answer text,
    assignment_type text NOT NULL DEFAULT 'automatic',
    membership_score double precision NOT NULL DEFAULT 1,
    is_multi_intent boolean NOT NULL DEFAULT false,
    intent_label text,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT candidate_source_assignments_type_check CHECK (
        assignment_type IN ('automatic', 'manual')
    ),
    CONSTRAINT candidate_source_assignments_unique_pair UNIQUE (
        candidate_id,
        message_pair_id
    )
);

CREATE INDEX IF NOT EXISTS idx_candidates_project_updated
ON candidates (project_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_candidates_project_status
ON candidates (project_id, auto_status, manual_status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_candidate_sources_candidate
ON candidate_source_assignments (project_id, candidate_id);

CREATE INDEX IF NOT EXISTS idx_candidate_sources_pair
ON candidate_source_assignments (message_pair_id);
