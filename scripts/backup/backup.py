import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# Add the project root to sys.path
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.database.connection import get_supabase_admin_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BACKUP_DIR = Path(__file__).parent.parent.parent / "testing" / "recovery" / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

TABLES_TO_BACKUP = ["users", "chat_history", "security_news"]

def backup_data():
    supabase_admin = get_supabase_admin_client()
    if not supabase_admin:
        logger.error("Failed to connect to Supabase admin client.")
        sys.exit(1)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"backup_{timestamp}.json"
    
    backup_data = {}
    
    for table in TABLES_TO_BACKUP:
        try:
            logger.info(f"Backing up table {table}...")
            # Ideally use pagination for large tables, but for testing we can fetch all
            res = supabase_admin.table(table).select("*").execute()
            backup_data[table] = res.data
        except Exception as e:
            logger.error(f"Error backing up {table}: {e}")
            sys.exit(1)

    with open(backup_file, "w", encoding="utf-8") as f:
        json.dump(backup_data, f, indent=2, ensure_ascii=False)
        
    logger.info(f"✅ Backup successfully written to {backup_file}")
    
if __name__ == "__main__":
    backup_data()
