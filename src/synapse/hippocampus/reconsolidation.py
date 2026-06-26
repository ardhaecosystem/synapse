"""Reconsolidation — memory activation and recall-based strengthening.

Biological inspiration: When a memory is recalled in the brain, it becomes
labile (unstable) for a period of 3-6 hours. During this "reconsolidation
window," the memory can be:
  - Strengthened (by new relevant information)
  - Weakened (if the recall was misleading)
  - Updated (if new information contradicts the existing memory)

This is the neural basis of spaced repetition — each recall event
reinforces the memory and makes it more durable.

In Synapse: The ReconsolidationTracker tracks which entities have been
recently recalled (via prefetch/search). During the activation window:
  1. New edges to active entities get a salience boost (they're "warm")
  2. Contradictions to active entities get priority processing
  3. The recall counter feeds into the ForgettingCurve's recall_boost
     parameter (spaced repetition effect)

Biological reference:
    - Nader et al. (2000): Reconsolidation after recall
    - Lee (2009): Memory updating during reconsolidation
    - Forcato et al. (2007): Reconsolidation window timing
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Set


@dataclass
class _EntityState:
    """Internal tracking state for a single entity."""
    recall_count: int = 0
    activated_at_turn: int = 0
    last_recalled_turn: int = -1


class ReconsolidationTracker:
    """Tracks recall events and activation windows for entities.

    Usage:
        tracker = ReconsolidationTracker(window_turns=10, boost=0.2)

        # When an entity is retrieved (prefetch/search)
        tracker.recall("Synapse")

        # Each conversation turn
        tracker.tick()

        # Check if entity is in reconsolidation window
        if tracker.is_active("Synapse"):
            boost = tracker.get_boost("Synapse")

        # Feed recall count into forgetting curve
        recall_count = tracker.get_recall_count("Synapse")
    """

    def __init__(self, window_turns: int = 10, boost: float = 0.2):
        """Initialize the reconsolidation tracker.

        Args:
            window_turns: Number of turns the activation window stays open.
                In the brain, this is ~3-6 hours. In a conversation,
                ~10 turns is a reasonable default (roughly 10 exchanges).
            boost: The salience boost applied to active entities (0.0-1.0).
                New edges to active entities get this added to their salience.
        """
        self.window_turns = window_turns
        self.boost = boost
        self._entities: Dict[str, _EntityState] = {}
        self._current_turn: int = 0

    def recall(self, entity_name: str) -> None:
        """Record a recall event for an entity.

        This should be called whenever an entity is retrieved via
        prefetch(), search(), or synapse_query tool calls.

        Args:
            entity_name: The name of the recalled entity.
        """
        if entity_name not in self._entities:
            self._entities[entity_name] = _EntityState()
        state = self._entities[entity_name]
        state.recall_count += 1
        state.activated_at_turn = self._current_turn
        state.last_recalled_turn = self._current_turn

    def tick(self) -> None:
        """Advance the turn counter.

        Should be called once per conversation turn (in sync_turn or on_turn_start).
        """
        self._current_turn += 1

    def is_active(self, entity_name: str) -> bool:
        """Check if an entity is within its reconsolidation window.

        Args:
            entity_name: The entity to check.

        Returns:
            True if the entity was recalled within the last `window_turns` turns.
        """
        state = self._entities.get(entity_name)
        if state is None:
            return False
        return (self._current_turn - state.activated_at_turn) < self.window_turns

    def get_recall_count(self, entity_name: str) -> int:
        """Get the total number of recall events for an entity.

        This feeds into the ForgettingCurve's recall_boost for
        spaced repetition effects.

        Args:
            entity_name: The entity to query.

        Returns:
            Total recall count (0 if never recalled).
        """
        state = self._entities.get(entity_name)
        return state.recall_count if state else 0

    def get_last_recalled_turn(self, entity_name: str) -> int:
        """Get the turn number of the most recent recall.

        Returns -1 if the entity was never recalled.
        """
        state = self._entities.get(entity_name)
        return state.last_recalled_turn if state else -1

    def get_boost(self, entity_name: str) -> float:
        """Get the current salience boost for an entity.

        Returns the boost value if the entity is active, 0.0 otherwise.
        This should be added to the salience score of new edges to this entity
        during the reconsolidation window.

        Args:
            entity_name: The entity to check.

        Returns:
            Boost value (0.0 if not active, self.boost if active).
        """
        if self.is_active(entity_name):
            return self.boost
        return 0.0

    def get_active_entities(self) -> Set[str]:
        """Return all currently active entities (within their reconsolidation window).

        Returns:
            Set of entity names that are currently active.
        """
        return {
            name for name, state in self._entities.items()
            if (self._current_turn - state.activated_at_turn) < self.window_turns
        }

    def clear(self) -> None:
        """Clear all tracking state (e.g., on session end)."""
        self._entities.clear()
        self._current_turn = 0
