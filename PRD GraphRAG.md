# PRD — Graph RAG Text-to-SQL

## 1. Project Overview

Transform the existing `rag-text-to-sql` repository into a genuine **Graph RAG Text-to-SQL** system while preserving its existing FastAPI, PostgreSQL, Ollama, Qwen, SQL validation, and query execution functionality.

The system must use a **schema knowledge graph** to retrieve only the database structures relevant to a natural-language question before asking Qwen to generate SQL.

### Target pipeline

```text
User Question
     ↓
Graph RAG Retriever
     ↓
Schema Knowledge Graph
     ↓
Relevant Tables / Columns / Relationships
     ↓
Compact Graph Context
     ↓
Qwen via Ollama
     ↓
SQL Cleaning
     ↓
SQL Validation
     ↓
PostgreSQL
     ↓
Results
```

---

## 2. Existing Repository

Expected local repository:

```text
C:\Users\A\Documents\GraphRagPipeline\rag-text-to-sql
```

Current structure:

```text
rag-text-to-sql/
├── backend/
│   ├── __pycache__/
│   ├── database.py
│   ├── llm.py
│   ├── main.py
│   ├── schema.py
│   ├── test_pipeline.py
│   ├── test_schema.py
│   ├── validator.py
│   └── __init__.py
├── data/
├── .env
├── requirements.txt
└── .venv/
```

Current branch:

```text
graph-rag-implementation
```

---

## 3. Git Safety Requirements

Work only on the current local repository and current development branch.

**DO NOT:**

- run `git init`
- clone another repository
- push to GitHub
- push to the original `origin`
- modify the `Main` branch
- force push
- delete existing branches
- change the remote URL
- expose `.env` contents

All changes must remain local unless the user explicitly asks to publish them.

---

## 4. Existing Technology Stack

Preserve the current stack where possible:

- Python
- FastAPI
- PostgreSQL
- Psycopg
- Ollama
- Qwen
- Pydantic
- Requests
- python-dotenv

The current Ollama defaults are:

```text
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:8b
```

Do not introduce a cloud LLM.

Do not replace Ollama unless explicitly requested.

---

# 5. Existing System

The current system approximately does:

```text
Question
   ↓
get_database_schema()
   ↓
format_schema()
   ↓
generate_sql()
   ↓
clean_sql()
   ↓
validate_sql()
   ↓
execute_sql()
   ↓
PostgreSQL results
```

The existing system is therefore a schema-aware Text-to-SQL application, but it does **not** yet implement actual Graph RAG.

---

# 6. Existing Important Files

## `backend/main.py`

Currently:

- creates the FastAPI app
- exposes `/`
- exposes `/query`
- retrieves database schema
- calls the LLM
- validates SQL
- executes SQL
- returns results

Preserve this functionality.

---

## `backend/database.py`

Currently uses Psycopg and:

```text
DB_HOST
DB_PORT
DB_NAME
DB_USER
DB_PASSWORD
```

Preserve:

```python
get_connection()
test_connection()
```

---

## `backend/schema.py`

Currently retrieves:

- table names
- column names
- data types

from:

```text
information_schema.columns
```

This module must be enhanced to also retrieve:

- primary keys
- foreign keys
- referenced tables
- referenced columns
- table relationships

---

## `backend/llm.py`

Currently sends the complete schema to Qwen.

Change this so Qwen receives the **retrieved graph context**, rather than the complete database schema on every request.

Keep the existing Ollama integration.

---

## `backend/validator.py`

Currently performs basic read-only SQL validation.

Improve it so multi-statement and dangerous SQL cannot pass validation.

---

# 7. Core Product Goal

Build a lightweight, explainable Graph RAG system specifically for **database schema retrieval**.

The graph represents database metadata rather than every database row.

The graph should contain:

### Nodes

- Database
- Tables
- Columns

### Metadata

- primary keys
- foreign keys
- data types

### Relationships

```text
HAS_TABLE
HAS_COLUMN
PRIMARY_KEY
FOREIGN_KEY
REFERENCES
```

The implementation must actually use this graph during retrieval.

---

# 8. Important: Do Not Fake Graph RAG

This is NOT acceptable:

```text
Question
  ↓
Entire database schema
  ↓
Qwen
```

while calling the system "Graph RAG".

The implementation must perform:

```text
Question
  ↓
Graph retrieval
  ↓
Relevant subgraph
  ↓
Graph context
  ↓
Qwen
  ↓
SQL
```

The graph retrieval must materially influence the context sent to the LLM.

---

# 9. Technology Choice for Graph

For the first implementation, use a lightweight **in-memory Python graph**.

