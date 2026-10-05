"""Deterministic question-to-schema-graph retrieval and context formatting."""

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


def _normalize(token):
    token = _SYNONYMS.get(token, token)
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _tokens(value):
    return {
        _normalize(token.lower())
        for token in re.findall(r"[A-Za-z0-9]+", value.replace("_", " "))
        if token.lower() not in _STOP_WORDS
    }


def get_max_hops():
    try:
        return max(0, int(os.getenv("GRAPH_MAX_HOPS", "2")))
    except ValueError:
        return 2


def retrieve_relevant_subgraph(question, graph, max_hops=None):
    """Match table/column names, then expand matched tables over FK graph edges."""
    if max_hops is None:
        max_hops = get_max_hops()
    question_tokens = _tokens(question)
    matches = {}
    for table_name, metadata in graph.schema.items():
        table_tokens = _tokens(table_name)
        matched = question_tokens & table_tokens
        columns = metadata.get("columns", []) if isinstance(metadata, dict) else metadata
        matched_columns = []
        for column in columns:
            name = column.get("name", column.get("column"))
            overlap = question_tokens & _tokens(name)
            if overlap:
                matched.update(overlap)
                matched_columns.append((name, overlap))
        if matched:
            matches[table_name] = {"tokens": sorted(matched), "columns": matched_columns}

    seed_tables = sorted(matches)
    if not seed_tables:
        return {
            "relevant_tables": [], "relevant_columns": [], "relationships": [],
            "paths": [], "explanation": [], "context": "",
        }

    paths_by_seed = {seed: graph.table_paths(seed, max_hops=max_hops) for seed in seed_tables}
    selected = set(seed_tables)
    paths = []
    if len(seed_tables) == 1:
        selected.update(paths_by_seed[seed_tables[0]])
        paths = [paths_by_seed[seed_tables[0]][table]
                 for table in sorted(selected - set(seed_tables))]
    else:
        # When several tables match the question, retrieve the shortest paths
        # connecting those anchors. This avoids adding unrelated tables two
        # hops beyond an already matched table. The per-anchor hop limit allows
        # a path to span up to twice that many edges between two anchors.
        connector_limit = 2 * max_hops + 1 if max_hops else 0
        connector_paths = {}
        fully_connected = True
        for index, source in enumerate(seed_tables):
            source_paths = graph.table_paths(source, max_hops=connector_limit)
            for target in seed_tables[index + 1:]:
                if target not in source_paths:
                    fully_connected = False
                else:
                    connector_paths[(source, target)] = source_paths[target]
        if fully_connected:
            for path in connector_paths.values():
                selected.update(path)
            for table in sorted(selected - set(seed_tables)):
                candidates = [path for path in connector_paths.values() if table in path]
                paths.append(min(candidates, key=lambda path: (len(path), path)))
        else:
            for seed, seed_paths in paths_by_seed.items():
                selected.update(seed_paths)
            for table in sorted(selected - set(seed_tables)):
                candidates = [path_map[table] for path_map in paths_by_seed.values() if table in path_map]
                paths.append(min(candidates, key=lambda path: (len(path), path)))

    relationships = []
    for edge in graph.edges:
        if edge["type"] == "REFERENCES" and edge["source_table"] in selected and edge["target_table"] in selected:
            relationship = {
                "source_table": edge["source_table"], "source_column": edge["source_column"],
                "target_table": edge["target_table"], "target_column": edge["target_column"],
                "path": f"{edge['source_table']}.{edge['source_column']} -> "
                        f"{edge['target_table']}.{edge['target_column']}",
            }
            relationships.append(relationship)
    relationships.sort(key=lambda rel: rel["path"])

    explanation = []
    for table in seed_tables:
        match = matches[table]
        explanation.append({
            "table": table, "reason": "matched question terms: " + ", ".join(match["tokens"])
        })
    for path in paths:
        explanation.append({"table": path[-1], "reason": "reachable by foreign-key path: " + " -> ".join(path)})

    relevant_columns = []
    for table in sorted(selected):
        metadata = graph.schema[table]
        columns = metadata.get("columns", []) if isinstance(metadata, dict) else metadata
        relevant_columns.append({
            "table": table,
            "columns": [column.get("name", column.get("column")) for column in columns],
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
            details = f"- {name} {column['type']}"
            if name in metadata.get("primary_keys", []):
                details += " [PRIMARY KEY]"
            if name in foreign_keys:
                targets = foreign_keys[name]
                details += " [FOREIGN KEY -> " + ", ".join(
                    f"{fk['references_table']}.{fk['references_column']}" for fk in targets
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
