ALTER TABLE cluster_sets
    ADD COLUMN IF NOT EXISTS keyword_count integer NOT NULL DEFAULT 10;

ALTER TABLE clusters
    ADD COLUMN IF NOT EXISTS keywords jsonb NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE cluster_sets
    DROP CONSTRAINT IF EXISTS cluster_sets_keyword_count_range_check;

ALTER TABLE cluster_sets
    ADD CONSTRAINT cluster_sets_keyword_count_range_check
    CHECK (keyword_count >= 1 AND keyword_count <= 50);

ALTER TABLE clusters
    DROP CONSTRAINT IF EXISTS clusters_keywords_array_check;

ALTER TABLE clusters
    ADD CONSTRAINT clusters_keywords_array_check
    CHECK (jsonb_typeof(keywords) = 'array');

ALTER TABLE clusters
    DROP CONSTRAINT IF EXISTS clusters_auto_status_check;

ALTER TABLE clusters
    ADD CONSTRAINT clusters_auto_status_check
    CHECK (
        auto_status IN (
            'unreviewed', 'in_progress', 'reviewed', 'rejected', 'outlier', 'fixed'
        )
    );

ALTER TABLE clusters
    DROP CONSTRAINT IF EXISTS clusters_manual_status_check;

ALTER TABLE clusters
    ADD CONSTRAINT clusters_manual_status_check
    CHECK (
        manual_status IS NULL OR manual_status IN (
            'unreviewed', 'in_progress', 'reviewed', 'rejected', 'outlier', 'fixed'
        )
    );
