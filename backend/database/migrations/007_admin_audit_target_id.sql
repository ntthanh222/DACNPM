-- Add target resource identifier for admin audit entries.
-- Existing admin endpoints already write this field; keep the migration
-- idempotent so existing QA databases converge safely.

ALTER TABLE public.admin_audit_log
ADD COLUMN IF NOT EXISTS target_id uuid;

CREATE INDEX IF NOT EXISTS idx_admin_audit_log_target
ON public.admin_audit_log(target_type, target_id);
