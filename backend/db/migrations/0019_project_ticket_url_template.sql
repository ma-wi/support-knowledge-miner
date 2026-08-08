ALTER TABLE projects
ADD COLUMN IF NOT EXISTS ticket_url_template text;