Do NOT introduce:

- Neo4j
- LangChain
- LlamaIndex
- Chroma
- Pinecone
- FAISS
- another graph/vector platform

unless there is a strong technical reason.

The initial system should remain easy to run locally.

A graph database can be considered later as a production enhancement.

---

# 10. Enhanced Schema Extraction

Update `backend/schema.py`.

Retrieve:

### Table metadata

```text
table_name
```

### Column metadata

```text
column_name
data_type
ordinal_position
```

### Primary key metadata

```text
table
column
```

### Foreign key metadata

```text
source_table
source_column
target_table
target_column
```

Example:

```text
orders.customer_id
    ↓
customers.id
```

Do not hardcode table names or relationships.

All relationships must be discovered dynamically from PostgreSQL metadata.

---

# 11. Suggested Schema Representation

A useful internal representation is:

```python
{
    "customers": {
        "columns": [
            {
                "name": "id",
                "type": "integer"
            },
            {
                "name": "name",
                "type": "text"
            }
        ],
        "primary_keys": ["id"],
        "foreign_keys": []
    },

    "orders": {
        "columns": [
            {
                "name": "id",
                "type": "integer"
            },
            {
                "name": "customer_id",
                "type": "integer"
            }
        ],
        "primary_keys": ["id"],
        "foreign_keys": [
            {
                "column": "customer_id",
                "references_table": "customers",
                "references_column": "id"
            }
        ]
    }
}
```

The exact implementation may differ if a cleaner design is found.

---

# 12. Graph Builder

Create a graph-building module, preferably:

```text
backend/graph.py
```

or:

```text
backend/graph_builder.py
```

The module should:

1. receive enhanced schema metadata
2. create table nodes
3. create column nodes
4. attach key metadata
5. create foreign-key edges
6. expose graph traversal/query functions

Example:

```text
customers
  ├── id
  ├── name
  └── email

orders
  ├── id
  ├── customer_id
  └── total_amount

orders.customer_id
        │
        └──── REFERENCES ────> customers.id
```

---

# 13. Graph Node Metadata

Table nodes should contain enough metadata to generate useful context.

Example:

```python
{
    "type": "table",
    "name": "orders",
    "columns": [
        "id",
        "customer_id",
        "total_amount"
    ],
    "primary_keys": ["id"]
}
```

Column nodes should contain:

```python
{
    "type": "column",
    "name": "customer_id",
    "table": "orders",
    "data_type": "integer"
}
```

---

# 14. Graph Retriever

Create:

```text
backend/retriever.py
```

The retriever accepts:

```text
natural-language question
```

and returns:

- relevant tables
- relevant columns
- relevant relationships
- relevant graph paths
- retrieval explanation

The retrieval must be deterministic and explainable.

---

# 15. Initial Retrieval Strategy

Do not immediately introduce embeddings or a vector database.

Use lightweight matching:

1. tokenize the question
2. normalize terms
3. compare against table names
4. compare against column names
5. identify candidate tables
6. expand candidates through graph relationships
7. retrieve neighboring tables
8. construct a relevant subgraph

Matching may support:

- exact matches
- partial matches
- singular/plural normalization
- simple token overlap
- small synonym mapping

Example:

```text
customer → customers
product → products
order → orders
```

Do not build a large NLP framework.

---

# 16. Multi-Hop Retrieval

Graph traversal must support multiple hops.

Example:

```text
customers
    ↓
orders
    ↓
order_items
    ↓
products
```

Question:

```text
Which customers spent the most on products?
```

The retriever should be able to discover:

```text
customers
→ orders
→ order_items
→ products
```

even when the user does not explicitly name every table.

Default graph traversal depth:

```text
2 hops
```

Make this configurable.

Example environment variable:

```text
GRAPH_MAX_HOPS=2
```

---

# 17. Graph Context Formatter

The retrieved subgraph must be converted into compact LLM-readable context.

Example:

```text
RELEVANT DATABASE CONTEXT

TABLE: customers
COLUMNS:
- id INTEGER [PRIMARY KEY]
- name TEXT
- email TEXT

TABLE: orders
COLUMNS:
- id INTEGER [PRIMARY KEY]
- customer_id INTEGER [FOREIGN KEY -> customers.id]
- total_amount NUMERIC

RELATIONSHIPS:
- orders.customer_id -> customers.id
```

Only relevant information should be included.

---

# 18. LLM Integration

Modify `backend/llm.py`.

The function should conceptually become:

```python
generate_sql(question, graph_context)
```

instead of requiring the complete database schema.

Prompt should be similar to:

