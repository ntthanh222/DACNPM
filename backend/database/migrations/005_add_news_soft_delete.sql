-- Add soft-delete support expected by admin/news runtime paths.
-- Safe to rerun: Supabase/Postgres will skip existing objects.

ALTER TABLE public.news_articles
    ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_news_is_deleted
    ON public.news_articles(is_deleted);
