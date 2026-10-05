import unittest
from unittest.mock import patch

from fastapi import HTTPException

from backend import main
from backend.graph import build_schema_graph


def fixture_graph():
    return build_schema_graph({
        "customers": {"columns": [{"name": "id", "type": "integer"}, {"name": "name", "type": "text"}],
                      "primary_keys": ["id"], "foreign_keys": []},
        "orders": {"columns": [{"name": "customer_id", "type": "integer"}], "primary_keys": [],
                   "foreign_keys": [{"column": "customer_id", "references_table": "customers", "references_column": "id"}]},
        "audit_log": {"columns": [{"name": "id", "type": "integer"}], "primary_keys": ["id"], "foreign_keys": []},
    })


class FakeCursor:
    description = [type("Description", (), {"name": "name"})()]

    def __init__(self):
        self.statements = []

    def execute(self, statement):
        self.statements.append(statement)

    def fetchall(self):
        return [("Ada",)]

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


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.previous_graph = main._schema_graph
        main._schema_graph = fixture_graph()

    def tearDown(self):
        main._schema_graph = self.previous_graph

    def test_query_uses_retrieved_context_and_returns_explanation_and_results(self):
        with patch("backend.main.generate_sql", return_value="SELECT name FROM customers" ) as generate, \
             patch("backend.main.execute_sql", return_value=(["name"], [("Ada",)])):
            result = main.query_database(main.QueryRequest(question="Which customers?"))
        self.assertEqual(result["retrieved_tables"], ["customers", "orders"])
        self.assertTrue(result["retrieval_explanation"])
        self.assertEqual(result["results"], [{"name": "Ada"}])
        self.assertIn("TABLE: customers", generate.call_args.args[1])
        self.assertIn("TABLE: orders", generate.call_args.args[1])
        self.assertNotIn("TABLE: audit_log", generate.call_args.args[1])

    def test_rejects_empty_question_and_invalid_generated_sql(self):
        with self.assertRaises(HTTPException) as empty:
            main.query_database(main.QueryRequest(question="  "))
        self.assertEqual(empty.exception.status_code, 400)
        with patch("backend.main.generate_sql", return_value="DROP TABLE customers"):
            with self.assertRaises(HTTPException) as invalid:
                main.query_database(main.QueryRequest(question="customers"))
        self.assertEqual(invalid.exception.status_code, 400)

    def test_execution_starts_read_only_transaction(self):
        cursor = FakeCursor()
        with patch("backend.main.get_connection", return_value=FakeConnection(cursor)):
            columns, rows = main.execute_sql("SELECT name FROM customers")
        self.assertEqual(cursor.statements[0], "SET TRANSACTION READ ONLY")
        self.assertEqual(columns, ["name"])
        self.assertEqual(rows, [("Ada",)])


if __name__ == "__main__":
    unittest.main()
