from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .schema import get_database_schema, format_schema
from .llm import generate_sql
from .validator import validate_sql, clean_sql
from .database import get_connection


app = FastAPI(
    title="RAG Text-to-SQL API",
    description="Natural language to PostgreSQL query system",
    version="0.1.0"
)


class QueryRequest(BaseModel):
    question: str


def execute_sql(sql):

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(sql)

            columns = [desc.name for desc in cur.description]

            rows = cur.fetchall()

    return columns, rows


@app.get("/")
def root():

    return {
        "message": "RAG Text-to-SQL API is running"
    }


@app.post("/query")
def query_database(request: QueryRequest):

    question = request.question.strip()

    if not question:

        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )

    # Get live database schema
    schema = get_database_schema()

    formatted_schema = format_schema(schema)

    # Generate SQL
    sql = clean_sql(
        generate_sql(
            question,
            formatted_schema
        )
    )

    # Validate SQL
    valid, message = validate_sql(sql)

    if not valid:

        raise HTTPException(
            status_code=400,
            detail={
                "error": "Generated SQL rejected",
                "reason": message,
                "sql": sql
            }
        )

    # Execute SQL
    try:

        columns, rows = execute_sql(sql)

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail={
                "error": "SQL execution failed",
                "message": str(e),
                "sql": sql
            }
        )

    # Convert rows to JSON-friendly objects
    results = [
        dict(zip(columns, row))
        for row in rows
    ]

    return {
        "question": question,
        "sql": sql,
        "columns": columns,
        "results": results
    }