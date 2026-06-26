"""Salience scoring — entity/edge importance based on 4 weighted factors.

Factors:
    - Recency (35%): exponential decay from creation time
    - Frequency (30%): log-normalized edge count
    - Correction (20%): boost for entities involved in contradictions
    - Emotional (15%): keyword detection for urgency/emotion

Score range: 0.0 to 1.0
"""

from __future__ import annotations

import math
from datetime import datetime, timezone


class SalienceScorer:
    """Score entities and edges by importance."""

    EMOTIONAL_KEYWORDS = frozenset({
        "urgent", "critical", "important", "must", "need", "asap",
        "breaking", "warning", "error", "fix", "broken", "wrong",
        "love", "hate", "terrible", "amazing", "disaster", "crisis",
    })

    WEIGHTS = {"recency": 0.35, "frequency": 0.30, "correction": 0.20, "emotional": 0.15}

    def __init__(self, half_life_days: float = 7.0):
        self.half_life_days = half_life_days
        self.now = datetime.now(timezone.utc)

    def score_entity(
        self,
        name: str,
        summary: str,
        created_at: str,
        edge_count: int,
        invalid_at: str | None = None,
    ) -> dict:
        """Score a single entity on a 0.0-1.0 scale."""
        scores = {}

        # Recency: exponential decay from creation time
        if created_at:
            try:
                created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                age_days = max(0, (self.now - created).total_seconds() / 86400)
                scores["recency"] = math.exp(-0.693 * age_days / self.half_life_days)
            except Exception:
                scores["recency"] = 0.5
        else:
            scores["recency"] = 0.5

        # Frequency: log normalization
        scores["frequency"] = min(1.0, math.log(1 + edge_count) / math.log(10))

        # Correction: boost if entity was involved in a superseded fact
        scores["correction"] = 0.3 if invalid_at else 0.0

        # Emotional: keyword detection in summary
        summary_lower = (summary or "").lower()
        hits = sum(1 for kw in self.EMOTIONAL_KEYWORDS if kw in summary_lower)
        scores["emotional"] = min(1.0, hits * 0.3)

        # Weighted total
        scores["total"] = round(
            sum(scores[f] * self.WEIGHTS[f] for f in self.WEIGHTS), 4
        )
        scores["edge_count"] = edge_count
        return scores

    def score_edge(
        self,
        fact: str,
        valid_at: str,
        invalid_at: str | None,
        recall_count: int = 0,
    ) -> dict:
        """Score a single edge/fact on a 0.0-1.0 scale."""
        scores = {}

        # Recency
        if valid_at:
            try:
                valid = datetime.fromisoformat(valid_at.replace("Z", "+00:00"))
                age_days = max(0, (self.now - valid).total_seconds() / 86400)
                scores["recency"] = math.exp(-0.693 * age_days / self.half_life_days)
            except Exception:
                scores["recency"] = 0.5
        else:
            scores["recency"] = 0.5

        # Validity: still active?
        scores["validity"] = 0.0 if invalid_at else 1.0

        # Recall frequency
        scores["recall"] = min(1.0, recall_count * 0.2)

        # Richness: fact length as information proxy
        scores["richness"] = min(1.0, len(fact) / 200)

        weights = {"recency": 0.30, "validity": 0.35, "recall": 0.20, "richness": 0.15}
        scores["total"] = round(
            sum(scores[f] * weights[f] for f in weights), 4
        )
        return scores
