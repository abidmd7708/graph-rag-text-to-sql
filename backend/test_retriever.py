import unittest

from backend.graph import build_schema_graph
from backend.retriever import retrieve_relevant_subgraph


def commerce_graph():
    return build_schema_graph({
        "customers": {"columns": [{"name": "id", "type": "integer"}, {"name": "name", "type": "text"}],
                      "primary_keys": ["id"], "foreign_keys": []},
        "orders": {"columns": [{"name": "id", "type": "integer"}, {"name": "account_key", "type": "integer"}],
                   "primary_keys": ["id"], "foreign_keys": [{"column": "account_key", "references_table": "customers", "references_column": "id"}]},
        "line_items": {"columns": [{"name": "receipt_key", "type": "integer"}, {"name": "goods_key", "type": "integer"}],
                        "primary_keys": [], "foreign_keys": [
                            {"column": "receipt_key", "references_table": "orders", "references_column": "id"},
                            {"column": "goods_key", "references_table": "inventory", "references_column": "id"}]},
        "inventory": {"columns": [{"name": "id", "type": "integer"}, {"name": "name", "type": "text"}],
                     "primary_keys": ["id"], "foreign_keys": []},
        "audit_log": {"columns": [{"name": "id", "type": "integer"}], "primary_keys": ["id"], "foreign_keys": []},
    })


class RetrieverTests(unittest.TestCase):
    def test_matches_terms_and_expands_to_join_table(self):
        result = retrieve_relevant_subgraph("Which customers placed the most orders?", commerce_graph())
        self.assertEqual(result["relevant_tables"], ["customers", "orders"])
        self.assertIn("orders.account_key -> customers.id", [r["path"] for r in result["relationships"]])
        self.assertTrue(any("matched question terms" in item["reason"] for item in result["explanation"]))
        self.assertIn("[PRIMARY KEY]", result["context"])

    def test_discovers_multi_hop_path_between_customer_and_inventory(self):
        result = retrieve_relevant_subgraph("Which customers spent most money on inventory?", commerce_graph(), max_hops=2)
        self.assertEqual(set(result["relevant_tables"]), {"customers", "orders", "line_items", "inventory"})
        self.assertTrue(any(len(path) == 4 for path in result["paths"]))
        self.assertNotIn("audit_log", result["relevant_tables"])

    def test_returns_empty_result_for_unmatched_question(self):
        result = retrieve_relevant_subgraph("Tell me the weather forecast", commerce_graph())
        self.assertEqual(result["relevant_tables"], [])
        self.assertEqual(result["context"], "")


if __name__ == "__main__":
    unittest.main()
