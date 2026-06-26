"""FalkorDB connection helper with temporal query workaround.

Graphiti stores data in FalkorDB graphs named after the group_id,
not the database name. This helper manages connections to the
correct graph and provides temporal query builders that work
around the FalkorDB <= bug on edge properties (v4.18.11).

The bug: the <= and < comparison operators on edge properties in
WHERE clauses do not filter correctly. The > operator works fine.
Node property comparisons work correctly for all operators.

Workaround: wrap edge property comparisons in substring() before
comparing. This forces function evaluation first, which works correctly.
"""

from __future__ import annotations


class FalkorHelper:
    """FalkorDB connection helper with temporal query workaround."""

    def __init__(self, host: str, port: int, password: str | None = None):
        self._host = host
        self._port = port
        self._password = password
        self._client = None

    def _get_client(self):
        """Lazy-import and create the FalkorDB client."""
        if self._client is None:
            import falkordb
            self._client = falkordb.FalkorDB(
                host=self._host, port=self._port, password=self._password
            )
        return self._client

    def get_graph(self, group_id: str):
        """Get the FalkorDB graph for a given group_id."""
        return self._get_client().select_graph(group_id)

    def temporal_filter_query(
        self,
        valid_at_max: str | None = None,
        valid_at_min: str | None = None,
        include_invalid: bool = False,
        limit: int = 20,
    ) -> str:
        """Build a Cypher query with temporal filtering using the substring() workaround.

        Args:
            valid_at_max: ISO date string (YYYY-MM-DD). Only facts valid before this date.
            valid_at_min: ISO date string. Only facts valid after this date.
            include_invalid: If False, exclude edges where invalid_at IS NOT NULL
            limit: Max results

        Returns:
            Cypher query string
        """
        conditions = ["r.valid_at IS NOT NULL"]

        if valid_at_max:
            # Workaround: substring() forces function evaluation before comparison
            conditions.append(
                f"substring(r.valid_at, 0, 10) <= '{valid_at_max[:10]}'"
            )

        if valid_at_min:
            conditions.append(
                f"substring(r.valid_at, 0, 10) > '{valid_at_min[:10]}'"
            )

        if not include_invalid:
            conditions.append(
                f"(r.invalid_at IS NULL OR substring(r.invalid_at, 0, 10) > "
                f"'{valid_at_max[:10] if valid_at_max else '9999-12-31'}')"
            )

        where_clause = " AND ".join(conditions)

        return (
            f"MATCH (a)-[r:RELATES_TO]->(b) "
            f"WHERE {where_clause} "
            f"RETURN a.name AS from_node, r.fact AS fact, b.name AS to_node, "
            f"r.valid_at AS valid_at, r.invalid_at AS invalid_at "
            f"ORDER BY r.valid_at LIMIT {limit}"
        )

    def count_entities(self, group_id: str) -> int:
        """Count entities in a graph."""
        graph = self.get_graph(group_id)
        result = graph.query("MATCH (n:Entity) RETURN count(n) AS count")
        return result.result_set[0][0] if result.result_set else 0

    def count_edges(self, group_id: str) -> int:
        """Count RELATES_TO edges in a graph."""
        graph = self.get_graph(group_id)
        result = graph.query("MATCH ()-[r:RELATES_TO]->() RETURN count(r) AS count")
        return result.result_set[0][0] if result.result_set else 0

    def get_entities(self, group_id: str) -> list[dict]:
        """Get all entities with summaries."""
        graph = self.get_graph(group_id)
        result = graph.query(
            "MATCH (n:Entity) RETURN n.name AS name, n.uuid AS uuid, "
            "n.summary AS summary, n.created_at AS created_at"
        )
        header = [h[1] for h in result.header]
        return [
            {header[i]: row[i] for i in range(min(len(header), len(row)))}
            for row in result.result_set
        ]

    def get_edges(self, group_id: str) -> list[dict]:
        """Get all RELATES_TO edges with temporal data."""
        graph = self.get_graph(group_id)
        result = graph.query(
            "MATCH (a)-[r:RELATES_TO]->(b) "
            "RETURN a.name AS from_node, r.fact AS fact, b.name AS to_node, "
            "r.uuid AS uuid, r.valid_at AS valid_at, r.invalid_at AS invalid_at"
        )
        header = [h[1] for h in result.header]
        return [
            {header[i]: row[i] for i in range(min(len(header), len(row)))}
            for row in result.result_set
        ]

    def close(self):
        """Close the connection."""
        # falkordb client doesn't have explicit close
        pass
