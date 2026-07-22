CREATE TABLE IF NOT EXISTS import_logs (
    id uuid PRIMARY KEY,
    project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    source_type text NOT NULL,
    source_name text NOT NULL,
    status text NOT NULL,
    failure_reason text,
    total_records integer NOT NULL DEFAULT 0,
    valid_records integer NOT NULL DEFAULT 0,
    skipped_records integer NOT NULL DEFAULT 0,
    dataset_version_id uuid,
    started_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz NOT NULL DEFAULT now(),
    created_by_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT import_logs_source_type_check CHECK (source_type IN ('csv', 'json')),
    CONSTRAINT import_logs_status_check CHECK (status IN ('completed', 'failed')),
    CONSTRAINT import_logs_counts_nonnegative_check CHECK (
        total_records >= 0 AND valid_records >= 0 AND skipped_records >= 0
    )
);

CREATE TABLE IF NOT EXISTS dataset_versions (
    id uuid PRIMARY KEY,
    project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    version_number integer NOT NULL,
    import_log_id uuid NOT NULL UNIQUE REFERENCES import_logs(id) ON DELETE RESTRICT,
    record_count integer NOT NULL,
    source_type text NOT NULL,
    source_name text NOT NULL,
    created_by_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT dataset_versions_record_count_positive_check CHECK (record_count > 0),
    CONSTRAINT dataset_versions_source_type_check CHECK (source_type IN ('csv', 'json')),
    CONSTRAINT dataset_versions_project_version_unique UNIQUE (project_id, version_number)
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'import_logs_dataset_version_fk'
    ) THEN
        ALTER TABLE import_logs
        ADD CONSTRAINT import_logs_dataset_version_fk
        FOREIGN KEY (dataset_version_id)
        REFERENCES dataset_versions(id)
        ON DELETE SET NULL;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS message_pairs (
    id uuid PRIMARY KEY,
    project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    dataset_version_id uuid NOT NULL REFERENCES dataset_versions(id) ON DELETE CASCADE,
    ordinal integer NOT NULL,
    ticketid text NOT NULL,
    messagegroupid text NOT NULL,
    message text NOT NULL,
    answer text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT message_pairs_message_nonempty_check CHECK (length(btrim(message)) > 0),
    CONSTRAINT message_pairs_answer_nonempty_check CHECK (length(btrim(answer)) > 0),
    CONSTRAINT message_pairs_dataset_ordinal_unique UNIQUE (dataset_version_id, ordinal)
);

CREATE TABLE IF NOT EXISTS import_log_entries (
    id uuid PRIMARY KEY,
    import_log_id uuid NOT NULL REFERENCES import_logs(id) ON DELETE CASCADE,
    source_location text NOT NULL,
    reason text NOT NULL,
    context jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_dataset_versions_project_created
ON dataset_versions (project_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_message_pairs_project_dataset
ON message_pairs (project_id, dataset_version_id, ordinal);

CREATE INDEX IF NOT EXISTS idx_import_logs_project_started
ON import_logs (project_id, started_at DESC);
