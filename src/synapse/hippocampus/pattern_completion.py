"""Pattern Completion (CA3 analog).

Biological inspiration: The CA3 region of the hippocampus operates as an
autoassociative memory. Given a partial cue, it retrieves the full memory
pattern — completing the missing pieces from stored associations.

In Synapse: When a BM25 search matches an entity, pattern completion expands
to the entity's neighborhood (1-hop and 2-hop edges) to retrieve the full
context subgraph. This gives the agent the complete picture, not just the
matching fragment.

Example:
    Query: "FalkorDB"
    BM25 match: "Synapse uses FalkorDB for storage"
    Pattern completion expands to:
      - Synapse uses Graphiti for temporal modeling (2-hop via Synapse)
      - FalkorDB runs in Docker (1-hop from FalkorDB)
    Agent receives: full context about Synapse + FalkorDB + Graphiti + Docker

Biological reference:
    - CA3 recurrent collaterals implement autoassociative recall
    - Pattern completion from partial/noisy cues
    - Neighbors in the hippocampal representation co-activate during retrieval
"""

from __future__ import annotations

from collections import deque


class PatternCompletion:
    """Expand a partial search match into a full context subgraph.

    Given a query and a set of edges, this module:
    1. Finds edges that match the query (BM25-style CONTAINS)
    2. Identifies the entities in those edges
    3. Expands to the N-hop neighborhood via BFS on the edge graph
    4. Returns the full subgraph of facts and entities
    """

    def __init__(self, group_id: str, max_depth: int = 2, max_facts: int = 20):
        """Initialize the pattern completion engine.

        Args:
            group_id: The graph group identifier.
            max_depth: Maximum BFS expansion depth (default: 2 hops).
            max_facts: Maximum number of facts to return (prevents explosion).
        """
        self.group_id = group_id
        self.max_depth = max_depth
        self.max_facts = max_facts

    def complete(self, query: str, edges: list[dict]) -> dict:
        """Complete a partial search match into a full subgraph.

        Args:
            query: The search query string.
            edges: All edges in the graph (from FalkorHelper.get_edges()).

        Returns:
            Dict with:
                - facts: list of edge dicts (active edges only, sorted by relevance)
                - entities: list of entity names in the completed subgraph
                - depth: expansion depth reached
        """
        if not edges:
            return {"facts": [], "entities": [], "depth": 0}

        query_lower = query.lower()

        # Step 1: Find direct matches (edges whose fact contains the query)
        direct_matches = []
        matched_entities: set[str] = set()
        for edge in edges:
            fact = (edge.get("fact", "") or "").lower()
            if query_lower in fact:
                # Only include active edges (no invalid_at)
                if not edge.get("invalid_at"):
                    direct_matches.append(edge)
                    matched_entities.add(edge.get("from_node", ""))
                    matched_entities.add(edge.get("to_node", ""))
        matched_entities.discard("")

        if not matched_entities:
            return {"facts": [], "entities": [], "depth": 0}

        # Step 2: BFS expansion to max_depth
        # Build adjacency: entity -> connected entities (via active edges)
        adjacency: dict[str, set[str]] = {}
        active_edges: list[dict] = []
        for edge in edges:
            if edge.get("invalid_at"):
                continue
            active_edges.append(edge)
            from_n = edge.get("from_node", "")
            to_n = edge.get("to_node", "")
            if from_n and to_n:
                adjacency.setdefault(from_n, set()).add(to_n)
                adjacency.setdefault(to_n, set()).add(from_n)

        # BFS
        visited: set[str] = set(matched_entities)
        all_entities: set[str] = set(matched_entities)
        queue: deque[tuple[str, int]] = deque(
            (e, 0) for e in matched_entities
        )
        max_depth_reached = 0

        while queue:
            entity, depth = queue.popleft()
            if depth >= self.max_depth:
                continue
            for neighbor in adjacency.get(entity, set()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    all_entities.add(neighbor)
                    queue.append((neighbor, depth + 1))
                    max_depth_reached = max(max_depth_reached, depth + 1)

        # Step 3: Collect all facts involving entities in the completed subgraph
        completed_facts: list[dict] = []
        seen_facts: set[str] = set()
        for edge in active_edges:
            from_n = edge.get("from_node", "")
            to_n = edge.get("to_node", "")
            if from_n in all_entities or to_n in all_entities:
                fact_text = edge.get("fact", "")
                if fact_text and fact_text not in seen_facts:
                    completed_facts.append(edge)
                    seen_facts.add(fact_text)
            if len(completed_facts) >= self.max_facts:
                break

        # Sort: direct matches first, then neighbors
        def sort_key(edge):
            fact = (edge.get("fact", "") or "").lower()
            is_direct = query_lower in fact
            return (0 if is_direct else 1, fact)

        completed_facts.sort(key=sort_key)

        return {
            "facts": completed_facts,
            "entities": sorted(all_entities),
            "depth": max_depth_reached,
        }
