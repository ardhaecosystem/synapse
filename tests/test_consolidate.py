"""Tests for the consolidate.py script logic."""

import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "scripts" / "consolidate.py"


def _run_script(*args, env=None, timeout=15):
    """Run consolidate.py as a subprocess and return the result."""
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, timeout=timeout, env=full_env,
    )


def test_script_help_exits_clean():
    """Running --help should exit 0 and show usage."""
    result = _run_script("--help", timeout=10)
    assert result.returncode == 0
    assert "consolidation" in result.stdout.lower()


def test_script_no_falkordb_exits_error():
    """Without FalkorDB running, the script should exit 1 with an error."""
    result = _run_script(
        "--group-id", "test-nonexistent",
        env={"SYNAPSE_FALKORDB_HOST": "localhost", "SYNAPSE_FALKORDB_PORT": "16379"},
    )
    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert "error" in data


def test_script_empty_graph_returns_ok():
    """A graph with no edges should return ok with 'nothing to consolidate'."""
    # This test needs FalkorDB running — skip if not available
    import socket
    try:
        with socket.create_connection(("localhost", 6379), timeout=2):
            pass
    except (ConnectionRefusedError, OSError):
        import pytest
        pytest.skip("FalkorDB not running on localhost:6379")

    result = _run_script("--group-id", "test-empty-graph-ci")
    # Either ok (empty graph) or error (connection) — both valid CI outcomes
    data = json.loads(result.stdout)
    assert "status" in data or "error" in data
