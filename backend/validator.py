"""Conservative single-read-query validation for generated PostgreSQL SQL."""

import re


FORBIDDEN_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "MERGE", "DROP", "ALTER", "TRUNCATE",
    "CREATE", "GRANT", "REVOKE", "COPY", "CALL", "DO", "EXECUTE",
    "VACUUM", "ANALYZE", "REFRESH", "COMMENT", "LOCK", "SET", "RESET",
    "BEGIN", "COMMIT", "ROLLBACK", "SAVEPOINT", "PREPARE", "DEALLOCATE",
}


def clean_sql(sql):
    """Remove model markdown fences and surrounding whitespace."""
    sql = (sql or "").strip()
    sql = re.sub(r"^```(?:sql)?\s*", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\s*```$", "", sql)
    return sql.strip()


def _lex(sql):
    """Return unquoted SQL words and whether a non-final semicolon exists."""
    words = []
    i = 0
    pending_semicolon = False
    while i < len(sql):
        char = sql[i]
        if char.isspace():
            i += 1
            continue
        if sql.startswith("--", i):
            end = sql.find("\n", i + 2)
            i = len(sql) if end < 0 else end + 1
            continue
        if sql.startswith("/*", i):
            depth, i = 1, i + 2
            while i < len(sql) and depth:
                if sql.startswith("/*", i):
                    depth += 1
                    i += 2
                elif sql.startswith("*/", i):
                    depth -= 1
                    i += 2
                else:
                    i += 1
            if depth:
                raise ValueError("Unterminated SQL comment.")
            continue
        if char == ";":
            if pending_semicolon:
                raise ValueError("Multiple SQL statements are not allowed.")
            pending_semicolon = True
            i += 1
            continue
        if pending_semicolon:
            raise ValueError("Multiple SQL statements are not allowed.")
        if char in "'\"":
            quote = char
            i += 1
            while i < len(sql):
                if sql[i] == quote:
                    if i + 1 < len(sql) and sql[i + 1] == quote:
                        i += 2
                        continue
                    i += 1
                    break
                if sql[i] == "\\" and quote == "'":
                    i += 2
                else:
                    i += 1
            else:
                raise ValueError("Unterminated SQL string or quoted identifier.")
            continue
        if char == "$":
            match = re.match(r"\$[A-Za-z_0-9]*\$", sql[i:])
            if match:
                delimiter = match.group(0)
                end = sql.find(delimiter, i + len(delimiter))
                if end < 0:
                    raise ValueError("Unterminated dollar-quoted string.")
                i = end + len(delimiter)
                continue
        match = re.match(r"[A-Za-z_][A-Za-z_0-9$]*", sql[i:])
        if match:
            words.append(match.group(0).upper())
            i += len(match.group(0))
        else:
            i += 1
    return words


def validate_sql(sql):
    sql = clean_sql(sql)
    if not sql:
        return False, "SQL query is empty."
    try:
        words = _lex(sql)
    except ValueError as exc:
        return False, str(exc)
    if not words or words[0] not in {"SELECT", "WITH"}:
        return False, "Only SELECT queries are allowed."
    for keyword in words:
        if keyword in FORBIDDEN_KEYWORDS:
            return False, f"Forbidden SQL keyword detected: {keyword}"
    # SELECT INTO creates a table, and row-locking clauses are not read-only.
    for index, keyword in enumerate(words):
        if keyword == "INTO":
            return False, "SELECT INTO is not allowed."
        if keyword == "FOR" and index + 1 < len(words) and words[index + 1] in {"UPDATE", "SHARE", "NO", "KEY"}:
            return False, "Row-locking SELECT clauses are not allowed."
    if any(word in {"NEXTVAL", "SETVAL"} for word in words):
        return False, "Sequence modification functions are not allowed."
    return True, "SQL is valid."


if __name__ == "__main__":
    sample = "SELECT name FROM customers LIMIT 5;"
    valid, message = validate_sql(sample)
    print("Valid:", valid)
    print("Message:", message)
