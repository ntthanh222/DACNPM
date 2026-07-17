import os
import sys
import json
import logging
from pathlib import Path

# Add the project root to sys.path
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.config.settings import get_settings
from backend.database.connection import get_supabase_admin_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TABLES_TO_RESTORE = ["users", "chat_history", "security_news"]

def restore_data(backup_file: str):
    settings = get_settings()
    
    if not settings.is_test():
        # Only allow restore in non-test environments if specifically confirmed
        confirm = os.environ.get("CONFIRM_PRODUCTION_RESTORE")
        if confirm != "YES_I_KNOW_WHAT_I_AM_DOING":
            logger.error("Restore aborted. To restore outside of test environment, set CONFIRM_PRODUCTION_RESTORE=YES_I_KNOW_WHAT_I_AM_DOING")
            sys.exit(1)

    supabase_admin = get_supabase_admin_client()
    if not supabase_admin:
        logger.error("Failed to connect to Supabase admin client.")
        sys.exit(1)

    backup_path = Path(backup_file)
    if not backup_path.exists():
        logger.error(f"Backup file not found: {backup_file}")
        sys.exit(1)
        
    with open(backup_path, "r", encoding="utf-8") as f:
        backup_data = json.load(f)
        
    for table in TABLES_TO_RESTORE:
        if table in backup_data:
            logger.info(f"Restoring table {table} with {len(backup_data[table])} records...")
            # For simplicity, we clear and then insert. In reality, upsert would be safer.
            try:
                if settings.is_test():
                    supabase_admin.table(table).delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
                
                if backup_data[table]:
                    supabase_admin.table(table).upsert(backup_data[table]).execute()
                logger.info(f"✅ Table {table} restored successfully.")
            except Exception as e:
                logger.error(f"Error restoring table {table}: {e}")
                sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python restore.py <path_to_backup_json>")
        sys.exit(1)
    restore_data(sys.argv[1])
