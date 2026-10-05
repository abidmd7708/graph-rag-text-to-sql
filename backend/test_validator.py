import unittest

from backend.validator import clean_sql, validate_sql


class ValidatorTests(unittest.TestCase):
    def test_accepts_select_and_optional_trailing_semicolon(self):
        self.assertEqual(validate_sql("SELECT * FROM customers;"), (True, "SQL is valid."))
        self.assertTrue(validate_sql("SELECT 'DROP TABLE' AS note -- harmless\n FROM customers")[0])
        self.assertEqual(clean_sql("```sql\nSELECT 1\n```"), "SELECT 1")

    def test_rejects_write_and_ddl_statements(self):
        for sql in ("DELETE FROM customers", "DROP TABLE customers", "UPDATE customers SET name='x'", "INSERT INTO customers VALUES (1)"):
            with self.subTest(sql=sql):
                self.assertFalse(validate_sql(sql)[0])

    def test_rejects_multiple_statements_and_write_ctes(self):
        for sql in (
            "SELECT * FROM customers; DROP TABLE customers;",
            "SELECT * FROM customers; DELETE FROM customers",
            "WITH gone AS (DELETE FROM customers RETURNING *) SELECT * FROM gone",
            "SELECT * INTO copy_of_customers FROM customers",
        ):
            with self.subTest(sql=sql):
                self.assertFalse(validate_sql(sql)[0])

    def test_ignores_sql_keywords_in_comments_and_strings(self):
        self.assertTrue(validate_sql("SELECT 'UPDATE DROP' FROM customers /* DELETE */;")[0])


if __name__ == "__main__":
    unittest.main()
