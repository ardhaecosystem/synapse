"""Schema Extraction (Neocortex analog — the slow learning system).

Biological inspiration: Complementary Learning Systems (CLS) theory posits
that the brain has two learning systems:
  1. **Hippocampus**: fast, episodic, specific — learns individual experiences
  2. **Neocortex**: slow, semantic, generalized — extracts patterns/schema
     from hippocampal memories during sleep replay

The hippocampus learns "I went to coffee shop X at 3pm and had a latte."
The neocortex slowly learns "This person likes coffee in the afternoon."

In Synapse: Graphiti is the hippocampus (fast episode storage with entities
and edges). SchemaExtraction is the neocortex — it periodically clusters
entities by their connections, identifies communities of related concepts,
and creates "schema nodes" that summarize the generalized knowledge.

Example:
    Episodic (hippocampus):
      - "User asked about deploying FastAPI to ECS Fargate"
      - "User discussed Docker Compose for PostgreSQL"
      - "User switched to MongoDB"

    Schema (neocortex):
      - Schema: "User works on containerized Python deployments"
        Entities: [FastAPI, Docker, ECS Fargate, PostgreSQL, MongoDB]
        Facts: 15

This is the bridge from "remembering" to "understanding."

Biological reference:
    - McClelland et al. (1995): Why there are complementary learning systems
    - Kumaran et al. (2016): What learning systems do intelligent agents need
    - Nature Neuroscience (2023): Organizing memories for generalization in CLS
"""

from __future__ import annotations

from collections import defaultdict


class SchemaExtractor:
    """Extracts generalized schemas from episodic memory clusters.

    Usage:
        extractor = SchemaExtractor(min_cluster_size=3)
        schemas = extractor.extract(edges)

        for schema in schemas:
            print(f"Schema: {schema['summary']}")
            print(f"  Entities: {schema['entities']}")
            print(f"  Facts: {schema['fact_count']}")
    """

    def __init__(self, min_cluster_size: int = 2, max_schemas: int = 50):
        """Initialize the schema extractor.

        Args:
            min_cluster_size: Minimum number of entities in a cluster
                to be considered a schema. Clusters smaller than this
                are noise, not patterns.
            max_schemas: Maximum number of schemas to extract (prevents
                explosion on very large graphs).
        """
        self.min_cluster_size = min_cluster_size
        self.max_schemas = max_schemas

    def extract(self, edges: list[dict]) -> list[dict]:
        """Extract schemas from a set of edges.

        This is the "slow learning" pass that runs periodically (every N hours)
        to extract generalized knowledge from the episodic graph.

        Args:
            edges: All active (non-invalidated) edges in the graph.

        Returns:
            List of schema dicts, each with:
                - entities: list of entity names in the cluster
                - facts: list of fact strings in the cluster
                - fact_count: number of facts
                - summary: generated summary string
                - density: ratio of actual edges to possible edges
        """
        if not edges:
            return []

        # Filter to active edges only
        active_edges = [
            e for e in edges
            if not e.get("invalid_at") and e.get("from_node") and e.get("to_node")
        ]
        if not active_edges:
            return []

        # Build adjacency for connected components (simple clustering)
        adjacency: dict[str, set[str]] = defaultdict(set)
        edge_facts: dict[str, list[str]] = defaultdict(list)

        for edge in active_edges:
            from_n = edge["from_node"]
            to_n = edge["to_node"]
            adjacency[from_n].add(to_n)
            adjacency[to_n].add(from_n)
            edge_key = f"{from_n}->{to_n}"
            edge_facts[edge_key].append(edge.get("fact", ""))

        # Find connected components via BFS (simple community detection)
        visited: set[str] = set()
        clusters: list[set[str]] = []

        all_entities = set(adjacency.keys())
        for entity in all_entities:
            if entity in visited:
                continue
            # BFS to find the connected component
            component: set[str] = set()
            queue = [entity]
            while queue:
                node = queue.pop(0)
                if node in visited:
                    continue
                visited.add(node)
                component.add(node)
                for neighbor in adjacency.get(node, set()):
                    if neighbor not in visited:
                        queue.append(neighbor)
            if len(component) >= self.min_cluster_size:
                clusters.append(component)

        # Build schema for each cluster
        schemas: list[dict] = []
        for cluster in clusters:
            # Collect facts within this cluster
            cluster_facts: list[str] = []
            cluster_edges: list[dict] = []
            for edge in active_edges:
                from_n = edge["from_node"]
                to_n = edge["to_node"]
                if from_n in cluster or to_n in cluster:
                    fact = edge.get("fact", "")
                    if fact and fact not in cluster_facts:
                        cluster_facts.append(fact)
                        cluster_edges.append(edge)

            # Compute density: actual edges / possible edges
            n = len(cluster)
            max_possible = n * (n - 1) / 2  # undirected
            actual = len(cluster_edges)
            density = round(actual / max_possible, 4) if max_possible > 0 else 0.0

            # Generate summary
            summary = self._generate_summary(cluster, cluster_facts)

            schemas.append({
                "entities": sorted(cluster),
                "facts": cluster_facts[:10],  # Top 10 facts as preview
                "fact_count": len(cluster_facts),
                "summary": summary,
                "density": density,
                "entity_count": n,
            })

            if len(schemas) >= self.max_schemas:
                break

        # Sort by fact count (most information-rich first)
        schemas.sort(key=lambda s: s["fact_count"], reverse=True)
        return schemas

    def _generate_summary(self, entities: set[str], facts: list[str]) -> str:
        """Generate a human-readable summary for a schema cluster.

        This is a simple heuristic summary. In production, this could use an
        LLM to generate a natural-language description of the cluster.

        Args:
            entities: Set of entity names in the cluster.
            facts: List of fact strings in the cluster.

        Returns:
            Summary string.
        """
        if not entities:
            return ""
        entity_list = sorted(entities)
        if len(entity_list) <= 3:
            entities_str = ", ".join(entity_list)
        else:
            entities_str = f"{', '.join(entity_list[:3])} (+{len(entity_list) - 3} more)"

        # Extract the most common verbs/actions from facts
        actions: set[str] = set()
        for fact in facts[:20]:
            fact_lower = fact.lower()
            for verb in ["uses", "is", "has", "runs", "deploys", "relates to",
                         "connects", "manages", "builds", "uses"]:
                if verb in fact_lower:
                    actions.add(verb)

        action_str = " / ".join(sorted(actions)[:3]) if actions else "relates to"
        return (
            f"Cluster of {len(entities)} entities ({entities_str}) "
            f"— {action_str} — {len(facts)} facts"
        )
