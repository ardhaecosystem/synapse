# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in Synapse, please report it privately.

**Do not open a public issue.**

Send a report to **security@ardha.ecosystem** with:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will acknowledge your report within 48 hours and provide a timeline for a fix.

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅        |

## Security Considerations

- Synapse connects to a self-hosted FalkorDB instance. Ensure your FalkorDB container is not exposed to the public internet.
- LLM API keys are stored in environment variables, never in the graph.
- Conversation data is stored in FalkorDB on your infrastructure. No data leaves your network except LLM API calls for entity extraction.