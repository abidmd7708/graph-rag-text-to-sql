import re


FORBIDDEN_KEYWORDS = [
    "DROP",
    "DELETE",
    "UPDATE",
    "INSERT",
    "ALTER",
    "TRUNCATE",
    "CREATE",
    "GRANT",
    "REVOKE"
]


def clean_sql(sql):
    """
    Remove markdown code fences and extra whitespace.
    """

    sql = sql.strip()

    sql = re.sub(r"```sql", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"```", "", sql)

    return sql.strip()


def validate_sql(sql):

    sql = clean_sql(sql)

    upper_sql = sql.upper()

    # Only allow SELECT queries
    if not upper_sql.startswith("SELECT"):
        return False, "Only SELECT queries are allowed."

    # Block dangerous operations
    for keyword in FORBIDDEN_KEYWORDS:

        pattern = rf"\b{keyword}\b"

        if re.search(pattern, upper_sql):
            return False, f"Forbidden SQL keyword detected: {keyword}"

    return True, "SQL is valid."


if __name__ == "__main__":

    test_sql = """
    SELECT name
    FROM customers
    LIMIT 5;
    """

    valid, message = validate_sql(test_sql)

    print("Valid:", valid)
    print("Message:", message)