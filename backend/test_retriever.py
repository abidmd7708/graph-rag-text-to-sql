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

    def test_single_table_question_does_not_expand_connected_schema(self):
        graph = build_schema_graph({
            "employees": {"columns": [{"name": "employee_code", "type": "integer"}],
                          "primary_keys": ["employee_code"], "foreign_keys": []},
            "departments": {"columns": [{"name": "department_code", "type": "integer"}],
                            "primary_keys": ["department_code"], "foreign_keys": [
                                {"column": "department_code", "references_table": "employees",
                                 "references_column": "employee_code"},
                            ]},
            "offices": {"columns": [{"name": "office_code", "type": "integer"}],
                        "primary_keys": ["office_code"], "foreign_keys": []},
        })
        result = retrieve_relevant_subgraph("How many employees are there?", graph)
        self.assertEqual(result["relevant_tables"], ["employees"])

    def test_connects_synthetic_students_and_courses_through_enrollments(self):
        graph = build_schema_graph({
            "students": {"columns": [
                {"name": "student_key", "type": "integer"},
                {"name": "student_name", "type": "text"},
                {"name": "contact_address", "type": "text"}],
                         "primary_keys": ["student_key"], "foreign_keys": []},
            "enrollments": {"columns": [
                {"name": "student_ref", "type": "integer"},
                {"name": "course_ref", "type": "integer"},
                {"name": "recorded_at", "type": "timestamp"}], "primary_keys": [],
                "foreign_keys": [
                    {"column": "student_ref", "references_table": "students", "references_column": "student_key"},
                    {"column": "course_ref", "references_table": "courses", "references_column": "course_key"},
                ]},
            "courses": {"columns": [
                {"name": "course_key", "type": "integer"},
                {"name": "course_title", "type": "text"},
                {"name": "internal_notes", "type": "text"}],
                        "primary_keys": ["course_key"], "foreign_keys": []},
        })
        result = retrieve_relevant_subgraph(
            "Which students are enrolled in a particular course?", graph, max_hops=1
        )
        self.assertEqual(result["relevant_tables"], ["courses", "enrollments", "students"])
        self.assertTrue(any(len(path) == 3 for path in result["paths"]))
        self.assertEqual(len(result["relationships"]), 2)
        columns = {entry["table"]: set(entry["columns"]) for entry in result["relevant_columns"]}
        self.assertEqual(columns["students"], {"student_key", "student_name"})
        self.assertEqual(columns["enrollments"], {"student_ref", "course_ref"})
        self.assertEqual(columns["courses"], {"course_key", "course_title"})
        self.assertNotIn("contact_address", result["context"])
        self.assertNotIn("recorded_at", result["context"])
        self.assertNotIn("internal_notes", result["context"])

    def test_only_includes_required_branch_of_connected_graph(self):
        graph = build_schema_graph({
            "alpha": {"columns": [{"name": "alpha_key", "type": "integer"}], "primary_keys": ["alpha_key"], "foreign_keys": []},
            "beta": {"columns": [{"name": "alpha_ref", "type": "integer"}, {"name": "beta_key", "type": "integer"}], "primary_keys": ["beta_key"], "foreign_keys": [
                {"column": "alpha_ref", "references_table": "alpha", "references_column": "alpha_key"},
            ]},
            "gamma": {"columns": [{"name": "beta_ref", "type": "integer"}], "primary_keys": [], "foreign_keys": [
                {"column": "beta_ref", "references_table": "beta", "references_column": "beta_key"},
            ]},
            "delta": {"columns": [{"name": "beta_ref", "type": "integer"}], "primary_keys": [], "foreign_keys": [
                {"column": "beta_ref", "type": "integer", "references_table": "beta", "references_column": "beta_key"},
            ]},
        })
        result = retrieve_relevant_subgraph("Show alpha and beta", graph)
        self.assertEqual(result["relevant_tables"], ["alpha", "beta"])
        self.assertEqual(len(result["relationships"]), 1)

    def test_hop_limit_controls_connections_between_seeds(self):
        graph = commerce_graph()
        question = "Which customers spent money on inventory?"
        self.assertEqual(
            retrieve_relevant_subgraph(question, graph, max_hops=0)["relevant_tables"],
            ["customers", "inventory"],
        )
        self.assertEqual(
            retrieve_relevant_subgraph(question, graph, max_hops=1)["relevant_tables"],
            ["customers", "inventory"],
        )
        self.assertEqual(
            set(retrieve_relevant_subgraph(question, graph, max_hops=2)["relevant_tables"]),
            {"customers", "orders", "line_items", "inventory"},
        )

    def test_specific_column_can_seed_without_table_name_match(self):
        graph = build_schema_graph({
            "geographic_records": {"columns": [{"name": "municipality", "type": "text"}],
                                   "primary_keys": [], "foreign_keys": []},
            "other_records": {"columns": [{"name": "record_key", "type": "integer"}],
                              "primary_keys": [], "foreign_keys": []},
        })
        result = retrieve_relevant_subgraph("Find municipality values", graph)
        self.assertEqual(result["relevant_tables"], ["geographic_records"])

    def test_column_context_keeps_primary_key_and_question_match_only(self):
        graph = build_schema_graph({
            "geographic_records": {"columns": [
                {"name": "record_key", "type": "integer"},
                {"name": "municipality", "type": "text"},
                {"name": "private_notes", "type": "text"}],
                "primary_keys": ["record_key"], "foreign_keys": []},
        })
        result = retrieve_relevant_subgraph("Find municipality values", graph)
        self.assertEqual(result["relevant_columns"], [{
            "table": "geographic_records", "columns": ["record_key", "municipality"],
        }])
        self.assertIn("- record_key integer [PRIMARY KEY]", result["context"])
        self.assertIn("- municipality text", result["context"])
        self.assertNotIn("private_notes", result["context"])

    def test_customer_name_question_uses_direct_table_and_only_requested_columns(self):
        result = retrieve_relevant_subgraph(
            "What are the names of all customers?", commerce_graph()
        )
        self.assertEqual(result["relevant_tables"], ["customers"])
        self.assertEqual(result["relevant_columns"], [{
            "table": "customers", "columns": ["id", "name"],
        }])
        self.assertEqual(result["relationships"], [])
        self.assertEqual(result["paths"], [])

    def test_location_filter_keeps_compatible_columns_without_expanding_graph(self):
        graph = build_schema_graph({
            "customers": {"columns": [
                {"name": "id", "type": "integer"},
                {"name": "name", "type": "text"},
                {"name": "city", "type": "text"},
                {"name": "email", "type": "text"}],
                "primary_keys": ["id"], "foreign_keys": []},
            "orders": {"columns": [
                {"name": "id", "type": "integer"},
                {"name": "customer_id", "type": "integer"}],
                "primary_keys": ["id"], "foreign_keys": [
                    {"column": "customer_id", "references_table": "customers", "references_column": "id"},
                ]},
        })
        result = retrieve_relevant_subgraph(
            "Which customers live in Hyderabad?", graph
        )
        self.assertEqual(result["relevant_tables"], ["customers"])
        self.assertEqual(result["relationships"], [])
        columns = result["relevant_columns"][0]["columns"]
        self.assertEqual(columns, ["id", "name", "city"])
        self.assertEqual(result["paths"], [])

    def test_product_name_question_ignores_common_name_columns(self):
        graph = build_schema_graph({
            "customers": {"columns": [{"name": "id", "type": "integer"},
                                       {"name": "name", "type": "text"}],
                          "primary_keys": ["id"], "foreign_keys": []},
            "orders": {"columns": [{"name": "id", "type": "integer"},
                                    {"name": "name", "type": "text"}],
                       "primary_keys": ["id"], "foreign_keys": []},
            "order_items": {"columns": [{"name": "id", "type": "integer"},
                                         {"name": "name", "type": "text"}],
                            "primary_keys": ["id"], "foreign_keys": []},
            "products": {"columns": [{"name": "id", "type": "integer"},
                                      {"name": "name", "type": "text"}],
                         "primary_keys": ["id"], "foreign_keys": []},
        })
        result = retrieve_relevant_subgraph("What are the names of products?", graph)
        self.assertEqual(result["relevant_tables"], ["products"])
        self.assertEqual(result["relevant_columns"], [{
            "table": "products", "columns": ["id", "name"],
        }])
        self.assertEqual(result["relationships"], [])
        self.assertEqual(result["paths"], [])

    def test_location_question_preserves_minimal_multihop_join_columns(self):
        graph = build_schema_graph({
            "customers": {"columns": [
                {"name": "id", "type": "integer"},
                {"name": "name", "type": "text"},
                {"name": "city", "type": "text"},
                {"name": "email", "type": "text"}],
                "primary_keys": ["id"], "foreign_keys": []},
            "orders": {"columns": [
                {"name": "id", "type": "integer"},
                {"name": "customer_id", "type": "integer"},
                {"name": "order_date", "type": "date"}],
                "primary_keys": ["id"], "foreign_keys": [
                    {"column": "customer_id", "references_table": "customers", "references_column": "id"},
                ]},
            "order_items": {"columns": [
                {"name": "order_id", "type": "integer"},
                {"name": "product_id", "type": "integer"},
                {"name": "quantity", "type": "integer"}],
                "primary_keys": [], "foreign_keys": [
                    {"column": "order_id", "references_table": "orders", "references_column": "id"},
                    {"column": "product_id", "references_table": "products", "references_column": "id"},
                ]},
            "products": {"columns": [
                {"name": "id", "type": "integer"},
                {"name": "name", "type": "text"},
                {"name": "description", "type": "text"}],
                "primary_keys": ["id"], "foreign_keys": []},
        })
        result = retrieve_relevant_subgraph(
            "What products were purchased by customers from Hyderabad?", graph
        )
        self.assertEqual(result["relevant_tables"], ["customers", "order_items", "orders", "products"])
        columns = {item["table"]: set(item["columns"]) for item in result["relevant_columns"]}
        self.assertEqual(columns["customers"], {"id", "name", "city"})
        self.assertEqual(columns["orders"], {"id", "customer_id"})
        self.assertEqual(columns["order_items"], {"order_id", "product_id"})
        self.assertEqual(columns["products"], {"id", "name"})
        self.assertEqual(len(result["paths"]), 1)
        self.assertEqual(len(result["relationships"]), 3)
        self.assertNotIn("email", result["context"])
        self.assertNotIn("description", result["context"])


if __name__ == "__main__":
    unittest.main()
