"""Hippocampus layer — biologically-inspired memory management.

Submodules:
- salience: Entity/edge importance scoring (recency, frequency, corrections, emotional)
- forgetting: Ebbinghaus decay curve with salience modulation
- consolidation: Hebbian strengthening, contradiction detection, pruning
- pattern_completion: CA3 autoassociative recall from partial cues
- reconsolidation: Recall tracking + activation window (spaced repetition)
- prediction_error: Novelty detection + contradiction-triggered updates
- schema_extraction: Neocortex — CLS slow learning, schema generalization
- pattern_separation: Dentate gyrus — Jaccard fingerprint similarity
- cognitive_map: Grid/place cells — graph navigation utilities

The Hippocampus coordinator below wires all nine algorithms together and
provides the two entry points the rest of Synapse calls:
    - on_episode_ingested(): runs after Graphiti extracts a new episode
    - on_recall(): runs when entities are retrieved via search/prefetch
      Also applies retrieval-induced forgetting (RIF): similar-but-not-recalled
      entities get a session-scoped ranking penalty.
"""

from __future__ import annotations

import logging

from synapse.hippocampus.cognitive_map import CognitiveMap as CognitiveMap
from synapse.hippocampus.consolidation import ConsolidationEngine
from synapse.hippocampus.forgetting import ForgettingCurve
from synapse.hippocampus.pattern_completion import PatternCompletion
from synapse.hippocampus.pattern_separation import PatternSeparation
from synapse.hippocampus.prediction_error import PredictionErrorDetector
from synapse.hippocampus.reconsolidation import ReconsolidationTracker
from synapse.hippocampus.salience import SalienceScorer
from synapse.hippocampus.schema_extraction import SchemaExtractor

logger = logging.getLogger(__name__)


