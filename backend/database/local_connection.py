"""
Local PostgreSQL connection layer for development.

This module provides a bridge between local PostgreSQL and Supabase-compatible API
for development when Supabase is not available.
"""

import os
import logging
from typing import Optional, List, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

class LocalPostgreSQLClient:
    """Local PostgreSQL client that mimics Supabase client interface"""

    def __init__(self):
        self.connection_params = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'database': os.getenv('DB_NAME', 'cybersecurity_platform'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', 'postgres')
        }
        self._connection = None

    def _get_connection(self):
        """Get or create PostgreSQL connection"""
        if self._connection is None or self._connection.closed:
            try:
                self._connection = psycopg2.connect(**self.connection_params)
                logger.info(f"✅ Connected to local PostgreSQL: {self.connection_params['host']}:{self.connection_params['port']}/{self.connection_params['database']}")
            except Exception as e:
                logger.error(f"❌ Failed to connect to PostgreSQL: {e}")
                raise
        return self._connection

    def table(self, table_name: str):
        """Return a table-like interface for Supabase compatibility"""
        return TableOperations(self._get_connection(), table_name)

    def close(self):
        """Close the database connection"""
        if self._connection and not self._connection.closed:
            self._connection.close()
            logger.info("🔌 Database connection closed")

class TableOperations:
    """Mimics Supabase table operations for local PostgreSQL"""

    def __init__(self, connection, table_name: str):
        self.conn = connection
        self.table_name = table_name

    def select(self, columns: str = '*'):
        """Start a SELECT query"""
        return QueryBuilder(self.conn, self.table_name, 'SELECT', columns)

    def insert(self, data: Dict[str, Any], returning: str = '*'):
        """Execute an INSERT query"""
        return QueryBuilder(self.conn, self.table_name, 'INSERT', None, data, returning)

    def update(self, data: Dict[str, Any], returning: str = '*'):
        """Start an UPDATE query"""
        return QueryBuilder(self.conn, self.table_name, 'UPDATE', None, data, returning)

    def delete(self, returning: str = '*'):
        """Start a DELETE query"""
        return QueryBuilder(self.conn, self.table_name, 'DELETE', None, None, returning)

