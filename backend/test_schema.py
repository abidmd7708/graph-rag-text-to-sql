import unittest
from unittest.mock import patch

from backend.schema import format_schema, get_database_schema


class FakeCursor:
    def __init__(self, result_sets):
        self.result_sets = iter(result_sets)
        self.executed = []

    def execute(self, query):
        self.executed.append(query)

    def fetchall(self):
        return next(self.result_sets)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class FakeConnection:
    def __init__(self, cursor):
        self.fake_cursor = cursor

    def cursor(self):
        return self.fake_cursor

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class SchemaTests(unittest.TestCase):
    def test_extracts_columns_primary_keys_and_foreign_keys(self):
        cursor = FakeCursor([
            [("customers", "id", "integer", 1), ("customers", "name", "text", 2),
             ("orders", "customer_id", "integer", 1)],
            [("customers", "id")],
            [("orders", "customer_id", "customers", "id")],
        ])
        with patch("backend.schema.get_connection", return_value=FakeConnection(cursor)):
            schema = get_database_schema()
        self.assertEqual(schema["customers"]["columns"][1]["name"], "name")
        self.assertEqual(schema["customers"]["primary_keys"], ["id"])
        self.assertEqual(schema["orders"]["foreign_keys"], [{
            "column": "customer_id", "references_table": "customers", "references_column": "id"
        }])
        self.assertEqual(len(cursor.executed), 3)

    def test_format_schema_includes_key_annotations_and_legacy_format(self):
        schema = {"orders": {
            "columns": [{"name": "id", "type": "integer"}, {"name": "customer_id", "type": "integer"}],
            "primary_keys": ["id"],
            "foreign_keys": [{"column": "customer_id", "references_table": "customers", "references_column": "id"}],
        }}
        formatted = format_schema(schema)
        self.assertIn("id integer [PRIMARY KEY]", formatted)
        self.assertIn("customer_id integer [FOREIGN KEY -> customers.id]", formatted)
        self.assertIn("name text", format_schema({"customers": [{"column": "name", "type": "text"}]}))


if __name__ == "__main__":
    unittest.main()
