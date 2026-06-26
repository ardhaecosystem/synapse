"""Pattern Separation (Dentate Gyrus analog).

Biological inspiration: The dentate gyrus performs pattern separation —
transforming similar inputs into dissimilar representations. This prevents
catastrophic interference between similar memories. When you visit two
different coffee shops, pattern separation ensures you don't confuse the
two experiences despite their structural similarity.

In Synapse: When the user has two conversations about similar topics but
different projects, pattern separation identifies entities that have high
overlap in their connections. If two entities are "similar" (Jaccard
similarity above threshold) but belong to different group_ids, they should
be kept separate — not merged.

Implementation: Entity fingerprints (sets of connected entities) compared
via Jaccard similarity. High similarity → flag for separation review.

Biological reference:
    - Leutgeb et al. (2007): Pattern separation in dentate gyrus
    - Bakker et al. (2008): DG lesions impair pattern separation
    - Yassa & Stark (2011): Pattern separation in humans
"""

from __future__ import annotations

from itertools import combinations


class PatternSeparation:
    """Detects similar-but-different contexts using entity fingerprints.

    Usage:
        ps = PatternSeparation(similarity_threshold=0.7)

        # Get an entity's fingerprint (set of connected entities)
        fp = ps.fingerprint("Synapse", edges)

        # Compare two entities
        sim = ps.entity_similarity("Project_A", "Project_B", edges)

        # Find all similar pairs in a graph
        pairs = ps.find_similar_pairs(["A", "B", "C"], edges)
    """

    def __init__(self, similarity_threshold: float = 0.7):
        """Initialize the pattern separation detector.

        Args:
            similarity_threshold: Jaccard similarity above this value
                flags entities as "similar but potentially distinct."
                Default: 0.7 (70% connection overlap).
        """
        self.similarity_threshold = similarity_threshold

    def fingerprint(self, entity_name: str, edges: list[dict]) -> set[str]:
        """Compute the fingerprint of an entity.

        The fingerprint is the set of all entities connected to this entity
        via active (non-invalidated) edges. This is the entity's "context
        signature" — what it's associated with.

        Args:
            entity_name: The entity to fingerprint.
            edges: All edges in the graph.

        Returns:
            Set of connected entity names.
        """
        fp: set[str] = set()
        for edge in edges:
            if edge.get("invalid_at"):
                continue
            from_n = edge.get("from_node", "")
            to_n = edge.get("to_node", "")
            if from_n == entity_name and to_n:
                fp.add(to_n)
            elif to_n == entity_name and from_n:
                fp.add(from_n)
        return fp

    def jaccard_similarity(self, set_a: set[str], set_b: set[str]) -> float:
        """Compute Jaccard similarity between two sets.

        J(A, B) = |A ∩ B| / |A ∪ B|

        Args:
            set_a: First set.
            set_b: Second set.

        Returns:
            Jaccard similarity (0.0-1.0). 0.0 if both empty.
        """
        if not set_a and not set_b:
            return 1.0  # Both empty = identical
        union = set_a | set_b
        if not union:
            return 0.0
        intersection = set_a & set_b
        return round(len(intersection) / len(union), 4)

    def entity_similarity(
        self,
        entity_a: str,
        entity_b: str,
        edges: list[dict],
    ) -> float:
        """Compute similarity between two entities based on their fingerprints.

        Args:
            entity_a: First entity name.
            entity_b: Second entity name.
            edges: All edges in the graph.

        Returns:
            Jaccard similarity of their fingerprints (0.0-1.0).
        """
        fp_a = self.fingerprint(entity_a, edges)
        fp_b = self.fingerprint(entity_b, edges)
        return self.jaccard_similarity(fp_a, fp_b)

    def should_separate(self, similarity: float) -> bool:
        """Check if similarity is above the separation threshold.

        Args:
            similarity: Jaccard similarity score.

        Returns:
            True if entities should be flagged for separation review.
        """
        return similarity >= self.similarity_threshold

    def find_similar_pairs(
        self,
        entity_names: list[str],
        edges: list[dict],
    ) -> list[dict]:
        """Find all pairs of entities with similarity above threshold.

        Args:
            entity_names: List of entity names to compare.
            edges: All edges in the graph.

        Returns:
            List of dicts with entity_a, entity_b, similarity.
            Sorted by similarity (descending).
        """
        # Pre-compute fingerprints
        fingerprints: dict[str, set[str]] = {}
        for name in entity_names:
            fingerprints[name] = self.fingerprint(name, edges)

        pairs = []
        for a, b in combinations(entity_names, 2):
            sim = self.jaccard_similarity(fingerprints[a], fingerprints[b])
            if sim >= self.similarity_threshold:
                pairs.append({
                    "entity_a": a,
                    "entity_b": b,
                    "similarity": sim,
                })

        pairs.sort(key=lambda p: p["similarity"], reverse=True)
        return pairs
