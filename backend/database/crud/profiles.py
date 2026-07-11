from typing import Optional, List
from uuid import UUID
from backend.database.connection import supabase, supabase_admin
from backend.database.models import Profile, ProfileCreate, ProfileUpdate


def get_profile(profile_id: UUID) -> Optional[Profile]:
    """
    Get a profile by ID with admin client fallback to bypass RLS
    """
    # Try admin client first (bypasses RLS)
    if supabase_admin:
        try:
            response = supabase_admin.table('profiles').select('*').eq('id', str(profile_id)).execute()
            if response.data:
                return Profile(**response.data[0])
            return None
        except Exception as admin_error:
            print(f"Admin client error fetching profile {profile_id}: {admin_error}")

    # Fallback to regular client (may be blocked by RLS)
    if not supabase:
        return None

    try:
        response = supabase.table('profiles').select('*').eq('id', str(profile_id)).execute()
        if response.data:
            return Profile(**response.data[0])
        return None
    except Exception as e:
        print(f"Error fetching profile {profile_id}: {e}")
        return None


def get_profile_by_username(username: str) -> Optional[Profile]:
    """
    Get a profile by username
    Security: Uses supabase_admin to bypass RLS for authentication/registration checks
    """
    # Try admin client first (bypasses RLS for auth checks)
    if supabase_admin:
        try:
            response = supabase_admin.table('profiles').select('*').eq('username', username).execute()
            if response.data:
                return Profile(**response.data[0])
            return None
        except Exception as admin_error:
            print(f"Admin client error fetching profile by username {username}: {admin_error}")

    # Fallback to regular client (may be blocked by RLS)
    if not supabase:
        return None

    try:
        response = supabase.table('profiles').select('*').eq('username', username).execute()
        if response.data:
            return Profile(**response.data[0])
        return None
    except Exception as e:
        print(f"Error fetching profile by username {username}: {e}")
        return None


def create_profile(profile: ProfileCreate) -> Profile:
    """Create a new profile"""
    try:
        # Use supabase_admin if available to bypass RLS for registration/creation
        client = supabase_admin if supabase_admin else supabase
        if not client:
            raise Exception("No database client available")

        insert_data = {
            'username': profile.username,
            'full_name': profile.full_name,
            'avatar_url': profile.avatar_url
        }
        if profile.id:
            insert_data['id'] = str(profile.id)

        response = client.table('profiles').insert(insert_data).execute()
        if response.data:
            return Profile(**response.data[0])
        raise Exception("No data returned from insert operation")
    except Exception as e:
        print(f"Error creating profile: {e}")
        raise


def update_profile(profile_id: UUID, profile_update: ProfileUpdate) -> Optional[Profile]:
    """Update a profile"""
    try:
        # Use supabase_admin if available to bypass RLS
        client = supabase_admin if supabase_admin else supabase
        if not client:
            raise Exception("No database client available")

        update_data = profile_update.model_dump(exclude_unset=True)
        if update_data:
            response = client.table('profiles').update(update_data).eq('id', str(profile_id)).execute()
            if response.data:
                return Profile(**response.data[0])
        return get_profile(profile_id)
    except Exception as e:
        print(f"Error updating profile {profile_id}: {e}")
        return None


def delete_profile(profile_id: UUID) -> bool:
    """Delete a profile"""
    try:
        # Use supabase_admin if available to bypass RLS
        client = supabase_admin if supabase_admin else supabase
        if not client:
            raise Exception("No database client available")

        response = client.table('profiles').delete().eq('id', str(profile_id)).execute()
        return len(response.data) > 0
    except Exception as e:
        print(f"Error deleting profile {profile_id}: {e}")
        return False
