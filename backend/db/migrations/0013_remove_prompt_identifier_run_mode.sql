ALTER TABLE analysis_profiles
    DROP COLUMN prompt_identifier;

UPDATE analysis_runs
SET profile_snapshot = profile_snapshot - 'prompt_identifier'
WHERE profile_snapshot ? 'prompt_identifier';

UPDATE analysis_runs
SET parameters = parameters - 'mode'
WHERE parameters ? 'mode';
