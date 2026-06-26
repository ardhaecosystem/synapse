# Changelog

All notable changes to Synapse will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project structure
- SynapseConfig with optimization defaults
- SalienceScorer (4-factor entity/edge scoring)
- ForgettingCurve (Ebbinghaus with salience modulation)
- ConsolidationEngine (Hebbian + invalid_at contradiction detection)
- TurnBuffer (batch ingestion + trivial turn skip)
- RetrievalEngine (BM25-only + background cache)
- SynapseMemoryProvider (full MemoryProvider ABC implementation)
- Merged synapse_query tool (76 tokens)
- Docker Compose for development
- GitHub Actions CI with FalkorDB service container