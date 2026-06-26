"""Synapse tools — synapse_query (recall) + synapse_remember (explicit write).

Two tools exposed to the agent:

synapse_query: Search the temporal knowledge graph for memories.
    Set at_time for point-in-time queries. Replaces passive database search
    with pattern-completion-aware retrieval.

synapse_remember: Save a durable fact to the knowledge graph with maximum
    salience (1.0). These facts never decay — they are the agent's explicit,
    curated memories, equivalent to MEMORY.md and USER.md but stored in the
    graph with full relationship context.

Categories:
    - user_profile: facts about the user (preferences, style, habits)
    - environment: facts about the agent's environment (tools, conventions)
    - conclusion: insights and conclusions worth remembering
    - general: anything else

Biological analog: synapse_remember is the amygdala tagging an experience
as emotionally significant — ensuring it gets enhanced encoding and
resists forgetting. These are the memories that persist for years.
"""

from __future__ import annotations

import json
from typing import Any, Callable

# --- synapse_query (recall) ------------------------------------------------

QUERY_SCHEMA = {
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


# --- synapse_remember (explicit write) -------------------------------------

REMEMBER_SCHEMA = {
    "name": "synapse_remember",
    "description": "Save a durable fact to memory permanently.",
    "parameters": {
        "type": "object",
        "properties": {
            "content": {"type": "string", "description": "The fact to remember."},
            "category": {
                "type": "string",
                "description": "user_profile, environment, conclusion, or general.",
            },
        },
        "required": ["content"],
    },
}


# --- Public API ------------------------------------------------------------

def get_tool_schema() -> dict:
    """Return the synapse_query tool schema (backward compatibility)."""
    return QUERY_SCHEMA


def get_all_tool_schemas() -> list[dict]:
    """Return all Synapse tool schemas.

    Returns both synapse_query and synapse_remember.
    """
    return [QUERY_SCHEMA, REMEMBER_SCHEMA]


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


def handle_remember(
    args: dict[str, Any],
    store_fn: Callable[[str, str], bool],
) -> str:
    """Handle a synapse_remember tool call.

    Stores an explicit fact in the graph with maximum salience (1.0).
    These facts are exempt from the forgetting curve — they are the
    agent's curated, permanent memories.

    Args:
        args: Tool arguments (content, optional category)
        store_fn: Callback that stores the fact and returns True on success.
            Signature: store_fn(content: str, category: str) -> bool

    Returns:
        JSON string with success status
    """
    content = args.get("content", "").strip()
    category = args.get("category", "general").strip()

    if not content:
        return json.dumps({
            "success": False,
            "error": "Content is required for synapse_remember.",
        })

    if category not in ("user_profile", "environment", "conclusion", "general"):
        category = "general"

    try:
        success = store_fn(content, category)
        if success:
            return json.dumps({
                "success": True,
                "message": f"Saved to memory (category: {category}).",
                "category": category,
            })
        else:
            return json.dumps({
                "success": False,
                "error": "Failed to store memory.",
            })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
        })
