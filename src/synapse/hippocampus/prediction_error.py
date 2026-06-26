"""Prediction Error / Novelty Detection (hippocampal surprise signal).

Biological inspiration: The hippocampus signals "prediction errors" when
reality contradicts expectations. This triggers memory updating — surprised
memories get enhanced encoding, and the brain allocates more resources to
encoding novel information.

Two distinct signals:
  1. **Novelty**: completely new information (never seen before)
  2. **Prediction error**: existing information contradicted by new facts

Both signals enhance encoding and trigger targeted memory updating.

In Synapse: The PredictionErrorDetector compares new episode entities and
edges against the existing graph state to detect:
  - Novel entities (completely new) → enhanced encoding (salience boost)
  - Contradictions (new facts that contradict existing edges) → priority
    invalidation + targeted consolidation
  - Surprise (known entity in unexpected context) → salience boost

Biological reference:
    - Kumaran & Maguire (2006): Novelty detection in hippocampus
    - PNAS (2021): Prediction errors disrupt hippocampal representations
    - Hasselmo (2005): Expectation and prediction in hippocampal function
"""

from __future__ import annotations


class PredictionErrorDetector:
    """Detects novelty, contradictions, and surprise in new information.

    Usage:
        detector = PredictionErrorDetector()

        # After extracting entities from a new episode
        result = detector.detect(
            existing_entities=["Synapse", "FalkorDB"],
            new_entities=["Synapse", "Neo4j"],
        )
        # result["novel_entities"] == ["Neo4j"]

        # After extracting edges from a new episode
        contradictions = detector.detect_contradictions(
            existing_edges=[...],
            new_edges=[...],
        )
    """

    CONTRADICTION_KEYWORDS = frozenset({
        "instead of", "replacing", "not ", "switched from",
        "no longer", "changed to", "upgraded to", "moved from",
    })

    def detect(
        self,
        existing_entities: list[str],
        new_entities: list[str],
    ) -> dict:
        """Detect novel entities in a new episode.

        Args:
            existing_entities: Entity names currently in the graph.
            new_entities: Entity names extracted from the new episode.

        Returns:
            Dict with:
                - novel_entities: entities that are completely new
                - known_entities: entities that already existed
                - novelty_score: 0.0-1.0 (fraction of new entities that are novel)
        """
        existing_set = {e.lower() for e in existing_entities}
        novel = []
        known = []

        for entity in new_entities:
            if entity.lower() in existing_set:
                known.append(entity)
            else:
                novel.append(entity)

        score = self.novelty_score(existing_entities, new_entities)

        return {
            "novel_entities": novel,
            "known_entities": known,
            "novelty_score": score,
        }

    def novelty_score(
        self,
        existing_entities: list[str],
        new_entities: list[str],
    ) -> float:
        """Compute a novelty score (0.0-1.0).

        1.0 = all entities are completely new.
        0.0 = all entities already exist.

        Args:
            existing_entities: Entity names currently in the graph.
            new_entities: Entity names from the new episode.

        Returns:
            Novelty score (0.0-1.0).
        """
        if not new_entities:
            return 0.0
        existing_set = {e.lower() for e in existing_entities}
        novel_count = sum(1 for e in new_entities if e.lower() not in existing_set)
        return round(novel_count / len(new_entities), 4)

    def detect_contradictions(
        self,
        existing_edges: list[dict],
        new_edges: list[dict],
    ) -> list[dict]:
        """Detect contradictions between existing and new edges.

        A contradiction occurs when:
        1. A new edge uses a contradiction keyword ("instead of", "replacing")
        2. A new edge targets the same entity pair as an existing edge but
           states a different fact

        Args:
            existing_edges: Edges currently in the graph.
            new_edges: Edges from the new episode.

        Returns:
            List of contradiction dicts with type, existing_fact, new_fact.
        """
        contradictions = []

        # Signal 1: Keyword-based contradiction detection
        for new_edge in new_edges:
            new_fact = (new_edge.get("fact", "") or "").lower()
            if any(kw in new_fact for kw in self.CONTRADICTION_KEYWORDS):
                # Find the existing edge this contradicts
                new_from = new_edge.get("from_node", "")
                for existing in existing_edges:
                    if existing.get("from_node", "") == new_from:
                        contradictions.append({
                            "type": "keyword_contradiction",
                            "existing_fact": existing.get("fact", ""),
                            "new_fact": new_edge.get("fact", ""),
                            "entity": new_from,
                        })
                        break

        # Signal 2: Same entity pair, different fact
        existing_pairs: dict[tuple[str, str], list[dict]] = {}
        for edge in existing_edges:
            key = (edge.get("from_node", ""), edge.get("to_node", ""))
            existing_pairs.setdefault(key, []).append(edge)

        for new_edge in new_edges:
            key = (new_edge.get("from_node", ""), new_edge.get("to_node", ""))
            if key in existing_pairs:
                for existing in existing_pairs[key]:
                    if existing.get("fact", "") != new_edge.get("fact", ""):
                        # Check if the new fact doesn't already contain a
                        # contradiction keyword (avoid double-counting)
                        if not any(
                            kw in (new_edge.get("fact", "") or "").lower()
                            for kw in self.CONTRADICTION_KEYWORDS
                        ):
                            contradictions.append({
                                "type": "entity_pair_contradiction",
                                "existing_fact": existing.get("fact", ""),
                                "new_fact": new_edge.get("fact", ""),
                                "entity": key[0],
                            })

        return contradictions

    def detect_surprise(
        self,
        existing_edges: list[dict],
        new_edges: list[dict],
    ) -> list[dict]:
        """Detect surprise — known entities appearing in unexpected contexts.

        A surprise signal occurs when:
        - A known entity (appears in existing edges) appears in a new edge
          with a target it has never been connected to before.

        Args:
            existing_edges: Edges currently in the graph.
            new_edges: Edges from the new episode.

        Returns:
            List of surprise dicts.
        """
        surprises = []

        # Build map: entity -> set of known targets
        known_targets: dict[str, set[str]] = {}
        for edge in existing_edges:
            from_n = edge.get("from_node", "")
            to_n = edge.get("to_node", "")
            known_targets.setdefault(from_n, set()).add(to_n)

        for new_edge in new_edges:
            from_n = new_edge.get("from_node", "")
            to_n = new_edge.get("to_node", "")
            if from_n in known_targets and to_n not in known_targets[from_n]:
                surprises.append({
                    "type": "unexpected_context",
                    "entity": from_n,
                    "known_contexts": sorted(known_targets[from_n]),
                    "new_context": to_n,
                    "fact": new_edge.get("fact", ""),
                })

        return surprises
