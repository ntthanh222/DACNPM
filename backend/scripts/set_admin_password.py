"""
Admin Password Management Utility

This script provides secure password management for admin users.
It generates proper bcrypt hashes and updates existing users in the database.
"""
import sys
import getpass
import logging
from datetime import datetime, timezone

try:
    from backend.database.connection import supabase_admin, is_database_available
    from backend.api.auth import hash_password
except ImportError as e:
    print(f"❌ Error importing required modules: {e}")
    print("Make sure you're running this from the backend directory with all dependencies installed.")
    sys.exit(1)


def set_user_password(username: str, email: str, password: str, force: bool = False) -> bool:
    """
    Set password for an existing user using proper bcrypt hashing.

    Args:
        username: Username to update
        email: Email for verification
        password: New password to set
        force: Skip confirmation prompts

    Returns:
        True if successful, False otherwise
    """
    try:
        # Check database availability
        if not is_database_available():
            print("❌ Database is not available. Check your connection.")
            return False

        # Get current user
        user_response = supabase_admin.table('users').select('*').eq('username', username).execute()

        if not user_response.data:
            print(f"❌ User '{username}' not found in database.")
            return False

        user = user_response.data[0]

        # Verify email matches
        if user.get('email') != email:
            print(f"❌ Email mismatch. Expected: {user.get('email')}, Got: {email}")
            return False

        # Confirm operation
        if not force:
            print(f"\n👤 User found:")
            print(f"   Username: {user.get('username')}")
            print(f"   Email: {user.get('email')}")
            print(f"   Role: {user.get('role')}")
            print(f"   Has password: {'Yes' if user.get('password_hash') else 'No'}")

            confirm = input(f"\n⚠️  Set new password for '{username}'? (yes/no): ").strip().lower()
            if confirm not in ['yes', 'y']:
                print("❌ Operation cancelled.")
                return False

        # Generate bcrypt hash
        print(f"🔐 Generating bcrypt hash...")
        hashed_password = hash_password(password)

        # Update user with new password hash
        print(f"🔄 Updating user password in database...")
        update_response = supabase_admin.table('users').update({
            'password_hash': hashed_password,
            'updated_at': datetime.now(timezone.utc).isoformat()
        }).eq('username', username).execute()

        if update_response.data:
            print(f"✅ Password set successfully for user '{username}'")
            print(f"⏰ Updated at: {datetime.now(timezone.utc).isoformat()}")
            return True
        else:
            print(f"❌ Failed to update password")
            return False

    except Exception as e:
        print(f"❌ Error setting password: {type(e).__name__}: {e}")
        return False


def list_users_without_passwords():
    """List all users that don't have passwords set."""
    try:
        if not is_database_available():
            print("❌ Database is not available.")
            return

        print("🔍 Checking for users without passwords...")
        response = supabase_admin.table('users').select('*').execute()

        users_no_password = [
            user for user in response.data
            if not user.get('password_hash')
        ]

        if users_no_password:
            print(f"\n⚠️  Found {len(users_no_password)} user(s) without passwords:")
            for user in users_no_password:
                print(f"   • {user.get('username')} ({user.get('email')}) - Role: {user.get('role')}")
        else:
            print("✅ All users have passwords set.")

    except Exception as e:
        print(f"❌ Error listing users: {e}")


def main():
    """Main entry point for password management utility."""
    import argparse

    parser = argparse.ArgumentParser(description='Admin Password Management Utility')
    parser.add_argument('--list', action='store_true', help='List users without passwords')
    parser.add_argument('--username', type=str, help='Username to set password for')
    parser.add_argument('--email', type=str, help='Email for verification')
    parser.add_argument('--password', type=str, help='New password (or use --prompt)')
    parser.add_argument('--prompt', action='store_true', help='Prompt for password securely')
    parser.add_argument('--force', action='store_true', help='Skip confirmation prompts')

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if args.list:
        list_users_without_passwords()
    elif args.username and args.email:
        # Get password
        if args.prompt:
            password = getpass.getpass("Enter new password: ")
            confirm_password = getpass.getpass("Confirm new password: ")
            if password != confirm_password:
                print("❌ Passwords do not match.")
                sys.exit(1)
        elif args.password:
            password = args.password
        else:
            print("❌ Please provide --password or use --prompt")
            sys.exit(1)

        # Set password
        success = set_user_password(args.username, args.email, password, args.force)
        sys.exit(0 if success else 1)
    else:
        # Default: show help and list users
        parser.print_help()
        print("\n" + "="*50)
        list_users_without_passwords()


if __name__ == "__main__":
    main()
