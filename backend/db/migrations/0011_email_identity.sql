DO $$
DECLARE
    cross_identity_collisions bigint;
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'users'
          AND column_name = 'username'
    ) THEN
        SELECT count(*)
        INTO cross_identity_collisions
        FROM users legacy_user
        JOIN users email_user
          ON legacy_user.username = email_user.email
         AND legacy_user.id <> email_user.id;

        IF cross_identity_collisions > 0 THEN
            RAISE NOTICE
                'Resolving % legacy username/email collisions by retaining email identities only',
                cross_identity_collisions;
        END IF;
    END IF;
END
$$;

DROP INDEX IF EXISTS idx_users_active_username;

ALTER TABLE users
DROP COLUMN IF EXISTS username;

CREATE INDEX IF NOT EXISTS idx_users_active_email
ON users (email)
WHERE deleted_at IS NULL;
