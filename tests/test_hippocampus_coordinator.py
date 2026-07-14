"""Tests for the Hippocampus coordinator."""

from synapse.hippocampus import Hippocampus


def test_hippocampus_init():
    hp = Hippocampus()
    assert hp.salience is not None
    assert hp.forgetting is not None
    assert hp.consolidation is not None
    assert hp.pattern_completion is not None
    assert hp.reconsolidation is not None
    assert hp.prediction_error is not None
    assert hp.schema_extraction is not None
    assert hp.pattern_separation is not None


def test_on_recall_tracks_entities():
    hp = Hippocampus()
    assert not hp.get_active_entities()
    hp.on_recall(["Synapse", "FalkorDB"])
    active = hp.get_active_entities()
    assert "Synapse" in active
    assert "FalkorDB" in active
    assert hp.get_recall_count("Synapse") == 1


def test_tick_advances_turn_counter():
    hp = Hippocampus()
    hp.on_recall(["Synapse"])
    assert hp.reconsolidation.is_active("Synapse")
    for _ in range(11):
        hp.tick()
    assert not hp.reconsolidation.is_active("Synapse")


def test_on_episode_ingested_detects_novelty():
    hp = Hippocampus()
    result = hp.on_episode_ingested(
        new_entities=["Synapse", "Neo4j"],
        existing_entities=["Synapse", "FalkorDB"],
        new_edges=[],
        existing_edges=[],
    )
    assert result["novelty_score"] == 0.5  # 1 of 2 is novel
    assert "Neo4j" in result["novel_entities"]
    assert "Synapse" in result["known_entities"]


def test_on_episode_ingested_detects_contradictions():
    hp = Hippocampus()
    existing = [
        {"from_node": "DB", "to_node": "Prod", "fact": "Using PostgreSQL",
         "valid_at": "2026-01-01T00:00:00Z", "invalid_at": None},
    ]
    new = [
        {"from_node": "DB", "to_node": "Prod",
         "fact": "Switched from PostgreSQL to MongoDB",
         "valid_at": "2026-07-01T00:00:00Z", "invalid_at": None},
    ]
    result = hp.on_episode_ingested(
        new_entities=["DB", "Prod", "MongoDB"],
        existing_entities=["DB", "Prod", "PostgreSQL"],
        new_edges=new,
        existing_edges=existing,
    )
    assert len(result["contradictions"]) >= 1


def test_on_episode_ingested_scores_edges():
    hp = Hippocampus()
    new_edges = [
        {"from_node": "A", "to_node": "B", "fact": "A uses B",
         "valid_at": "2026-07-14T00:00:00Z", "invalid_at": None},
    ]
    result = hp.on_episode_ingested(
        new_entities=["A", "B"],
        existing_entities=[],
        new_edges=new_edges,
        existing_edges=[],
    )
    assert len(result["scored_edges"]) == 1
    assert "salience_scores" in result["scored_edges"][0]
    assert "total" in result["scored_edges"][0]["salience_scores"]


def test_on_episode_ingested_reconsolidation_boost():
    hp = Hippocampus()
    hp.on_recall(["A"])
    new_edges = [
        {"from_node": "A", "to_node": "C", "fact": "A connects to C",
         "valid_at": "2026-07-14T00:00:00Z", "invalid_at": None},
    ]
    result = hp.on_episode_ingested(
        new_entities=["A", "C"],
        existing_entities=["A"],
        new_edges=new_edges,
        existing_edges=[],
    )
    boosted = result["scored_edges"][0]["salience_scores"]["total"]
    assert boosted > 0


def test_run_consolidation_drains_pending():
    hp = Hippocampus()
    existing = [
        {"from_node": "X", "to_node": "Y", "fact": "X is Y",
         "valid_at": "2026-01-01T00:00:00Z", "invalid_at": None},
    ]
    new = [
        {"from_node": "X", "to_node": "Y", "fact": "X is not Y",
         "valid_at": "2026-07-01T00:00:00Z", "invalid_at": None},
    ]
    hp.on_episode_ingested(
        new_entities=["X", "Y"],
        existing_entities=["X", "Y"],
        new_edges=new,
        existing_edges=existing,
    )
    assert len(hp._pending_contradictions) > 0

    result = hp.run_consolidation(existing + new)
    assert len(result["online_contradictions"]) > 0
    assert len(hp._pending_contradictions) == 0


def test_extract_schemas():
    hp = Hippocampus()
    edges = [
        {"from_node": "A", "to_node": "B", "fact": "A uses B",
         "valid_at": "2026-01-01T00:00:00Z", "invalid_at": None},
        {"from_node": "B", "to_node": "C", "fact": "B connects to C",
         "valid_at": "2026-01-01T00:00:00Z", "invalid_at": None},
        {"from_node": "A", "to_node": "C", "fact": "A relates to C",
         "valid_at": "2026-01-01T00:00:00Z", "invalid_at": None},
    ]
    schemas = hp.extract_schemas(edges)
    assert len(schemas) >= 1
    assert "summary" in schemas[0]


def test_compute_strength_and_prune():
    hp = Hippocampus()
    strength = hp.compute_strength(salience=0.9, age_days=1.0)
    assert strength > 0.8

    strength = hp.compute_strength(salience=0.1, age_days=100.0)
    assert strength < 0.5
    assert hp.should_prune(strength)


def test_clear_resets_state():
    hp = Hippocampus()
    hp.on_recall(["Test"])
    assert hp.get_active_entities()
    hp.clear()
    assert not hp.get_active_entities()
    assert len(hp._pending_contradictions) == 0


def test_expand_recall_pattern_completion():
    hp = Hippocampus()
    edges = [
        {"from_node": "A", "to_node": "B", "fact": "A uses B for storage",
         "valid_at": "2026-01-01T00:00:00Z", "invalid_at": None},
        {"from_node": "B", "to_node": "C", "fact": "B runs in Docker",
         "valid_at": "2026-01-01T00:00:00Z", "invalid_at": None},
    ]
    result = hp.expand_recall("storage", edges)
    assert len(result["facts"]) >= 1
    assert "A" in result["entities"] or "B" in result["entities"]
