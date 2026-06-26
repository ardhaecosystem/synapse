"""Test configuration and fixtures for Synapse.

Provides a FalkorDB container fixture for integration tests.
"""

import pytest
import subprocess
import time
import socket


def _is_falkordb_running(host="localhost", port=6379):
    """Check if FalkorDB is reachable."""
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except (ConnectionRefusedError, OSError):
        return False


@pytest.fixture(scope="session")
def falkordb():
    """Ensure FalkorDB is running for the test session."""
    if not _is_falkordb_running():
        pytest.skip("FalkorDB not running on localhost:6379 — start with: docker run -d -p 6379:6379 falkordb/falkordb:latest")
    yield True


@pytest.fixture
def falkor_helper(falkordb):
    """Provide a FalkorHelper instance."""
    from synapse.falkor import FalkorHelper
    helper = FalkorHelper(host="localhost", port=6379)
    yield helper
    helper.close()