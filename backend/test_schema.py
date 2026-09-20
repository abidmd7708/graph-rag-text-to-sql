from schema import get_database_schema, format_schema


if __name__ == "__main__":

    schema = get_database_schema()

    formatted_schema = format_schema(schema)

    print(formatted_schema)