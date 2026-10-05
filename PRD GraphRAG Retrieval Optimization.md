# PRD — Schema-Agnostic Graph RAG Retrieval Optimization

## 1. Project Context

This project is an existing FastAPI + PostgreSQL + Ollama/Qwen Text-to-SQL application that has already been extended into a Graph RAG Text-to-SQL system.

Current architecture:

Question
→ Question/schema matching
→ Schema Knowledge Graph
→ Graph-based retrieval
→ Relevant graph context
→ Qwen/Ollama
→ SQL validation
→ Read-only PostgreSQL execution
→ Results

The current Graph RAG implementation dynamically discovers PostgreSQL tables, columns, primary keys, and foreign-key relationships.

The system uses a lightweight in-memory schema graph and does not require Neo4j or another external graph database.

---

## 2. Problem

The current retriever in:

    backend/retriever.py

can retrieve more schema information than is necessary for some questions.

When several tables match a question, graph expansion can include tables that are not actually required to answer the question.

This can increase:

- LLM context size
- prompt processing time
- LLM inference latency
- irrelevant schema information
- risk of unnecessary LLM reasoning

The optimization must reduce unnecessary graph context while preserving Graph RAG behavior and SQL correctness.

---

## 3. Primary Goal

Optimize Graph RAG retrieval so that the system sends the smallest useful relevant subgraph to the LLM.

The optimized retriever must:

1. Remain fully schema-agnostic.
2. Work with arbitrary PostgreSQL schemas.
3. Use dynamically discovered tables, columns, PKs, and FKs.
4. Preserve graph-based retrieval.
5. Preserve multi-hop relationship discovery.
6. Reduce unnecessary context sent to Qwen.
7. Preserve SQL generation correctness.
8. Keep the implementation deterministic and testable.
9. Avoid introducing unnecessary external infrastructure.

---

# 4. Critical Requirement — Schema Agnostic

The implementation MUST NOT contain database-specific logic.

Do NOT hard-code:

    customers
    orders
    order_items
    products

or any other table or column names.

Do NOT create rules such as:

    if table == "customers":
        ...

Do NOT assume:

- a fixed number of tables
- a specific FK structure
- specific column names
- a specific business domain
- that relationships use names such as customer_id, order_id, or product_id

All relationships must come from the dynamically discovered PostgreSQL schema graph.

The same implementation must work with completely different schemas without changing the Python code.

Example schemas may include:

    users → payments → invoices

    employees → departments

    students → enrollments → courses

    patients → visits → doctors

The implementation must remain generic.

---

# 5. Graph RAG Requirement

This optimization MUST remain a genuine Graph RAG implementation.

The architecture must remain:

Question
→ Question/schema matching
→ Seed tables
→ Graph traversal
→ Relevant subgraph
→ Compact graph context
→ LLM
→ SQL

The implementation must NOT replace graph retrieval with:

- hard-coded table selection
- a static schema list
- full-schema injection
- keyword-only retrieval
- fixed SQL templates

The graph must continue determining how related schema elements are connected.

---

# 6. Existing Graph Architecture

The existing graph is dynamically created from PostgreSQL metadata.

It contains information such as:

- tables
- columns
- primary keys
- foreign keys
- relationships between tables

Foreign-key relationships conceptually have the form:

    table_a.column_a
        →
    table_b.column_b

Continue using the existing graph implementation.

Do NOT introduce Neo4j, NetworkX, LangChain, LlamaIndex, or a vector database for this optimization.

The existing lightweight in-memory graph is sufficient.

---

# 7. Retrieval Optimization

Change retrieval from broad graph expansion toward relevance-driven graph retrieval.

Required stages:

### Stage 1 — Question normalization

Continue using the existing:

- tokenization
- stop-word removal
- normalization
- plural handling
- synonym handling

Do not remove existing useful normalization without justification.

### Stage 2 — Identify seed tables

Identify tables and columns relevant to the question.

A table may become a seed when:

- table name matches question terms
- column name matches question terms

### Stage 3 — Rank seed relevance

Use a deterministic relevance score.

Conceptually:

- table-name match = strong signal
- column-name match = strong signal
- multiple matching columns = stronger evidence
- exact/strong token match = stronger than weak overlap

The exact scoring formula should remain lightweight and deterministic.

Do not introduce an external embedding model solely for this optimization.

### Stage 4 — Connect relevant seeds

Use the FK graph to discover paths between relevant seed tables.

### Stage 5 — Build minimal useful subgraph

Include:

- strongly relevant seed tables
- tables required to connect relevant seeds
- relationships required for those paths

Avoid unrelated graph expansion.

---

