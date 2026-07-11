import sys
import types

import pytest

psycopg2 = types.ModuleType("psycopg2")
psycopg2_extras = types.ModuleType("psycopg2.extras")
psycopg2_extras.RealDictCursor = object
psycopg2.extras = psycopg2_extras
sys.modules.setdefault("psycopg2", psycopg2)
sys.modules.setdefault("psycopg2.extras", psycopg2_extras)

from backend.database.local_connection import QueryBuilder


class CursorStub:
    def __init__(self):
        self.executed = []
        self.closed = False

    def execute(self, query, params):
        self.executed.append((query, params))

    def fetchone(self):
        return {"id": 1}

    def fetchall(self):
        return [{"id": 1}]

    def close(self):
        self.closed = True


class ConnectionStub:
    def __init__(self):
        self.cursor_instance = CursorStub()
        self.commits = 0
        self.rollbacks = 0

    def cursor(self, **_kwargs):
        return self.cursor_instance

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def test_query_builder_select_preserves_filters_order_and_pagination():
    connection = ConnectionStub()

    result = (
        QueryBuilder(connection, "chat_history", "SELECT", "id")
        .eq("user_id", "user-1")
        .order("created_at", desc=True)
        .limit(10)
        .offset(5)
        .execute()
    )

    assert result.data == [{"id": 1}]
    assert result.error is None
    assert connection.cursor_instance.executed == [
        (
            "SELECT id FROM chat_history WHERE user_id = %s ORDER BY created_at DESC LIMIT 10 OFFSET 5",
            ["user-1"],
        )
    ]
    assert connection.cursor_instance.closed is True
    assert connection.commits == 0


@pytest.mark.parametrize(
    ("operation", "expected_query", "expected_params", "expected_data"),
    [
        (
            "INSERT",
            "INSERT INTO users (name) VALUES (%s) RETURNING *",
            ["Ada"],
            [{"id": 1}],
        ),
        (
            "UPDATE",
            "UPDATE users SET name = %s WHERE id = %s RETURNING *",
            ["Ada", 1],
            [{"id": 1}],
        ),
        (
            "DELETE",
            "DELETE FROM users WHERE id = %s RETURNING *",
            [1],
            [{"id": 1}],
        ),
    ],
)
def test_query_builder_write_operations_preserve_queries_and_results(
    operation, expected_query, expected_params, expected_data
):
    connection = ConnectionStub()
    builder = QueryBuilder(connection, "users", operation, data={"name": "Ada"})

    if operation == "UPDATE":
        builder.eq("id", 1)
    if operation == "DELETE":
        builder.data = {}
        builder.eq("id", 1)

    result = builder.execute()

    assert result.data == expected_data
    assert result.error is None
    assert connection.cursor_instance.executed == [(expected_query, expected_params)]
    assert connection.cursor_instance.closed is True
    assert connection.commits == 1
