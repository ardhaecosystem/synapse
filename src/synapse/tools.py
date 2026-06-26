"""Merged synapse_query tool — single tool for search and temporal recall.

Optimization: one tool (76 tokens) instead of two (192 tokens).
The at_time parameter makes it dual-purpose: omit for current search,
include for point-in-time queries.
"""

from __future__ import annotations

import json
from typing import Any

TOOL_SCHEMA = {
    "name": "synapse_query",
    "description": "Search memories. Set at_time for point-in-time queries.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query."},
            "at_time": {"type": "string", "description": "ISO date (optional)."},
        },
        "required": ["query"],
    },
}


def get_tool_schema() -> dict:
    """Return the tool schema for synapse_query."""
    return TOOL_SCHEMA


def handle_tool_call(args: dict[str, Any], retrieval_engine) -> str:
    """Handle a synapse_query tool call.

    Args:
        args: Tool arguments (query, optional at_time)
        retrieval_engine: RetrievalEngine instance

    Returns:
        JSON string with results
    """
    query = args.get("query", "")
    at_time = args.get("at_time")

    if at_time:
        results = retrieval_engine.temporal_search(query, at_time)
    else:
        results = retrieval_engine.search(query)

    return json.dumps({"results": results, "count": len(results)})
