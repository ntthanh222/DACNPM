-- ============================================================
-- CyberSec Assistant Platform - Enterprise Upgrade Migration (006)
-- ============================================================

-- ============================================
-- 1. Assets Table
-- ============================================
CREATE TABLE IF NOT EXISTS public.assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    asset_type VARCHAR(100) NOT NULL,
    hostname VARCHAR(255),
    ip_address VARCHAR(100),
    os VARCHAR(100),
    vendor VARCHAR(100),
    product VARCHAR(100),
    version VARCHAR(100),
    cpe VARCHAR(255),
    owner VARCHAR(100),
    department VARCHAR(100),
    environment VARCHAR(100),
    criticality VARCHAR(50) DEFAULT 'medium', -- low, medium, high, critical
    internet_exposure BOOLEAN DEFAULT false,
    status VARCHAR(50) DEFAULT 'active',
    notes TEXT,
    is_deleted BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_assets_name ON public.assets(name);
CREATE INDEX IF NOT EXISTS idx_assets_type ON public.assets(asset_type);
CREATE INDEX IF NOT EXISTS idx_assets_ip ON public.assets(ip_address);
CREATE INDEX IF NOT EXISTS idx_assets_cpe ON public.assets(cpe);
CREATE INDEX IF NOT EXISTS idx_assets_criticality ON public.assets(criticality);
CREATE INDEX IF NOT EXISTS idx_assets_status ON public.assets(status);

-- ============================================
-- 2. CVE Watchlist Table
-- ============================================
CREATE TABLE IF NOT EXISTS public.cve_watchlist (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    cve_id VARCHAR(50) NOT NULL,
    notes TEXT,
    asset_id UUID REFERENCES public.assets(id) ON DELETE SET NULL,
    notification_preference VARCHAR(100) DEFAULT 'all',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, cve_id, asset_id)
);

CREATE INDEX IF NOT EXISTS idx_watchlist_user ON public.cve_watchlist(user_id);
CREATE INDEX IF NOT EXISTS idx_watchlist_cve ON public.cve_watchlist(cve_id);
CREATE INDEX IF NOT EXISTS idx_watchlist_asset ON public.cve_watchlist(asset_id);

-- ============================================
-- 3. Security Alerts Table
-- ============================================
CREATE TABLE IF NOT EXISTS public.security_alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    severity VARCHAR(50) DEFAULT 'medium', -- info, low, medium, high, critical
    alert_type VARCHAR(100) NOT NULL, -- crawler_failure, backup_failure, service_unhealthy, prompt_injection, risk_increase
    status VARCHAR(50) DEFAULT 'unread', -- unread, acknowledged, resolved
    related_entity_type VARCHAR(100),
    related_entity_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_alerts_severity ON public.security_alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON public.security_alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_created ON public.security_alerts(created_at);

-- ============================================
-- 4. Incident Workspace Table
-- ============================================
CREATE TABLE IF NOT EXISTS public.incidents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    severity VARCHAR(50) DEFAULT 'medium',
    status VARCHAR(50) DEFAULT 'open', -- open, investigating, contained, remediated, closed
    owner_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    assignee_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    timeline JSONB DEFAULT '[]',
    evidence JSONB DEFAULT '{}',
    notes TEXT,
    tasks JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    closed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_incidents_status ON public.incidents(status);
CREATE INDEX IF NOT EXISTS idx_incidents_severity ON public.incidents(severity);
CREATE INDEX IF NOT EXISTS idx_incidents_assignee ON public.incidents(assignee_id);

-- ============================================
-- 5. Audit Logs Table (Append-only)
-- ============================================
CREATE TABLE IF NOT EXISTS public.audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    actor VARCHAR(255) NOT NULL,
    action VARCHAR(255) NOT NULL,
    resource_type VARCHAR(255) NOT NULL,
    resource_id VARCHAR(255),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    result VARCHAR(50) NOT NULL, -- success, failure
    ip_address VARCHAR(100),
    user_agent TEXT,
    request_id VARCHAR(255),
    trace_id VARCHAR(255),
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_audit_actor ON public.audit_logs(actor);
CREATE INDEX IF NOT EXISTS idx_audit_action ON public.audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_time ON public.audit_logs(timestamp);

-- ============================================
-- 6. Notifications Table
-- ============================================
CREATE TABLE IF NOT EXISTS public.notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    type VARCHAR(100) NOT NULL,
    is_read BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notif_user ON public.notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notif_read ON public.notifications(is_read);
CREATE INDEX IF NOT EXISTS idx_notif_created ON public.notifications(created_at);
