-- ============================================================
-- CyberSec Assistant Platform - Supabase Cloud Migration
-- ============================================================
-- CHẠY FILE NÀY TRONG: Supabase Dashboard → SQL Editor
-- URL: https://supabase.com/dashboard → Chọn project → SQL Editor → New Query
-- Paste toàn bộ nội dung này và click "Run"
-- ============================================================
-- ============================================
-- Extensions (Supabase Cloud)
-- ============================================
-- uuid-ossp và pg_trgm đã có sẵn trên Supabase
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
-- pgvector cho RAG vector search
CREATE EXTENSION IF NOT EXISTS "vector";
-- ============================================
-- Users Table
-- ============================================
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user',
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    avatar_url VARCHAR(500),
    bio TEXT,
    security_context JSONB DEFAULT '{"preferences": {"language": "vi", "notifications_enabled": true, "scan_frequency": "weekly"}}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ
);

-- Đảm bảo mọi cột bắt buộc đều tồn tại ngay cả khi table đã được tạo trước đó
-- với shape khác (CREATE TABLE IF NOT EXISTS sẽ bỏ qua table đã có).
-- Idempotent: chạy lại bao nhiêu lần cũng an toàn.
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS email VARCHAR(255);
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS username VARCHAR(100);
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS full_name VARCHAR(255);
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS role VARCHAR(50) DEFAULT 'user';
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT false;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(500);
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS bio TEXT;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS security_context JSONB;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS last_login TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON public.users(username);
CREATE INDEX IF NOT EXISTS idx_users_role ON public.users(role);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON public.users(created_at);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON public.users(is_active);
-- ============================================
-- User Sessions Table
-- ============================================
CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    token VARCHAR(500) UNIQUE NOT NULL,
    refresh_token VARCHAR(500),
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT
);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(token);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON user_sessions(expires_at);
-- ============================================
-- Chatbot Conversations Table
-- ============================================
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at);
-- ============================================
-- Chatbot Messages Table
-- ============================================
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
CREATE INDEX IF NOT EXISTS idx_messages_role ON messages(role);
CREATE INDEX IF NOT EXISTS idx_messages_content_gin ON messages USING gin(to_tsvector('english', content));
-- ============================================
-- News Articles Table
-- ============================================
CREATE TABLE IF NOT EXISTS news_articles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    content TEXT,
    source VARCHAR(100),
    author VARCHAR(255),
    url VARCHAR(1000) UNIQUE,
    image_url VARCHAR(1000),
    published_at TIMESTAMPTZ,
    scraped_at TIMESTAMPTZ DEFAULT NOW(),
    category VARCHAR(100),
    tags TEXT [],
    sentiment VARCHAR(20),
    relevance_score DECIMAL(3, 2),
    is_approved BOOLEAN DEFAULT false,
    is_featured BOOLEAN DEFAULT false,
    view_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_news_url ON news_articles(url);
CREATE INDEX IF NOT EXISTS idx_news_source ON news_articles(source);
CREATE INDEX IF NOT EXISTS idx_news_category ON news_articles(category);
CREATE INDEX IF NOT EXISTS idx_news_published_at ON news_articles(published_at);
CREATE INDEX IF NOT EXISTS idx_news_is_approved ON news_articles(is_approved);
CREATE INDEX IF NOT EXISTS idx_news_created_at ON news_articles(created_at);
CREATE INDEX IF NOT EXISTS idx_news_content_gin ON news_articles USING gin(
    to_tsvector(
        'english',
        title || ' ' || COALESCE(description, '')
    )
);
CREATE INDEX IF NOT EXISTS idx_news_tags_gin ON news_articles USING gin(tags);
-- ============================================
-- CVE Records Table
-- ============================================
CREATE TABLE IF NOT EXISTS cve_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cve_id VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    severity VARCHAR(20),
    cvss_score DECIMAL(3, 1),
    cvss_vector VARCHAR(100),
    cve_published_at TIMESTAMPTZ,
    cve_modified_at TIMESTAMPTZ,
    affected_products TEXT [],
    "references" TEXT [],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_cve_cve_id ON cve_records(cve_id);
