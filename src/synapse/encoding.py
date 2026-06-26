"""Turn buffering for batch episode ingestion.

Optimization: instead of creating a Graphiti episode per turn (1 LLM call each),
we buffer turns and ingest them in batches (default: 5 turns per episode).
This reduces LLM calls by ~86%.

Also skips trivial turns (e.g., "ok", "thanks", "got it") that carry
no meaningful information for memory.
"""

from __future__ import annotations

from datetime import datetime, timezone


class TurnBuffer:
    """Buffers conversation turns for batch episode ingestion."""

    def __init__(self, batch_size: int = 5, trivial_threshold: int = 10):
        self.batch_size = batch_size
        self.trivial_threshold = trivial_threshold
        self._turns: list[tuple[str, str]] = []

    def add(self, user_content: str, assistant_content: str) -> None:
        """Add a turn to the buffer. Skips trivial turns."""
        # Skip trivial turns (short user message AND short assistant response)
        if len(user_content) < self.trivial_threshold and len(assistant_content) < 100:
            return
        self._turns.append((user_content, assistant_content))

    def __len__(self) -> int:
        return len(self._turns)

    def should_flush(self) -> bool:
        """Check if buffer has enough turns to flush."""
        return len(self._turns) >= self.batch_size

    def flush(self) -> dict | None:
        """Flush the buffer as a batch episode.

        Returns:
            Episode dict with name, body, and reference_time, or None if buffer empty.
        """
        if not self._turns:
            return None

        turns = self._turns
        self._turns = []

        body_parts = []
        for i, (user_msg, assistant_msg) in enumerate(turns, 1):
            body_parts.append(f"Turn {i} (User): {user_msg}")
            body_parts.append(f"Turn {i} (Assistant): {assistant_msg}")
            body_parts.append("")

        return {
            "name": f"Batch episode ({len(turns)} turns) {datetime.now(timezone.utc).isoformat()}",
            "body": "\n".join(body_parts),
            "reference_time": datetime.now(timezone.utc),
            "turn_count": len(turns),
        }
