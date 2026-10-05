"""Deterministic question-to-schema-graph retrieval and context formatting."""

import math
import os
import re


_STOP_WORDS = {
    "a", "an", "the", "of", "for", "to", "by", "in", "on", "with", "show",
    "list", "find", "which", "what", "who", "where", "when", "how", "many",
    "most", "least", "top", "all", "their", "that", "is", "are", "was", "were",
}
_SYNONYMS = {
    "buyer": "customer", "buyers": "customer", "client": "customer",
    "clients": "customer", "purchase": "order", "purchases": "order",
    "bought": "buy", "items": "item",
}
_NON_FILTER_TEXT_TOKENS = {
    "comment", "description", "email", "fax", "note", "phone", "url", "website",
}
_OUTPUT_TEXT_TOKENS = {"name", "title", "label"}


def _normalize(token):
    token = _SYNONYMS.get(token, token)
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _tokens(value):
    if not value:
        return set()
    return {
        _normalize(token.lower())
        for token in re.findall(r"[A-Za-z0-9]+", str(value).replace("_", " "))
        if token.lower() not in _STOP_WORDS
    }


def _columns(metadata):
    return metadata.get("columns", []) if isinstance(metadata, dict) else metadata


def get_max_hops():
    try:
        return max(0, int(os.getenv("GRAPH_MAX_HOPS", "2")))
    except ValueError:
        return 2


def _empty_result():
    return {
        "relevant_tables": [], "relevant_columns": [], "relationships": [],
        "paths": [], "explanation": [], "context": "",
    }


def _table_mentions(question, table_name):
    question_words = [
        (_normalize(word.lower()), match.start())
        for match in re.finditer(r"[A-Za-z0-9]+", question)
        for word in [match.group()]
    ]
    table_words = [
        _normalize(word.lower())
        for word in re.findall(r"[A-Za-z0-9]+", table_name.replace("_", " "))
        if word.lower() not in _STOP_WORDS
    ]
    if not table_words:
        return []
    return [
        question_words[index][1]
        for index in range(len(question_words) - len(table_words) + 1)
        if [word for word, _position in question_words[index:index + len(table_words)]] == table_words
    ]


def _filter_column_tables(question, seed_tables, schema_vocabulary):
    """Map filter cues to the nearest mentioned seed table, without domain names."""
    location_cues = list(re.finditer(
        r"\b(?:live(?:s|d|ing)?|resid(?:e|es|ed|ing)|located|based|from|near)\b",
        question, re.IGNORECASE,
    ))
    # "in <value>" is a location cue when the following term is not itself a
    # discovered table/column concept. This leaves phrases such as "in orders"
    # to graph matching rather than treating them as a location filter.
    for match in re.finditer(r"\bin\s+([A-Za-z][A-Za-z0-9_-]*)", question, re.IGNORECASE):
        next_token = _normalize(match.group(1).lower())
        if next_token not in _STOP_WORDS and next_token not in schema_vocabulary:
            location_cues.append(match)

    general_cues = list(re.finditer(
        r"\b(?:where|with|having|whose|over|under|above|below|between|after|before|"
        r"less|greater|older|younger)\b|at\s+least|at\s+most",
        question, re.IGNORECASE,
    ))
    cues = [(cue.start(), "location") for cue in location_cues]
    cues.extend((cue.start(), "general") for cue in general_cues)

    mentions = [
        (position, table)
        for table in seed_tables
        for position in _table_mentions(question, table)
    ]
    selected = {}
    for cue_position, cue_type in cues:
        preceding = [mention for mention in mentions if mention[0] <= cue_position]
        candidates = preceding or mentions
        if candidates:
            table = max(candidates, key=lambda mention: mention[0])[1] if preceding else min(
                candidates, key=lambda mention: (abs(mention[0] - cue_position), mention[0])
            )[1]
            selected[table] = "location" if cue_type == "location" else selected.get(table, "general")
    return selected