CREATE INDEX IF NOT EXISTS idx_cve_severity ON cve_records(severity);
CREATE INDEX IF NOT EXISTS idx_cve_cvss_score ON cve_records(cvss_score);
CREATE INDEX IF NOT EXISTS idx_cve_published_at ON cve_records(cve_published_at);
CREATE INDEX IF NOT EXISTS idx_cve_affected_products ON cve_records USING gin(affected_products);
-- ============================================
-- Crawler Configurations Table
-- ============================================
CREATE TABLE IF NOT EXISTS crawler_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    source_url VARCHAR(1000),
    enabled BOOLEAN DEFAULT true,
    schedule VARCHAR(100),
    max_articles INTEGER DEFAULT 10,
    selectors JSONB,
    last_run TIMESTAMPTZ,
    last_status VARCHAR(50),
    last_articles_count INTEGER,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_crawler_name ON crawler_configs(name);
CREATE INDEX IF NOT EXISTS idx_crawler_enabled ON crawler_configs(enabled);
-- ============================================
-- Crawler Logs Table
-- ============================================
CREATE TABLE IF NOT EXISTS crawler_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    crawler_id UUID NOT NULL REFERENCES crawler_configs(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status VARCHAR(50) CHECK (status IN ('running', 'completed', 'failed')),
    articles_found INTEGER,
    articles_scraped INTEGER,
    error_message TEXT,
    execution_time INTEGER
);
CREATE INDEX IF NOT EXISTS idx_crawler_logs_crawler_id ON crawler_logs(crawler_id);
CREATE INDEX IF NOT EXISTS idx_crawler_logs_started_at ON crawler_logs(started_at);
CREATE INDEX IF NOT EXISTS idx_crawler_logs_status ON crawler_logs(status);
-- ============================================
-- Statistics Table
-- ============================================
CREATE TABLE IF NOT EXISTS statistics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(20, 2),
    dimensions JSONB,
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_statistics_metric_name ON statistics(metric_name);
CREATE INDEX IF NOT EXISTS idx_statistics_recorded_at ON statistics(recorded_at);
-- ============================================
-- Analytics Events Table
-- ============================================
CREATE TABLE IF NOT EXISTS analytics_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.users(id) ON DELETE
    SET NULL,
        event_type VARCHAR(100) NOT NULL,
        event_properties JSONB,
        session_id UUID,
        ip_address INET,
        user_agent TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_analytics_user_id ON analytics_events(user_id);
CREATE INDEX IF NOT EXISTS idx_analytics_event_type ON analytics_events(event_type);
CREATE INDEX IF NOT EXISTS idx_analytics_created_at ON analytics_events(created_at);
CREATE INDEX IF NOT EXISTS idx_analytics_session_id ON analytics_events(session_id);
-- ============================================
-- Reports Table
-- ============================================
CREATE TABLE IF NOT EXISTS reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    report_type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    parameters JSONB,
    status VARCHAR(50) DEFAULT 'pending' CHECK (
        status IN ('pending', 'processing', 'completed', 'failed')
    ),
    file_url VARCHAR(1000),
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_reports_user_id ON reports(user_id);
CREATE INDEX IF NOT EXISTS idx_reports_type ON reports(report_type);
CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);
CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reports(created_at);
-- ============================================
-- System Logs Table
-- ============================================
CREATE TABLE IF NOT EXISTS system_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    level VARCHAR(20) NOT NULL CHECK (
        level IN ('info', 'warning', 'error', 'critical')
    ),
    logger VARCHAR(100),
    message TEXT NOT NULL,
    extra_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_logs_level ON system_logs(level);
CREATE INDEX IF NOT EXISTS idx_logs_logger ON system_logs(logger);
CREATE INDEX IF NOT EXISTS idx_logs_created_at ON system_logs(created_at);
-- ============================================
-- RAG Documents Table
-- ============================================
CREATE TABLE IF NOT EXISTS rag_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    source VARCHAR(255),
    document_type VARCHAR(100),
    metadata JSONB,
    chunk_count INTEGER DEFAULT 0,
    is_indexed BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_rag_source ON rag_documents(source);
