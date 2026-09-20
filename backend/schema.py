from .database import get_connection


def get_database_schema():

    query = """
        SELECT
            table_name,
            column_name,
            data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.execute(query)
            rows = cur.fetchall()

    schema = {}

    for table_name, column_name, data_type in rows:

        if table_name not in schema:
            schema[table_name] = []

        schema[table_name].append({
            "column": column_name,
            "type": data_type
        })

    return schema


def format_schema(schema):

    formatted = []

    for table, columns in schema.items():

        formatted.append(f"TABLE: {table}")

        for column in columns:

            formatted.append(
                f"  {column['column']} "
                f"{column['type']}"
            )

        formatted.append("")

    return "\n".join(formatted)