```text
You are a PostgreSQL Text-to-SQL system.

Convert the user's question into exactly ONE PostgreSQL SELECT statement.

USER QUESTION:
{question}

RELEVANT DATABASE GRAPH CONTEXT:
{graph_context}

RULES:
- Return ONLY SQL.
- Do not use markdown.
- Do not explain.
- Use only tables and columns in the provided context.
- Respect foreign-key relationships.
- Generate correct JOIN conditions.
- Use PostgreSQL syntax.
- Return exactly one SELECT statement.
- Never modify database data.
- Never generate INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, GRANT, or REVOKE.

SQL:
```

Keep:

```text
temperature = 0
```

and the existing Ollama request structure unless improvement is required.

---

# 19. Main API Pipeline

Update `backend/main.py`.

The `/query` pipeline must become:

```text
User Question
      ↓
Graph Retriever
      ↓
Relevant Subgraph
      ↓
Graph Context
      ↓
Qwen / Ollama
      ↓
clean_sql()
      ↓
validate_sql()
      ↓
PostgreSQL
      ↓
Results
```

The existing `/query` endpoint must remain.

---

# 20. Query Response

Recommended response:

```json
{
  "question": "Which customers placed the most orders?",
  "retrieved_tables": [
    "customers",
    "orders"
  ],
  "relationships": [
    "orders.customer_id -> customers.id"
  ],
  "sql": "SELECT ...",
  "columns": [
    "name",
    "order_count"
  ],
  "results": []
}
```

The exact response can vary, but it should expose enough retrieval information to demonstrate that Graph RAG is actually being used.

---

# 21. Retrieval Explainability

The system should explain why tables were retrieved.

For example:

```text
customers:
matched "customer"

orders:
matched "orders"

relationship:
orders.customer_id -> customers.id
```

This should be generated deterministically from the retriever.

Do not ask the LLM to invent the retrieval explanation.

---

# 22. Optional Development Endpoints

Add:

```text
GET /schema
```

to inspect extracted schema.

Add:

```text
GET /graph
```

to inspect the graph.

Possible `/graph` response:

```json
{
  "nodes": [
    {
      "id": "customers",
      "type": "table"
    }
  ],
  "relationships": [
    {
      "source": "orders",
      "target": "customers",
      "type": "FOREIGN_KEY"
    }
  ]
}
```

These endpoints are primarily for debugging and demonstration.

If adding them significantly complicates the code, prioritize `/query`.

---

# 23. Graph Initialization

Prefer building the graph once when the application starts.

Conceptually:

```text
FastAPI startup
      ↓
Read PostgreSQL metadata
      ↓
Build schema graph
      ↓
Store graph in memory
```

Then every query can reuse it.

Do not rebuild the entire graph for every `/query` request unless necessary.

---

# 24. Graph Refresh

If practical, add:

```text
POST /graph/refresh
```

It should:

1. read current PostgreSQL schema
2. rebuild graph
3. replace the old graph

This allows schema changes without restarting the API.

Keep this feature simple.

---

# 25. SQL Validator Improvements

Improve `backend/validator.py`.

Only read-only queries are allowed.

Allowed:

```sql
SELECT ...
```

Reject:

```sql
INSERT
UPDATE
DELETE
DROP
ALTER
TRUNCATE
CREATE
GRANT
REVOKE
```

Also reject:

```sql
SELECT * FROM customers;
DROP TABLE customers;
```

Multiple SQL statements must not be allowed.

The validator should account for:

- multiple statements
- semicolon-separated statements
- comments
- dangerous keywords
- non-SELECT statements

Do not rely only on:

```python
sql.startswith("SELECT")
```

---

# 26. Database Safety

Do not automatically change database permissions.

However, document that production deployment should use a PostgreSQL user with read-only permissions.

The application should never intentionally perform write operations.

---

# 27. Error Handling

Handle:

### Empty question

Return:

```text
400 Bad Request
```

### Ollama unavailable

Return a useful error explaining that Ollama must be running.

### Empty LLM response

Return a useful error.

### Invalid SQL

Return:

```text
400
```

including the validation reason.

### PostgreSQL failure

Return an appropriate error without exposing credentials.

### Graph retrieval failure

Return a useful API error instead of silently continuing with an incorrect context.

---

# 28. Logging

Add lightweight logs for:

```text
Question received
Graph retrieval started
Retrieved tables
Retrieved relationships
LLM generation started
SQL generated
SQL validation result
SQL execution
```

Never log:

- DB passwords
- API keys
- `.env` contents
- other secrets

---

# 29. Tests

Preserve existing tests.

Add:

```text
backend/test_graph.py
backend/test_retriever.py
```

and improve existing tests as needed.

