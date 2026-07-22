CREATE TABLE IF NOT EXISTS projects (
    id uuid PRIMARY KEY,
    name text NOT NULL,
    lifecycle_state text NOT NULL DEFAULT 'active',
    created_by_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
    updated_by_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    deleted_at timestamptz,
    CONSTRAINT projects_lifecycle_state_check
        CHECK (lifecycle_state IN ('active'))
);

CREATE INDEX IF NOT EXISTS idx_projects_active_updated
ON projects (updated_at DESC)
WHERE deleted_at IS NULL;
