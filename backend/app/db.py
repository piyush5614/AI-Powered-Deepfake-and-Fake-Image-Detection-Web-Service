import base64
import sqlite3
from pathlib import Path
from typing import Any


class AnalysisDatabase:
    def __init__(self, path: str) -> None:
        self.path = path

    def _connect(self) -> sqlite3.Connection:
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS analyses (
                    id TEXT PRIMARY KEY,
                    verdict TEXT NOT NULL CHECK (verdict IN ('REAL', 'FAKE')),
                    confidence REAL NOT NULL,
                    filename TEXT NOT NULL,
                    thumbnail TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    def add(
        self,
        analysis_id: str,
        verdict: str,
        confidence: float,
        filename: str,
        thumbnail_bytes: bytes,
        created_at: str,
    ) -> None:
        thumbnail = f"data:image/jpeg;base64,{base64.b64encode(thumbnail_bytes).decode('ascii')}"
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO analyses (id, verdict, confidence, filename, thumbnail, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (analysis_id, verdict, confidence, filename, thumbnail, created_at),
            )

    def list(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, verdict, confidence, filename, thumbnail, created_at FROM analyses ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def delete(self, analysis_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,))
        return cursor.rowcount > 0

    def clear(self) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM analyses")
