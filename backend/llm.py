import os
import requests
from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")


def generate_sql(question, schema):

    prompt = f"""
Convert the user's question into ONE PostgreSQL SELECT query.

DATABASE SCHEMA:
{schema}

QUESTION:
{question}

RULES:
- Return ONLY the SQL query.
- Do not explain.
- Do not use markdown.
- Use only tables and columns in the schema.
- Use PostgreSQL syntax.
- Exclude cancelled orders when calculating spending.
- Return exactly one SELECT statement.

SQL:
"""

    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "options": {
                "temperature": 0,
                "num_predict": 300
            }
        },
        timeout=300
    )

    response.raise_for_status()

    result = response.json()

    print("\nDEBUG - Ollama response:")
    print(result)

    sql = result.get("response", "").strip()

    if not sql:
        raise RuntimeError(
            "Qwen returned an empty response."
        )

    return sql