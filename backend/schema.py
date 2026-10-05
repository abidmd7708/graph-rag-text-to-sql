"""Live PostgreSQL schema extraction."""

from .database import get_connection


def get_database_schema():
    """Return public tables, ordered columns, primary keys, and foreign keys."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name, column_name, data_type, ordinal_position
                FROM information_schema.columns
                WHERE table_schema = 'public'
                ORDER BY table_name, ordinal_position;
                """
            )
            column_rows = cur.fetchall()
            cur.execute(
                """
                SELECT tc.table_name, kcu.column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_catalog = kcu.constraint_catalog
                 AND tc.constraint_schema = kcu.constraint_schema
                 AND tc.constraint_name = kcu.constraint_name
                 AND tc.table_schema = kcu.table_schema
                 AND tc.table_name = kcu.table_name
                WHERE tc.constraint_type = 'PRIMARY KEY'
                  AND tc.table_schema = 'public'
                ORDER BY tc.table_name, kcu.ordinal_position;
                """
            )
            primary_key_rows = cur.fetchall()
            cur.execute(
                """
                SELECT source.table_name, source.column_name,
                       target.table_name, target.column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS source
                  ON tc.constraint_catalog = source.constraint_catalog
                 AND tc.constraint_schema = source.constraint_schema
                 AND tc.constraint_name = source.constraint_name
                 AND tc.table_schema = source.table_schema
                 AND tc.table_name = source.table_name
                JOIN information_schema.referential_constraints AS rc
                  ON tc.constraint_catalog = rc.constraint_catalog
                 AND tc.constraint_schema = rc.constraint_schema
                 AND tc.constraint_name = rc.constraint_name
                JOIN information_schema.key_column_usage AS target
                  ON rc.unique_constraint_catalog = target.constraint_catalog
                 AND rc.unique_constraint_schema = target.constraint_schema
                 AND rc.unique_constraint_name = target.constraint_name
                 AND source.position_in_unique_constraint = target.ordinal_position
                WHERE tc.constraint_type = 'FOREIGN KEY'
                  AND tc.table_schema = 'public'
                ORDER BY source.table_name, source.ordinal_position;
                """
            )
            foreign_key_rows = cur.fetchall()

    schema = {}
    for table_name, column_name, data_type, ordinal_position in column_rows:
        table = schema.setdefault(
            table_name, {"columns": [], "primary_keys": [], "foreign_keys": []}
        )
        table["columns"].append(
            {"name": column_name, "type": data_type, "ordinal_position": ordinal_position}
        )

    for table_name, column_name in primary_key_rows:
        if table_name in schema:
            schema[table_name]["primary_keys"].append(column_name)

    for source_table, source_column, target_table, target_column in foreign_key_rows:
        if source_table in schema:
            schema[source_table]["foreign_keys"].append(
                {
                    "column": source_column,
                    "references_table": target_table,
                    "references_column": target_column,
                }
            )
    return schema


def format_schema(schema):
    """Format either legacy column lists or the enhanced schema structure."""
    lines = []
    for table_name, metadata in schema.items():
        if isinstance(metadata, list):  # Backwards compatibility for old callers.
            metadata = {"columns": metadata, "primary_keys": [], "foreign_keys": []}
        lines.append(f"TABLE: {table_name}")
        foreign_keys = {}
        for foreign_key in metadata.get("foreign_keys", []):
            foreign_keys.setdefault(foreign_key["column"], []).append(foreign_key)
        for column in metadata.get("columns", []):
            name = column.get("name", column.get("column"))
            details = f"  {name} {column['type']}"
            if name in metadata.get("primary_keys", []):
                details += " [PRIMARY KEY]"
            if name in foreign_keys:
                targets = foreign_keys[name]
                details += (
                    " [FOREIGN KEY -> " + ", ".join(
                        f"{fk['references_table']}.{fk['references_column']}" for fk in targets
                    ) + "]"
                )
            lines.append(details)
        lines.append("")
    return "\n".join(lines)
