#!/usr/bin/env python3
"""Synapse consolidation script — the 'sleep replay' cycle.

Runs the hippocampus offline batch: Hebbian strengthening, contradiction
detection, forgetting curve pruning, and schema extraction. Designed to
be called by Hermes cron (no-agent mode) or manually.

Usage:
    python scripts/consolidate.py
    python scripts/consolidate.py --group-id my-agent
    python scripts/consolidate.py --schemas

Environment:
    SYNAPSE_FALKORDB_HOST  (default: localhost)
    SYNAPSE_FALKORDB_PORT  (default: 6379)
    SYNAPSE_FALKORDB_PASSWORD (optional)
    SYNAPSE_HALF_LIFE_DAYS (default: 7.0)
    SYNAPSE_DATABASE       (default: synapse)

Exit code 0 on success, 1 on error. Prints a JSON summary to stdout.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Run Synapse hippocampus consolidation (sleep replay)."
    )
    parser.add_argument(
        "--group-id",
        default=os.environ.get("SYNAPSE_DATABASE", "synapse"),
        help="FalkorDB graph group ID (default: SYNAPSE_DATABASE or 'synapse')",
    )
    parser.add_argument(
        "--schemas",
        action="store_true",
        help="Also run schema extraction (neocortical slow learning)",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="Report pruning candidates (does not delete from graph)",
    )
    args = parser.parse_args()

    host = os.environ.get("SYNAPSE_FALKORDB_HOST", "localhost")
    port = int(os.environ.get("SYNAPSE_FALKORDB_PORT", "6379"))
    password = os.environ.get("SYNAPSE_FALKORDB_PASSWORD")
    half_life = float(os.environ.get("SYNAPSE_HALF_LIFE_DAYS", "7.0"))

    from synapse.falkor import FalkorHelper
    from synapse.hippocampus import Hippocampus

    helper = FalkorHelper(host=host, port=port, password=password)

    try:
        edges = helper.get_edges(args.group_id)
        entities = helper.get_entities(args.group_id)
    except Exception as e:
        print(json.dumps({"error": f"Failed to fetch graph: {e}"}))
        sys.exit(1)

    if not edges:
        print(json.dumps({
            "status": "ok",
            "message": "No edges in graph — nothing to consolidate.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }))
        sys.exit(0)

    hp = Hippocampus(
        half_life_days=half_life,
        group_id=args.group_id,
    )

    # 1. Consolidation (Hebbian + contradiction detection + drain online queue)
    consolidation = hp.run_consolidation(edges)

    result = {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "group_id": args.group_id,
        "edge_count": len(edges),
        "entity_count": len(entities),
        "consolidation": {
            "online_contradictions": len(consolidation["online_contradictions"]),
            "offline_contradictions": len(consolidation["offline_contradictions"]),
            "co_occurrences": len(consolidation["co_occurrences"]),
        },
    }

    # 2. Schema extraction (optional)
    if args.schemas:
        schemas = hp.extract_schemas(edges)
        result["schemas"] = {
            "count": len(schemas),
            "top_schema": schemas[0]["summary"] if schemas else None,
        }

    # 3. Pruning candidates (optional — report only, does not delete)
    if args.prune:
        prune_candidates = []
        for entity in entities:
            name = entity.get("name", "")
            created_at = entity.get("created_at", "")
            edge_count = sum(
                1 for e in edges
                if e.get("from_node") == name or e.get("to_node") == name
            )
            scores = hp.salience.score_entity(
                name=name,
                summary=entity.get("summary", ""),
                created_at=created_at,
                edge_count=edge_count,
                invalid_at=None,
            )
            strength = hp.compute_strength(
                salience=scores["total"],
                age_days=_age_days(created_at),
            )
            if hp.should_prune(strength):
                prune_candidates.append({
                    "entity": name,
                    "salience": scores["total"],
                    "strength": strength,
                })
        result["prune_candidates"] = {
            "count": len(prune_candidates),
            "entities": prune_candidates[:10],
        }

    print(json.dumps(result, indent=2))
    sys.exit(0)


def _age_days(created_at: str) -> float:
    """Compute age in days from an ISO timestamp."""
    if not created_at:
        return 0.0
    try:
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        return max(0.0, (datetime.now(timezone.utc) - created).total_seconds() / 86400)
    except Exception:
        return 0.0


if __name__ == "__main__":
    main()
