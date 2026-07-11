"""
Profile Repository - Specific implementation for user profiles

Demonstrates how to extend BaseRepository for domain-specific operations.
"""

from typing import Optional, List
from uuid import UUID
from backend.repositories.base_repository import BaseRepository
from backend.database.models import Profile, ProfileCreate, ProfileUpdate


class ProfileRepository(BaseRepository[Profile]):
    """
    Repository for user profile operations.

    Inherits generic CRUD operations from BaseRepository and adds
    domain-specific methods for profile management.
    """

    def __init__(self):
        """Initialize the profile repository."""
        super().__init__('profiles', Profile)

    def find_by_username(self, username: str) -> Optional[Profile]:
        """
        Find a profile by username.

        Args:
            username: Username to search for

        Returns:
            Profile instance or None if not found
        """
        return self.find_by_field('username', username)

    def find_by_email(self, email: str) -> Optional[Profile]:
        """
        Find a profile by email.

        Args:
            email: Email to search for

        Returns:
            Profile instance or None if not found
        """
        return self.find_by_field('email', email)

    def create_profile(self, profile_create: ProfileCreate) -> Optional[Profile]:
        """
        Create a new profile.

        Args:
            profile_create: Profile creation data

        Returns:
            Created profile or None if failed
        """
        # Convert Pydantic model to dictionary
        profile_data = {
            'username': profile_create.username,
            'full_name': profile_create.full_name,
        }

        # Add optional fields
        if profile_create.avatar_url:
            profile_data['avatar_url'] = profile_create.avatar_url

        if profile_create.id:
            profile_data['id'] = str(profile_create.id)

        return self.create(profile_data)

    def update_profile(self, profile_id: UUID, profile_update: ProfileUpdate) -> Optional[Profile]:
        """
        Update an existing profile.

        Args:
            profile_id: Profile ID to update
            profile_update: Profile update data

        Returns:
            Updated profile or None if failed
        """
        # Convert Pydantic model to dictionary (only include set fields)
        update_data = profile_update.model_dump(exclude_unset=True)

        if not update_data:
            return self.find_by_id(profile_id)

        return self.update(profile_id, update_data)

    def search_profiles(self, search_term: str, limit: int = 10) -> List[Profile]:
        """
        Search profiles by username or full name.

        Args:
            search_term: Search term to look for
            limit: Maximum results to return

        Returns:
            List of matching profiles
        """
        if not self._is_client_available():
            self.logger.warning("Database unavailable - cannot search profiles")
            return []

        try:
            client = self._get_client()

            # Search using ilike for case-insensitive partial matching
            response = client.table(self.table_name).select('*').or_(
                f'username.ilike.%{search_term}%,full_name.ilike.%{search_term}%'
            ).limit(limit).execute()

            return [Profile(**item) for item in response.data]

        except Exception as e:
            self._handle_error(e, f"searching profiles with term '{search_term}'")
            return []

    def get_active_profiles(self, limit: int = 100) -> List[Profile]:
        """
        Get recently active profiles.

        Args:
            limit: Maximum profiles to return

        Returns:
            List of active profiles
        """
        if not self._is_client_available():
            self.logger.warning("Database unavailable - cannot get active profiles")
            return []

        try:
            client = self._get_client()

            # Get profiles ordered by last_activity (if the field exists)
            response = client.table(self.table_name).select('*')\
                .order('last_activity', desc=True)\
                .limit(limit)\
                .execute()

            return [Profile(**item) for item in response.data]

        except Exception as e:
            self._handle_error(e, "fetching active profiles")
            # Fallback to basic find_all if ordering fails
            return self.find_all(limit=limit)


# Singleton instance for application-wide use
profile_repository = ProfileRepository()