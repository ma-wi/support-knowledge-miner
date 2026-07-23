CREATE TABLE IF NOT EXISTS export_logs (
    id uuid PRIMARY KEY,
    project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    export_type text NOT NULL,
    include_original_text boolean NOT NULL DEFAULT false,
    filters jsonb NOT NULL DEFAULT '{}'::jsonb,
    selection jsonb NOT NULL DEFAULT '{}'::jsonb,
    dataset_version_id uuid REFERENCES dataset_versions(id) ON DELETE SET NULL,
    analysis_run_id uuid REFERENCES analysis_runs(id) ON DELETE SET NULL,
    output_filename text NOT NULL,
    output_path text,
    row_count integer NOT NULL DEFAULT 0,
    created_by_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT export_logs_type_check CHECK (
        export_type IN ('candidate_csv', 'source_assignment_csv')
    ),
    CONSTRAINT export_logs_row_count_nonnegative_check CHECK (row_count >= 0),
    CONSTRAINT export_logs_output_filename_nonempty_check CHECK (
        length(btrim(output_filename)) > 0
    )
);

CREATE INDEX IF NOT EXISTS idx_export_logs_project_created
ON export_logs (project_id, created_at DESC);
