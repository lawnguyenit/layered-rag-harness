"""Local SQLite conversation history, isolated by authenticated OIDC subject."""
from __future__ import annotations

import sqlite3
from pathlib import Path


class ConversationStore:
    def __init__(self, path: str | Path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS turns (
                conversation_id TEXT NOT NULL,
                actor_subject TEXT NOT NULL,
                turn_no INTEGER NOT NULL,
                utterance TEXT NOT NULL,
                PRIMARY KEY (conversation_id, actor_subject, turn_no)
            )""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_turn_owner ON turns(conversation_id, actor_subject, turn_no)")

    def _connect(self):
        return sqlite3.connect(self.path, timeout=5)

    def exists_for_other_actor(self, conversation_id: str, actor_subject: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM turns WHERE conversation_id=? AND actor_subject<>? LIMIT 1",
                (conversation_id, actor_subject),
            ).fetchone()
        return row is not None

    def history(self, conversation_id: str, actor_subject: str, limit: int = 8) -> list[dict[str, object]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT turn_no, utterance FROM turns WHERE conversation_id=? AND actor_subject=? ORDER BY turn_no DESC LIMIT ?",
                (conversation_id, actor_subject, limit),
            ).fetchall()
        rows.reverse()
        return [{"turn": number, "utterance": text} for number, text in rows]

    def append(self, conversation_id: str, actor_subject: str, utterance: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO turns(conversation_id, actor_subject, turn_no, utterance) "
                "VALUES (?, ?, COALESCE((SELECT MAX(turn_no)+1 FROM turns WHERE conversation_id=? AND actor_subject=?), 1), ?)",
                (conversation_id, actor_subject, conversation_id, actor_subject, utterance),
            )
