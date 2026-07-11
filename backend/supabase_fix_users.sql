-- ============================================
-- FIX BLOCK: public.users — chạy 100% trong SQL Editor
-- ============================================
-- Paste TOÀN BỘ file này vào Supabase Dashboard → SQL Editor → Run.
-- File này TỰ ĐỦ và IDEMPOTENT: chạy lại bao nhiêu lần cũng an toàn.
--
-- Vấn đề trước: file migration dùng `INSERT INTO users ... password_hash`
-- (KHÔNG có prefix schema). Trong Supabase, tên table không có schema sẽ
-- resolve thành `auth.users` (table auth nội bộ, dùng `encrypted_password`
-- chứ KHÔNG phải `password_hash`) → lỗi "column password_hash does not exist".
--
-- Giải pháp: luôn dùng prefix `public.` và đảm bảo cột tồn tại trước khi INSERT.
--
-- Lỗi 42P13 (cannot change return type of existing function) xảy ra ở
-- phần CVE functions của MIGRATION, KHÔNG nằm trong file fix này.
-- Xem phần (B) fix ở cuối hướng dẫn hoặc chạy migration đã sửa.
-- ============================================

-- (1) Đảm bảo table public.users tồn tại (nếu chưa có)
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
    security_context JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ
);

-- (2) Đảm bảo cột password_hash tồn tại dù table đã tạo trước đó với shape khác.
-- Đây là dòng "cứu" — nếu lỗi trước đây là vì table cũ thiếu cột, lệnh này sẽ thêm.
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

-- (3) Seed admin user.
--     SECURITY: plaintext password is NOT stored here. It is generated randomly
--     and written to backend/ADMIN_CREDENTIALS.txt (gitignored) on first setup.
--     ON CONFLICT (email) DO UPDATE → ensures the password is reset to the
--     strong random value even if a weaker admin (e.g. Admin123) already exists.
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
        '{"preferences": {"language": "vi", "notifications_enabled": true, "scan_frequency": "weekly"}}'::jsonb
    )
ON CONFLICT (email) DO UPDATE
SET password_hash = EXCLUDED.password_hash,
    role = EXCLUDED.role,
    is_active = EXCLUDED.is_active;

-- (4) Indexes (idempotent)
CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON public.users(username);
CREATE INDEX IF NOT EXISTS idx_users_role ON public.users(role);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON public.users(is_active);

-- (5) Xác minh kết quả — xem admin đã có hash bcrypt hợp lệ
SELECT
    username,
    email,
    role,
    (password_hash IS NOT NULL) AS has_password,
    CASE
        WHEN password_hash LIKE '$2b$%' OR password_hash LIKE '$2a$%' THEN 'bcrypt ✓'
        ELSE 'unexpected: ' || password_hash
    END AS hash_format
FROM public.users
WHERE username = 'admin';
