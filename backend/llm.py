
import time
import os
from click import prompt
import requests
from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")


def generate_sql(question, graph_context):

    prompt = f"""
You are a PostgreSQL Text-to-SQL system. Convert the user's question into exactly ONE read-only PostgreSQL SELECT statement.

USER QUESTION:
{question}

RELEVANT DATABASE GRAPH CONTEXT:
{graph_context}

RULES:
- Return ONLY the SQL query.
- Do not explain.
- Do not use markdown.
- Use only tables and columns in the provided context.
- Respect foreign-key relationships and use their columns for JOIN conditions.
- Use PostgreSQL syntax.
- Return exactly one SELECT statement.
- Never modify database data.

SQL:
"""
    print(f"[PERF] Prompt characters: {len(prompt)}")
    print(f"[PERF] Graph context characters: {len(graph_context)}")
    start_time = time.perf_counter()

    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "options": {
                "temperature": 0,
                "num_predict": 64
            }
        },
        timeout=300
)

    response.raise_for_status()

    try:
        result = response.json()
    except ValueError as exc:
        raise RuntimeError("Ollama returned an invalid response.") from exc

    if not isinstance(result, dict):
        raise RuntimeError("Ollama returned an invalid response.")

    sql = result.get("response", "").strip()

    llm_time = time.perf_counter() - start_time
    print(f"[PERF] Ollama generation: {llm_time:.2f} seconds")

    if not sql:
        raise RuntimeError("Qwen returned an empty response.")

    return sql
