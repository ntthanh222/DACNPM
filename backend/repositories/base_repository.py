"""
Generic Repository Pattern for Data Access Layer

Provides a base repository class that eliminates CRUD code duplication
and ensures consistent data access patterns across the application.
"""

from typing import Optional, List, Type, TypeVar, Generic, Dict, Any
from uuid import UUID
from abc import abstractmethod
import logging

from backend.database.connection import supabase, supabase_admin

# Generic type for model classes
T = TypeVar('T')


class BaseRepository(Generic[T]):
    """
    Generic base repository for common CRUD operations.

    Provides automatic client selection (admin vs regular),
    consistent error handling, and standard CRUD operations.

    Type Parameters:
        T: The model type (e.g., Profile, ChatHistory, etc.)
    """

    def __init__(self, table_name: str, model_class: Type[T]):
        """
        Initialize the base repository.

        Args:
            table_name: Database table name
            model_class: Pydantic model class for deserialization
        """
        self.table_name = table_name
        self.model_class = model_class
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    def _get_client(self):
        """
        Get database client with admin fallback.

        Returns:
            Database client (admin client preferred to bypass RLS)
        """
        return supabase_admin if supabase_admin else supabase

    def _is_client_available(self) -> bool:
        """
        Check if any database client is available.

        Returns:
            True if at least one client is available
        """
        return supabase_admin is not None or supabase is not None

    def _handle_error(self, error: Exception, operation: str, context: str = "") -> None:
        """
        Centralized error handling with logging.

        Args:
            error: The exception that occurred
            operation: Operation being performed (e.g., "fetching profile")
            context: Additional context information
        """
        error_msg = f"Error {operation}"
        if context:
            error_msg += f" ({context})"
        error_msg += f": {error}"
        self.logger.error(error_msg)

    def find_by_id(self, id: UUID) -> Optional[T]:
        """
        Find a single record by ID.

        Args:
            id: Record ID to search for

        Returns:
            Model instance or None if not found
        """
        if not self._is_client_available():
            self.logger.warning(f"Database unavailable - cannot find {self.table_name} by id")
            return None

        try:
            client = self._get_client()
            response = client.table(self.table_name).select('*').eq('id', str(id)).execute()

            if response.data:
                return self.model_class(**response.data[0])
            return None

        except Exception as e:
            self._handle_error(e, f"fetching {self.table_name} with id {id}")
            return None

    def find_by_field(self, field_name: str, field_value: Any) -> Optional[T]:
        """
        Find a single record by a specific field.

        Args:
            field_name: Name of the field to search
            field_value: Value to search for

        Returns:
            Model instance or None if not found
        """
        if not self._is_client_available():
            self.logger.warning(f"Database unavailable - cannot find {self.table_name} by {field_name}")
            return None

        try:
            client = self._get_client()
            response = client.table(self.table_name).select('*').eq(field_name, str(field_value)).execute()

            if response.data:
                return self.model_class(**response.data[0])
            return None

        except Exception as e:
            self._handle_error(e, f"fetching {self.table_name} by {field_name}={field_value}")
            return None

    def find_all(self, skip: int = 0, limit: int = 100, **filters) -> List[T]:
        """
        Find multiple records with optional filtering and pagination.

        Args:
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return
            **filters: Additional field filters

        Returns:
            List of model instances
        """
        if not self._is_client_available():
            self.logger.warning(f"Database unavailable - cannot find {self.table_name} records")
            return []

        try:
            client = self._get_client()
            query = client.table(self.table_name).select('*')

            # Apply filters
            for field_name, field_value in filters.items():
                query = query.eq(field_name, str(field_value))

            # Apply pagination
            response = query.range(skip, skip + limit - 1).execute()

            return [self.model_class(**item) for item in response.data]

        except Exception as e:
            self._handle_error(e, f"fetching {self.table_name} records")
            return []

    def create(self, entity_create: Dict[str, Any]) -> Optional[T]:
        """
        Create a new record.

        Args:
            entity_create: Dictionary containing entity data

        Returns:
            Created model instance or None if failed
        """
        if not self._is_client_available():
            self.logger.error(f"Database unavailable - cannot create {self.table_name}")
            return None

        try:
            client = self._get_client()
            response = client.table(self.table_name).insert(entity_create).execute()

            if response.data:
                return self.model_class(**response.data[0])

            raise Exception("No data returned from insert operation")

        except Exception as e:
            self._handle_error(e, f"creating {self.table_name}")
            return None

    def update(self, id: UUID, entity_update: Dict[str, Any]) -> Optional[T]:
        """
        Update an existing record.

        Args:
            id: Record ID to update
            entity_update: Dictionary containing fields to update

        Returns:
            Updated model instance or None if failed
        """
        if not self._is_client_available():
            self.logger.error(f"Database unavailable - cannot update {self.table_name}")
            return None

        try:
            client = self._get_client()
            response = client.table(self.table_name).update(entity_update).eq('id', str(id)).execute()

            if response.data:
                return self.model_class(**response.data[0])

            # Return original record if update didn't change anything
            return self.find_by_id(id)

        except Exception as e:
            self._handle_error(e, f"updating {self.table_name} with id {id}")
            return None

    def delete(self, id: UUID) -> bool:
        """
        Delete a record by ID.

        Args:
            id: Record ID to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        if not self._is_client_available():
            self.logger.warning(f"Database unavailable - cannot delete {self.table_name}")
            return False

        try:
            client = self._get_client()
            response = client.table(self.table_name).delete().eq('id', str(id)).execute()

            return len(response.data) > 0

        except Exception as e:
            self._handle_error(e, f"deleting {self.table_name} with id {id}")
            return False

    def count(self, **filters) -> int:
        """
        Count records matching optional filters.

        Args:
            **filters: Field filters to apply

        Returns:
            Number of matching records
        """
        if not self._is_client_available():
            self.logger.warning(f"Database unavailable - cannot count {self.table_name}")
            return 0

        try:
            client = self._get_client()
            query = client.table(self.table_name).select('*', count='exact')

            # Apply filters
            for field_name, field_value in filters.items():
                query = query.eq(field_name, str(field_value))

            response = query.execute()
            return response.count if response.count is not None else 0

        except Exception as e:
            self._handle_error(e, f"counting {self.table_name} records")
            return 0

    def exists(self, id: UUID) -> bool:
        """
        Check if a record exists by ID.

        Args:
            id: Record ID to check

        Returns:
            True if record exists, False otherwise
        """
        return self.find_by_id(id) is not None


class FallbackRepository(BaseRepository[T]):
    """
    Extended repository with in-memory fallback capability.

    Provides automatic fallback to in-memory storage when database
    is unavailable, ensuring continuous operation.
    """

    def __init__(self, table_name: str, model_class: Type[T], fallback_storage: Dict[str, Any] = None):
        """
        Initialize the fallback repository.

        Args:
            table_name: Database table name
            model_class: Pydantic model class for deserialization
            fallback_storage: In-memory storage dictionary
        """
        super().__init__(table_name, model_class)
        self.fallback_storage = fallback_storage or {}

    @abstractmethod
    def _save_to_fallback(self, entity_data: Dict[str, Any]) -> None:
        """
        Save entity to fallback storage.

        Args:
            entity_data: Entity data to save
        """
        pass

    @abstractmethod
    def _get_from_fallback(self, **identifiers) -> Optional[Dict[str, Any]]:
        """
        Get entity from fallback storage.

        Args:
            **identifiers: Identifiers to search for

        Returns:
            Entity data or None if not found
        """
        pass

    @abstractmethod
    def _get_all_from_fallback(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get all entities from fallback storage.

        Args:
            limit: Maximum number of entities to return

        Returns:
            List of entity data
        """
        pass

    @abstractmethod
    def _delete_from_fallback(self, **identifiers) -> bool:
        """
        Delete entity from fallback storage.

        Args:
            **identifiers: Identifiers to locate entity

        Returns:
            True if deleted, False otherwise
        """
        pass

    def create(self, entity_create: Dict[str, Any]) -> Optional[T]:
        """
        Create with automatic fallback to in-memory storage.

        Args:
            entity_create: Dictionary containing entity data

        Returns:
            Created model instance or None if failed
        """
        # Try database first
        result = super().create(entity_create)
        if result:
            return result

        # Fallback to in-memory storage
        self.logger.warning(f"Database unavailable - saving {self.table_name} to memory")
        try:
            self._save_to_fallback(entity_create)
            # Return a model instance for compatibility
            return self.model_class(**entity_create)
        except Exception as e:
            self._handle_error(e, f"saving {self.table_name} to fallback storage")
            return None

    def find_all(self, skip: int = 0, limit: int = 100, **filters) -> List[T]:
        """
        Find all with automatic fallback to in-memory storage.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            **filters: Additional field filters

        Returns:
            List of model instances
        """
        # Try database first
        if self._is_client_available():
            result = super().find_all(skip, limit, **filters)
            if result or not filters:  # If we got results or no filters
                return result

        # Fallback to in-memory storage
        self.logger.warning(f"Database unavailable - using in-memory {self.table_name}")
        try:
            fallback_data = self._get_all_from_fallback(limit)
            return [self.model_class(**item) for item in fallback_data[skip:skip + limit]]
        except Exception as e:
            self._handle_error(e, f"fetching {self.table_name} from fallback")
            return []

    def delete(self, id: UUID) -> bool:
        """
        Delete with automatic fallback to in-memory storage.

        Args:
            id: Record ID to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        # Try database first
        if self._is_client_available():
            result = super().delete(id)
            if result:
                return True

        # Fallback to in-memory deletion
        self.logger.warning(f"Database unavailable - deleting {self.table_name} from memory")
        try:
            return self._delete_from_fallback(id=str(id))
        except Exception as e:
            self._handle_error(e, f"deleting {self.table_name} from fallback")
            return False