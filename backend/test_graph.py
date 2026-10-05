import unittest

from backend.graph import build_schema_graph


class GraphTests(unittest.TestCase):
    def setUp(self):
        self.graph = build_schema_graph({
            "customers": {"columns": [{"name": "id", "type": "integer"}], "primary_keys": ["id"], "foreign_keys": []},
            "orders": {"columns": [{"name": "customer_id", "type": "integer"}], "primary_keys": [],
                       "foreign_keys": [{"column": "customer_id", "references_table": "customers", "references_column": "id"}]},
        })

    def test_builds_table_column_key_and_reference_edges(self):
        self.assertEqual(self.graph.nodes["table:customers"]["type"], "table")
        self.assertTrue(self.graph.nodes["column:customers.id"]["primary_key"])
        self.assertIn({"source": "table:customers", "target": "column:customers.id", "type": "PRIMARY_KEY"}, self.graph.edges)
        references = [edge for edge in self.graph.edges if edge["type"] == "REFERENCES"]
        self.assertEqual(references[0]["target_table"], "customers")
        self.assertIn("HAS_TABLE", [edge["type"] for edge in self.graph.edges])

    def test_traverses_foreign_key_relationship(self):
        self.assertEqual(self.graph.table_paths("orders", max_hops=1)["customers"], ["orders", "customers"])


if __name__ == "__main__":
    unittest.main()
