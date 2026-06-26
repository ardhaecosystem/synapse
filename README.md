# Synapse

**Temporal knowledge graph memory for AI agents.**

Synapse gives AI agents a biologically-inspired memory system — not just storage, but a temporal knowledge graph with a hippocampus layer that scores salience, manages forgetting, and consolidates memories during idle time.

Built on [Graphiti](https://github.com/getzep/graphiti) + [FalkorDB](https://www.falkordb.com/), with a custom hippocampus layer implementing Ebbinghaus forgetting curves, Hebbian consolidation, and salience-based memory management.

Ships as a [Hermes Agent](https://hermes-agent.nousresearch.com) memory provider plugin — drops in with zero core changes.

## Why Synapse?

Most agent memory systems are either:
- **Flat text storage** (no relationships, no temporal awareness)
- **Cloud-locked** (your conversations live on someone else's server)
- **All-or-nothing** (every memory has equal weight, nothing is forgotten)

Synapse is different:
- **Temporal** — knows *when* facts were true, not just *that* they were true
- **Self-hosted** — your conversations stay on your infrastructure
- **Biological** — important memories persist, unimportant ones fade, just like a real brain
- **Provider-agnostic** — works with any OpenAI-compatible LLM (Ollama, OpenRouter, vLLM, etc.)

## Quick Start

```bash
# 1. Start FalkorDB (self-hosted, privacy-first)
docker run -d --name falkordb -p 6379:6379 falkordb/falkordb:latest

# 2. Install Synapse
pip install synapse-memory

# 3. Configure Hermes to use Synapse
hermes config set memory.provider synapse
# Set env vars in ~/.hermes/.env:
# SYNAPSE_FALKORDB_HOST=localhost
# SYNAPSE_LLM_API_KEY=your-key
# SYNAPSE_LLM_BASE_URL=https://openrouter.ai/api/v1
```

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

## The Hippocampus Layer

The novel contribution. Three algorithms inspired by biological memory:

| Algorithm | What It Does | Biological Analogy |
|-----------|-------------|-------------------|
| **Salience Scoring** | Scores entities 0.0-1.0 by recency, frequency, corrections, emotional markers | Amygdala tagging important experiences |
| **Forgetting Curve** | Ebbinghaus exponential decay, modulated by salience — important memories decay slower | Memory consolidation during sleep |
| **Consolidation** | Hebbian strengthening of co-occurring entities + contradiction detection + pruning | Sleep replay and synaptic pruning |

## Configuration

All configuration via environment variables or `hermes config setup`:

| Variable | Default | Description |
|----------|---------|-------------|
| `SYNAPSE_FALKORDB_HOST` | localhost | FalkorDB host |
| `SYNAPSE_FALKORDB_PORT` | 6379 | FalkorDB port |
| `SYNAPSE_LLM_API_KEY` | (required) | LLM API key (OpenAI-compatible) |
| `SYNAPSE_LLM_BASE_URL` | (required) | LLM base URL |
| `SYNAPSE_LLM_MODEL` | gpt-4o-mini | Model for entity extraction |
| `SYNAPSE_BATCH_SIZE` | 5 | Turns per episode (optimization) |
| `SYNAPSE_HALF_LIFE_DAYS` | 7.0 | Forgetting curve half-life |

See [Configuration docs](docs/configuration.md) for all options.

## License

MIT © Ardha Studios