# 8. Seed Ranking

The retriever should distinguish strong matches from weak matches.

For example:

Question:

    Which customers live in Hyderabad?

A table and column such as:

    customers
    customers.city

should receive strong relevance.

A table that only shares a generic word should not automatically receive the same importance.

The purpose is to prevent weak matches from causing unnecessary graph expansion.

---

# 9. Graph Expansion

After identifying strong seed tables, use the existing FK graph to discover relationships required to connect relevant tables.

Traversal remains configurable through:

    GRAPH_MAX_HOPS

Default:

    GRAPH_MAX_HOPS=2

The implementation must continue supporting configurable values such as:

    GRAPH_MAX_HOPS=0
    GRAPH_MAX_HOPS=1
    GRAPH_MAX_HOPS=2
    GRAPH_MAX_HOPS=3

Do not assume that two hops are always sufficient.

---

# 10. Connecting Relevant Seeds

When multiple relevant seed tables exist, prioritize paths that connect those seeds.

Example generic graph:

    Table A
       |
    Table B
       |
    Table C

If A and C are relevant to the question, B is useful because it connects them.

Therefore:

    A → B → C

should be included.

Unrelated tables connected to A or C should not automatically be included merely because they are within the hop limit.

---

# 11. Single-Seed Questions

For a question where only one table is strongly relevant, do not automatically include every table within the configured hop distance.

Example:

    How many records are in the employee table?

If the graph contains:

    employees
       |
    departments
       |
    locations

the retriever should primarily return the relevant employee schema.

It should not automatically send all connected tables unless they are actually required.

This is an important latency optimization.

---

# 12. Multi-Seed Questions

For questions involving multiple entities, retrieve graph paths connecting the relevant entities.

For example, a generic graph:

    Entity A
        |
    Relationship B
        |
    Entity C
        |
    Relationship D
        |
    Entity E

If the question requires Entity A and Entity E, the retriever should dynamically discover:

    A → B → C → D → E

No table names should be hard-coded.

---

# 13. Relationship Preservation

The optimized context MUST preserve foreign-key relationships required for SQL generation.

For every selected relationship, include:

    source_table.source_column
        →
    target_table.target_column

Relationships must always originate from dynamically discovered database metadata.

---

# 14. Relevant Columns

Continue exposing columns for selected tables.

At minimum, preserve:

- columns needed to answer the question
- primary keys
- foreign-key columns
- columns needed to understand selected relationships

If exact column relevance is uncertain, retaining all columns for a selected table is acceptable.

Correctness is more important than aggressive context reduction.

---

# 15. Context Formatting

Preserve the existing compact context concept:

    RELEVANT DATABASE GRAPH CONTEXT

    TABLE: table_name
    - column type
    - id integer [PRIMARY KEY]
    - foreign_id integer [FOREIGN KEY -> other_table.id]

    RELATIONSHIPS:
    - table_a.column -> table_b.column

Only selected relevant graph information should be included.

Do not send the complete database schema when it is unnecessary.

---

# 16. Retrieval Explanation

Continue returning explanations describing why tables were selected.

Example:

    {
        "table": "some_table",
        "reason": "matched question terms: ..."
    }

For graph-selected tables:

    {
        "table": "bridge_table",
        "reason": "required FK path: table_a -> bridge_table -> table_b"
    }

All explanations must be generated dynamically.

---

# 17. Retrieval Output Contract

Keep compatibility with the existing retriever return structure.

It should continue providing fields equivalent to:

    relevant_tables
    relevant_columns
    relationships
    paths
    explanation
    context

Do not unnecessarily change the API response contract.

---

# 18. No LLM-Based Retrieval

Retrieval must remain deterministic.

Do NOT call Qwen/Ollama during retrieval.

The pipeline must remain:

Question
→ deterministic retrieval
→ compact graph context
→ Qwen

This keeps retrieval predictable and fast.

---

# 19. No Embedding Model Required

Do not introduce an embedding model solely for this optimization.

Use the current lightweight mechanisms:

- token matching
- normalization
- synonyms
- deterministic relevance scoring
- FK graph traversal

Embeddings may be considered later but are outside this scope.

---

# 20. Performance Goals

Measure the effect of the optimization.

At minimum, compare before and after:

- retrieved table count
- relationship count
- context character count
- context token count if available
- total `/query` latency

The optimized system should generally produce smaller context for simple questions.

Do not sacrifice SQL correctness merely to minimize context.

---

# 21. Correctness Priority

Priority order:

1. Correct SQL
2. Correct graph relationships
3. Relevant schema context
4. Reduced context size
5. Lower latency

If aggressive pruning can cause incorrect SQL generation, prefer retaining the necessary schema information.

