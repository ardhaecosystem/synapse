# Configuration

## Environment Variables

All configuration is via environment variables with the `SYNAPSE_` prefix.

### Required

| Variable | Description | Default |
|----------|-------------|---------|
| `SYNAPSE_FALKORDB_HOST` | FalkorDB host address | `localhost` |
| `SYNAPSE_LLM_API_KEY` | LLM API key (OpenAI-compatible) | (required) |
| `SYNAPSE_LLM_BASE_URL` | LLM base URL (OpenAI-compatible endpoint) | (required) |

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `SYNAPSE_FALKORDB_PORT` | FalkorDB port | `6379` |
| `SYNAPSE_FALKORDB_PASSWORD` | FalkorDB password (if configured) | None |
| `SYNAPSE_DATABASE` | FalkorDB database name | `synapse` |
| `SYNAPSE_LLM_MODEL` | LLM model for entity extraction | `gpt-4o-mini` |
| `SYNAPSE_EMBEDDING_MODEL` | Embedding model for vector search | `text-embedding-3-small` |
| `SYNAPSE_BATCH_SIZE` | Turns per episode (optimization) | `5` |
| `SYNAPSE_HALF_LIFE_DAYS` | Forgetting curve half-life in days | `7.0` |

## Supported LLM Providers

Any OpenAI-compatible endpoint works:

| Provider | Base URL | Notes |
|----------|----------|-------|
| OpenRouter | `https://openrouter.ai/api/v1` | Access to many models |
| OpenAI | `https://api.openai.com/v1` | Native support |
| Ollama (local) | `http://localhost:11434/v1` | Free, self-hosted |
| vLLM | `http://localhost:8000/v1` | High-throughput local inference |
| LM Studio | `http://localhost:1234/v1` | Desktop local inference |
| DeepSeek | `https://api.deepseek.com` | Cost-effective |
| Together | `https://api.together.xyz/v1` | Open models |

## Hermes Configuration

```bash
# Set the memory provider
hermes config set memory.provider synapse

# Or via interactive setup
hermes memory setup
# Select "synapse" and follow the prompts
```

## Docker Compose

For development, use the included Docker Compose:

```bash
cd docker
docker compose up -d
```

This starts FalkorDB with persistent storage in a named volume.

## Tuning Guide

### Forgetting Curve Half-Life

| Use Case | Recommended | Rationale |
|----------|-----------|-----------|
| Coding assistant | 3-7 days | Code context changes fast |
| Research assistant | 14-30 days | Research spans weeks |
| Personal assistant | 30-90 days | Long-term relationships |
| General purpose | 7 days | Good default balance |

### Batch Size

| Value | LLM Calls/100 turns | When to use |
|-------|---------------------|------------|
| 1 | 100 | Never (no benefit) |
| 3 | 33 | High-precision conversations |
| 5 | 14 | Default — good balance |
| 10 | 7 | Long sessions with similar topics |