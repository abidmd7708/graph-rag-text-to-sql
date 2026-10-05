"""A small in-memory knowledge graph built from relational schema metadata."""

from collections import deque


def _column_name(column):
    return column.get("name", column.get("column"))


class SchemaGraph:
    def __init__(self, schema):
        self.schema = schema
        self.nodes = {"database:public": {"id": "database:public", "type": "database", "name": "public"}}
        self.edges = []
        self._table_ids = {}
        self._column_ids = {}
        for table_name, raw_metadata in schema.items():
            metadata = raw_metadata if isinstance(raw_metadata, dict) else {
                "columns": raw_metadata, "primary_keys": [], "foreign_keys": []
            }
            table_id = f"table:{table_name}"
            self._table_ids[table_name] = table_id
            self.nodes[table_id] = {
                "id": table_id, "type": "table", "name": table_name,
                "columns": [_column_name(col) for col in metadata.get("columns", [])],
                "primary_keys": list(metadata.get("primary_keys", [])),
            }
            self.edges.append({"source": "database:public", "target": table_id, "type": "HAS_TABLE"})
            for column in metadata.get("columns", []):
                name = _column_name(column)
                column_id = f"column:{table_name}.{name}"
                self._column_ids[(table_name, name)] = column_id
                self.nodes[column_id] = {
                    "id": column_id, "type": "column", "name": name,
                    "table": table_name, "data_type": column["type"],
                    "primary_key": name in metadata.get("primary_keys", []),
                }
                self.edges.append({"source": table_id, "target": column_id, "type": "HAS_COLUMN"})
                if name in metadata.get("primary_keys", []):
                    self.edges.append({"source": table_id, "target": column_id, "type": "PRIMARY_KEY"})

        for source_table, raw_metadata in schema.items():
            metadata = raw_metadata if isinstance(raw_metadata, dict) else {"foreign_keys": []}
            for fk in metadata.get("foreign_keys", []):
                source_column = self._column_ids.get((source_table, fk["column"]))
                target_column = self._column_ids.get((fk["references_table"], fk["references_column"]))
                target_table = self._table_ids.get(fk["references_table"])
                source_table_id = self._table_ids[source_table]
                if source_column and target_column and target_table:
                    self.edges.append({"source": source_table_id, "target": source_column, "type": "FOREIGN_KEY"})
                    self.edges.append({
                        "source": source_column, "target": target_column, "type": "REFERENCES",
                        "source_table": source_table, "source_column": fk["column"],
                        "target_table": fk["references_table"],
                        "target_column": fk["references_column"],
                    })

        self._neighbors = {name: set() for name in self._table_ids}
        for edge in self.edges:
            if edge["type"] == "REFERENCES":
                left, right = edge["source_table"], edge["target_table"]
                self._neighbors[left].add(right)
                self._neighbors[right].add(left)

    def table_neighbors(self, table_name):
        return sorted(self._neighbors.get(table_name, ()))

    def table_paths(self, start_table, max_hops=2):
        """Return deterministic shortest paths from a table within max_hops."""
        paths = {start_table: [start_table]}
        queue = deque([start_table])
        while queue:
            current = queue.popleft()
            if len(paths[current]) - 1 >= max_hops:
                continue
            for neighbor in self.table_neighbors(current):
                if neighbor not in paths:
                    paths[neighbor] = paths[current] + [neighbor]
                    queue.append(neighbor)
        return paths

    def to_dict(self):
        return {"nodes": list(self.nodes.values()), "relationships": list(self.edges)}


def build_schema_graph(schema):
    return SchemaGraph(schema)
