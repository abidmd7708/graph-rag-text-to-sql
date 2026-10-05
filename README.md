# Graph RAG Text-to-SQL

A local FastAPI application that retrieves a relevant PostgreSQL schema subgraph before asking Qwen through Ollama to generate SQL. It keeps schema metadata in a lightweight in-memory Python graph and does not send database rows to the model.

## Architecture

```text
Question
  -> match table and column names
  -> expand matched tables over PostgreSQL foreign-key edges
  -> format only the retrieved tables and relationships
  -> Qwen via Ollama
  -> clean and validate one SELECT statement
  -> execute in a PostgreSQL read-only transaction
  -> return rows and retrieval explanation
```

The graph contains a database node, table nodes, and column nodes. `HAS_TABLE`, `HAS_COLUMN`, `PRIMARY_KEY`, and `FOREIGN_KEY` edges describe the metadata, while `REFERENCES` edges connect foreign-key columns to referenced columns. It is rebuilt at application startup and can be refreshed after schema changes.

Retrieval is deterministic: question terms are normalized for simple singular/plural forms, compared to table and column names, then expanded through the graph up to `GRAPH_MAX_HOPS` (default `2`). The API response includes the matched tables, join relationships, paths, and deterministic reasons for selection. There are no embeddings or external graph/vector services.

## Requirements and setup

Use Python 3.10 or later, PostgreSQL, and Ollama with the configured model available locally. The default Ollama model is `qwen3:8b`.

From the `rag-text-to-sql` directory, create/activate an environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create a local `.env` file with the following variables. Keep credentials local and never commit the file:

```dotenv
DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_database
DB_USER=your_read_only_user
DB_PASSWORD=your_password
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:8b
GRAPH_MAX_HOPS=2
```

The included `data/init.sql` is an optional demo schema/data script. It drops and recreates its demo tables, so review it before running against any database with existing data.

## Run

Start PostgreSQL and Ollama, then start the API from the repository root:

```powershell
uvicorn backend.main:app --reload
```

The schema graph is loaded at startup. If PostgreSQL is temporarily unavailable, the API can start, but graph-backed endpoints return a useful service error until the database is reachable; call the refresh endpoint after recovery.

Example request:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/query `
  -ContentType 'application/json' `
  -Body '{"question":"Which customers placed the most orders?"}'
```

Useful endpoints:

| Endpoint | Purpose |
| --- | --- |
| `GET /` | Health message |
| `GET /schema` | Extracted public schema, including keys |
| `GET /graph` | In-memory graph nodes and edges |
| `POST /graph/refresh` | Re-read PostgreSQL metadata and replace the graph |
| `POST /query` | Retrieve context, generate, validate, and execute SQL |

`/query` returns the generated SQL, columns/results, selected tables, relationships, graph paths, and deterministic retrieval explanations. Questions without matching schema terms are rejected rather than sending the entire schema to the model.

## Safety

The validator accepts one `SELECT` query (including a read-only `WITH` query), rejects stacked statements, data-changing keywords/CTEs, `SELECT INTO`, row-locking clauses, and sequence modification functions. SQL execution also marks the PostgreSQL transaction read-only. For production, configure the database role itself with read-only privileges; application checks are an additional safeguard, not a replacement for database permissions.

## Tests

Run the standard-library unit suite from the repository root:

```powershell
python -m unittest discover -s backend -t . -v
```

The suite uses fake PostgreSQL/Ollama boundaries and does not require a live database or LLM.
