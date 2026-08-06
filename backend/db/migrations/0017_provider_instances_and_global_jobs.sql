-- CHG-005: provider instances, active vLLM removal and provenance snapshots.

ALTER TABLE provider_configurations
    ADD COLUMN IF NOT EXISTS id uuid,
    ADD COLUMN IF NOT EXISTS display_name text;

UPDATE provider_configurations
SET id = CASE provider
    WHEN 'openai' THEN '00000000-0000-0000-0000-000000000001'::uuid
    WHEN 'ollama' THEN '00000000-0000-0000-0000-000000000002'::uuid
    WHEN 'vllm' THEN '00000000-0000-0000-0000-000000000003'::uuid
    ELSE id
END
WHERE id IS NULL;

UPDATE provider_configurations
SET display_name = CASE provider
    WHEN 'openai' THEN 'OpenAI'
    WHEN 'ollama' THEN 'Ollama'
    ELSE provider
END
WHERE display_name IS NULL;

DELETE FROM provider_configurations
WHERE provider = 'vllm';

ALTER TABLE provider_configurations
    ALTER COLUMN id SET NOT NULL,
    ALTER COLUMN display_name SET NOT NULL;

ALTER TABLE provider_configurations
    DROP CONSTRAINT IF EXISTS provider_configurations_pkey,
    DROP CONSTRAINT IF EXISTS provider_configurations_provider_check;

ALTER TABLE provider_configurations
    ADD CONSTRAINT provider_configurations_pkey PRIMARY KEY (id),
    ADD CONSTRAINT provider_configurations_provider_check CHECK (
        provider IN ('openai', 'ollama')
    );

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'provider_configurations_display_name_nonempty_check'
    ) THEN
        ALTER TABLE provider_configurations
        ADD CONSTRAINT provider_configurations_display_name_nonempty_check
        CHECK (length(btrim(display_name)) > 0);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_provider_configurations_provider_created
ON provider_configurations (provider, created_at ASC);

ALTER TABLE analysis_runs
    ADD COLUMN IF NOT EXISTS provider_configuration_id uuid REFERENCES provider_configurations(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS provider_display_name text;

UPDATE analysis_runs ar
SET provider_configuration_id = pc.id
FROM provider_configurations pc
WHERE ar.provider_configuration_id IS NULL
  AND ar.provider = pc.provider;

UPDATE analysis_runs
SET provider_display_name = CASE provider
    WHEN 'openai' THEN 'OpenAI'
    WHEN 'ollama' THEN 'Ollama'
    ELSE provider
END
WHERE provider_display_name IS NULL;

ALTER TABLE cluster_sets
    ADD COLUMN IF NOT EXISTS llm_provider_configuration_id uuid REFERENCES provider_configurations(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS llm_provider_display_name text;

UPDATE cluster_sets cs
SET llm_provider_configuration_id = pc.id
FROM provider_configurations pc
WHERE cs.llm_provider_configuration_id IS NULL
  AND cs.llm_provider = pc.provider;

UPDATE cluster_sets
SET llm_provider_display_name = CASE llm_provider
    WHEN 'openai' THEN 'OpenAI'
    WHEN 'ollama' THEN 'Ollama'
    ELSE llm_provider
END
WHERE llm_provider IS NOT NULL
  AND llm_provider_display_name IS NULL;

CREATE INDEX IF NOT EXISTS idx_analysis_runs_global_active
ON analysis_runs (status, updated_at DESC)
WHERE deleted_at IS NULL
  AND status IN ('queued', 'running', 'cancelling');

CREATE INDEX IF NOT EXISTS idx_cluster_sets_global_active
ON cluster_sets (status, updated_at DESC)
WHERE deleted_at IS NULL
  AND status IN ('queued', 'running', 'cancelling');

CREATE INDEX IF NOT EXISTS idx_cluster_sets_project_updated
ON cluster_sets (project_id, updated_at DESC)
WHERE deleted_at IS NULL;
