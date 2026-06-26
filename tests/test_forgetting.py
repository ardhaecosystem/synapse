"""Tests for ForgettingCurve."""

from synapse.hippocampus.forgetting import ForgettingCurve


def test_fresh_memory_full_strength():
    fc = ForgettingCurve(base_half_life_days=7.0)
    strength = fc.compute_strength(salience=0.5, age_days=0.0)
    assert strength == 1.0


def test_decayed_memory():
    fc = ForgettingCurve(base_half_life_days=7.0)
    # At 1 half-life with salience=0 → base decay → ~0.5
    strength = fc.compute_strength(salience=0.0, age_days=7.0)
    assert 0.49 < strength < 0.51


def test_high_salience_decays_slower():
    fc = ForgettingCurve(base_half_life_days=7.0, salience_boost=3.0)
    low = fc.compute_strength(salience=0.0, age_days=14.0)
    high = fc.compute_strength(salience=1.0, age_days=14.0)
    assert high > low


def test_pruning_threshold():
    fc = ForgettingCurve(base_half_life_days=1.0)  # fast decay for test
    strength = fc.compute_strength(salience=0.0, age_days=20.0)
    assert fc.should_prune(strength)


def test_recall_boost():
    fc = ForgettingCurve(base_half_life_days=7.0, recall_boost=1.5)
    no_recall = fc.compute_strength(salience=0.5, age_days=14.0)
    with_recall = fc.compute_strength(salience=0.5, age_days=14.0, last_recall_days=1.0)
    assert with_recall > no_recall
