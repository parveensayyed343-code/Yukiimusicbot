import sqlite3
from pathlib import Path

DB_PATH = Path("data") / "vcbot.db"
DB_PATH.parent.mkdir(exist_ok=True)


class VCDatabase:
    def __init__(self):
        self.conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init()

    def _init(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS chats (
                    chat_id  INTEGER PRIMARY KEY,
                    mode_247 INTEGER DEFAULT 0
                )
            """)

    def set_247(self, chat_id: int, state: bool):
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO chats (chat_id, mode_247) VALUES (?, ?)",
                (chat_id, int(state))
            )

    def get_247(self, chat_id: int) -> bool:
        row = self.conn.execute(
            "SELECT mode_247 FROM chats WHERE chat_id = ?", (chat_id,)
        ).fetchone()
        return bool(row["mode_247"]) if row else False