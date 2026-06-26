# Contributing to Synapse

Thank you for your interest in contributing to Synapse! This document covers everything you need to get started.

## Development Setup

```bash
git clone https://github.com/ardhaecosystem/synapse.git
cd synapse
pip install -e ".[dev]"

# Start FalkorDB for testing
docker run -d --name falkordb -p 6379:6379 falkordb/falkordb:latest
```

## Branch Naming

- `feat/<description>` — new features
- `fix/<description>` — bug fixes
- `docs/<description>` — documentation
- `refactor/<description>` — code refactoring

## Commit Conventions

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
type: concise subject line

Optional body.
```

Types: `feat:`, `fix:`, `refactor:`, `docs:`, `ci:`, `chore:`, `test:`

## Testing

All code changes require tests. We use TDD:

1. Write a failing test
2. Write minimal code to pass
3. Refactor

```bash
# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --tb=short

# Lint
ruff check src/ tests/
```

## Pull Request Process

1. Create a branch from `main`
2. Write tests first (TDD)
3. Implement the feature
4. Ensure all tests pass and linting is clean
5. Update documentation if needed
6. Submit PR with a clear description

## Code Style

- Python 3.11+
- `ruff` for linting (line length: 100)
- Type hints encouraged
- Docstrings for public functions

## Project Structure

```
src/synapse/          # Source code
  hippocampus/        # Salience, forgetting, consolidation
tests/                # Test suite
docs/                 # Documentation
```

## Questions?

Open a [GitHub Discussion](https://github.com/ardhaecosystem/synapse/discussions) or an issue.