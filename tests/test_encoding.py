"""Tests for TurnBuffer."""

from synapse.encoding import TurnBuffer


def test_buffer_accumulates_turns():
    buf = TurnBuffer(batch_size=5)
    buf.add("Hello, how are you doing?", "Hi there! I'm doing well.")
    buf.add("What's up with the project?", "Not much, still in progress.")
    assert len(buf) == 2


def test_buffer_flushes_at_batch_size():
    buf = TurnBuffer(batch_size=3)
    buf.add("This is turn one content", "This is response one content")
    buf.add("This is turn two content", "This is response two content")
    buf.add("This is turn three content", "This is response three content")
    episode = buf.flush()
    assert episode is not None
    assert "This is turn one content" in episode["body"]
    assert "This is response three content" in episode["body"]
    assert len(buf) == 0


def test_trivial_turn_skipped():
    buf = TurnBuffer(batch_size=5, trivial_threshold=10)
    buf.add("ok", "Got it!")
    assert len(buf) == 0


def test_nontrivial_turn_not_skipped():
    buf = TurnBuffer(batch_size=5, trivial_threshold=10)
    buf.add("This is a real question", "Here is a real answer")
    assert len(buf) == 1


def test_force_flush():
    buf = TurnBuffer(batch_size=10)
    buf.add("This is turn one", "This is response one")
    buf.add("This is turn two", "This is response two")
    episode = buf.flush()
    assert episode is not None
    assert len(buf) == 0


def test_should_flush():
    buf = TurnBuffer(batch_size=3)
    buf.add("Turn one content here", "Response one content here")
    assert not buf.should_flush()
    buf.add("Turn two content here", "Response two content here")
    assert not buf.should_flush()
    buf.add("Turn three content here", "Response three content here")
    assert buf.should_flush()


def test_empty_flush_returns_none():
    buf = TurnBuffer(batch_size=5)
    assert buf.flush() is None
