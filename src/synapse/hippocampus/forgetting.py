"""Ebbinghaus forgetting curve with salience modulation.

S(t) = exp(-t / tau)
tau = base_half_life * (1 + salience * boost) / ln(2)

High-salience memories decay slower.
Recall events boost strength (spaced repetition).
"""

from __future__ import annotations

import math


class ForgettingCurve:
    """Memory strength decay with configurable half-life and salience boost."""

    def __init__(
        self,
        base_half_life_days: float = 7.0,
        salience_boost: float = 3.0,
        recall_boost: float = 1.5,
    ):
        self.base_half_life = base_half_life_days
        self.salience_boost = salience_boost
        self.recall_boost = recall_boost

    def compute_strength(
        self,
        salience: float,
        age_days: float,
        last_recall_days: float | None = None,
    ) -> float:
        """Compute current memory strength (0.0-1.0).

        Args:
            salience: 0.0-1.0 salience score
            age_days: days since the memory was formed
            last_recall_days: days since last recall (None = never recalled)

        Returns:
            strength: 0.0-1.0 (1.0 = perfect, 0.0 = forgotten)
        """
        # Salience modulates the decay rate — higher salience = slower decay
        effective_half_life = self.base_half_life * (1 + salience * self.salience_boost)
        tau = effective_half_life / 0.693  # Convert half-life to decay constant

        # Base decay
        strength = math.exp(-age_days / tau)

        # Recall boost: if recalled recently, strength is boosted
        if last_recall_days is not None and last_recall_days < age_days:
            recall_factor = math.exp(-last_recall_days / (tau * self.recall_boost))
            strength = max(strength, recall_factor * 0.8)

        return round(max(0.0, min(1.0, strength)), 4)

    def should_prune(self, strength: float, threshold: float = 0.05) -> bool:
        """Should this memory be pruned (forgotten)?"""
        return strength < threshold

    def consolidation_candidates(
        self, entities: list[dict], threshold: float = 0.3
    ) -> list[dict]:
        """Find entities that are candidates for consolidation (merging or summarization)."""
        return [
            e for e in entities
            if e.get("strength", 0) < threshold and e.get("salience", 0) > 0.3
        ]