---

# 30. Schema Tests

Test:

- table retrieval
- column retrieval
- data types
- primary keys
- foreign keys
- relationships
- schema formatting

Expected conceptual relationship:

```text
orders.customer_id -> customers.id
```

Do not hardcode this relationship unless it exists in the test database.

---

# 31. Graph Tests

Test:

- table node creation
- column node creation
- primary-key metadata
- foreign-key edge creation
- graph traversal

Example:

```text
orders --FOREIGN_KEY--> customers
```

---

# 32. Retriever Tests

Test questions such as:

```text
Which customers placed the most orders?
```

Expected relevant tables should include:

```text
customers
orders
```

Another example:

```text
Which products sold the most?
```

Expected relevant tables may include:

```text
products
order_items
orders
```

depending on the actual database schema.

Do not assume a specific schema if the repository's database differs.

---

# 33. Multi-Hop Retriever Test

Test a question requiring multiple joins.

Example:

```text
Which customers spent the most money on products?
```

Expected retrieval should discover the appropriate path through the actual schema.

The test should verify graph traversal, not merely string matching.

---

# 34. Validator Tests

Valid:

```sql
SELECT * FROM customers;
```

Invalid:

```sql
DELETE FROM customers;
```

Invalid:

```sql
DROP TABLE customers;
```

Invalid:

```sql
SELECT * FROM customers; DROP TABLE customers;
```

Invalid:

```sql
UPDATE customers SET name = 'x';
```

---

# 35. End-to-End Testing

Provide an end-to-end pipeline test where practical:

```text
Question
 ↓
Graph retrieval
 ↓
LLM generation
 ↓
SQL validation
 ↓
PostgreSQL
```

Do not require a real LLM for every unit test.

Mock the LLM where appropriate.

---

# 36. Dependency Rules

Keep dependencies minimal.

Do not add large frameworks unnecessarily.

Existing dependencies should continue to be used.

Only add dependencies if they directly support the required implementation.

The initial Graph RAG version should preferably work without:

```text
LangChain
LlamaIndex
Neo4j
Chroma
Pinecone
FAISS
```

---

# 37. Configuration

Continue using `.env`.

Existing variables:

```text
DB_HOST
DB_PORT
DB_NAME
DB_USER
DB_PASSWORD

OLLAMA_URL
OLLAMA_MODEL
```

Optional:

```text
GRAPH_MAX_HOPS=2
```

Never commit secrets.

---

# 38. `.gitignore`

Ensure these are ignored:

```text
.env
.venv/
__pycache__/
*.pyc
```

Do not remove existing ignore rules.

---

# 39. No Hardcoded Schema

Do not write logic such as:

```python
if "customer" in question:
    table = "customers"
```

The system must dynamically use PostgreSQL metadata.

Examples in this PRD are illustrative only.

---

# 40. No Hardcoded Relationships

Do not hardcode:

```text
orders.customer_id -> customers.id
```

Discover relationships dynamically from PostgreSQL foreign-key metadata.

---

# 41. Semantic Matching

The first implementation should remain lightweight.

Support simple variations such as:

```text
customer → customers
order → orders
product → products
```

A small synonym map is acceptable if useful.

Do not over-engineer semantic retrieval in version 1.

---

# 42. Optional Semantic Metadata

The graph architecture should allow future descriptions:

```text
customers:
Stores customer information.

orders:
Stores customer orders.

products:
Stores product information.
```

Do not require manually written descriptions for the initial implementation.

---

# 43. Performance

The graph should normally be built once and reused.

Preferred:

```text
Startup
  ↓
Build graph
  ↓
Reuse graph
```

rather than:

```text
Every query
  ↓
Rebuild entire graph
```

Graph retrieval should be lightweight.

---

# 44. Important Implementation Principle

Do not rewrite working files unnecessarily.

Before changing anything:

1. inspect the current repository
2. inspect all relevant files
3. understand existing behavior
4. make incremental changes
5. run tests after each major change

Preserve working code whenever possible.

---

# 45. Recommended New Structure

A good final structure is:

```text
rag-text-to-sql/
│
├── backend/
│   ├── __init__.py
│   ├── main.py
│   ├── database.py
│   ├── schema.py
│   ├── graph.py
│   ├── retriever.py
│   ├── llm.py
│   ├── validator.py
│   │
│   ├── test_pipeline.py
│   ├── test_schema.py
│   ├── test_graph.py
│   └── test_retriever.py
│
├── data/
├── .env
├── .gitignore
├── requirements.txt
├── PRD.md
└── README.md
```

The agent may adjust the exact structure if it results in cleaner code.

---

