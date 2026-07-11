-- ============================================
-- CHẨN ĐOÁN SCHEMA: public.users vs auth.users
-- ============================================
-- Chạy file này trong Supabase Dashboard → SQL Editor.
-- Tất cả các câu lệnh đều READ-ONLY, an toàn chạy lại nhiều lần.
-- Mục đích: xem ground-truth tên cột thật trong DB để loại bỏ
-- hoài nghi về cache PostgREST hay nhầm lẫn auth.users.
-- ============================================

-- (1) Tất cả các cột thật trong public.users (table app dùng)
SELECT
    ordinal_position AS pos,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'users'
ORDER BY ordinal_position;

-- (2) Chứng minh auth.users dùng tên cột KHÁC (encrypted_password, không phải password_hash)
SELECT
    column_name,
    data_type
FROM information_schema.columns
WHERE table_schema = 'auth'
  AND table_name = 'users'
  AND column_name LIKE '%pass%';

-- (3) Đếm số dòng trong public.users (đúng table app dùng)
SELECT count(*) AS public_users_count
FROM public.users;

-- (4) Xác nhận cột password_hash có dữ liệu thật
SELECT
    username,
    email,
    role,
    is_active,
    (password_hash IS NOT NULL) AS has_password,
    CASE
        WHEN password_hash IS NULL THEN 'NULL'
        WHEN password_hash LIKE '$2b$%' OR password_hash LIKE '$2a$%' THEN 'bcrypt'
        ELSE 'other'
    END AS hash_format
FROM public.users
ORDER BY username;

-- (5) Liệt kê các table tên 'users' tồn tại trong mọi schema (kiểm tra trùng tên)
SELECT
    table_schema,
    table_name
FROM information_schema.tables
WHERE table_name = 'users'
ORDER BY table_schema;