def _filter_column_compatible(column, intent):
    data_type = str(column.get("type", "")).lower()
    text_type = any(token in data_type for token in ("char", "text", "string", "citext"))
    if intent == "location":
        name = column.get("name", column.get("column", ""))
        return text_type and not (_tokens(name) & _NON_FILTER_TEXT_TOKENS)
    return any(token in data_type for token in (
        "char", "text", "string", "citext", "int", "numeric", "decimal",
        "real", "double", "float", "bool", "date", "time",
    ))


def retrieve_relevant_subgraph(question, graph, max_hops=None):
    """Return matched schema seeds and only FK paths connecting those seeds.

    A table or a sufficiently specific column match can seed retrieval. A single
    seed stays local; graph traversal is used to connect multiple seeds rather
    than treating every nearby table as relevant. The hop limit is the maximum
    radius searched from each seed, so a connecting path can span two radii.
    """
    if max_hops is None:
        max_hops = get_max_hops()
    max_hops = max(0, int(max_hops))
    question_tokens = _tokens(question)
    if not question_tokens:
        return _empty_result()

    # Count how many table/column names contain each token. Common schema words
    # provide weaker evidence than distinctive names such as a domain column.
    token_frequency = {}
    schema_tokens = {}
    for table_name, metadata in graph.schema.items():
        table_tokens = _tokens(table_name)
        column_tokens = [
            _tokens(column.get("name", column.get("column")))
            for column in _columns(metadata)
        ]
        schema_tokens[table_name] = (table_tokens, column_tokens)
        all_tokens = set(table_tokens)
        for tokens in column_tokens:
            all_tokens.update(tokens)
        for token in all_tokens:
            token_frequency[token] = token_frequency.get(token, 0) + 1

    matches = {}
    column_matches = {}
    for table_name, metadata in graph.schema.items():
        table_tokens, column_tokens = schema_tokens[table_name]
        matched_table_tokens = question_tokens & table_tokens
        matched_columns = []
        column_match_tokens = set()
        for column, tokens in zip(_columns(metadata), column_tokens):
            name = column.get("name", column.get("column"))
            overlap = question_tokens & tokens
            if overlap:
                matched_columns.append((name, overlap))
                column_match_tokens.update(overlap)
        column_matches[table_name] = matched_columns

        # Table-name evidence is always strong. Column-only seeds need at least
        # one token appearing in no more than two table schemas to avoid common
        # fields (for example, a generic label column) seeding broad retrieval.
        strong_column_tokens = {
            token for token in column_match_tokens if token_frequency.get(token, 0) <= 2
        }
        if matched_table_tokens or strong_column_tokens:
            score = sum(4.0 / math.sqrt(token_frequency.get(token, 1))
                        for token in matched_table_tokens)
            score += sum(2.0 / math.sqrt(token_frequency.get(token, 1))
                         for token in strong_column_tokens)
            score += min(len(matched_columns), 3) * 0.25
            matches[table_name] = {
                "tokens": sorted(matched_table_tokens | strong_column_tokens),
                "score": score,
            }

    if not matches:
        return _empty_result()

    # A direct table match is stronger evidence than a generic column match.
    # Column-only seeds are used only when no table name matched the question.
    direct_seeds = [table for table in matches if question_tokens & schema_tokens[table][0]]
    seed_tables = sorted(
        direct_seeds or matches,
        key=lambda table: (-matches[table]["score"], table),
    )
    selected = set(seed_tables)
    paths = []
    connecting_pairs = set()
    if len(seed_tables) > 1 and max_hops:
        connector_limit = 2 * max_hops
        parent = {table: table for table in seed_tables}

        def find(table):
            while parent[table] != table:
                parent[table] = parent[parent[table]]
                table = parent[table]
            return table

        candidates = []
        for index, source in enumerate(seed_tables):
            source_paths = graph.table_paths(source, max_hops=connector_limit)
            for target in seed_tables[index + 1:]:
                path = source_paths.get(target)
                if path:
                    candidates.append((len(path), tuple(path), source, target))
        for _length, path_tuple, source, target in sorted(candidates):
            source_root, target_root = find(source), find(target)
            if source_root == target_root:
                continue
            parent[target_root] = source_root
            path = list(path_tuple)
            paths.append(path)
            selected.update(path)
            connecting_pairs.update(frozenset(pair) for pair in zip(path, path[1:]))

    relationships = []
    for edge in graph.edges:
        if edge["type"] != "REFERENCES":
            continue
        pair = frozenset((edge["source_table"], edge["target_table"]))
        if pair in connecting_pairs:
            relationships.append({
                "source_table": edge["source_table"], "source_column": edge["source_column"],
                "target_table": edge["target_table"], "target_column": edge["target_column"],
                "path": f"{edge['source_table']}.{edge['source_column']} -> "
                        f"{edge['target_table']}.{edge['target_column']}",
            })
    relationships.sort(key=lambda relationship: relationship["path"])

    explanation = []
    for table in seed_tables:
        explanation.append({
            "table": table,
            "reason": "matched question terms: " + ", ".join(matches[table]["tokens"]),
        })
    for path in paths:
        for table in path[1:-1]:
            explanation.append({
                "table": table,
                "reason": "required FK path: " + " -> ".join(path),
            })

    selected_columns = {table: set() for table in selected}
    filter_intents = _filter_column_tables(question, seed_tables, token_frequency)
    for table in selected:
        metadata = graph.schema[table]
        if isinstance(metadata, dict):
            selected_columns[table].update(metadata.get("primary_keys", []))
        for column, _overlap in column_matches.get(table, []):
            selected_columns[table].add(column)
        if table in direct_seeds:
            for column, tokens in zip(_columns(metadata), schema_tokens[table][1]):
                if tokens & _OUTPUT_TEXT_TOKENS and _filter_column_compatible(column, "location"):
                    selected_columns[table].add(column.get("name", column.get("column")))
        if table in filter_intents:
            for column in _columns(metadata):
                if _filter_column_compatible(column, filter_intents[table]):
                    selected_columns[table].add(column.get("name", column.get("column")))
    for relationship in relationships:
        selected_columns[relationship["source_table"]].add(relationship["source_column"])
        selected_columns[relationship["target_table"]].add(relationship["target_column"])

    relevant_columns = []
    for table in sorted(selected):
        relevant_columns.append({
            "table": table,
            "columns": [column.get("name", column.get("column"))
                        for column in _columns(graph.schema[table])
                        if column.get("name", column.get("column")) in selected_columns[table]],
        })

    context_lines = ["RELEVANT DATABASE GRAPH CONTEXT", ""]
    for table in sorted(selected):
        metadata = graph.schema[table]
        if not isinstance(metadata, dict):
            metadata = {"columns": metadata, "primary_keys": [], "foreign_keys": []}
        context_lines.append(f"TABLE: {table}")
        foreign_keys = {}
        for foreign_key in metadata.get("foreign_keys", []):
            foreign_keys.setdefault(foreign_key["column"], []).append(foreign_key)
        for column in metadata.get("columns", []):
            name = column.get("name", column.get("column"))
            if name not in selected_columns[table]:
                continue
            details = f"- {name} {column['type']}"
            if name in metadata.get("primary_keys", []):
                details += " [PRIMARY KEY]"
            if name in foreign_keys:
                selected_targets = [
                    fk for fk in foreign_keys[name]
                    if fk["references_table"] in selected
                    and frozenset((table, fk["references_table"])) in connecting_pairs
                ]
            else:
                selected_targets = []
            if selected_targets:
                details += " [FOREIGN KEY -> " + ", ".join(
                    f"{fk['references_table']}.{fk['references_column']}"
                    for fk in selected_targets
                ) + "]"
            context_lines.append(details)
        context_lines.append("")
    if relationships:
        context_lines.extend(["RELATIONSHIPS:"])
        context_lines.extend(f"- {relationship['path']}" for relationship in relationships)
    return {
        "relevant_tables": sorted(selected), "relevant_columns": relevant_columns,
        "relationships": relationships, "paths": paths, "explanation": explanation,
        "context": "\n".join(context_lines).strip(),
    }
