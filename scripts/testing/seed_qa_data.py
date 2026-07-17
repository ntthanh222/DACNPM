import os
import sys
import logging
from pathlib import Path

# Add the project root to sys.path
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.config.settings import get_settings
from backend.database.connection import get_supabase_admin_client
from testing.scripts.qa_guard import guard_or_exit

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_qa_data():
    guard_or_exit()
    settings = get_settings()
    if not settings.is_test():
        logger.error("Can only seed data in 'test' environment. Current environment: %s", settings.environment)
        sys.exit(1)

    supabase_admin = get_supabase_admin_client()
    if not supabase_admin:
        logger.error("Failed to connect to Supabase admin client.")
        sys.exit(1)

    logger.info("Connected to Test Supabase environment: %s", settings.supabase_url)

    # Note: Idempotent seeding.
    # In Supabase Auth, creating users via admin client:
    qa_admin_password = os.environ.get("QA_AUTH_ADMIN_PASSWORD")
    qa_user_password = os.environ.get("QA_AUTH_USER_PASSWORD")
    if not qa_admin_password or not qa_user_password:
        logger.error("Set QA_AUTH_ADMIN_PASSWORD and QA_AUTH_USER_PASSWORD before seeding Supabase Auth QA data.")
        sys.exit(2)

    qa_users = [
        {"email": "qa_admin@example.com", "password": qa_admin_password, "role": "admin"},
        {"email": "qa_user@example.com", "password": qa_user_password, "role": "user"}
    ]

    for user_data in qa_users:
        try:
            # Check if user exists
            # We can't directly list auth users easily, but we can try to sign up or create
            res = supabase_admin.auth.admin.create_user({
                "email": user_data["email"],
                "password": user_data["password"],
                "email_confirm": True
            })
            logger.info("Created user: %s", user_data["email"])
            
            # Note: A real app might also need to insert into the public.users table or set roles.
            # Assuming public.users is synced via trigger or needs manual insert.
        except Exception as e:
            if "already exists" in str(e).lower() or "User already registered" in str(e):
                logger.info("User %s already exists.", user_data["email"])
            else:
                logger.error("Error creating user %s: %s", user_data["email"], e)

    logger.info("QA data seeding completed.")

def cleanup_qa_data():
    guard_or_exit()
    settings = get_settings()
    if not settings.is_test():
        logger.error("Can only cleanup data in 'test' environment.")
        sys.exit(1)

    supabase_admin = get_supabase_admin_client()
    if not supabase_admin:
        logger.error("Failed to connect to Supabase admin client.")
        sys.exit(1)

    logger.info("Cleaning up QA data...")
    # Clean up operations would go here. For test projects, we might truncate tables.
    # Since we cannot easily delete auth users without their UUIDs, we'd query and delete.
    try:
        # We need the user UUIDs to delete them from auth.users.
        # As an example, we could just clear chat_history and security_news
        supabase_admin.table('chat_history').delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        supabase_admin.table('security_news').delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        logger.info("Test tables cleaned up.")
    except Exception as e:
        logger.error("Error during cleanup: %s", e)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--cleanup":
        cleanup_qa_data()
    else:
        seed_qa_data()
