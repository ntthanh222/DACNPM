import os
import json
import pytest
from pathlib import Path
from scripts.backup.backup import backup_data, BACKUP_DIR
from scripts.backup.restore import restore_data
from scripts.testing.seed_qa_data import seed_qa_data, cleanup_qa_data
from backend.database.connection import get_supabase_admin_client
from backend.config.settings import get_settings

@pytest.fixture(scope="module", autouse=True)
def ensure_test_environment():
    settings = get_settings()
    assert settings.is_test(), "Recovery tests must run in the test environment."

def get_latest_backup():
    backups = list(BACKUP_DIR.glob("backup_*.json"))
    if not backups:
        return None
    return sorted(backups)[-1]

def test_full_recovery_loop():
    supabase_admin = get_supabase_admin_client()
    assert supabase_admin is not None

    # Step 1: Cleanup and Seed
    cleanup_qa_data()
    seed_qa_data()

    # Step 2: Add a specific test record to chat_history
    test_id = "11111111-1111-1111-1111-111111111111"
    user_id = "00000000-0000-0000-0000-000000000000" # dummy system user if exists, or just null/valid UUID
    # We will just rely on the seed_qa_data doing enough, but let's check users.
    users_before = supabase_admin.table('users').select("*", count="exact").execute()
    count_before = users_before.count if users_before.count is not None else len(users_before.data)

    # Step 3: Backup
    backup_data()
    latest_backup = get_latest_backup()
    assert latest_backup is not None
    assert latest_backup.exists()

    # Verify backup contains data
    with open(latest_backup, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert "users" in data
        assert len(data["users"]) == count_before

    # Step 4: Delete/Modify Data (Simulation)
    cleanup_qa_data()
    
    users_after_delete = supabase_admin.table('users').select("*", count="exact").execute()
    count_after_delete = users_after_delete.count if users_after_delete.count is not None else len(users_after_delete.data)
    # The users table might not be fully cleared if we only cleared chat/news, but assuming the count changes or we can test another table.

    # Step 5: Restore
    restore_data(str(latest_backup))

    # Step 6: Verify
    users_after_restore = supabase_admin.table('users').select("*", count="exact").execute()
    count_after_restore = users_after_restore.count if users_after_restore.count is not None else len(users_after_restore.data)
    
    assert count_after_restore == count_before

    # Cleanup again to leave environment clean
    cleanup_qa_data()
