-- CHG-004 T2 destructive local derived-data migration.
-- Retains projects, users, provider configurations, imports and dataset versions.
-- Drops profile/run/embedding/cluster/candidate derived data accepted as obsolete.

UPDATE export_logs
SET analysis_run_id = NULL
WHERE analysis_run_id IS NOT NULL;

ALTER TABLE export_logs
    DROP CONSTRAINT IF EXISTS export_logs_analysis_run_id_fkey;

TRUNCATE TABLE
    candidate_source_assignments,
    candidates,
    cluster_memberships,
    clusters,
    embeddings,
    analysis_runs;

ALTER TABLE dataset_versions
    ADD COLUMN IF NOT EXISTS display_name text,
    ADD COLUMN IF NOT EXISTS deleted_at timestamptz,
    ADD COLUMN IF NOT EXISTS deleted_by_user_id uuid REFERENCES users(id) ON DELETE SET NULL;

UPDATE dataset_versions
SET display_name = source_name
WHERE display_name IS NULL;

ALTER TABLE dataset_versions
    ALTER COLUMN display_name SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'dataset_versions_display_name_nonempty_check'
    ) THEN
        ALTER TABLE dataset_versions
        ADD CONSTRAINT dataset_versions_display_name_nonempty_check
        CHECK (length(btrim(display_name)) > 0);
    END IF;
END $$;

ALTER TABLE analysis_runs
    DROP CONSTRAINT IF EXISTS analysis_runs_analysis_profile_id_fkey,
    DROP CONSTRAINT IF EXISTS analysis_runs_status_check,
    DROP CONSTRAINT IF EXISTS analysis_runs_profile_snapshot_object_check;

ALTER TABLE embeddings
    DROP CONSTRAINT IF EXISTS embeddings_analysis_profile_id_fkey;

ALTER TABLE analysis_runs
    DROP COLUMN IF EXISTS analysis_profile_id,
    DROP COLUMN IF EXISTS profile_snapshot,
    ADD COLUMN IF NOT EXISTS phase text NOT NULL DEFAULT 'queued',
    ADD COLUMN IF NOT EXISTS error_code text,
    ADD COLUMN IF NOT EXISTS cancel_requested_at timestamptz,
    ADD COLUMN IF NOT EXISTS deleted_at timestamptz,
    ADD COLUMN IF NOT EXISTS deleted_by_user_id uuid REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE embeddings
    DROP COLUMN IF EXISTS analysis_profile_id;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'analysis_runs_status_check'
    ) THEN
        ALTER TABLE analysis_runs
        ADD CONSTRAINT analysis_runs_status_check
        CHECK (
            status IN (
                'queued',
                'running',
                'cancelling',
                'completed',
                'failed',
                'cancelled'
            )
        );
    END IF;
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'analysis_runs_phase_nonempty_check'
    ) THEN
        ALTER TABLE analysis_runs
        ADD CONSTRAINT analysis_runs_phase_nonempty_check
        CHECK (length(btrim(phase)) > 0);
    END IF;
END $$;

DROP TABLE IF EXISTS analysis_profiles;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'export_logs_analysis_run_id_fkey'
    ) THEN
        ALTER TABLE export_logs
        ADD CONSTRAINT export_logs_analysis_run_id_fkey
        FOREIGN KEY (analysis_run_id)
        REFERENCES analysis_runs(id)
        ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_dataset_versions_project_deleted
ON dataset_versions (project_id, deleted_at, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_analysis_runs_project_active_created
ON analysis_runs (project_id, deleted_at, created_at DESC);