---

# 22. Test Requirements

Update or add tests in the existing backend test suite.

Tests MUST NOT rely only on the current database schema.

At least one synthetic schema graph with completely different table names must be tested.

Example:

    students
        |
    enrollments
        |
    courses

or:

    employees
        |
    departments

The same retriever code must work without modification.

---

# 23. Required Test Cases

## Test 1 — Single-table question

Question:

    How many employees are there?

Expected:

- the employee-related table is selected
- unrelated tables are not automatically included
- no hard-coded table logic

## Test 2 — Direct two-table relationship

Question:

    Show employees and their departments.

Expected:

- both relevant tables are selected
- their FK relationship is selected
- only the necessary relationship context is included

## Test 3 — Multi-hop relationship

Question:

    Which students are enrolled in a particular course?

Generic graph:

    students
        |
    enrollments
        |
    courses

Expected:

- all required tables are selected
- the multi-hop path is discovered dynamically
- relationships are included
- no schema-specific rules are used

## Test 4 — Unrelated connected table

Graph:

    A → B → C
         |
         D

Question only requires A and B.

Expected:

- A and B are selected
- C/D should not be added merely because they are reachable

## Test 5 — No direct table match

If no table directly matches the question:

- preserve current fallback behavior where possible
- do not crash
- do not fabricate relationships
- return an empty or safe retrieval result consistent with the current contract

## Test 6 — GRAPH_MAX_HOPS

Verify behavior with:

    GRAPH_MAX_HOPS=0
    GRAPH_MAX_HOPS=1
    GRAPH_MAX_HOPS=2

Traversal must respect the configured limit.

## Test 7 — Current project schema

Run the optimized retriever against the existing PostgreSQL schema.

The optimization must not break the existing application.

---

# 24. Regression Requirements

Existing tests must continue passing.

Run:

    .\.venv\Scripts\python.exe -m unittest discover -s backend -t . -v

Also run:

    git diff --check

No existing Graph RAG functionality should be removed.

---

# 25. API Regression Test

After implementation, start the application:

    uvicorn backend.main:app --reload

Verify:

    GET /

    GET /schema

    GET /graph

    POST /query

The `/query` endpoint must continue performing:

Question
→ Graph retrieval
→ Relevant context
→ Qwen
→ SQL validation
→ PostgreSQL execution

---

# 26. Logging / Observability

Add lightweight logging or metadata where useful to understand retrieval efficiency.

Prefer exposing metrics internally or in existing response metadata rather than adding unnecessary API complexity.

Useful metrics:

    seed table count
    selected table count
    relationship count
    context character count
    retrieval time

Do not log database passwords or other secrets.

---

# 27. Implementation Constraints

The implementation should:

- modify the smallest reasonable amount of code
- preserve existing architecture
- preserve existing public interfaces where possible
- avoid unnecessary dependencies
- remain deterministic
- remain readable
- remain testable
- avoid schema-specific assumptions

Primary file expected to change:

    backend/retriever.py

Tests may be added/updated under:

    backend/

Only modify other files if required for integration or testing.

---

# 28. Do Not Over-Optimize

Do not attempt to solve every possible semantic retrieval problem in this change.

This PRD is specifically about:

    reducing unnecessary graph context while preserving Graph RAG correctness

Do not add:

- external vector databases
- embedding infrastructure
- agent loops
- autonomous query planning
- unrelated UI changes
- unrelated database changes
- model replacement
- hardware dependencies

---

# 29. Acceptance Criteria

The implementation is complete when ALL of the following are true:

### Graph RAG

- [ ] Retrieval still uses the schema graph.
- [ ] FK relationships are still used.
- [ ] Multi-hop retrieval still works.
- [ ] The system still sends graph-derived context to Qwen.

### Schema Agnostic

- [ ] No current database table names are hard-coded.
- [ ] No current database column names are hard-coded.
- [ ] Tests prove the retriever works with a different synthetic schema.
- [ ] The algorithm works with arbitrary PostgreSQL schemas.

### Relevance

- [ ] Strong question matches become seeds.
- [ ] Relevant seeds can be connected through FK paths.
- [ ] Unrelated reachable tables are not automatically included.
- [ ] Single-table questions do not unnecessarily expand the whole graph.

### Performance

- [ ] Context size is reduced for appropriate queries.
- [ ] Retrieval remains deterministic.
- [ ] No additional LLM call is introduced.
- [ ] No embedding model is required.

### Correctness

- [ ] Existing tests pass.
- [ ] New retrieval tests pass.
- [ ] Multi-hop tests pass.
- [ ] Existing `/query` behavior still works.
- [ ] SQL validation remains intact.
- [ ] PostgreSQL execution remains read-only.

