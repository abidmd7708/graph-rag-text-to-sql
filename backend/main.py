"""FastAPI application for graph-retrieval Text-to-SQL."""

import logging
from contextlib import asynccontextmanager

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .database import get_connection
from .graph import build_schema_graph
from .llm import generate_sql
from .retriever import retrieve_relevant_subgraph
from .schema import get_database_schema
from .validator import clean_sql, validate_sql


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
_schema_graph = None


def _refresh_schema_graph():
    global _schema_graph
    schema = get_database_schema()
    graph = build_schema_graph(schema)
    _schema_graph = graph
    return graph


@asynccontextmanager
async def lifespan(_app):
    try:
        graph = _refresh_schema_graph()
        logger.info("Schema graph built with %d tables", len(graph.schema))
    except Exception:
        # Keep the API available for health/debug endpoints; requests needing a
        # graph get a useful 503 and can recover after PostgreSQL is restored.
        logger.exception("Could not initialize schema graph")
    yield


app = FastAPI(
    title="Graph RAG Text-to-SQL API",
    description="Natural language to PostgreSQL using schema-graph retrieval",
    version="1.0.0",
    lifespan=lifespan,
)


class QueryRequest(BaseModel):
    question: str


def execute_sql(sql):
    """Execute within a read-only transaction as a database-level safeguard."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SET TRANSACTION READ ONLY")
            cur.execute(sql)
            columns = [description.name for description in cur.description]
            rows = cur.fetchall()
    return columns, rows


def _get_graph():
    global _schema_graph
    if _schema_graph is None:
        try:
            return _refresh_schema_graph()
        except Exception as exc:
            logger.exception("Schema graph retrieval failed")
            raise HTTPException(
                status_code=503,
                detail="Could not load PostgreSQL schema metadata. Check database connectivity.",
            ) from exc
    return _schema_graph


@app.get("/")
def root():
    return {"message": "Graph RAG Text-to-SQL API is running"}


@app.get("/schema")
def inspect_schema():
    try:
        return _get_graph().schema
    except HTTPException:
        raise


@app.get("/graph")
def inspect_graph():
    try:
        return _get_graph().to_dict()
    except HTTPException:
        raise


@app.post("/graph/refresh")
def refresh_graph():
    try:
        graph = _refresh_schema_graph()
        logger.info("Schema graph refreshed with %d tables", len(graph.schema))
        return {"message": "Schema graph refreshed", "table_count": len(graph.schema)}
    except Exception as exc:
        logger.exception("Schema graph refresh failed")
        raise HTTPException(
            status_code=503,
            detail="Could not refresh PostgreSQL schema metadata. Check database connectivity.",
        ) from exc


@app.post("/query")
def query_database(request: QueryRequest):
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    logger.info("Question received: %s", question)
    logger.info("Graph retrieval started")
    try:
        retrieval = retrieve_relevant_subgraph(question, _get_graph())
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Graph retrieval failed")
        raise HTTPException(status_code=503, detail="Schema graph retrieval failed.") from exc
    if not retrieval["relevant_tables"]:
        raise HTTPException(
            status_code=400,
            detail="No database tables or columns matched the question. Try naming a database concept.",
        )
    logger.info("Retrieved tables: %s", retrieval["relevant_tables"])
    logger.info("Retrieved relationships: %s", [r["path"] for r in retrieval["relationships"]])

    logger.info("LLM generation started")
    try:
        sql = clean_sql(generate_sql(question, retrieval["context"]))
    except requests.RequestException as exc:
        logger.exception("Ollama request failed")
        raise HTTPException(
            status_code=503,
            detail="Could not reach Ollama. Make sure Ollama is running and the configured model is available.",
        ) from exc
    except RuntimeError as exc:
        logger.error("LLM returned no SQL: %s", exc)
        raise HTTPException(status_code=502, detail="Ollama did not return a usable SQL response.") from exc
    logger.info("SQL generated: %s", sql)

    valid, message = validate_sql(sql)
    logger.info("SQL validation result: %s (%s)", valid, message)
    if not valid:
        raise HTTPException(
            status_code=400,
            detail={"error": "Generated SQL rejected", "reason": message, "sql": sql},
        )

    logger.info("SQL execution started")
    try:
        columns, rows = execute_sql(sql)
    except Exception as exc:
        logger.exception("PostgreSQL query execution failed")
        raise HTTPException(
            status_code=500,
            detail="PostgreSQL query execution failed. Check database connectivity and query compatibility.",
        ) from exc
    results = [dict(zip(columns, row)) for row in rows]
    return {
        "question": question,
        "retrieved_tables": retrieval["relevant_tables"],
        "retrieved_columns": retrieval["relevant_columns"],
        "relationships": [relationship["path"] for relationship in retrieval["relationships"]],
        "retrieval_paths": retrieval["paths"],
        "retrieval_explanation": retrieval["explanation"],
        "sql": sql,
        "columns": columns,
        "results": results,
    }
