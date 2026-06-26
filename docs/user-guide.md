# Synapse — User Documentation

Welcome to Synapse, the temporal knowledge graph memory system for AI agents.

This documentation covers everything you need to install, configure, and use Synapse with Hermes Agent.

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Configuration](#configuration)
4. [Tools Reference](#tools-reference)
5. [Hippocampus Layer](#hippocampus-layer)
6. [Architecture](#architecture)
7. [Troubleshooting](#troubleshooting)
8. [API Reference](#api-reference)

---

## Installation

### Prerequisites

- **Python 3.11+**
- **Docker** (for FalkorDB)
- **An LLM API key** from any OpenAI-compatible provider

### Step 1: Start FalkorDB

FalkorDB is the self-hosted graph database that stores your memories. It runs in Docker — your data stays on your machine.

```bash
# Using Docker directly
docker run -d \
  --name synapse-falkordb \
  -p 6379:6379 \
  -v falkordb-data:/var/lib/falkordb \
  falkordb/falkordb:latest

# Or using Docker Compose (included in the repo)
cd synapse/docker
docker compose up -d
```

Verify FalkorDB is running:

```bash
docker exec synapse-falkordb redis-cli PING
# → PONG
```

### Step 2: Install Synapse

```bash
# From PyPI (when published)
pip install synapse-memory

# Or from source
git clone https://github.com/ardhaecosystem/synapse.git
cd synapse
pip install -e .
```

### Step 3: Configure Hermes

```bash
# Set Synapse as your memory provider
hermes config set memory.provider synapse

# Add your credentials to ~/.hermes/.env
cat >> ~/.hermes/.env << 'EOF'
SYNAPSE_FALKORDB_HOST=localhost
SYNAPSE_FALKORDB_PORT=6379
SYNAPSE_LLM_API_KEY=your-api-key
SYNAPSE_LLM_BASE_URL=https://openrouter.ai/api/v1
SYNAPSE_LLM_MODEL=openai/gpt-4o-mini
SYNAPSE_EMBEDDING_MODEL=openai/text-embedding-3-small
EOF

# Or use the interactive setup wizard
hermes memory setup
# Select "synapse" and follow the prompts
```

### Step 4: Restart Hermes

```bash
# CLI
hermes

# Or if running as a gateway service
hermes gateway restart
```

That's it. Synapse is now your agent's memory system.

---

## Quick Start

Once Synapse is configured, your Hermes agent automatically:

1. **Remembers conversations** — every turn is stored as a temporal knowledge graph episode with entity extraction
2. **Recalls relevant context** — before each turn, Synapse retrieves memories relevant to your current message
3. **Manages memory** — the hippocampus layer scores salience, applies forgetting curves, and consolidates memories during idle time

### Using the Tools

Your agent now has two memory tools:

#### `synapse_query` — Search Memories

The agent uses this to recall past conversations and facts:

```
User: "What database did we decide to use for the project?"
Agent: [calls synapse_query] "You decided to use MongoDB, switching from PostgreSQL
       because it's a better fit for document-based APIs."
```

Set `at_time` for point-in-time queries:

```
User: "What were we using before we switched to MongoDB?"
Agent: [calls synapse_query with at_time="2026-06-20"]
       "Before the switch, you were using PostgreSQL as the database."
```

#### `synapse_remember` — Save Important Facts

The agent uses this to save durable facts it should never forget:

```
Agent: [calls synapse_remember with content="User prefers concise responses"
        category="user_profile"]
       "Got it — I'll keep that in mind."
```

Categories:
- `user_profile` — facts about you (preferences, style, habits)
- `environment` — facts about the agent's setup (tools, conventions)
- `conclusion` — insights and decisions worth remembering
- `general` — anything else

These facts are stored with maximum salience (1.0) and **never decay** — they're the agent's permanent, curated memories.

---

## Configuration

### All Environment Variables

#### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `SYNAPSE_FALKORDB_HOST` | FalkorDB host address | `localhost` |
| `SYNAPSE_LLM_API_KEY` | LLM API key (OpenAI-compatible) | `sk-or-...` |
| `SYNAPSE_LLM_BASE_URL` | LLM base URL | `https://openrouter.ai/api/v1` |

#### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `SYNAPSE_FALKORDB_PORT` | `6379` | FalkorDB port |
| `SYNAPSE_FALKORDB_PASSWORD` | None | FalkorDB password (if configured) |
| `SYNAPSE_DATABASE` | `synapse` | FalkorDB database name |
| `SYNAPSE_LLM_MODEL` | `gpt-4o-mini` | Model for entity extraction |
| `SYNAPSE_EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model for vector search |
| `SYNAPSE_BATCH_SIZE` | `5` | Turns per episode (optimization) |
| `SYNAPSE_HALF_LIFE_DAYS` | `7.0` | Forgetting curve half-life in days |

### Supported LLM Providers

Any OpenAI-compatible endpoint works:

| Provider | Base URL | Notes |
|----------|----------|-------|
| OpenRouter | `https://openrouter.ai/api/v1` | Access to many models, supports embeddings |
| OpenAI | `https://api.openai.com/v1` | Native support |
| Ollama (local) | `http://localhost:11434/v1` | Free, self-hosted, privacy-first |
| vLLM | `http://localhost:8000/v1` | High-throughput local inference |
| LM Studio | `http://localhost:1234/v1` | Desktop local inference |
| DeepSeek | `https://api.deepseek.com` | Cost-effective |
| Together | `https://api.together.xyz/v1` | Open models |
| Z.AI / GLM | `https://open.bigmodel.cn/api/paas/v4` | GLM models |

### Native Memory Integration

Synapse works alongside or instead of Hermes' native memory:

#### Option A: Synapse only (recommended for full brain mode)

```yaml
# ~/.hermes/config.yaml
memory:
  memory_enabled: false        # Disable MEMORY.md
  user_profile_enabled: false  # Disable USER.md
  provider: synapse            # Use Synapse as sole memory
```

In this mode:
- The system prompt tells the agent to use `synapse_remember` for explicit facts
- User profile and environment facts are injected from the graph
- The `memory` tool still appears but the agent is guided to use `synapse_remember` instead

#### Option B: Native + Synapse (supplementary mode)

```yaml
# ~/.hermes/config.yaml
memory:
  memory_enabled: true         # Keep MEMORY.md
  user_profile_enabled: true   # Keep USER.md
  provider: synapse            # Add Synapse for temporal graph memory
```

In this mode:
- MEMORY.md and USER.md work as normal
- Synapse adds temporal knowledge graph memory on top
- `on_memory_write()` mirrors native writes to the graph
- System prompt is minimal (native handles the prompt injection)

### Tuning Guide

#### Forgetting Curve Half-Life

Controls how fast memories fade. Higher = memories persist longer.

| Use Case | Recommended | Rationale |
|----------|-----------|-----------|
| Coding assistant | 3-7 days | Code context changes fast |
| Research assistant | 14-30 days | Research spans weeks |
| Personal assistant | 30-90 days | Long-term relationships |
| General purpose | 7 days | Good default balance |

```bash
# Set a 30-day half-life for long-term memory
echo "SYNAPSE_HALF_LIFE_DAYS=30" >> ~/.hermes/.env
```

#### Batch Size

Controls how many conversation turns are batched into a single episode. Higher = fewer LLM calls but less granular temporal tracking.

| Value | LLM Calls/100 turns | When to use |
|-------|---------------------|------------|
| 1 | 100 | Never (no benefit) |
| 3 | 33 | High-precision conversations |
| 5 | 14 | Default — good balance |
| 10 | 7 | Long sessions with similar topics |

```bash
# Set batch size to 3 for more granular memory
echo "SYNAPSE_BATCH_SIZE=3" >> ~/.hermes/.env
```

---

## Tools Reference

### `synapse_query`

Search the temporal knowledge graph for memories.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | Search query |
| `at_time` | string | No | ISO date for point-in-time queries (e.g., `2026-06-22`) |

**Behavior:**
- Without `at_time`: searches all active memories (BM25 fulltext)
- With `at_time`: returns only facts that were valid at that point in time

**Example:**

```json
// Agent calls:
synapse_query(query="what database are we using")

// Returns:
{
  "results": [
    {"fact": "FastAPI service uses MongoDB for storage", "from_node": "FastAPI", "to_node": "MongoDB"},
    {"fact": "MongoDB replaced PostgreSQL for document APIs", "from_node": "FastAPI", "to_node": "MongoDB"}
  ],
  "count": 2
}
```

### `synapse_remember`

Save a durable fact to memory permanently. These facts never decay.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `content` | string | Yes | The fact to remember |
| `category` | string | No | `user_profile`, `environment`, `conclusion`, or `general` |

**Behavior:**
- Fact is stored in the knowledge graph with maximum salience (1.0)
- Fact is cached for system prompt injection (replaces USER.md/MEMORY.md)
- Fact is ingested as a Graphiti episode for entity extraction
- Fact **never decays** — exempt from the forgetting curve

**Example:**

```json
// Agent calls:
synapse_remember(content="User prefers Python over JavaScript", category="user_profile")

// Returns:
{
  "success": true,
  "message": "Saved to memory (category: user_profile).",
  "category": "user_profile"
}
```

---

## Hippocampus Layer

The hippocampus is what makes Synapse a brain, not a database. It implements nine biologically-inspired algorithms:

### Core Algorithms (v0.1)

#### 1. Salience Scoring

Every entity and edge gets a 0.0-1.0 importance score based on:

| Factor | Weight | What It Measures |
|--------|--------|-----------------|
| Recency | 35% | How recently the entity was referenced |
| Frequency | 30% | How many edges connect to this entity |
| Correction | 20% | Was this entity involved in a corrected fact? |
| Emotional | 15% | Does the summary contain urgency/emotion keywords? |

High-salience memories decay slower and are prioritized during consolidation.

#### 2. Forgetting Curve (Ebbinghaus)

Memories decay exponentially over time, but salience modulates the decay rate:

```
Strength(t) = exp(-t / τ)
τ = half_life × (1 + salience × 3.0) / ln(2)
```

- High-salience memories have 4x longer effective half-life
- Recall events reset the decay clock (spaced repetition)
- Memories below 0.05 strength are pruning candidates

#### 3. Consolidation Engine

The "sleep replay" cycle:

- **Hebbian strengthening**: entities co-occurring in the same episode get edge boosts
- **Contradiction detection**: finds superseded facts via `invalid_at` field + keyword patterns
- **Pruning**: identifies low-strength, low-salience memories for removal

### Advanced Algorithms (v0.2)

#### 4. Pattern Completion (CA3 Analog)

Given a partial search match, expands to the full context subgraph via BFS:

```
Query: "FalkorDB"
BM25 match: "Synapse uses FalkorDB"
Pattern completion expands to:
  → "Synapse uses Graphiti" (2-hop via Synapse)
  → "FalkorDB runs in Docker" (1-hop from FalkorDB)
```

Configurable max depth (default: 2 hops).

#### 5. Reconsolidation

When a memory is recalled, it enters a "labile" (unstable) window for N turns:

- Recalled entities get a salience boost (0.2 by default)
- New edges to recalled entities get priority encoding
- Recall counter feeds into the forgetting curve's spaced repetition

The reconsolidation window defaults to 10 turns (roughly 10 conversation exchanges).

#### 6. Prediction Error / Novelty Detection

Detects when new information contradicts or surprises existing memories:

- **Novelty**: completely new entities get enhanced encoding
- **Contradiction**: new facts that contradict existing edges trigger invalidation
- **Surprise**: known entities appearing in unexpected contexts get salience boost

#### 7. Schema Extraction (Neocortex Analog)

The "slow learning system" — implements Complementary Learning Systems theory:

- Periodically clusters entities by topic (connected components)
- Creates "schema nodes" that generalize from individual episodes
- Example: 50 conversations about different projects → schema: "User works on AI projects"

This is the bridge from remembering to understanding.

#### 8. Pattern Separation (Dentate Gyrus Analog)

Prevents context contamination between similar-but-different conversations:

- Computes entity fingerprints (sets of connected entities)
- Jaccard similarity between fingerprints
- High similarity + different contexts → flag for separation (don't merge)

#### 9. Cognitive Map

Navigation utilities for the knowledge graph:

- Shortest semantic path between two entities (BFS)
- Entity neighborhoods (1-hop, 2-hop subgraphs)
- Entity degree (number of connections)

Useful for debugging and understanding graph structure.

### Biological References

| Algorithm | Biological Inspiration | Key Reference |
|-----------|----------------------|---------------|
| Salience | Amygdala tagging | — |
| Forgetting | Memory decay | Ebbinghaus (1885) |
| Consolidation | Sleep replay | Wilson & McNaughton (1994) |
| Pattern Completion | CA3 autoassociative memory | Rolls (2015) |
| Reconsolidation | Memory reactivation lability | Nader et al. (2000) |
| Prediction Error | Hippocampal surprise signal | Kumaran & Maguire (2006) |
| Schema Extraction | Complementary Learning Systems | McClelland et al. (1995) |
| Pattern Separation | Dentate gyrus | Leutgeb et al. (2007) |
| Cognitive Map | Grid/place cells | O'Keefe & Nadel (1978) |

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                   Hermes Agent                         │
│                                                       │
│  System Prompt (frozen per session):                  │
│  ┌─────────────────────────────────────────────────┐  │
│  │ Synapse system_prompt_block():                   │  │
│  │   User profile facts (from graph)                │  │
│  │   Environment facts (from graph)                 │  │
│  │   Tool usage instructions                        │  │
│  └─────────────────────────────────────────────────┘  │
│                                                       │
│  Per-turn lifecycle:                                  │
│  ┌──────────┐  ┌────────────┐  ┌──────────────────┐  │
│  │ prefetch │  │ sync_turn  │  │ synapse_remember │  │
│  │ (BM25 +  │  │ (batch +  │  │ (explicit write  │  │
│  │  pattern │  │  prediction│  │  → max salience  │  │
│  │  complet-│  │  error +  │  │  → never decays) │  │
│  │  ion)    │  │  reconso- │  │                  │  │
│  │          │  │  lidation)│  │                  │  │
│  └──────────┘  └────────────┘  └──────────────────┘  │
│                                                       │
│  Background ("sleep"):                                │
│  ┌─────────────────────────────────────────────────┐  │
│  │ Schema Extraction → generalization               │  │
│  │ Forgetting Curve → pruning                       │  │
│  │ Consolidation → Hebbian + contradiction          │  │
│  └─────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
                         │
                         v
                 ┌───────────────┐
                 │   FalkorDB    │
                 │ (self-hosted  │
                 │  in Docker)   │
                 └───────────────┘
```

### Data Flow

1. **User sends message** → Hermes builds system prompt (includes Synapse's brain-mode block with cached facts)
2. **Prefetch** → Synapse returns cached BM25 results from previous turn's background search (zero blocking)
3. **Agent responds** → Turn completes
4. **sync_turn** → Turn buffered (batch ingestion). Trivial turns skipped. Reconsolidation tick fires.
5. **Background** → If buffer is full (5 turns), episode is ingested via Graphiti (entity extraction, edge creation)
6. **Queue prefetch** → Background BM25 search for next turn's context
7. **Periodic** → Consolidation cycle runs (schema extraction, forgetting, Hebbian strengthening)

### Optimizations

| Optimization | Impact |
|-------------|--------|
| Batch ingestion (5 turns/episode) | −86% LLM calls |
| BM25-only prefetch (no reranker) | 70x faster prefetch |
| Background prefetch caching | Zero blocking latency |
| Trivial turn skipping | −30% episodes |
| Merged tool schemas | Minimal prompt overhead |

---

## Troubleshooting

### FalkorDB Connection Issues

**Problem:** `Connection refused` or `PONG` not returned

```bash
# Check if container is running
docker ps | grep falkordb

# If not, start it
docker run -d --name synapse-falkordb -p 6379:6379 falkordb/falkordb:latest

# Check logs
docker logs synapse-falkordb
```

**Problem:** `Connection closed by server`

This can happen if multiple Graphiti instances try to connect simultaneously. Restart FalkorDB:

```bash
docker restart synapse-falkordb
```

### LLM API Issues

**Problem:** Entity extraction fails or times out

- Check your API key: `echo $SYNAPSE_LLM_API_KEY`
- Check your base URL: `echo $SYNAPSE_LLM_BASE_URL`
- Try a different model: `SYNAPSE_LLM_MODEL=openai/gpt-4o`
- Check rate limits on your provider

**Problem:** Embeddings fail

Not all OpenAI-compatible providers support embeddings. If yours doesn't:

- Use OpenRouter (supports `text-embedding-3-small`)
- Use OpenAI directly for embeddings
- Run Ollama locally with an embedding model

### Memory Not Working

**Problem:** Agent doesn't seem to remember past conversations

1. Verify Synapse is active: check system prompt for "Synapse memory active"
2. Check that turns are being ingested: look for log messages "Synapse episode ingestion"
3. Verify FalkorDB has data: `docker exec synapse-falkordb redis-cli KEYS "*"`
4. Try the `synapse_query` tool directly

**Problem:** `synapse_remember` returns failure

1. Check that Graphiti is initialized (look for "Synapse initialized" in logs)
2. Check FalkorDB connection
3. Check LLM API key is valid

### Performance

**Problem:** Prefetch is slow

- Ensure `SYNAPSE_BATCH_SIZE` is at least 3 (default 5)
- BM25-only prefetch should be <0.01s — if it's slower, check FalkorDB resources
- The first turn after restart may be slow (cache is empty)

**Problem:** Episode ingestion is slow

- Entity extraction takes ~13s per episode (LLM-bound)
- This is non-blocking — it runs in a background thread
- If it's consistently >30s, try a faster model

### FalkorDB `<=` Bug

FalkorDB v4.18.11 has a known bug where `<=` and `<` operators on edge properties in WHERE clauses don't filter correctly. Synapse works around this using `substring()` wrapping in temporal queries. If you experience temporal query issues:

- Verify you're using the latest Synapse version
- Check that `FalkorHelper.temporal_filter_query()` is being used (not raw Cypher)
- Report the bug to FalkorDB: https://github.com/FalkorDB/FalkorDB/issues

---

## API Reference

### Python API

#### SynapseConfig

```python
from synapse.config import SynapseConfig

# From environment variables
config = SynapseConfig.from_env()

# Direct construction
config = SynapseConfig(
    falkordb_host="localhost",
    falkordb_port=6379,
    llm_api_key="sk-...",
    llm_base_url="https://openrouter.ai/api/v1",
    batch_size=5,
    half_life_days=7.0,
)
```

#### SalienceScorer

```python
from synapse.hippocampus.salience import SalienceScorer

scorer = SalienceScorer(half_life_days=7.0)

# Score an entity
scores = scorer.score_entity(
    name="Synapse",
    summary="Temporal knowledge graph for AI agents",
    created_at="2026-06-20T10:00:00+00:00",
    edge_count=5,
    invalid_at=None,
)
# scores["total"] → 0.69

# Score an edge
edge_scores = scorer.score_edge(
    fact="Synapse uses FalkorDB for storage",
    valid_at="2026-06-20T10:00:00+00:00",
    invalid_at=None,
)
```

#### ForgettingCurve

```python
from synapse.hippocampus.forgetting import ForgettingCurve

fc = ForgettingCurve(base_half_life_days=7.0, salience_boost=3.0)

# Compute memory strength
strength = fc.compute_strength(salience=0.69, age_days=6.0)
# → 0.82

# Check if memory should be pruned
if fc.should_prune(strength):
    print("This memory is forgotten")
```

#### PatternCompletion

```python
from synapse.hippocampus.pattern_completion import PatternCompletion

pc = PatternCompletion(group_id="default", max_depth=2)

# Complete a partial search match
result = pc.complete("FalkorDB", edges)
# result["facts"] → all facts in the 2-hop neighborhood
# result["entities"] → all entities in the completed subgraph
```

#### ReconsolidationTracker

```python
from synapse.hippocampus.reconsolidation import ReconsolidationTracker

tracker = ReconsolidationTracker(window_turns=10, boost=0.2)

# When an entity is recalled
tracker.recall("Synapse")

# Each turn
tracker.tick()

# Check if entity is in reconsolidation window
if tracker.is_active("Synapse"):
    boost = tracker.get_boost("Synapse")  # → 0.2

# Get recall count (for spaced repetition)
count = tracker.get_recall_count("Synapse")  # → 1
```

#### SchemaExtractor

```python
from synapse.hippocampus.schema_extraction import SchemaExtractor

extractor = SchemaExtractor(min_cluster_size=3)

# Extract schemas from graph edges
schemas = extractor.extract(edges)
for schema in schemas:
    print(f"Schema: {schema['summary']}")
    print(f"  Entities: {schema['entities']}")
    print(f"  Facts: {schema['fact_count']}")
```

#### PredictionErrorDetector

```python
from synapse.hippocampus.prediction_error import PredictionErrorDetector

detector = PredictionErrorDetector()

# Detect novel entities
result = detector.detect(
    existing_entities=["Synapse", "FalkorDB"],
    new_entities=["Synapse", "Neo4j"],
)
# result["novel_entities"] → ["Neo4j"]

# Detect contradictions
contradictions = detector.detect_contradictions(existing_edges, new_edges)
```

### CLI (Future)

```bash
# Check Synapse status
hermes synapse status

# Run consolidation manually
hermes synapse consolidate

# Export graph
hermes synapse export --output memories.json

# Clear graph
hermes synapse clear --group-id default
```

---

## FAQ

### Is my data private?

Yes. FalkorDB runs on your machine in Docker. No conversation data leaves your network except LLM API calls for entity extraction (which send text to your chosen LLM provider). If you use Ollama locally, even entity extraction stays on your machine.

### Can I use Synapse without Hermes?

Not yet. Synapse is designed as a Hermes Agent memory provider plugin. The hippocampus algorithms (salience, forgetting, consolidation, etc.) are framework-agnostic and could be used independently, but the provider integration is Hermes-specific.

### How much does it cost?

With `gpt-4o-mini` via OpenRouter:
- ~$0.02 per 100-turn conversation (with batch optimization)
- ~$0.07 without optimization (batch size=1)

With a local Ollama model: free.

### Can I use multiple LLM providers?

Synapse uses one LLM for entity extraction and one embedder for vector search. They can be different providers (e.g., Ollama for extraction, OpenAI for embeddings) as long as both are OpenAI-compatible.

### What happens when FalkorDB runs out of memory?

The hippocampus layer prunes low-salience, low-strength memories automatically. You can also manually clear the graph or increase Docker's memory limit.

### How do I inspect the graph?

FalkorDB includes a web UI on port 3000:

```bash
# Access the FalkorDB browser
open http://localhost:3000
```

You can also use `redis-cli` for direct Cypher queries:

```bash
docker exec synapse-falkordb redis-cli GRAPH.QUERY synapse "MATCH (n:Entity) RETURN n.name"
```