class Hippocampus:
    """Coordinator for the nine hippocampus-layer algorithms.

    Owns instances of all algorithms and exposes two entry points that
    mirror actual cognitive events:

    - on_episode_ingested(new_entities, new_edges, existing_edges):
        Runs prediction error detection, scores new entities/edges with
        salience, applies reconsolidation boosts to active entities, and
        queues contradictions for priority consolidation.

    - on_recall(entity_names, edges):
        Records recall events in the reconsolidation tracker (opening the
        reconsolidation window for those entities). Also applies retrieval-
        induced forgetting (RIF): entities that are Jaccard-similar to
        recalled entities but were NOT themselves recalled get a session-
        scoped ranking penalty. The penalty decays each tick and expires
        with the reconsolidation window. This suppresses retrieval ranking,
        NOT forgetting curve strength — penalized entities remain fully
        recoverable by a direct, unambiguous query.

    The coordinator is intentionally NOT an event bus or actor system.
    It's a single-process orchestrator with two synchronous entry points.
    If Synapse ever goes multi-process (multi-agent sharing), revisit.

    All algorithms receive raw edge/entity dicts from FalkorHelper — the
    coordinator does no graph fetching itself. The caller (provider) is
    responsible for passing in the relevant edges.
    """

    # RIF penalty applied to similar-but-not-recalled entities.
    # ponytail: fixed penalty, not a decayed curve. The reconsolidation
    # window already handles expiry via tick(). A decay function here
    # would double-decay. Add per-entity decay if granularity matters.
    RIF_PENALTY = 0.3

    def __init__(
        self,
        half_life_days: float = 7.0,
        salience_boost: float = 3.0,
        recall_boost: float = 1.5,
        prune_threshold: float = 0.05,
        group_id: str = "default",
    ):
        self.salience = SalienceScorer(half_life_days=half_life_days)
        self.forgetting = ForgettingCurve(
            base_half_life_days=half_life_days,
            salience_boost=salience_boost,
            recall_boost=recall_boost,
        )
        self.consolidation = ConsolidationEngine()
        self.pattern_completion = PatternCompletion(group_id=group_id)
        self.reconsolidation = ReconsolidationTracker()
        self.prediction_error = PredictionErrorDetector()
        self.schema_extraction = SchemaExtractor()
        self.pattern_separation = PatternSeparation()
        self._prune_threshold = prune_threshold
        self._group_id = group_id
        self._pending_contradictions: list[dict] = []
        self._rif_penalties: dict[str, float] = {}

    def on_episode_ingested(
        self,
        new_entities: list[str],
        existing_entities: list[str],
        new_edges: list[dict],
        existing_edges: list[dict],
    ) -> dict:
        """Run hippocampus algorithms on a newly ingested episode."""
        novelty = self.prediction_error.detect(
            existing_entities=existing_entities,
            new_entities=new_entities,
        )
        contradictions = self.prediction_error.detect_contradictions(
            existing_edges=existing_edges,
            new_edges=new_edges,
        )
        surprises = self.prediction_error.detect_surprise(
            existing_edges=existing_edges,
            new_edges=new_edges,
        )

        if contradictions:
            self._pending_contradictions.extend(contradictions)

        scored_edges = []
        for edge in new_edges:
            fact = edge.get("fact", "")
            valid_at = edge.get("valid_at", "")
            invalid_at = edge.get("invalid_at")
            scores = self.salience.score_edge(
                fact=fact, valid_at=valid_at, invalid_at=invalid_at,
            )
            scored_edges.append({**edge, "salience_scores": scores})

        active = self.reconsolidation.get_active_entities()
        if active:
            for edge in scored_edges:
                from_n = edge.get("from_node", "")
                to_n = edge.get("to_node", "")
                boost = max(
                    self.reconsolidation.get_boost(from_n),
                    self.reconsolidation.get_boost(to_n),
                )
                if boost > 0:
                    edge["salience_scores"]["total"] = round(
                        min(1.0, edge["salience_scores"]["total"] + boost), 4
                    )

        similar_pairs = []
        if new_entities and existing_edges:
            similar_pairs = self.pattern_separation.find_similar_pairs(
                new_entities, existing_edges
            )

        return {
            "novelty_score": novelty["novelty_score"],
            "novel_entities": novelty["novel_entities"],
            "known_entities": novelty["known_entities"],
            "contradictions": contradictions,
            "surprises": surprises,
            "scored_edges": scored_edges,
            "similar_pairs": similar_pairs,
        }

    def on_recall(self, entity_names: list[str], edges: list[dict] | None = None) -> None:
        """Record recall events + apply retrieval-induced forgetting.

        Args:
            entity_names: Entities that were retrieved via search/prefetch.
            edges: Edges from the graph (neighborhood fetch from provider).
                Used to compute Jaccard similarity for RIF. If None, RIF
                is skipped — only reconsolidation tracking runs.
        """
        recalled_set = {n.lower() for n in entity_names}

        for name in entity_names:
            self.reconsolidation.recall(name)

        if edges and entity_names:
            self._apply_rif(entity_names, edges, recalled_set)

    def _apply_rif(
        self, recalled: list[str], edges: list[dict], recalled_set: set[str]
    ) -> None:
        """Apply retrieval-induced forgetting penalty to competitors.

        Extracts ALL entity names from the provided edges, then computes
        Jaccard similarity across all pairs. Pairs where one entity was
        recalled and the other wasn't → the non-recalled entity gets a
        ranking penalty.

        The penalty is session-scoped and decays with the reconsolidation
        window (tick). It suppresses retrieval ranking, not forgetting
        curve strength — penalized entities remain fully recoverable.
        """
        # Extract all entity names from the neighborhood edges
        all_entities: set[str] = set()
        for edge in edges:
            from_n = edge.get("from_node", "")
            to_n = edge.get("to_node", "")
            if from_n:
                all_entities.add(from_n)
            if to_n:
                all_entities.add(to_n)

        # Compare ALL entities against each other — find_similar_pairs
        # needs 2+ entities to produce pairs via combinations()
        candidates = list(all_entities)
        if len(candidates) < 2:
            return

        pairs = self.pattern_separation.find_similar_pairs(candidates, edges)
        for pair in pairs:
            a, b = pair["entity_a"], pair["entity_b"]
            a_recalled = a.lower() in recalled_set
            b_recalled = b.lower() in recalled_set
            # Only penalize the non-recalled entity in a mixed pair
            if a_recalled and not b_recalled:
                self._rif_penalties[b] = max(
                    self._rif_penalties.get(b, 0.0),
                    self.RIF_PENALTY,
                )
            elif b_recalled and not a_recalled:
                self._rif_penalties[a] = max(
                    self._rif_penalties.get(a, 0.0),
                    self.RIF_PENALTY,
                )

    def get_rif_penalty(self, entity_name: str) -> float:
        """Get the current RIF ranking penalty for an entity.

        Returns 0.0 if no penalty. The penalty suppresses retrieval
        ranking — it does NOT affect forgetting curve strength.
        """
        return self._rif_penalties.get(entity_name, 0.0)

    def tick(self) -> None:
        """Advance the turn counter and expire RIF penalties.

        RIF penalties expire when the reconsolidation window closes —
        same cadence, no separate decay function.
        """
        self.reconsolidation.tick()
        active = self.reconsolidation.get_active_entities()
        active_lower = {e.lower() for e in active}
        expired = [
            name for name in self._rif_penalties
            if name.lower() not in active_lower
        ]
        for name in expired:
            del self._rif_penalties[name]

    def expand_recall(
        self,
        query: str,
        edges: list[dict],
    ) -> dict:
        """Pattern completion: expand a partial search into a full subgraph."""
        return self.pattern_completion.complete(query, edges)

    def run_consolidation(self, edges: list[dict]) -> dict:
        """Run the offline consolidation pass ('sleep replay')."""
        online_contradictions = list(self._pending_contradictions)
        self._pending_contradictions.clear()

        offline_contradictions = self.consolidation.detect_contradictions(edges)
        co_occurrences = self.consolidation.hebbian_strengthening(edges)

        return {
            "online_contradictions": online_contradictions,
            "offline_contradictions": offline_contradictions,
            "co_occurrences": co_occurrences,
            "pending_count": 0,
        }

    def extract_schemas(self, edges: list[dict]) -> list[dict]:
        """Run schema extraction (neocortical slow learning)."""
        return self.schema_extraction.extract(edges)

    def compute_strength(
        self,
        salience: float,
        age_days: float,
        last_recall_days: float | None = None,
    ) -> float:
        """Compute forgetting curve strength for a memory."""
        return self.forgetting.compute_strength(
            salience=salience,
            age_days=age_days,
            last_recall_days=last_recall_days,
        )

    def should_prune(self, strength: float) -> bool:
        """Check if a memory should be pruned (forgotten)."""
        return self.forgetting.should_prune(
            strength, threshold=self._prune_threshold
        )

    def get_recall_count(self, entity_name: str) -> int:
        """Get recall count for an entity (feeds spaced repetition)."""
        return self.reconsolidation.get_recall_count(entity_name)

    def get_active_entities(self) -> set[str]:
        """Return entities currently in their reconsolidation window."""
        return self.reconsolidation.get_active_entities()

    def clear(self) -> None:
        """Clear all session-scoped state (call on session end)."""
        self.reconsolidation.clear()
        self._pending_contradictions.clear()
        self._rif_penalties.clear()
