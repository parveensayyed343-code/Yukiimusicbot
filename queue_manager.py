import random
from collections import defaultdict
from typing import Optional


class QueueManager:
    """
    Per-chat music queue.
    Each chat gets its own queue list + loop flag.
    """

    def __init__(self):
        self._queues: dict[int, list]  = defaultdict(list)
        self._loops:  dict[int, bool]  = defaultdict(bool)

    # ── Add ───────────────────────────────────────────────────────────────────
    def add(self, chat_id: int, song: dict) -> int:
        """Add song and return its position (1-indexed)."""
        self._queues[chat_id].append(song)
        return len(self._queues[chat_id])

    # ── Current ───────────────────────────────────────────────────────────────
    def current(self, chat_id: int) -> Optional[dict]:
        q = self._queues[chat_id]
        return q[0] if q else None

    # ── Next (remove current, return new current) ─────────────────────────────
    def next(self, chat_id: int) -> Optional[dict]:
        q = self._queues[chat_id]
        if not q:
            return None
        q.pop(0)
        return q[0] if q else None

    # ── Pop current (without returning next) ─────────────────────────────────
    def pop(self, chat_id: int):
        q = self._queues[chat_id]
        if q:
            q.pop(0)

    # ── Queue list ────────────────────────────────────────────────────────────
    def get_queue(self, chat_id: int) -> list:
        return list(self._queues[chat_id])

    # ── Is empty ──────────────────────────────────────────────────────────────
    def is_empty(self, chat_id: int) -> bool:
        return len(self._queues[chat_id]) == 0

    # ── Clear ─────────────────────────────────────────────────────────────────
    def clear(self, chat_id: int):
        self._queues[chat_id].clear()

    # ── Shuffle (keep current song, shuffle rest) ─────────────────────────────
    def shuffle(self, chat_id: int):
        q = self._queues[chat_id]
        if len(q) > 2:
            rest = q[1:]
            random.shuffle(rest)
            self._queues[chat_id] = [q[0]] + rest

    # ── Loop ─────────────────────────────────────────────────────────────────
    def toggle_loop(self, chat_id: int) -> bool:
        self._loops[chat_id] = not self._loops[chat_id]
        return self._loops[chat_id]

    def is_loop(self, chat_id: int) -> bool:
        return self._loops[chat_id]