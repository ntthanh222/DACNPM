-- ============================================
-- FIX BLOCK: CVE functions (lỗi 42P13)
-- ============================================
-- Chạy file này trong Supabase Dashboard → SQL Editor → Run.
-- Idempotent: chạy lại bao nhiêu lần cũng an toàn.
--
-- Nguyên nhân lỗi: CREATE OR REPLACE FUNCTION không được phép đổi OUT
-- parameters (row type) của hàm TABLE đã tồn tại. Postgres yêu cầu DROP
-- FUNCTION trước. File này DROP CASCADE rồi CREATE lại với signature đúng.
-- ============================================

-- Yêu cầu table cve_lookups tồn tại (được tạo ở phần khác của migration).
-- Nếu chưa có, tạo tối thiểu để hàm không lỗi:
CREATE TABLE IF NOT EXISTS cve_lookups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cve_id VARCHAR(50) UNIQUE NOT NULL,
    response_data JSONB,
    cvss_score VARCHAR(10),
    severity VARCHAR(20),
    query_count INTEGER DEFAULT 0,
    cache_expires_at TIMESTAMPTZ,
    last_accessed TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- (1) get_cached_cve
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

-- (2) extend_cache_ttl
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

-- (3) cleanup_expired_cache
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

-- (4) get_cache_statistics
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

-- (5) increment_cve_query_count (trigger function)
-- Trả về TRIGGER (return type cố định) nên CREATE OR REPLACE OK,
-- nhưng để nhất quán thì cũng DROP trước. Lưu ý: DROP trigger function
-- sẽ tự DROP mọi trigger dùng nó. Trigger được recreate ở phần khác.
DROP FUNCTION IF EXISTS increment_cve_query_count() CASCADE;
CREATE OR REPLACE FUNCTION increment_cve_query_count()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.query_count IS DISTINCT FROM OLD.query_count THEN
        -- query_count was updated, bump last_accessed too
        NEW.last_accessed := NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Recreate trigger nếu đã bị DROP CASCADE ở trên
DROP TRIGGER IF EXISTS trigger_increment_cve_query_count ON cve_lookups;
CREATE TRIGGER trigger_increment_cve_query_count
    BEFORE UPDATE ON cve_lookups
    FOR EACH ROW EXECUTE FUNCTION increment_cve_query_count();
