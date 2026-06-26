"""Consolidation engine — the 'sleep replay' cycle.

Operations:
1. Hebbian strengthening: co-occurring entities get edge boost
2. Contradiction detection: find superseded facts via invalid_at
3. Pruning: identify low-strength, low-salience memories
"""

from __future__ import annotations


class ConsolidationEngine:
    """Memory consolidation — Hebbian co-occurrence + contradiction detection."""

    def detect_contradictions(self, edges: list[dict]) -> list[dict]:
        """Detect superseded facts using invalid_at as primary signal.

        An edge with invalid_at set means the fact was superseded.
        Also checks for keyword patterns: "instead of", "replacing", "not".
        """
        contradictions = []

        # Primary signal: invalid_at is set
        for edge in edges:
            invalid_at = edge.get("invalid_at")
            if not invalid_at:
                continue
            from_n = edge.get("from_node", "")
            to_n = edge.get("to_node", "")
            # Find the superseding edge
            for other in edges:
                if other is edge:
                    continue
                other_from = other.get("from_node", "")
                other_to = other.get("to_node", "")
                # Superseding edge shares an entity and has valid_at ≈ invalid_at
                if (from_n == other_from or to_n == other_to) and \
                   other.get("valid_at", "")[:10] == invalid_at[:10]:
                    contradictions.append({
                        "type": "supersession",
                        "superseded_fact": edge.get("fact", ""),
                        "superseding_fact": other.get("fact", ""),
                        "entity": from_n,
                        "invalid_at": invalid_at,
                    })
                    break

        # Secondary signal: keyword patterns (catches intra-episode corrections)
        for edge in edges:
            fact = (edge.get("fact", "") or "").lower()
            if any(kw in fact for kw in ["instead of", "replacing", "not "]):
                contradictions.append({
                    "type": "keyword_correction",
                    "fact": edge.get("fact", ""),
                    "valid_at": edge.get("valid_at"),
                })

        return contradictions

    def hebbian_strengthening(self, edges: list[dict]) -> list[dict]:
        """Identify co-occurring entities for Hebbian strengthening.

        Entities appearing in edges with the same valid_at timestamp
        (same episode) should have their connections strengthened.
        """
        episode_groups: dict[str, list[dict]] = {}
        for edge in edges:
            valid_at = edge.get("valid_at", "")
            if not valid_at:
                continue
            ts = valid_at[:19]  # Group by second-level timestamp
            episode_groups.setdefault(ts, []).append(edge)

        co_occurrences = []
        for ts, group_edges in episode_groups.items():
            if len(group_edges) < 2:
                continue
            entities_in_episode: set[str] = set()
            for edge in group_edges:
                entities_in_episode.add(edge.get("from_node", ""))
                entities_in_episode.add(edge.get("to_node", ""))
            entities_in_episode.discard("")
            if len(entities_in_episode) >= 2:
                co_occurrences.append({
                    "timestamp": ts,
                    "entities": sorted(entities_in_episode),
                    "edge_count": len(group_edges),
                })

        return co_occurrences
