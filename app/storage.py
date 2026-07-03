import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class SQLiteStore:
    def __init__(self, database_path: str) -> None:
        self.path = Path(database_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS calls (
                    id TEXT PRIMARY KEY,
                    phone_hash TEXT NOT NULL,
                    phone_masked TEXT NOT NULL,
                    recipient_name TEXT NOT NULL,
                    purpose TEXT NOT NULL,
                    consent_basis TEXT NOT NULL,
                    status TEXT NOT NULL,
                    room_name TEXT,
                    dispatch_id TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_calls_phone_hash ON calls(phone_hash);
                CREATE INDEX IF NOT EXISTS idx_calls_created_at ON calls(created_at);
                CREATE TABLE IF NOT EXISTS suppressions (
                    phone_hash TEXT PRIMARY KEY,
                    phone_masked TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    def create_call(self, record: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO calls (
                    id, phone_hash, phone_masked, recipient_name, purpose,
                    consent_basis, status, room_name, dispatch_id, error, created_at
                ) VALUES (
                    :id, :phone_hash, :phone_masked, :recipient_name, :purpose,
                    :consent_basis, :status, :room_name, :dispatch_id, :error, :created_at
                )
                """,
                record,
            )

    def update_dispatch(
        self,
        call_id: str,
        *,
        status: str,
        room_name: str | None = None,
        dispatch_id: str | None = None,
        error: str | None = None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE calls
                SET status = ?, room_name = ?, dispatch_id = ?, error = ?
                WHERE id = ?
                """,
                (status, room_name, dispatch_id, error, call_id),
            )

    def get_call(self, call_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM calls WHERE id = ?", (call_id,)).fetchone()
        return dict(row) if row else None

    def is_suppressed(self, hashed_phone: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM suppressions WHERE phone_hash = ?", (hashed_phone,)
            ).fetchone()
        return row is not None

    def add_suppression(
        self, hashed_phone: str, phone_masked: str, reason: str
    ) -> None:
        created_at = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO suppressions (phone_hash, phone_masked, reason, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(phone_hash) DO UPDATE SET
                    reason = excluded.reason,
                    created_at = excluded.created_at
                """,
                (hashed_phone, phone_masked, reason, created_at),
            )

    def count_calls_since(self, since_iso: str) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM calls WHERE created_at >= ?", (since_iso,)
            ).fetchone()
        return int(row["count"])

    def latest_call_for_phone(self, hashed_phone: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT created_at FROM calls
                WHERE phone_hash = ?
                ORDER BY created_at DESC LIMIT 1
                """,
                (hashed_phone,),
            ).fetchone()
        return str(row["created_at"]) if row else None
