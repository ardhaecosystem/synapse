"""Tests for the consolidate.py script logic."""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "scripts" / "consolidate.py"


def test_age_days_with_valid_timestamp():
    from scripts.consolidate import _age_days
    recent = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    age = _age_days(recent)
    assert 0.9 < age < 1.1


def test_age_days_with_empty_string():
    from scripts.consolidate import _age_days
    assert _age_days("") == 0.0


def test_age_days_with_invalid_timestamp():
    from scripts.consolidate import _age_days
    assert _age_days("not-a-date") == 0.0


def test_script_help_exits_clean():
    """Running --help should exit 0 and show usage."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0
    assert "consolidation" in result.stdout.lower()


def test_script_no_falkordb_exits_error():
    """Without FalkorDB running, the script should exit 1 with an error."""
    env = os.environ.copy()
    env["SYNAPSE_FALKORDB_HOST"] = "localhost"
    env["SYNAPSE_FALKORDB_PORT"] = "16379"  # nothing listening here
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--group-id", "test-nonexistent"],
        capture_output=True, text=True, timeout=15, env=env,
    )
    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert "error" in data
