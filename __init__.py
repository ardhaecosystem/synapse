"""Shim for Hermes' memory-provider loader (expects __init__.py at the
plugin root, not under src/). The real provider lives in src/synapse/provider.py.
MemoryProvider
"""
from synapse.provider import register  # noqa: F401