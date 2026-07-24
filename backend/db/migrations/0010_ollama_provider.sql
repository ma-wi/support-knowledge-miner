ALTER TABLE provider_configurations
DROP CONSTRAINT IF EXISTS provider_configurations_provider_check;

ALTER TABLE provider_configurations
ADD CONSTRAINT provider_configurations_provider_check CHECK (
    provider IN ('openai', 'ollama', 'vllm')
);

ALTER TABLE analysis_profiles
DROP CONSTRAINT IF EXISTS analysis_profiles_provider_check;

ALTER TABLE analysis_profiles
ADD CONSTRAINT analysis_profiles_provider_check CHECK (
    provider IN ('openai', 'ollama', 'vllm')
);

ALTER TABLE analysis_runs
DROP CONSTRAINT IF EXISTS analysis_runs_provider_check;

ALTER TABLE analysis_runs
ADD CONSTRAINT analysis_runs_provider_check CHECK (
    provider IN ('openai', 'ollama', 'vllm')
);
