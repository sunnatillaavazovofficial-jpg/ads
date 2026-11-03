import json
import sqlite3
from datetime import datetime
from typing import Any, Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);
CREATE TABLE IF NOT EXISTS posts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    kind         TEXT NOT NULL,          -- text | media | album | copy
    data         TEXT NOT NULL,          -- JSON
    scheduled_at TEXT,                   -- 'YYYY-MM-DD HH:MM' (aniq sana) yoki NULL (navbat)
    status       TEXT NOT NULL DEFAULT 'queued',  -- queued | posted | failed
    created_at   TEXT NOT NULL,
    posted_at    TEXT,
    error        TEXT
);
"""

DEFAULTS = {
    "channel_id": "",
    "times": "09:00,13:00,18:00",
    "per_slot": "1",
    "paused": "0",
    "footer": "",
    "button": "",       # "Matn|https://..."
    "admins": "",
}


class DB:
    def __init__(self, path: str):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        for k, v in DEFAULTS.items():
            self.conn.execute("INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)", (k, v))
        # Bot to'xtab qolganda chala qolgan albomlarni tozalash
        self.conn.execute("DELETE FROM posts WHERE status='collecting'")
        self.conn.commit()

    # ---------- settings ----------
    def get(self, key: str) -> str:
        row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else DEFAULTS.get(key, "")

    def set(self, key: str, value: Any) -> None:
        self.conn.execute(
            "INSERT INTO settings(key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)),
        )
        self.conn.commit()

    # ---------- posts ----------
    def add_post(self, kind: str, data: dict, now: datetime) -> int:
        cur = self.conn.execute(
            "INSERT INTO posts(kind, data, created_at) VALUES (?, ?, ?)",
            (kind, json.dumps(data, ensure_ascii=False), now.strftime("%Y-%m-%d %H:%M:%S")),
        )
        self.conn.commit()
        return cur.lastrowid

    def reserve_post(self, kind: str, now: datetime) -> int:
        """Albom yig'ilayotganda tartib buzilmasligi uchun ID oldindan olinadi."""
        cur = self.conn.execute(
            "INSERT INTO posts(kind, data, status, created_at) VALUES (?, '{}', 'collecting', ?)",
            (kind, now.strftime("%Y-%m-%d %H:%M:%S")),
        )
        self.conn.commit()
        return cur.lastrowid

    def finish_post(self, post_id: int, data: dict) -> None:
        self.conn.execute(
            "UPDATE posts SET data=?, status='queued' WHERE id=?",
            (json.dumps(data, ensure_ascii=False), post_id),
        )
        self.conn.commit()

    def get_post(self, post_id: int) -> Optional[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM posts WHERE id=?", (post_id,)).fetchone()

    def queue(self) -> list:
        """Sanasiz, navbatdagi postlar (tartib bo'yicha)."""
        return self.conn.execute(
            "SELECT * FROM posts WHERE status='queued' AND scheduled_at IS NULL ORDER BY id"
        ).fetchall()

    def scheduled(self) -> list:
        """Aniq sana belgilangan postlar."""
        return self.conn.execute(
            "SELECT * FROM posts WHERE status='queued' AND scheduled_at IS NOT NULL ORDER BY scheduled_at, id"
        ).fetchall()

    def due_scheduled(self, now_str: str) -> list:
        return self.conn.execute(
            "SELECT * FROM posts WHERE status='queued' AND scheduled_at IS NOT NULL "
            "AND scheduled_at <= ? ORDER BY scheduled_at, id",
            (now_str,),
        ).fetchall()

    def set_schedule(self, post_id: int, when: Optional[str]) -> None:
        self.conn.execute("UPDATE posts SET scheduled_at=? WHERE id=?", (when, post_id))
        self.conn.commit()

    def mark_posted(self, post_id: int, now: datetime) -> None:
        self.conn.execute(
            "UPDATE posts SET status='posted', posted_at=?, error=NULL WHERE id=?",
            (now.strftime("%Y-%m-%d %H:%M:%S"), post_id),
        )
        self.conn.commit()

    def mark_failed(self, post_id: int, error: str) -> None:
        self.conn.execute("UPDATE posts SET status='failed', error=? WHERE id=?", (error[:500], post_id))
        self.conn.commit()

    def delete_post(self, post_id: int) -> None:
        self.conn.execute("DELETE FROM posts WHERE id=?", (post_id,))
        self.conn.commit()

    def clear_queue(self) -> int:
        cur = self.conn.execute("DELETE FROM posts WHERE status='queued'")
        self.conn.commit()
        return cur.rowcount

    def stats(self) -> dict:
        rows = self.conn.execute("SELECT status, COUNT(*) c FROM posts GROUP BY status").fetchall()
        return {r["status"]: r["c"] for r in rows}
