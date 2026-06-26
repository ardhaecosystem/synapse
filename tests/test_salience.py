"""Tests for SalienceScorer."""

from datetime import datetime, timedelta, timezone

from synapse.hippocampus.salience import SalienceScorer


def test_recency_decay():
    """Recency should decay exponentially with age."""
    scorer = SalienceScorer(half_life_days=7.0)
    now = datetime.now(timezone.utc)

    # Fresh entity (0 days old) → recency ≈ 1.0
    scores = scorer.score_entity("test", "summary", now.isoformat(), 1)
    assert scores["recency"] > 0.99

    # 7-day-old entity (1 half-life) → recency ≈ 0.5
    old = (now - timedelta(days=7)).isoformat()
    scores = scorer.score_entity("test", "summary", old, 1)
    assert 0.48 < scores["recency"] < 0.52


def test_frequency_log_scale():
    """Frequency should use log normalization."""
    scorer = SalienceScorer()
    # 0 edges → 0.0
    scores = scorer.score_entity("test", "", "", 0)
    assert scores["frequency"] == 0.0
    # 10 edges → ≈ 1.0
    scores = scorer.score_entity("test", "", "", 10)
    assert scores["frequency"] > 0.99


def test_correction_boost():
    """Entities with invalid_at should get correction boost."""
    scorer = SalienceScorer()
    scores_no_correction = scorer.score_entity("test", "", "", 1, invalid_at=None)
    scores_with_correction = scorer.score_entity("test", "", "", 1, invalid_at="2026-01-01")
    assert scores_with_correction["correction"] > scores_no_correction["correction"]


def test_emotional_keywords():
    """Emotional keywords in summary should boost emotional score."""
    scorer = SalienceScorer()
    scores_plain = scorer.score_entity("test", "a normal summary", "", 1)
    scores_urgent = scorer.score_entity("test", "this is urgent and critical", "", 1)
    assert scores_urgent["emotional"] > scores_plain["emotional"]


def test_total_score_range():
    """Total score should be between 0.0 and 1.0."""
    scorer = SalienceScorer()
    scores = scorer.score_entity("test", "summary", "", 3)
    assert 0.0 <= scores["total"] <= 1.0


def test_edge_scoring():
    """Edge scoring should include validity and richness."""
    scorer = SalienceScorer()
    scores = scorer.score_edge("A uses B for storage", "2026-01-01", None)
    assert scores["validity"] == 1.0  # active edge
    assert scores["total"] > 0.0
