CREATE TABLE IF NOT EXISTS users (
    id uuid PRIMARY KEY,
    username text NOT NULL UNIQUE,
    first_name text NOT NULL,
    last_name text NOT NULL,
    email text NOT NULL UNIQUE,
    password_hash text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    deleted_at timestamptz
);

CREATE INDEX IF NOT EXISTS idx_users_active_username
ON users (username)
WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS user_sessions (
    id uuid PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash text NOT NULL UNIQUE,
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz
);

CREATE INDEX IF NOT EXISTS idx_user_sessions_active_token_hash
ON user_sessions (token_hash)
WHERE revoked_at IS NULL;

CREATE TABLE IF NOT EXISTS audit_events (
    id uuid PRIMARY KEY,
    actor_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
    action text NOT NULL,
    target_type text NOT NULL,
    target_id text,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_events_actor_created
ON audit_events (actor_user_id, created_at DESC);