### Quality

- [ ] `git diff --check` passes.
- [ ] Code is readable and documented.
- [ ] No secrets are added to source control.
- [ ] No unnecessary dependencies are introduced.

---

# 30. Expected Final Architecture

After this optimization, the system should behave as:

                USER QUESTION
                     │
                     ▼
             Question Parsing
                     │
                     ▼
          Semantic/Token Matching
                     │
                     ▼
              Relevant Seeds
                     │
                     ▼
            Schema Knowledge Graph
                     │
             FK Graph Traversal
                     │
                     ▼
          Minimal Relevant Subgraph
                     │
                     ▼
            Compact Graph Context
                     │
                     ▼
                Qwen / Ollama
                     │
                     ▼
             SQL Validation
                     │
                     ▼
        Read-only PostgreSQL Query
                     │
                     ▼
                  Results

The key optimization is:

    Full/over-expanded graph context
                ↓
    Minimal relevant graph context

while preserving the fundamental Graph RAG architecture.

---

# 31. Developer Instruction

Implement this PRD carefully.

Before modifying code:

1. Inspect the existing `backend/retriever.py`.
2. Inspect `backend/graph.py`.
3. Inspect existing retriever and graph tests.
4. Understand the current return contract.
5. Do not rewrite unrelated components.

Then:

1. Implement relevance-driven graph retrieval.
2. Preserve dynamic schema discovery.
3. Preserve multi-hop FK traversal.
4. Prevent unnecessary graph expansion.
5. Add schema-agnostic tests.
6. Run the full existing test suite.
7. Run `git diff --check`.
8. Run the API and test `/query`.
9. Report exactly which files changed and why.

Do NOT commit or push changes automatically.

The implementation must remain a genuine, schema-agnostic Graph RAG Text-to-SQL system.

## Token-Efficient Column-Level Graph RAG Context

The retrieval system must optimize not only retrieval speed but also the number of schema tokens sent to the LLM.

### Goal

After identifying relevant tables and FK paths, do not automatically send every column from every selected table.

Instead, construct the smallest schema context that is sufficient for generating the SQL correctly.

### Column Selection Rules

For every selected table:

1. Always include the table's primary-key columns.
2. Always include foreign-key columns that participate in selected FK relationships.
3. Include columns whose names semantically match meaningful question tokens.
4. Include columns required by a selected multi-hop FK path.
5. Do not include unrelated columns merely because their table was selected.
6. If a table is selected only as an intermediate FK-path table, include only the structural columns required to traverse the path, plus any question-matched columns.

### Important Correctness Rule

Never remove a column that is required to connect selected tables.

For example:

Question:
"What products were purchased by customers from Hyderabad?"

If the graph selects:

customers -> orders -> order_items -> products

the context must retain the FK columns required to construct:

customers.id
orders.customer_id
orders.id
order_items.order_id
order_items.product_id
products.id

It should additionally retain relevant columns such as:

customers.city
customers.name
products.name

But unrelated columns such as:

customers.email
products.description

should not be included unless they match the question or are structurally required.

### Semantic Matching

Column matching must remain:

- deterministic
- schema-agnostic
- independent of hard-coded table names
- independent of hard-coded column names
- based on the existing token normalization/synonym mechanism

Do not introduce embeddings, vector databases, LangChain, LlamaIndex, or external services.

### Graph RAG Requirement

This optimization must remain genuine Graph RAG:

Question
→ schema graph matching
→ relevant table selection
→ relevant column selection
→ FK graph traversal
→ minimal relevant subgraph
→ compact graph context
→ LLM

Do not replace graph retrieval with simple keyword filtering.

### Fallback

If a selected table has no matched columns but is required by an FK path, include only the structural columns required for that path.

If the question directly matches a table but no specific columns, retain the table's PK and relevant FK columns rather than automatically including every column.

### Expected Result

The optimized retriever should reduce:

- number of selected tables when possible
- number of selected relationships when possible
- number of schema columns sent to the LLM
- total graph-context characters/tokens

while preserving SQL generation correctness.

### Testing

Add tests proving:

1. Relevant question columns are retained.
2. Primary keys are retained.
3. FK columns required for joins are retained.
4. Unrelated columns are excluded.
5. Multi-hop paths retain all required join columns.
6. The implementation works with arbitrary synthetic schemas.
7. Existing Graph RAG retrieval behavior continues to work.
8. Context size is smaller than the previous full-table-column context for suitable questions.

Do not hard-code the current project's table or column names in production retrieval logic.

Do not commit or push changes automatically.