class QueryBuilder:
    """Build and execute SQL queries with Supabase-like interface"""

    def __init__(self, connection, table_name: str, operation: str,
                 columns: str = None, data: Dict[str, Any] = None, returning: str = '*'):
        self.conn = connection
        self.table_name = table_name
        self.operation = operation
        self.columns = columns or '*'
        self.data = data or {}
        self.returning = returning
        self.filters = []
        self.limit_value = None
        self.offset_value = None
        self.order_by_clause = None
        self._not_mode = False  # Initialize NOT modifier state

    def filter(self, condition: str, *args):
        """Add WHERE condition (for simple cases)"""
        # This is a simplified implementation
        # For full compatibility, you'd need to parse complex conditions
        logger.warning("filter() method needs implementation for complex queries")
        return self

    def eq(self, column: str, value: Any):
        """Add equality condition"""
        self.filters.append(f"{column} = %s")
        self.filter_values = getattr(self, 'filter_values', [])
        self.filter_values.append(value)
        return self

    def not_(self):
        """Add NOT modifier for next condition - returns self for chaining"""
        # Store NOT state for next condition
        self._not_mode = True
        return self

    def is_(self, column: str, value: str):
        """Add IS condition (for NULL checks)"""
        operator = 'IS NOT' if self._not_mode else 'IS'
        normalized_value = 'NULL' if value.lower() == 'null' else value
        self.filters.append(f"{column} {operator} {normalized_value}")
        self._not_mode = False
        return self

    def limit(self, count: int):
        """Add LIMIT clause"""
        self.limit_value = count
        return self

    def offset(self, count: int):
        """Add OFFSET clause"""
        self.offset_value = count
        return self

    def order(self, column: str, desc: bool = False):
        """Add ORDER BY clause"""
        direction = 'DESC' if desc else 'ASC'
        self.order_by_clause = f"ORDER BY {column} {direction}"
        return self

    def execute(self):
        """Execute the built query"""
        try:
            cursor = self.conn.cursor(cursor_factory=RealDictCursor)

            if self.operation == 'SELECT':
                query = f"SELECT {self.columns} FROM {self.table_name}"
                params = []

                # Add filters
                if hasattr(self, 'filters') and self.filters:
                    query += " WHERE " + " AND ".join(self.filters)
                    params = getattr(self, 'filter_values', [])

                # Add ordering
                if self.order_by_clause:
                    query += f" {self.order_by_clause}"

                # Add limit
                if self.limit_value:
                    query += f" LIMIT {self.limit_value}"

                # Add offset
                if self.offset_value:
                    query += f" OFFSET {self.offset_value}"

                cursor.execute(query, params)
                results = cursor.fetchall()
                cursor.close()

                return ExecuteResult(data=results, error=None)

            elif self.operation == 'INSERT':
                columns = ', '.join(self.data.keys())
                placeholders = ', '.join(['%s'] * len(self.data))
                query = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})"

                if self.returning:
                    query += f" RETURNING {self.returning}"

                cursor.execute(query, list(self.data.values()))

                if self.returning:
                    result = cursor.fetchone()
                    cursor.close()
                    self.conn.commit()
                    return ExecuteResult(data=[result], error=None)
                else:
                    cursor.close()
                    self.conn.commit()
                    return ExecuteResult(data=[], error=None)

            elif self.operation == 'UPDATE':
                # Simplified UPDATE - would need WHERE clause implementation
                set_clause = ', '.join([f"{k} = %s" for k in self.data.keys()])
                query = f"UPDATE {self.table_name} SET {set_clause}"

                if hasattr(self, 'filters') and self.filters:
                    query += " WHERE " + " AND ".join(self.filters)
                    params = list(self.data.values()) + getattr(self, 'filter_values', [])
                else:
                    params = list(self.data.values())

                if self.returning:
                    query += f" RETURNING {self.returning}"

                cursor.execute(query, params)

                if self.returning:
                    result = cursor.fetchall()
                    cursor.close()
                    self.conn.commit()
                    return ExecuteResult(data=result, error=None)
                else:
                    cursor.close()
                    self.conn.commit()
                    return ExecuteResult(data=[], error=None)

            elif self.operation == 'DELETE':
                query = f"DELETE FROM {self.table_name}"
                params = []

                if hasattr(self, 'filters') and self.filters:
                    query += " WHERE " + " AND ".join(self.filters)
                    params = getattr(self, 'filter_values', [])

                if self.returning:
                    query += f" RETURNING {self.returning}"

                cursor.execute(query, params)

                if self.returning:
                    result = cursor.fetchall()
                    cursor.close()
                    self.conn.commit()
                    return ExecuteResult(data=result, error=None)
                else:
                    cursor.close()
                    self.conn.commit()
                    return ExecuteResult(data=[], error=None)

        except Exception as e:
            logger.error(f"❌ Query execution failed: {e}")
            self.conn.rollback()
            return ExecuteResult(data=None, error=str(e))

class ExecuteResult:
    """Mimics Supabase query result"""
    def __init__(self, data: List[Dict] = None, error: str = None):
        self.data = data or []
        self.error = error

# Global instances
local_client: Optional[LocalPostgreSQLClient] = None
local_admin_client: Optional[LocalPostgreSQLClient] = None

def get_local_client() -> LocalPostgreSQLClient:
    """Get local PostgreSQL client (mimics Supabase public client)"""
    global local_client
    if local_client is None:
        local_client = LocalPostgreSQLClient()
    return local_client

def get_local_admin_client() -> LocalPostgreSQLClient:
    """Get local PostgreSQL admin client (same as regular client for local)"""
    global local_admin_client
    if local_admin_client is None:
        local_admin_client = LocalPostgreSQLClient()
    return local_admin_client

def is_local_available() -> bool:
    """Check if local PostgreSQL is available"""
    try:
        client = get_local_client()
        conn = client._get_connection()
        return conn is not None and not conn.closed
    except:
        return False
