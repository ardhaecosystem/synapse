"""Test that the provider wires the Hippocampus coordinator correctly."""

from synapse.provider import SynapseMemoryProvider


def test_provider_has_hippocampus_slot():
    p = SynapseMemoryProvider()
    assert p._hippocampus is None  # before init


def test_sync_turn_ticks_hippocampus():
    """sync_turn should advance the hippocampus turn counter."""
    p = SynapseMemoryProvider()
    p._initialized = True

    ticks = []

    class MockHippocampus:
        def tick(self):
            ticks.append(1)

    p._hippocampus = MockHippocampus()

    # Mock turn buffer — must be truthy even when empty.
    # ponytail: real TurnBuffer is always truthy (no __len__ falsy trap),
    # so the mock just needs __bool__ = True.
    class MockBuffer:
        def __init__(self):
            self._turns = []

        def __bool__(self):
            return True

        def add(self, u, a):
            self._turns.append((u, a))

        def should_flush(self):
            return False

        def __len__(self):
            return len(self._turns)

    p._turn_buffer = MockBuffer()
    p.sync_turn("What is Synapse?", "Synapse is a memory system.")

    assert len(ticks) == 1


def test_shutdown_clears_hippocampus():
    """shutdown should clear hippocampus session state."""
    p = SynapseMemoryProvider()
    p._initialized = True

    cleared = []

    class MockHippocampus:
        def clear(self):
            cleared.append(1)

    p._hippocampus = MockHippocampus()
    p._turn_buffer = None
    p._graphiti = None
    p._loop = None

    p.shutdown()
    assert len(cleared) == 1
    assert not p._initialized


def test_on_session_end_clears_hippocampus():
    p = SynapseMemoryProvider()
    p._initialized = True

    cleared = []

    class MockHippocampus:
        def clear(self):
            cleared.append(1)

    p._hippocampus = MockHippocampus()
    p._turn_buffer = None

    p.on_session_end([])
    assert len(cleared) == 1
