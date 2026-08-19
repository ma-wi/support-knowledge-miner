ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS llm_taxonomy_max_source_clusters integer
        NOT NULL DEFAULT 200;

ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS llm_taxonomy_max_prompt_characters integer
        NOT NULL DEFAULT 80000;

ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS llm_taxonomy_max_total_keyword_terms integer
        NOT NULL DEFAULT 250000;

ALTER TABLE projects
    DROP CONSTRAINT IF EXISTS projects_llm_taxonomy_source_clusters_range_check;

ALTER TABLE projects
    ADD CONSTRAINT projects_llm_taxonomy_source_clusters_range_check
    CHECK (
        llm_taxonomy_max_source_clusters >= 1
        AND llm_taxonomy_max_source_clusters <= 500
    );

ALTER TABLE projects
    DROP CONSTRAINT IF EXISTS projects_llm_taxonomy_prompt_characters_range_check;

ALTER TABLE projects
    ADD CONSTRAINT projects_llm_taxonomy_prompt_characters_range_check
    CHECK (
        llm_taxonomy_max_prompt_characters >= 10000
        AND llm_taxonomy_max_prompt_characters <= 500000
    );

ALTER TABLE projects
    DROP CONSTRAINT IF EXISTS projects_cluster_keyword_terms_range_check;

ALTER TABLE projects
    ADD CONSTRAINT projects_cluster_keyword_terms_range_check
    CHECK (
        llm_taxonomy_max_total_keyword_terms >= 1000
        AND llm_taxonomy_max_total_keyword_terms <= 1000000
    );