# 46. Implementation Phases

## Phase 1 — Inspect

Inspect:

- all backend files
- tests
- requirements
- README
- `.gitignore`

Do not modify anything yet.

## Phase 2 — Schema

Add:

- PK extraction
- FK extraction
- relationship extraction

Run schema tests.

## Phase 3 — Graph

Build the in-memory schema graph.

Run graph tests.

## Phase 4 — Retriever

Implement:

- matching
- graph expansion
- multi-hop traversal
- relevant subgraph selection

Run retriever tests.

## Phase 5 — Context

Format retrieved graph context for Qwen.

## Phase 6 — LLM

Modify `llm.py` to consume graph context.

## Phase 7 — API

Integrate the retriever into `/query`.

## Phase 8 — Validator

Strengthen SQL safety.

## Phase 9 — Testing

Run all tests.

## Phase 10 — Documentation

Update README with setup, architecture, usage, and examples.

---

# 47. Example Scenario

Suppose the database contains:

```text
customers
---------
id
name
email

orders
------
id
customer_id
order_date
total_amount
```

and PostgreSQL reports:

```text
orders.customer_id -> customers.id
```

Question:

```text
Which customers placed the most orders?
```

Graph retrieval should identify:

```text
customers
orders
```

and:

```text
orders.customer_id -> customers.id
```

The LLM receives the relevant context and may generate:

```sql
SELECT
    c.name,
    COUNT(o.id) AS order_count
FROM customers c
JOIN orders o
    ON o.customer_id = c.id
GROUP BY c.id, c.name
ORDER BY order_count DESC;
```

The validator approves it and PostgreSQL executes it.

---

# 48. Multi-Hop Example

Suppose:

```text
customers
   |
orders
   |
order_items
   |
products
```

Question:

```text
Which customers spent the most money on products?
```

Graph retrieval should identify the path:

```text
customers
→ orders
→ order_items
→ products
```

The resulting graph context should contain the relevant tables and relationships.

This is a key demonstration of the Graph RAG capability.

---

# 49. Acceptance Criteria

The implementation is complete only when:

### AC1

FastAPI starts successfully.

### AC2

PostgreSQL connection works.

### AC3

Ollama/Qwen connection works.

### AC4

Existing `/query` endpoint still works.

### AC5

Database schema extraction includes PKs and FKs.

### AC6

A schema knowledge graph is built from live PostgreSQL metadata.

### AC7

The question is used to retrieve a relevant graph substructure.

### AC8

Only relevant graph context is sent to the LLM.

### AC9

Multi-hop relationships can be retrieved.

### AC10

Generated SQL is validated before execution.

### AC11

Multi-statement SQL is rejected.

### AC12

Write/destructive SQL is rejected.

### AC13

Retrieval information can be inspected through the API or logs.

### AC14

Graph and retriever tests pass.

### AC15

Existing tests continue to pass or are updated appropriately.

### AC16

No hardcoded table relationships are required.

### AC17

No cloud LLM is required.

### AC18

No unnecessary graph/vector framework is required.

### AC19

`.env` secrets are not committed.

### AC20

No changes are pushed to the original GitHub repository.

---

# 50. Definition of Done

The project is considered done when a user can run:

```powershell
.\.venv\Scripts\Activate.ps1
```

then start the API using the project's appropriate Uvicorn command, for example:

```powershell
uvicorn backend.main:app --reload
```

and send:

```json
{
  "question": "Which customers placed the most orders?"
}
```

The system must:

```text
1. Receive the question
2. Search the schema graph
3. Retrieve relevant tables
4. Retrieve relevant relationships
5. Build Graph-RAG context
6. Send context to Qwen
7. Generate SQL
8. Validate SQL
9. Execute SQL
10. Return results
```

The implementation must be understandable enough that a developer can explain why it qualifies as Graph RAG.

---

# 51. Final Instruction to the Coding Agent

Before implementation:

**Inspect the existing repository and source code first.**

Then implement this PRD incrementally.

Do not blindly replace the project.

Do not create a second application.

Do not initialize Git.

Do not push anything.

Do not expose `.env`.

Do not add unnecessary frameworks.

Do not fake Graph RAG.

Preserve the existing FastAPI + PostgreSQL + Ollama/Qwen pipeline and evolve it into a real graph-based retrieval architecture.

After each major phase:

1. run the relevant tests
2. fix errors
3. verify existing functionality
4. continue to the next phase

At the end, provide a concise summary of:

- files created
- files modified
- architecture implemented
- tests run
- test results
- commands needed to run the application
- any remaining limitations

Do not claim the implementation is complete if tests or required components are failing.
