-- CHG-004 T4/T5 Explorer export replaces obsolete candidate exports.

DELETE FROM export_logs
WHERE export_type IN ('candidate_csv', 'source_assignment_csv');

DROP TABLE IF EXISTS candidate_source_assignments;
DROP TABLE IF EXISTS candidates;

ALTER TABLE export_logs
    ADD COLUMN IF NOT EXISTS cluster_set_id uuid REFERENCES cluster_sets(id) ON DELETE SET NULL;

ALTER TABLE export_logs
    DROP CONSTRAINT IF EXISTS export_logs_type_check;

ALTER TABLE export_logs
    ADD CONSTRAINT export_logs_type_check CHECK (
        export_type IN ('explorer_csv', 'explorer_json')
    );

CREATE INDEX IF NOT EXISTS idx_export_logs_project_cluster_set_created
ON export_logs (project_id, cluster_set_id, created_at DESC);
