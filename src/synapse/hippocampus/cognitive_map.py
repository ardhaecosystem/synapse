"""Cognitive Map (Entorhinal-Hippocampal relational maps).

Biological inspiration: Grid cells in the entorhinal cortex and place cells
in the hippocampus create spatial maps. But these same systems also map
abstract relationships — the hippocampus can represent a "cognitive space"
of concepts and their relationships.

In Synapse: The knowledge graph IS the cognitive map. This module provides
utilities for navigating it:
  - Shortest semantic path between two entities (BFS)
  - Entity neighborhoods (1-hop, 2-hop subgraphs)
  - All entities in the graph

These are useful for:
  - Debugging/inspection ("how is Docker related to JWT?")
  - Context expansion in pattern completion
  - Topic clustering in schema extraction
  - Debugging the graph structure

Biological reference:
    - O'Keefe & Nadel (1978): Place cells and cognitive maps
    - Behrens et al. (2018): Cognitive maps in the hippocampus
    - Constantinescu et al. (2016): A map of abstract relational knowledge
"""

from __future__ import annotations

from collections import deque


class CognitiveMap:
    """Navigate the knowledge graph as a cognitive map.

    Usage:
        cm = CognitiveMap(edges)

        # Find how two entities are related
        path = cm.shortest_path("Docker", "JWT")
        # → ["Docker", "FastAPI", "JWT"]

        # Get an entity's neighborhood
        neighbors = cm.neighborhood("Synapse", depth=2)

        # List all entities
        entities = cm.all_entities()
    """

    def __init__(self, edges: list[dict]):
        """Initialize the cognitive map from a set of edges.

        Args:
            edges: All edges in the graph (active edges preferred).
        """
        self._adjacency: dict[str, set[str]] = {}
        self._entities: set[str] = set()

        for edge in edges:
            if edge.get("invalid_at"):
                continue
            from_n = edge.get("from_node", "")
            to_n = edge.get("to_node", "")
            if from_n and to_n:
                self._adjacency.setdefault(from_n, set()).add(to_n)
                self._adjacency.setdefault(to_n, set()).add(from_n)
                self._entities.add(from_n)
                self._entities.add(to_n)

    def shortest_path(self, start: str, end: str) -> list[str]:
        """Find the shortest semantic path between two entities.

        Uses BFS to find the minimum number of hops between entities.

        Args:
            start: Starting entity name.
            end: Target entity name.

        Returns:
            List of entity names forming the path, or empty list if no path exists.
        """
        if start == end:
            return [start] if start in self._entities else []

        if start not in self._entities or end not in self._entities:
            return []

        # BFS
        visited: set[str] = {start}
        queue: deque[tuple[str, list[str]]] = deque([(start, [start])])

        while queue:
            current, path = queue.popleft()
            for neighbor in self._adjacency.get(current, set()):
                if neighbor == end:
                    return path + [neighbor]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return []

    def neighborhood(self, entity: str, depth: int = 1) -> set[str]:
        """Get the N-hop neighborhood of an entity.

        This is the set of entities reachable within `depth` hops.

        Args:
            entity: The center entity.
            depth: Maximum hop distance (default: 1).

        Returns:
            Set of entity names in the neighborhood (excluding the center entity).
        """
        if entity not in self._entities:
            return set()

        visited: set[str] = {entity}
        queue: deque[tuple[str, int]] = deque([(entity, 0)])
        result: set[str] = set()

        while queue:
            current, d = queue.popleft()
            if d >= depth:
                continue
            for neighbor in self._adjacency.get(current, set()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    result.add(neighbor)
                    queue.append((neighbor, d + 1))

        return result

    def all_entities(self) -> set[str]:
        """Return all entities in the cognitive map."""
        return self._entities.copy()

    def degree(self, entity: str) -> int:
        """Get the degree (number of connections) of an entity.

        Args:
            entity: The entity name.

        Returns:
            Number of edges connected to this entity.
        """
        return len(self._adjacency.get(entity, set()))
