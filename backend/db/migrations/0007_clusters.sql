CREATE TABLE IF NOT EXISTS clusters (
    id uuid PRIMARY KEY,
    project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    analysis_run_id uuid NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    dataset_version_id uuid NOT NULL REFERENCES dataset_versions(id) ON DELETE CASCADE,
    auto_title text NOT NULL,
    manual_title text,
    auto_category text,
    manual_category text,
    auto_status text NOT NULL DEFAULT 'unreviewed',
    manual_status text,
    score double precision NOT NULL DEFAULT 0,
    is_outlier boolean NOT NULL DEFAULT false,
    algorithm text NOT NULL,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT clusters_auto_title_nonempty_check CHECK (length(btrim(auto_title)) > 0),
    CONSTRAINT clusters_auto_status_check CHECK (
        auto_status IN ('unreviewed', 'in_progress', 'reviewed', 'rejected', 'outlier')
    ),
    CONSTRAINT clusters_manual_status_check CHECK (
        manual_status IS NULL OR manual_status IN ('unreviewed', 'in_progress', 'reviewed', 'rejected', 'outlier')
    )
);

CREATE TABLE IF NOT EXISTS cluster_memberships (
    id uuid PRIMARY KEY,
    project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    cluster_id uuid NOT NULL REFERENCES clusters(id) ON DELETE CASCADE,
    analysis_run_id uuid NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    message_pair_id uuid NOT NULL REFERENCES message_pairs(id) ON DELETE CASCADE,
    membership_score double precision NOT NULL DEFAULT 1,
    is_outlier boolean NOT NULL DEFAULT false,
    assignment_type text NOT NULL DEFAULT 'automatic',
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT cluster_memberships_assignment_type_check CHECK (
        assignment_type IN ('automatic', 'manual')
    ),
    CONSTRAINT cluster_memberships_pair_unique UNIQUE (analysis_run_id, message_pair_id)
);

CREATE INDEX IF NOT EXISTS idx_clusters_project_run
ON clusters (project_id, analysis_run_id, is_outlier, score DESC);

CREATE INDEX IF NOT EXISTS idx_cluster_memberships_cluster
ON cluster_memberships (project_id, cluster_id);

CREATE INDEX IF NOT EXISTS idx_cluster_memberships_pair
ON cluster_memberships (message_pair_id);
