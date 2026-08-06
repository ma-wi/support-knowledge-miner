-- CHG-005 follow-up: separate available models from purpose allow-lists.

ALTER TABLE provider_configurations
    ADD COLUMN IF NOT EXISTS available_models jsonb NOT NULL DEFAULT '[]'::jsonb;

UPDATE provider_configurations pc
SET available_models = COALESCE(
    (
        SELECT jsonb_agg(model ORDER BY first_ordinal)
        FROM (
            SELECT model, MIN(ordinal) AS first_ordinal
            FROM jsonb_array_elements_text(
                COALESCE(pc.embedding_models, '[]'::jsonb)
                || COALESCE(pc.llm_models, '[]'::jsonb)
                || COALESCE(pc.manual_models, '[]'::jsonb)
            ) WITH ORDINALITY AS available(model, ordinal)
            GROUP BY model
        ) ordered_models
    ),
    '[]'::jsonb
)
WHERE pc.available_models = '[]'::jsonb;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'provider_configurations_available_models_array_check'
    ) THEN
        ALTER TABLE provider_configurations
        ADD CONSTRAINT provider_configurations_available_models_array_check
        CHECK (jsonb_typeof(available_models) = 'array');
    END IF;
END $$;

ALTER TABLE provider_configurations
    DROP COLUMN IF EXISTS supports_embedding,
    DROP COLUMN IF EXISTS supports_llm;
