CREATE TABLE IF NOT EXISTS provider_configurations (
    provider text PRIMARY KEY,
    endpoint_url text,
    api_key_secret text,
    manual_models jsonb NOT NULL DEFAULT '[]'::jsonb,
    created_by_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
    updated_by_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT provider_configurations_provider_check CHECK (
        provider IN ('openai', 'ollama', 'vllm')
    ),
    CONSTRAINT provider_configurations_manual_models_array_check CHECK (
        jsonb_typeof(manual_models) = 'array'
    )
);

CREATE TABLE IF NOT EXISTS analysis_profiles (
    id uuid PRIMARY KEY,
    project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name text NOT NULL,
    provider text NOT NULL,
    model text NOT NULL,
    is_cloud_provider boolean NOT NULL,
    thresholds jsonb NOT NULL DEFAULT '{}'::jsonb,
    algorithm_settings jsonb NOT NULL DEFAULT '{}'::jsonb,
    prompt_identifier text,
    prompt_template text,
    created_by_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
    updated_by_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT analysis_profiles_provider_check CHECK (
        provider IN ('openai', 'ollama', 'vllm')
    ),
    CONSTRAINT analysis_profiles_name_nonempty_check CHECK (length(btrim(name)) > 0),
    CONSTRAINT analysis_profiles_model_nonempty_check CHECK (length(btrim(model)) > 0),
    CONSTRAINT analysis_profiles_thresholds_object_check CHECK (
        jsonb_typeof(thresholds) = 'object'
    ),
    CONSTRAINT analysis_profiles_algorithm_settings_object_check CHECK (
        jsonb_typeof(algorithm_settings) = 'object'
    ),
    CONSTRAINT analysis_profiles_project_name_unique UNIQUE (project_id, name)
);

CREATE INDEX IF NOT EXISTS idx_analysis_profiles_project_updated
ON analysis_profiles (project_id, updated_at DESC);