CREATE INDEX IF NOT EXISTS idx_rag_type ON rag_documents(document_type);
CREATE INDEX IF NOT EXISTS idx_rag_is_indexed ON rag_documents(is_indexed);
CREATE INDEX IF NOT EXISTS idx_rag_content_gin ON rag_documents USING gin(to_tsvector('english', title || ' ' || content));
-- ============================================
-- RAG Embeddings Table (cho pgvector)
-- ============================================
CREATE TABLE IF NOT EXISTS rag_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES rag_documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_embeddings_document_id ON rag_embeddings(document_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_chunk_index ON rag_embeddings(document_id, chunk_index);
-- HNSW index cho vector similarity search (nhanh hơn IVFFlat cho datasets nhỏ-vừa)
CREATE INDEX IF NOT EXISTS idx_embeddings_vector_hnsw ON rag_embeddings USING hnsw (embedding vector_cosine_ops);
-- ============================================
-- Functions and Triggers
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column() RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = NOW();
RETURN NEW;
END;
$$ language 'plpgsql';
DROP TRIGGER IF EXISTS update_users_updated_at ON public.users;
CREATE TRIGGER update_users_updated_at BEFORE
UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
DROP TRIGGER IF EXISTS update_conversations_updated_at ON conversations;
CREATE TRIGGER update_conversations_updated_at BEFORE
UPDATE ON conversations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
DROP TRIGGER IF EXISTS update_news_updated_at ON news_articles;
CREATE TRIGGER update_news_updated_at BEFORE
UPDATE ON news_articles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
DROP TRIGGER IF EXISTS update_cve_updated_at ON cve_records;
CREATE TRIGGER update_cve_updated_at BEFORE
UPDATE ON cve_records FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
DROP TRIGGER IF EXISTS update_crawler_updated_at ON crawler_configs;
CREATE TRIGGER update_crawler_updated_at BEFORE
UPDATE ON crawler_configs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
DROP TRIGGER IF EXISTS update_reports_updated_at ON reports;
CREATE TRIGGER update_reports_updated_at BEFORE
UPDATE ON reports FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
DROP TRIGGER IF EXISTS update_rag_updated_at ON rag_documents;
CREATE TRIGGER update_rag_updated_at BEFORE
UPDATE ON rag_documents FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
-- ============================================
-- Row Level Security (RLS)
-- ============================================
-- Bật RLS cho các bảng chứa user data
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_events ENABLE ROW LEVEL SECURITY;
-- Service role bypass RLS (backend dùng service role key)
-- DROP trước nếu đã tồn tại (cho phép chạy lại nhiều lần)
DROP POLICY IF EXISTS "Service role full access" ON public.users;
DROP POLICY IF EXISTS "Service role full access" ON user_sessions;
DROP POLICY IF EXISTS "Service role full access" ON conversations;
DROP POLICY IF EXISTS "Service role full access" ON messages;
DROP POLICY IF EXISTS "Service role full access" ON reports;
DROP POLICY IF EXISTS "Service role full access" ON analytics_events;

CREATE POLICY "Service role full access" ON public.users FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access" ON user_sessions FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access" ON conversations FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access" ON messages FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access" ON reports FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access" ON analytics_events FOR ALL USING (auth.role() = 'service_role');
-- Public read cho news_articles và cve_records (không cần auth)
-- Các bảng này không bật RLS để frontend hiển thị được
-- ============================================
-- Seed Data
-- ============================================
-- Insert default admin user.
-- SECURITY: The plaintext password is intentionally NOT stored here.
-- It is generated randomly and written to backend/ADMIN_CREDENTIALS.txt (gitignored)
-- on first setup. Use an UPDATE statement if you need to reset it.
-- ON CONFLICT DO UPDATE ensures the strong random password replaces any
-- pre-existing weaker admin password (e.g. the old "Admin123" default).
INSERT INTO public.users (
        email,
        username,
        password_hash,
        full_name,
        role,
        is_active,
        is_verified,
        security_context
    )
VALUES (
        'admin@cybersec.local',
        'admin',
        '$2b$12$r3Gvf2KmCVHKJ7r/E.F7aeX9169zcEd4B70gkBTwrsbLQN/0Zda3q',
        'System Administrator',
        'admin',
        true,
        true,
        '{"preferences": {"language": "vi", "notifications_enabled": true, "scan_frequency": "weekly"}}'
    )
ON CONFLICT (email) DO UPDATE
SET password_hash = EXCLUDED.password_hash,
    role = EXCLUDED.role,
    is_active = EXCLUDED.is_active;
-- ============================================
-- Missing Tables & Schema Realignment Fixes
-- ============================================

-- 1. Profiles Table
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY REFERENCES public.users(id) ON DELETE CASCADE,
    username VARCHAR(100) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    avatar_url VARCHAR(500),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_profiles_username ON profiles(username);

-- 2. Chat History Table
CREATE TABLE IF NOT EXISTS chat_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    user_message TEXT NOT NULL,
    bot_response TEXT NOT NULL,
    intent VARCHAR(100),
    entities JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_chat_history_user_id ON chat_history(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_history_created_at ON chat_history(created_at);

-- 3. Security Scans Table
CREATE TABLE IF NOT EXISTS security_scans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    scan_type VARCHAR(50) NOT NULL CHECK (scan_type IN ('url_scan', 'password_check', 'vulnerability_scan')),
    target TEXT NOT NULL,
    scan_result JSONB,
    risk_score INTEGER CHECK (risk_score >= 0 AND risk_score <= 100),
    severity VARCHAR(20) CHECK (severity IN ('info', 'low', 'medium', 'high', 'critical')),
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed')),
    scan_metadata JSONB,
    error_message TEXT,
    scan_timestamp TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_security_scans_user_id ON security_scans(user_id);
CREATE INDEX IF NOT EXISTS idx_security_scans_scan_type ON security_scans(scan_type);
CREATE INDEX IF NOT EXISTS idx_security_scans_scan_timestamp ON security_scans(scan_timestamp);

-- 4. CVE Cache (Lookups) Table
CREATE TABLE IF NOT EXISTS cve_lookups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cve_id VARCHAR(50) UNIQUE NOT NULL,
    query_data JSONB,
    response_data JSONB,
    cvss_score VARCHAR(10),
    severity VARCHAR(20) CHECK (severity IN ('none', 'low', 'medium', 'high', 'critical')),
    query_timestamp TIMESTAMPTZ DEFAULT NOW(),
    cache_expires_at TIMESTAMPTZ NOT NULL,
    query_count INTEGER DEFAULT 1 CHECK (query_count >= 1),
    last_accessed TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_cve_lookups_cve_id ON cve_lookups(cve_id);
CREATE INDEX IF NOT EXISTS idx_cve_lookups_cache_expires ON cve_lookups(cache_expires_at);

-- 5. Admin Audit Log Table
CREATE TABLE IF NOT EXISTS admin_audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    admin_user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    action_type VARCHAR(100) NOT NULL,
    target_type VARCHAR(100) NOT NULL,
    action_details JSONB DEFAULT '{}',
    timestamp TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_admin_audit_log_admin ON admin_audit_log(admin_user_id);
CREATE INDEX IF NOT EXISTS idx_admin_audit_log_timestamp ON admin_audit_log(timestamp);

-- ============================================
-- Row Level Security (RLS) Policies
-- ============================================
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE security_scans ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_audit_log ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role full access" ON profiles;
DROP POLICY IF EXISTS "Service role full access" ON chat_history;
DROP POLICY IF EXISTS "Service role full access" ON security_scans;
DROP POLICY IF EXISTS "Service role full access" ON admin_audit_log;

CREATE POLICY "Service role full access" ON profiles FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access" ON chat_history FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access" ON security_scans FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access" ON admin_audit_log FOR ALL USING (auth.role() = 'service_role');

-- ============================================
-- RPC Database Functions
-- ============================================

-- Function to get cached CVE details
-- DROP trước để tránh lỗi 42P13 khi đổi OUT parameters của hàm TABLE đã tồn tại
DROP FUNCTION IF EXISTS get_cached_cve(TEXT) CASCADE;
CREATE OR REPLACE FUNCTION get_cached_cve(cve_id_param TEXT)
RETURNS TABLE (
    cve_id VARCHAR(50),
    response_data JSONB,
    cvss_score VARCHAR(10),
    severity VARCHAR(20),
    is_cached BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.cve_id,
        c.response_data,
        c.cvss_score,
        c.severity,
        (c.cache_expires_at > NOW()) AS is_cached
    FROM 
        cve_lookups c
    WHERE 
        c.cve_id = UPPER(cve_id_param)
    LIMIT 1;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to extend CVE cache TTL
DROP FUNCTION IF EXISTS extend_cache_ttl(TEXT, INTEGER) CASCADE;
CREATE OR REPLACE FUNCTION extend_cache_ttl(cve_id_param TEXT, hours_to_add INTEGER)
RETURNS BOOLEAN AS $$
DECLARE
    updated BOOLEAN := FALSE;
BEGIN
    UPDATE cve_lookups
    SET 
        cache_expires_at = cache_expires_at + (hours_to_add || ' hours')::INTERVAL,
        last_accessed = NOW()
    WHERE 
        cve_id = UPPER(cve_id_param);
        
    IF FOUND THEN
        updated := TRUE;
    END IF;
    
    RETURN updated;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to cleanup expired CVE cache entries
DROP FUNCTION IF EXISTS cleanup_expired_cache() CASCADE;
CREATE OR REPLACE FUNCTION cleanup_expired_cache()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER := 0;
BEGIN
    DELETE FROM cve_lookups
    WHERE cache_expires_at < NOW();
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get CVE cache statistics
DROP FUNCTION IF EXISTS get_cache_statistics() CASCADE;
CREATE OR REPLACE FUNCTION get_cache_statistics()
RETURNS TABLE (
    total_entries INTEGER,
    active_entries INTEGER,
    expired_entries INTEGER,
    avg_query_count FLOAT,
    most_accessed_cve VARCHAR(50),
    cache_hit_rate FLOAT
) AS $$
DECLARE
    v_total INTEGER := 0;
    v_active INTEGER := 0;
    v_expired INTEGER := 0;
    v_avg_query FLOAT := 0.0;
    v_most_accessed VARCHAR(50) := NULL;
    v_hit_rate FLOAT := 0.0;
BEGIN
    -- Get counts
    SELECT COUNT(*), 
           COUNT(*) FILTER (WHERE cache_expires_at > NOW()),
           COUNT(*) FILTER (WHERE cache_expires_at <= NOW()),
           COALESCE(AVG(query_count), 0.0)
    INTO v_total, v_active, v_expired, v_avg_query
    FROM cve_lookups;

    -- Get most accessed
    SELECT cve_id INTO v_most_accessed
    FROM cve_lookups
    ORDER BY query_count DESC, last_accessed DESC
    LIMIT 1;

    -- Cache hit rate calculation
    DECLARE
        total_queries INTEGER := 0;
    BEGIN
        SELECT COALESCE(SUM(query_count), 0) INTO total_queries FROM cve_lookups;
        IF total_queries > 0 THEN
            v_hit_rate := (total_queries - v_total)::FLOAT / total_queries::FLOAT;
            IF v_hit_rate < 0 THEN
                v_hit_rate := 0.0;
            END IF;
        ELSE
            v_hit_rate := 0.0;
        END IF;
    END;

    RETURN QUERY SELECT v_total, v_active, v_expired, v_avg_query, v_most_accessed, v_hit_rate;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- Triggers and Hooks
-- ============================================

-- Automatically update updated_at for profiles
DROP TRIGGER IF EXISTS update_profiles_updated_at ON profiles;
CREATE TRIGGER update_profiles_updated_at BEFORE UPDATE ON profiles
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Automatically increment query_count in cve_lookups on access update
CREATE OR REPLACE FUNCTION increment_cve_query_count()
RETURNS TRIGGER AS $$
BEGIN
    NEW.query_count = OLD.query_count + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_cve_lookups_query_count ON cve_lookups;
CREATE TRIGGER update_cve_lookups_query_count
BEFORE UPDATE ON cve_lookups
FOR EACH ROW
WHEN (NEW.last_accessed IS DISTINCT FROM OLD.last_accessed)
EXECUTE FUNCTION increment_cve_query_count();

-- ============================================
-- Verification
-- ============================================
DO $$
DECLARE table_count INTEGER;
BEGIN
SELECT COUNT(*) INTO table_count
FROM information_schema.tables
WHERE table_schema = 'public'
    AND table_type = 'BASE TABLE';
RAISE NOTICE '    Migration completed! % tables created.',
table_count;
RAISE NOTICE 'Tables: users, user_sessions, conversations, messages, news_articles, cve_records, crawler_configs, crawler_logs, statistics, analytics_events, reports, system_logs, rag_documents, rag_embeddings, profiles, chat_history, security_scans, cve_lookups, admin_audit_log';
END $$;