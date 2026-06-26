# Synapse Architecture

## Overview

Synapse is a temporal knowledge graph memory system for AI agents. It gives agents the ability to remember past conversations, understand when facts change over time, and manage which memories to keep and which to forget — mimicking biological memory.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Hermes Agent                        │
│  ┌───────────────────────────────────────────────┐  │
│  │         Synapse Memory Provider                │  │
│  │                                               │  │
│  │  ┌─────────┐  ┌──────────┐  ┌──────────────┐  │  │
│  │  │ Encoding│  │ Retrieval│  │ Hippocampus  │  │  │
│  │  │ (batch) │  │ (BM25)   │  │ (salience +  │  │  │
│  │  │         │  │          │  │  forgetting) │  │  │
│  │  └────┬────┘  └────┬─────┘  └──────┬───────┘  │  │
│  │       │            │               │         │  │
│  │       v            v               v         │  │
│  │  ┌──────────────────────────────────────┐    │  │
│  │  │         Graphiti Engine               │    │  │
│  │  │  (bi-temporal KG, entity extraction)  │    │  │
│  │  └──────────────────┬───────────────────┘    │  │
│  └─────────────────────┼───────────────────────┘  │
└────────────────────────┼────────────────────────────┘
                         │
                         v
                 ┌───────────────┐
                 │   FalkorDB    │
                 │ (self-hosted) │
                 └───────────────┘
```

## Layers

### 1. Encoding Layer (`synapse/encoding.py`)

Buffers conversation turns and ingests them as batched Graphiti episodes.

- **Batch ingestion**: 5 turns per episode (configurable), reducing LLM calls by 86%
- **Trivial turn skipping**: turns with <10 char user messages AND <100 char assistant responses are skipped
- **Non-blocking**: ingestion runs in a background thread, never blocks the conversation loop

### 2. Retrieval Layer (`synapse/retrieval.py`)

BM25-only Cypher search with background caching.

- **BM25 fulltext search**: no LLM call needed, 0.01s vs 0.7s with reranker
- **Background caching**: `queue_prefetch()` runs search after each turn, `prefetch()` returns cached result on the next turn — zero blocking
- **Temporal search**: point-in-time queries using the `substring()` workaround for FalkorDB's `<=` bug

### 3. Hippocampus Layer (`synapse/hippocampus/`)

The novel contribution. Three biologically-inspired algorithms:

#### Salience Scorer (`salience.py`)

Scores entities and edges on a 0.0-1.0 scale:

| Factor | Weight | Description |
|--------|--------|-------------|
| Recency | 35% | Exponential decay from creation (half-life: 7 days) |
| Frequency | 30% | Log-normalized edge count |
| Correction | 20% | Boost for entities in superseded facts |
| Emotional | 15% | Keyword detection for urgency/emotion |

#### Forgetting Curve (`forgetting.py`)

Ebbinghaus exponential decay with salience modulation:

```
S(t) = exp(-t / tau)
tau = base_half_life × (1 + salience × boost) / ln(2)
```

- High-salience memories decay 4x slower than low-salience
- Recall events boost strength (spaced repetition)
- Pruning threshold: strength < 0.05

#### Consolidation Engine (`consolidation.py`)

The "sleep replay" cycle:

- **Hebbian strengthening**: entities co-occurring in the same episode get edge boost
- **Contradiction detection**: uses `invalid_at` as primary signal + keyword patterns
- **Pruning**: identifies low-strength, low-salience memories for removal

### 4. Graphiti Engine

External library that provides:
- Bi-temporal knowledge graph storage
- LLM-powered entity extraction from conversation text
- Edge temporal fields: `valid_at`, `invalid_at`, `expired_at`
- Entity summaries (auto-generated)
- BM25 + cosine similarity search

### 5. FalkorDB

Self-hosted Redis-backed graph database:
- Cypher query support
- Sparse-matrix acceleration
- Runs in Docker — privacy-first, no cloud dependency
- Graphs named after `group_id` (not database name)

## Optimizations

| # | Optimization | Impact |
|---|-------------|--------|
| 1 | Batch episode ingestion (5 turns/episode) | −86% LLM calls |
| 2 | BM25-only prefetch (no reranker) | 70x faster prefetch |
| 3 | Merged tools (synapse_query, not 2) | −61% prompt overhead |
| 4 | Trimmed system prompt block | −63% prompt tokens |
| 5 | Trivial turn skipping (<10 chars) | −30% episodes |
| 6 | Background prefetch with caching | Zero blocking latency |
| 7 | Configurable half-life | Runtime flexibility |

**Projected per 100-turn conversation:**
- Cost: $0.0192 (was $0.0705) — 73% reduction
- Latency: ~0s blocking (was 70s) — eliminated
- LLM calls: 14 (was 200) — 86% reduction

## Known Issues

- **FalkorDB `<=` bug**: The `<=` and `<` operators on edge properties in WHERE clauses don't filter correctly (v4.18.11). Workaround: wrap in `substring()`. Reported upstream.
- **Graph naming**: Graphiti stores data in FalkorDB graphs named after `group_id`, not the database name. Direct Cypher queries must target the correct graph.
- **Intra-episode corrections**: Graphiti doesn't auto-invalidate facts when corrections happen within the same episode. The hippocampus handles this via keyword detection.