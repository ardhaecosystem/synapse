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

    - on_recall(entity_names):
        Records recall events in the reconsolidation tracker (opening the
        reconsolidation window for those entities).

    The coordinator is intentionally NOT an event bus or actor system.
    It's a single-process orchestrator with two synchronous entry points.
    If Synapse ever goes multi-process (multi-agent sharing), revisit.

    All algorithms receive raw edge/entity dicts from FalkorHelper — the
    coordinator does no graph fetching itself. The caller (provider) is
    responsible for passing in the relevant edges.
    """

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
        # Priority queue: contradictions detected online, drained by
        # the offline consolidation pass (Phase 2 will add the scheduler).
        self._pending_contradictions: list[dict] = []

    def on_episode_ingested(
        self,
        new_entities: list[str],
        existing_entities: list[str],
        new_edges: list[dict],
        existing_edges: list[dict],
    ) -> dict:
        """Run hippocampus algorithms on a newly ingested episode.

        Args:
            new_entities: Entity names extracted from the new episode.
            existing_entities: Entity names already in the graph.
            new_edges: Edges from the new episode (Graphiti extraction).
            existing_edges: Current graph edges (bounded fetch recommended).

        Returns:
            Dict with novelty_score, novel_entities, contradictions,
            surprises, and scored entities/edges.
        """
        # 1. Prediction error: novelty + contradictions + surprise
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

        # Queue contradictions for priority consolidation
        if contradictions:
            self._pending_contradictions.extend(contradictions)

        # 2. Salience scoring on new edges
        scored_edges = []
        for edge in new_edges:
            fact = edge.get("fact", "")
            valid_at = edge.get("valid_at", "")
            invalid_at = edge.get("invalid_at")
            scores = self.salience.score_edge(
                fact=fact,
                valid_at=valid_at,
                invalid_at=invalid_at,
            )
            scored_edges.append({**edge, "salience_scores": scores})

        # 3. Reconsolidation: boost new edges to active entities
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

        # 4. Pattern separation: check if new entities overlap with existing
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

    def on_recall(self, entity_names: list[str]) -> None:
        """Record recall events for entities (opens reconsolidation window).

        Args:
            entity_names: Entities that were retrieved via search/prefetch.
        """
        for name in entity_names:
            self.reconsolidation.recall(name)

    def tick(self) -> None:
        """Advance the turn counter (call once per conversation turn)."""
        self.reconsolidation.tick()

    def expand_recall(
        self,
        query: str,
        edges: list[dict],
    ) -> dict:
        """Pattern completion: expand a partial search into a full subgraph.

        Args:
            query: The search query string.
            edges: All edges from the graph (from FalkorHelper.get_edges()).

        Returns:
            Dict with facts, entities, and expansion depth.
        """
        return self.pattern_completion.complete(query, edges)

    def run_consolidation(self, edges: list[dict]) -> dict:
        """Run the offline consolidation pass ('sleep replay').

        Drains the pending contradiction queue first, then runs
        Hebbian strengthening and contradiction detection over
        the full edge set.

        Args:
            edges: All active edges in the graph.

        Returns:
            Dict with co_occurrences, contradictions, and pending_count.
        """
        # Drain online-detected contradictions first
        online_contradictions = list(self._pending_contradictions)
        self._pending_contradictions.clear()

        # Offline contradiction detection over full graph
        offline_contradictions = self.consolidation.detect_contradictions(edges)

        # Hebbian co-occurrence strengthening
        co_occurrences = self.consolidation.hebbian_strengthening(edges)

        return {
            "online_contradictions": online_contradictions,
            "offline_contradictions": offline_contradictions,
            "co_occurrences": co_occurrences,
            "pending_count": 0,  # drained
        }

    def extract_schemas(self, edges: list[dict]) -> list[dict]:
        """Run schema extraction (neocortical slow learning).

        Args:
            edges: All active edges in the graph.

        Returns:
            List of schema dicts.
        """
        return self.schema_extraction.extract(edges)

    def compute_strength(
        self,
        salience: float,
        age_days: float,
        last_recall_days: float | None = None,
    ) -> float:
        """Compute forgetting curve strength for a memory.

        Args:
            salience: 0.0-1.0 salience score.
            age_days: Days since the memory was formed.
            last_recall_days: Days since last recall (None = never recalled).

        Returns:
            Memory strength 0.0-1.0.
        """
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
