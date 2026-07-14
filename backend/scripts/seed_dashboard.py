import uuid
from datetime import datetime, timedelta, timezone

from backend.database.connection import supabase_admin, is_database_available
from backend.database.local_connection import get_local_admin_client

def seed():
    # Use local PostgreSQL connection if Supabase is not available
    if not is_database_available():
        print("❌ Database is not available.")
        return

    print("🌱 Database connection verified. Starting seeding...")

    # Try to use local connection if Supabase fails
    db_client = supabase_admin
    try:
        # Test connection
        db_client.table('users').select('id').limit(1).execute()
    except Exception as e:
        print(f"⚠️ Supabase connection failed: {e}")
        print("🔄 Trying local PostgreSQL connection...")
        db_client = get_local_admin_client()

    # 1. Get a valid user ID from 'users' table
    users_response = db_client.table('users').select('id').limit(1).execute()
    
    if users_response.data:
        user_id = users_response.data[0]['id']
        print(f"✅ Found existing user ID in 'users': {user_id}")
    else:
        # Create a new user since none exist
        user_id = str(uuid.uuid4())
        print(f"🌱 Creating a new user with ID: {user_id}")
        
        user_data = {
            'id': user_id,
            'username': 'User_Sentinel',
            'email': 'user@sentinel.org',
            'full_name': 'Sentinel User',
            'role': 'user',
            'is_active': True,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'security_context': {}
        }
        db_client.table('users').insert(user_data).execute()
        
        # Also ensure profile exists
        profile_data = {
            'id': user_id,
            'username': 'User_Sentinel',
            'full_name': 'Sentinel User',
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        try:
            db_client.table('profiles').insert(profile_data).execute()
        except Exception:
            pass  # Trigger might have handled it
            
        print(f"✅ Created new user: {user_id}")

    # 2. Insert mock CVE cached entries
    print("🌱 Seeding CVE Cache entries...")
    cves = [
        {"cve_id": "CVE-2026-0001", "cvss_score": "9.8", "severity": "critical"},
        {"cve_id": "CVE-2026-0002", "cvss_score": "7.5", "severity": "high"},
        {"cve_id": "CVE-2026-0003", "cvss_score": "8.8", "severity": "high"},
        {"cve_id": "CVE-2025-1020", "cvss_score": "5.3", "severity": "medium"},
        {"cve_id": "CVE-2025-4321", "cvss_score": "4.8", "severity": "medium"},
        {"cve_id": "CVE-2025-9999", "cvss_score": "9.1", "severity": "critical"},
        {"cve_id": "CVE-2024-5000", "cvss_score": "3.5", "severity": "low"},
        {"cve_id": "CVE-2024-1234", "cvss_score": "8.5", "severity": "high"},
        {"cve_id": "CVE-2024-5678", "cvss_score": "6.2", "severity": "medium"},
        {"cve_id": "CVE-2024-0099", "cvss_score": "9.8", "severity": "critical"},
    ]

    cve_inserted = 0
    for cve in cves:
        try:
            db_client.table('cve_lookups').insert({
                "cve_id": cve["cve_id"],
                "query_data": {"query": cve["cve_id"]},
                "response_data": {
                    "vulnerabilities": [{
                        "cve": {
                            "id": cve["cve_id"],
                            "descriptions": [{"lang": "en", "value": f"Mock vulnerability description for {cve['cve_id']}"}],
                            "metrics": {
                                "cvssMetricV31": [{
                                    "cvssData": {
                                        "baseScore": float(cve["cvss_score"]),
                                        "baseSeverity": cve["severity"].upper()
                                    }
                                }]
                            }
                        }
                    }]
                },
                "cvss_score": cve["cvss_score"],
                "severity": cve["severity"],
                "query_timestamp": datetime.now(timezone.utc).isoformat(),
                "cache_expires_at": (datetime.now(timezone.utc) + timedelta(days=365)).isoformat(),
                "query_count": 1,
                "last_accessed": datetime.now(timezone.utc).isoformat()
            }).execute()
            cve_inserted += 1
        except Exception as e:
            # Ignore if already exists (duplicate key error)
            pass

    print(f"✅ Seeding CVE Cache complete: inserted {cve_inserted} records")

    # 3. Seed Chat History with vulnerability intents
    print("🌱 Seeding Chat History with security intents...")
    chat_seeds = [
        # Injection (intents: sql_injection, command_injection, injection) -> expect ~35%
        {"message": "Kiểm tra SQL injection trong web như thế nào?", "intent": "sql_injection"},
        {"message": "Làm sao để ngăn chặn SQLi?", "intent": "sql_injection"},
        {"message": "Command injection là gì vậy?", "intent": "command_injection"},
        {"message": "Giúp tôi viết code phòng chống SQL injection bằng PHP PDO", "intent": "sql_injection"},
        {"message": "Cách tấn công LDAP injection", "intent": "ldap_injection"},
        {"message": "Lỗi Injection xảy ra khi nào?", "intent": "injection"},
        {"message": "Làm sao để quét lỗi SQL injection?", "intent": "sql_injection"},
        
        # XSS (intents: xss, cross_site_scripting) -> expect ~25%
        {"message": "Cross Site Scripting là gì?", "intent": "xss"},
        {"message": "Stored XSS khác gì Reflected XSS?", "intent": "xss"},
        {"message": "Làm thế nào để chặn lỗi XSS trong NodeJS?", "intent": "xss"},
        {"message": "Mã khai thác XSS cơ bản", "intent": "xss"},
        {"message": "DOM-based XSS là gì?", "intent": "xss"},
        
        # Authentication & Authorization (intents: authentication, authorization, session_management) -> expect ~20%
        {"message": "Làm sao để bảo mật session trong ứng dụng web?", "intent": "session_management"},
        {"message": "Lỗi Broken Authentication là gì?", "intent": "authentication"},
        {"message": "Giải thích về OAuth2 và JWT", "intent": "authentication"},
        {"message": "Cách phân quyền RBAC an toàn", "intent": "authorization"},
        
        # Memory Corruption (intents: buffer_overflow, memory_corruption) -> expect ~15%
        {"message": "Buffer overflow hoạt động ra sao trên C++?", "intent": "buffer_overflow"},
        {"message": "Memory corruption là gì?", "intent": "memory_corruption"},
        {"message": "Làm thế nào để chặn lỗi tràn bộ đệm?", "intent": "buffer_overflow"},
        
        # CSRF (intents: csrf) -> expect ~5%
        {"message": "Cách chống lỗi CSRF bằng token", "intent": "csrf"},
    ]

    chat_inserted = 0
    for chat in chat_seeds:
        try:
            db_client.table('chat_history').insert({
                "user_id": user_id,
                "user_message": chat["message"],
                "bot_response": f"Đây là câu trả lời mẫu cho truy vấn về lỗi: {chat['intent']}",
                "intent": chat["intent"],
                "entities": {},
                "created_at": datetime.now(timezone.utc).isoformat()
            }).execute()
            chat_inserted += 1
        except Exception as e:
            print(f"❌ Failed to insert chat history seed: {e}")

    print(f"✅ Seeding Chat History complete: inserted {chat_inserted} records")
    print("🎉 Seeding dashboard statistics complete!")

if __name__ == "__main__":
    seed()
