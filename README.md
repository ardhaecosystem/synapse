<div align="center">

# 🧠 Synapse

### A synthetic hippocampus for AI agents.

Temporal knowledge graph memory that doesn't just *store* — it *remembers*.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
|[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
|[![CI](https://github.com/ardhaecosystem/synapse/actions/workflows/ci.yml/badge.svg)](https://github.com/ardhaecosystem/synapse/actions/workflows/ci.yml)
|[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-ff69b4.svg)](https://github.com/ardhaecosystem/synapse/blob/main/CONTRIBUTING.md)

</div>

<p align="center">
  <strong>Self-hosted temporal memory for AI agents.</strong><br>
  If this project is useful to you, consider <a href="https://github.com/ardhaecosystem/synapse">⭐ starring the repo</a> — it helps others discover it.
</p>

---

## The Problem

Every AI agent memory system today falls into one of three buckets:

| ❌ Flat text | ❌ Cloud-locked | ❌ All-or-nothing |
|---|---|---|
| No relationships. No temporal awareness. Just a growing blob of text. | Your conversations live on someone else's server. Your data, their infrastructure. | Every memory has equal weight. Nothing is forgotten. The context window drowns. |

## The Solution

Synapse gives AI agents a **biologically-inspired memory system** — a temporal knowledge graph with a hippocampus layer that scores importance, manages forgetting, and consolidates memories during idle time. Just like a real brain.

- **🕐 Temporal** — Knows *when* facts were true, not just *that* they were true. Query the past, not just the present.
- **🔒 Self-hosted** — Your conversations stay on your machine. FalkorDB in Docker. Zero cloud dependency.
- **🧠 Biological** — Important memories persist. Unimportant ones fade. Mistakes are remembered vividly. Just like you.
- **🔌 Provider-agnostic** — Works with any OpenAI-compatible LLM. OpenRouter, Ollama, vLLM, OpenAI — your choice.
- **⚡ Optimized** — Projected 73% cheaper, 70x faster prefetch, 86% fewer LLM calls than naive implementations. Zero blocking latency. ([See methodology](docs/benchmarks.md))

> *Built on [Graphiti](https://github.com/getzep/graphiti) + [FalkorDB](https://www.falkordb.com/). Ships as a [Hermes Agent](https://hermes-agent.nousresearch.com) memory provider plugin — drops in with zero core changes.*

---

## Quick Start

Three commands. That's it.

```bash
# 1. Start FalkorDB (self-hosted, privacy-first)
docker run -d --name falkordb -p 6379:6379 falkordb/falkordb:latest

# 2. Install Synapse
pip install "git+https://github.com/ardhaecosystem/synapse.git"

# 3. Configure Hermes
hermes config set memory.provider synapse
# Add to ~/.hermes/.env:
# SYNAPSE_FALKORDB_HOST=localhost
# SYNAPSE_LLM_API_KEY=your-key
# SYNAPSE_LLM_BASE_URL=https://openrouter.ai/api/v1
```

Your agent now has a memory that:

- ✅ Remembers every conversation and extracts entities automatically
- ✅ Knows when facts changed and can answer "what was true on June 20?"
- ✅ Scores memory importance (salience + forgetting curve)
- ✅ Tracks recall events for spaced repetition (reconsolidation)
- ✅ Detects novelty and contradictions in new episodes (prediction error)
- ✅ Consolidates memories in the background like sleep replay (`scripts/consolidate.py` via Hermes cron)
- ✅ Lets the agent explicitly save facts worth remembering forever

---

## The Hippocampus Layer

This is the novel contribution. Nine algorithms inspired by biological memory — the part that makes Synapse a *brain*, not a *database*. All nine are wired into the live runtime through a single `Hippocampus` coordinator that exposes two entry points:

- **`on_episode_ingested()`** — fires after each batch episode is ingested. Runs prediction error detection, salience scoring, reconsolidation boosts, and pattern separation.
- **`on_recall()`** — fires when entities are retrieved via `synapse_query`. Opens the reconsolidation window for those entities (spaced repetition effect).

### Core Memory Management

| Algorithm | What It Does | Biological Analog |
|-----------|-------------|-------------------|
| **Salience Scoring** | Scores entities 0.0–1.0 by recency, frequency, corrections, and emotional markers | Amygdala tagging important experiences |
| **Forgetting Curve** | Ebbinghaus exponential decay — important memories decay 4x slower | Memory consolidation during sleep |
| **Consolidation Engine** | Hebbian strengthening of co-occurring entities + contradiction detection + pruning | Sleep replay and synaptic pruning |

### Advanced Cognitive Functions

| Algorithm | What It Does | Biological Analog |
|-----------|-------------|-------------------|
| **Pattern Completion** | Given a partial cue, retrieves the full context subgraph via BFS expansion | CA3 autoassociative memory |
| **Reconsolidation** | Recalled memories enter a labile window — new info gets priority encoding (spaced repetition) | Memory reactivation lability |
| **Prediction Error** | Novelty detection + contradiction-triggered updates + surprise signals for unexpected contexts | Hippocampal surprise signal |
| **Schema Extraction** | Periodically clusters entities into generalized "schema nodes" — the slow learning system | Neocortex (Complementary Learning Systems) |
| **Pattern Separation** | Entity fingerprints + Jaccard similarity to prevent context contamination between similar conversations | Dentate gyrus |
| **Cognitive Map** | Semantic path finding, entity neighborhoods, topic clustering — navigates the graph like a spatial map | Grid cells + place cells |

### How It Works

```
┌──────────────────────────────────────────────────────────┐
│                      Hermes Agent                          │
│                                                           │
│  System Prompt (frozen per session):                      │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ "You remember your user prefers concise responses.  │  │
│  │  They work on AI projects using Python and Docker." │  │
│  │  (pulled from the graph, not from a static file)     │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                           │
│  Every turn:                                              │
│  ┌───────────┐  ┌────────────┐  ┌─────────────────────┐  │
│  │  prefetch  │  │ sync_turn  │  │ synapse_remember   │  │
│  │ (BM25      │  │ (batch +   │  │ (explicit write →  │  │
│  │  cache)    │  │  tick +    │  │  max salience,     │  │
│  │            │  │  ingest)   │  │  never decays)     │  │
│  └───────────┘  └────────────┘  └─────────────────────┘  │
│                       │                                   │
│                       ▼                                   │
│              ┌─────────────────┐                          │
│              │  Hippocampus     │                          │
│              │  Coordinator      │                          │
│              │                  │                          │
│              │ on_episode_      │                          │
│              │  ingested():      │                          │
│              │  • prediction    │                          │
│              │    error         │                          │
│              │  • salience      │                          │
│              │  • reconsol.    │                          │
│              │  • pattern sep. │                          │
│              │                  │                          │
│              │ on_recall():     │                          │
│              │  • reconsol.    │                          │
│              │    window opens  │                          │
│              └─────────────────┘                          │
│                                                           │
│  Background ("sleep") — via scripts/consolidate.py:        │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ Schema Extraction → "User works on AI projects"      │  │
│  │ Forgetting Curve → prunes forgotten memories         │  │
│  │ Consolidation → strengthens important connections   │  │
│  └─────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
                    │
                    ▼
            ┌───────────────┐
            │   FalkorDB    │
            │ (self-hosted  │
            │  in Docker)   │
            └───────────────┘
```

### Tools Available to the Agent

| Tool | Purpose | Example |
|------|---------|---------|
| `synapse_query` | Search memories. Set `at_time` for point-in-time queries. | *"What database were we using before the switch?"* |
| `synapse_remember` | Save a durable fact permanently. Never decays. | *"User prefers concise responses"* |

---

## Two Usage Modes

### 🧠 Brain Mode (Synapse only)

Disable native MEMORY.md/USER.md, use Synapse as the sole memory system:

```yaml
memory:
  memory_enabled: false
  user_profile_enabled: false
  provider: synapse
```

The agent gets:
- Full system prompt with user profile + environment facts pulled from the graph
- `synapse_remember` as the explicit memory tool (replaces the native `memory` tool)
- Automatic brain-mode instructions in the system prompt

### 🔗 Supplementary Mode (Native + Synapse)

Keep native memory, add Synapse for temporal graph memory:

```yaml
memory:
  memory_enabled: true
  user_profile_enabled: true
  provider: synapse
```

The agent gets:
- Native MEMORY.md/USER.md as normal
- Synapse adds temporal knowledge graph memory on top
- Native writes are mirrored to the graph automatically
- System prompt is minimal (native handles injection)

---

## Performance

> **Projected** estimates based on architectural analysis. See the [benchmark methodology](docs/benchmarks.md) for calculations, assumptions, and reproduction steps.

| Metric | Naive Implementation | Synapse (Optimized) | Improvement |
|--------|-----------------------|-----------------------|-------------|
| Cost per 100 turns | $0.0705 | $0.0192 | **73% reduction** |
| Prefetch latency | 0.70s (blocking) | 0.01s (cached) | **70x faster** |
| LLM calls per 100 turns | 200 | 14 | **86% fewer** |
| Prompt overhead per turn | 232 tokens | 91 tokens | **61% less** |
| Blocking time per 100 turns | 70s | ~0s | **eliminated** |

---

## Supported LLM Providers

Any OpenAI-compatible endpoint works:

| Provider | Base URL | Free? | Embeddings? |
|----------|----------|-------|-------------|
| **Ollama** (local) | `http://localhost:11434/v1` | ✅ | ✅ |
| **OpenRouter** | `https://openrouter.ai/api/v1` | — | ✅ |
| **OpenAI** | `https://api.openai.com/v1` | — | ✅ |
| **vLLM** | `http://localhost:8000/v1` | ✅ | ✅ |
| **LM Studio** | `http://localhost:1234/v1` | ✅ | ✅ |
| **DeepSeek** | `https://api.deepseek.com` | — | — |
| **Together** | `https://api.together.xyz/v1` | — | — |
| **Z.AI / GLM** | `https://open.bigmodel.cn/api/paas/v4` | — | — |

> 💡 **Want 100% free + private?** Use Ollama locally for both LLM and embeddings. Zero data leaves your machine.

---

## Configuration

All configuration via environment variables with the `SYNAPSE_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `SYNAPSE_FALKORDB_HOST` | `localhost` | FalkorDB host |
| `SYNAPSE_FALKORDB_PORT` | `6379` | FalkorDB port |
| `SYNAPSE_LLM_API_KEY` | *(required)* | LLM API key |
| `SYNAPSE_LLM_BASE_URL` | *(required)* | LLM base URL |
| `SYNAPSE_LLM_MODEL` | `gpt-4o-mini` | Model for entity extraction |
| `SYNAPSE_EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model |
| `SYNAPSE_BATCH_SIZE` | `5` | Turns per episode |
| `SYNAPSE_HALF_LIFE_DAYS` | `7.0` | Forgetting curve half-life |

### Tuning Guide

| Use Case | Half-Life | Batch Size |
|----------|-----------|------------|
| Coding assistant | 3–7 days | 5 |
| Research assistant | 14–30 days | 5 |
| Personal assistant | 30–90 days | 3 |
| General purpose | 7 days | 5 |

---

## Documentation

| Document | What's Inside |
|----------|---------------|
| **[User Guide](docs/user-guide.md)** | Installation, quick start, tools reference, troubleshooting, FAQ |
| **[Architecture](docs/architecture.md)** | System design, data flow, optimization details |
| **[Configuration](docs/configuration.md)** | All env vars, LLM providers, tuning guide |
| **[Hippocampus Layer](docs/hippocampus.md)** | Algorithm formulas, biological references |
| **[Benchmarks](docs/benchmarks.md)** | Performance methodology, calculations, assumptions |

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide.

```bash
git clone https://github.com/ardhaecosystem/synapse.git
cd synapse
pip install -e ".[dev]"

# Start FalkorDB for testing
docker run -d --name falkordb -p 6379:6379 falkordb/falkordb:latest

# Run tests
pytest tests/ -v

# Lint
ruff check src/ tests/
```

We use **TDD** (test-first), **conventional commits**, and **PR-based workflow** — every change goes through CI with FalkorDB as a service container.

### Project Structure

```
src/synapse/
├── config.py              Configuration
├── falkor.py              FalkorDB helper + temporal workaround
├── encoding.py            Batch turn buffering
├── retrieval.py           BM25 prefetch + background cache
├── tools.py               synapse_query + synapse_remember
├── provider.py            MemoryProvider implementation
└── hippocampus/
    ├── __init__.py            Hippocampus coordinator (wires all 9 algorithms)
    ├── salience.py            Salience scoring (4-factor)
    ├── forgetting.py          Ebbinghaus decay curve
    ├── consolidation.py       Hebbian + contradiction detection
    ├── pattern_completion.py  CA3 BFS subgraph expansion
    ├── reconsolidation.py     Recall tracking + activation window
    ├── prediction_error.py    Novelty + contradiction + surprise
    ├── schema_extraction.py   Neocortex — CLS slow learning
    ├── pattern_separation.py  DG — Jaccard fingerprint comparison
    └── cognitive_map.py       Grid/place cells — graph navigation

scripts/
└── consolidate.py            Offline consolidation batch (sleep replay)
```

---

## Biological References

The hippocampus layer is grounded in neuroscience research:

| Algorithm | Key Reference |
|-----------|---------------|
| Complementary Learning Systems | McClelland et al. (1995) |
| Reconsolidation | Nader et al. (2000) |
| Pattern Separation | Leutgeb et al. (2007) |
| Prediction Error | Kumaran & Maguire (2006) |
| CA3 Autoassociative Memory | Rolls (2015) |
| Cognitive Maps | O'Keefe & Nadel (1978) |
| Hippocampal Replay | Wilson & McNaughton (1994) |

---

## Roadmap

### Done

- [x] Core memory provider (Graphiti + FalkorDB)
- [x] 9 hippocampus algorithms
- [x] Hippocampus coordinator — all 9 algorithms wired into runtime
- [x] `synapse_remember` explicit memory tool
- [x] Brain-aware system prompt (native memory detection)
- [x] BM25-only optimized prefetch
- [x] Batch episode ingestion
- [x] Salience scoring + reconsolidation tracking on every episode
- [x] Prediction error detection on every episode
- [x] Consolidation script (`scripts/consolidate.py` — sleep replay via Hermes cron)
- [x] Pre-init tool call guard (Issue #16)

### In Progress

- [ ] Bounded graph fetch for post-episode hippocampus processing
- [ ] Pattern completion wired into prefetch (CA3 subgraph expansion)
- [ ] Retrieval-induced forgetting (active suppression of competing memories)

### Planned

- [ ] Plugin CLI commands (`hermes synapse status/consolidate/export`)
- [ ] Leiden community detection for schema extraction
- [ ] LLM-powered schema summaries
- [ ] Graph visualization dashboard
- [ ] Multi-agent shared memory (schema-layer sharing with privacy controls)

---

## License

**MIT** © [Ardha Studios](https://github.com/ardhaecosystem)

---

<div align="center">

**[⭐ Star this repo](https://github.com/ardhaecosystem/synapse)** if you're building AI agents that need real memory.

Built with 🧠 by [Ardha Studios](https://github.com/ardhaecosystem)

</div>