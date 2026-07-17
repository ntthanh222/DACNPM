import sys
import os
import requests

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000").rstrip("/")

def test_user(username, password, expected_login_ok, expect_admin_users=False, expect_cache=False):
    print(f"\n--- Testing user: {username} ---")
    
    # 1. Login
    login_url = f"{API_BASE_URL}/api/auth/login"
    try:
        response = requests.post(login_url, json={
            "username": username,
            "password": password
        })
    except Exception as e:
        print(f"❌ Failed to connect to backend: {e}")
        return False

    if not expected_login_ok:
        if response.status_code in (401, 403):
            print(f"✅ Login correctly failed with status {response.status_code}")
            return True
        else:
            print(f"❌ Login succeeded or returned unexpected status: {response.status_code}")
            return False

    if response.status_code != 200:
        print(f"❌ Login failed with status {response.status_code}: {response.text}")
        return False

    data = response.json()
    token = data.get("access_token")
    if not token:
        print("❌ Login response did not contain access_token")
        return False
    print("✅ Login successful")

    headers = {"Authorization": f"Bearer {token}"}
    success = True

    # 2. Get profile
    me_url = f"{API_BASE_URL}/api/auth/me"
    me_resp = requests.get(me_url, headers=headers)
    if me_resp.status_code != 200:
        print(f"❌ Failed to get profile: {me_resp.status_code}")
        success = False
    else:
        profile = me_resp.json()
        print(f"✅ Profile retrieved. Role: {profile.get('role')}")
        if profile.get("username") != username:
            print(f"❌ Username mismatch: expected {username}, got {profile.get('username')}")
            success = False

    # 3. Test Admin users endpoint
    admin_users_url = f"{API_BASE_URL}/api/admin/users"
    admin_users_resp = requests.get(admin_users_url, headers=headers)
    if expect_admin_users:
        if admin_users_resp.status_code == 200:
            print("✅ Admin users list retrieved successfully (authorized)")
        else:
            print(f"❌ Admin users list failed for admin user: {admin_users_resp.status_code}")
            success = False
    else:
        if admin_users_resp.status_code == 403:
            print("✅ Admin users list correctly blocked (403 Forbidden)")
        else:
            print(f"❌ Admin users list not blocked correctly: {admin_users_resp.status_code}")
            success = False

    # 4. Test Admin system cache endpoint
    admin_cache_url = f"{API_BASE_URL}/api/admin/system/cache"
    admin_cache_resp = requests.get(admin_cache_url, headers=headers)
    if expect_cache:
        if admin_cache_resp.status_code == 200:
            print("✅ Admin system cache retrieved successfully (authorized)")
        else:
            print(f"❌ Admin system cache failed for admin user: {admin_cache_resp.status_code}")
            success = False
    else:
        if admin_cache_resp.status_code == 403:
            print("✅ Admin system cache correctly blocked (403 Forbidden)")
        else:
            print(f"❌ Admin system cache not blocked correctly: {admin_cache_resp.status_code}")
            success = False

    return success

def main():
    print("Starting authenticated role and permission matrix checks...")

    required_passwords = {
        "qa_superadmin": os.environ.get("QA_SUPERADMIN_PASSWORD"),
        "qa_admin": os.environ.get("QA_ADMIN_PASSWORD"),
        "qa_analyst": os.environ.get("QA_ANALYST_PASSWORD"),
        "qa_user_a": os.environ.get("QA_USER_A_PASSWORD"),
        "qa_disabled": os.environ.get("QA_DISABLED_PASSWORD"),
    }
    missing = [name for name, value in required_passwords.items() if not value]
    if missing:
        print("Missing QA password environment variables for: " + ", ".join(missing))
        return 2

    users_to_test = [
        ("qa_superadmin", required_passwords["qa_superadmin"], True, True, True),
        ("qa_admin", required_passwords["qa_admin"], True, True, True),
        ("qa_analyst", required_passwords["qa_analyst"], True, False, True),
        ("qa_user_a", required_passwords["qa_user_a"], True, False, False),
        ("qa_disabled", required_passwords["qa_disabled"], False, False, False),
    ]

    all_passed = True
    for username, password, expected_login, expect_admin_users, expect_cache in users_to_test:
        passed = test_user(username, password, expected_login, expect_admin_users, expect_cache)
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 ALL MATRIX PERMISSION CHECKS PASSED SUCCESSFULLY!")
        return 0
    else:
        print("\n❌ SOME MATRIX PERMISSION CHECKS FAILED!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
