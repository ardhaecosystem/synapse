# The Hippocampus Layer

The hippocampus is the novel contribution of Synapse. It implements biologically-inspired memory management on top of Graphiti's temporal knowledge graph.

## Why a Hippocampus?

In the human brain, the hippocampus is responsible for:
- **Memory consolidation**: transferring short-term memories to long-term storage during sleep
- **Spatial mapping**: understanding relationships between entities
- **Pattern separation**: distinguishing similar but different experiences

Synapse's hippocampus implements these concepts as algorithms that run on the knowledge graph.

## Algorithms

### 1. Salience Scoring

Every entity and edge in the graph gets a salience score from 0.0 to 1.0. This score determines how slowly the memory decays and whether it's a candidate for pruning.

#### Factors

| Factor | Weight | Formula | Rationale |
|--------|--------|---------|----------|
| Recency | 35% | `exp(-0.693 × age_days / half_life)` | Recent memories are more relevant |
| Frequency | 30% | `log(1 + edge_count) / log(10)` | Well-connected entities are more important |
| Correction | 20% | `0.3 if invalid_at else 0.0` | Mistakes and corrections are remembered vividly |
| Emotional | 15% | `min(1.0, keyword_hits × 0.3)` | Emotional content gets priority |

#### Emotional Keywords

```
urgent, critical, important, must, need, asap,
breaking, warning, error, fix, broken, wrong,
love, hate, terrible, amazing, disaster, crisis
```

### 2. Forgetting Curve

Based on Hermann Ebbinghaus's forgetting curve, with a modification: salience modulates the decay rate.

#### Formula

```
S(t) = S₀ × exp(-t / τ)
τ = base_half_life × (1 + salience × boost) / ln(2)
```

Where:
- `S(t)` = memory strength at time t
- `S₀` = initial strength (1.0)
- `t` = age in days
- `τ` = time constant (salience-modulated)
- `base_half_life` = 7 days (configurable)
- `boost` = 3.0 (high-salience decays 4x slower)

#### Spaced Repetition (Recall Boost)

When a memory is recalled (appears in search results), its decay clock resets:

```
if last_recall_days < age_days:
    recall_strength = exp(-last_recall_days / (τ × recall_boost)) × 0.8
    strength = max(base_strength, recall_strength)
```

#### Pruning

Memories with strength < 0.05 (configurable) are candidates for pruning.

### 3. Consolidation

The consolidation engine runs periodically (default: every 6 hours) as a background task.

#### Hebbian Strengthening

"Neurons that fire together wire together."

Entities that appear in the same episode (same `valid_at` timestamp) have their edges strengthened. This is detected by grouping edges by timestamp and identifying co-occurring entities.

#### Contradiction Detection

Two signals are used:

1. **Primary**: `invalid_at` field on edges. When an edge has `invalid_at` set, it was superseded. The engine finds the superseding edge (same entity, `valid_at ≈ invalid_at`).

2. **Secondary**: Keyword patterns in fact text. Detects "instead of", "replacing", "not X" patterns that indicate intra-episode corrections.

#### Example

```
T1: "A uses PostgreSQL" (valid_at=2026-01-01, invalid_at=None)
T2: "A uses MongoDB instead of PostgreSQL" (valid_at=2026-01-03, invalid_at=None)
```

The hippocampus detects this as a contradiction and would mark the PostgreSQL edge as invalidated at 2026-01-03.

## Integration

The hippocampus algorithms are designed to run as a periodic background task via Hermes's cron system:

```yaml
# In Hermes cron
schedule: "0 */6 * * *"  # Every 6 hours
prompt: "Run Synapse hippocampus consolidation"
```

Or can be triggered manually via a future CLI command:

```bash
hermes synapse consolidate  # Future feature
```