from schema import get_database_schema, format_schema
from llm import generate_sql
from validator import validate_sql, clean_sql
from database import get_connection


def execute_sql(sql):

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(sql)

            columns = [desc.name for desc in cur.description]

            rows = cur.fetchall()

    return columns, rows


if __name__ == "__main__":

    question = "Show the top 5 customers by total spending."

    print("\nQuestion:")
    print(question)

    # 1. Get database schema
    schema = get_database_schema()
    formatted_schema = format_schema(schema)

    # 2. Generate SQL
    print("\nGenerating SQL...\n")

    sql = generate_sql(
        question,
        formatted_schema
    )

    sql = clean_sql(sql)

    print("Generated SQL:")
    print("=" * 60)
    print(sql)
    print("=" * 60)

    # 3. Validate SQL
    valid, message = validate_sql(sql)

    print("\nValidation:")
    print(message)

    if not valid:
        print("\nSQL rejected.")
        exit()

    # 4. Execute SQL
    print("\nExecuting SQL...\n")

    columns, rows = execute_sql(sql)

    # 5. Display result
    print("Results:")
    print("=" * 60)

    print(" | ".join(columns))
    print("-" * 60)

    for row in rows:
        print(" | ".join(str(value) for value in row))