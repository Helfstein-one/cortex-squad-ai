"""SQLite implementation of Episodic Store."""

import json
import sqlite3
from datetime import datetime

from cortex_squad.application.ports.memory_port import MemoryStorePort
from cortex_squad.domain.models.cognitive import EpisodicEntry, SemanticFact


class SqliteEpisodicStore(MemoryStorePort):
    """Stores episodic failures and semantic contracts using SQLite."""

    def __init__(self, db_path: str = ":memory:"):
        self._db_path = db_path
        self._connection: sqlite3.Connection | None = None
        if db_path == ":memory:":
            self._connection = sqlite3.connect(":memory:")
            self._connection.row_factory = sqlite3.Row
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self._connection is not None:
            return self._connection
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS episodic_entries (
                    id TEXT PRIMARY KEY,
                    mission_id TEXT,
                    failure_signature TEXT,
                    root_cause TEXT,
                    remediation_hint TEXT,
                    persona_culprit TEXT,
                    timestamp TEXT,
                    metadata_json TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS semantic_facts (
                    key TEXT PRIMARY KEY,
                    category TEXT,
                    content TEXT,
                    source_ref TEXT,
                    metadata_json TEXT
                )
                """
            )
            conn.commit()

    async def save_episodic_entry(self, entry: EpisodicEntry) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO episodic_entries (
                    id, mission_id, failure_signature, root_cause,
                    remediation_hint, persona_culprit, timestamp, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.id,
                    entry.mission_id,
                    entry.failure_signature,
                    entry.root_cause,
                    entry.remediation_hint,
                    entry.persona_culprit,
                    entry.timestamp.isoformat(),
                    json.dumps(entry.metadata),
                ),
            )
            conn.commit()

    async def get_episodic_history(self, mission_id: str, limit: int = 10) -> list[EpisodicEntry]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, mission_id, failure_signature, root_cause,
                       remediation_hint, persona_culprit, timestamp, metadata_json
                FROM episodic_entries
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
            return [
                EpisodicEntry(
                    id=row["id"],
                    mission_id=row["mission_id"],
                    failure_signature=row["failure_signature"],
                    root_cause=row["root_cause"],
                    remediation_hint=row["remediation_hint"],
                    persona_culprit=row["persona_culprit"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    metadata=json.loads(row["metadata_json"]),
                )
                for row in rows
            ]

    async def save_semantic_fact(self, fact: SemanticFact) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO semantic_facts
                (key, category, content, source_ref, metadata_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    fact.key,
                    fact.category,
                    fact.content,
                    fact.source_ref,
                    json.dumps(fact.metadata),
                ),
            )
            conn.commit()

    async def search_semantic_facts(
        self, query: str, category: str | None = None, limit: int = 5
    ) -> list[SemanticFact]:
        with self._get_connection() as conn:
            if category:
                cursor = conn.execute(
                    """
                    SELECT key, category, content, source_ref, metadata_json
                    FROM semantic_facts
                    WHERE category = ? AND (content LIKE ? OR key LIKE ?)
                    LIMIT ?
                    """,
                    (category, f"%{query}%", f"%{query}%", limit),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT key, category, content, source_ref, metadata_json
                    FROM semantic_facts
                    WHERE content LIKE ? OR key LIKE ?
                    LIMIT ?
                    """,
                    (f"%{query}%", f"%{query}%", limit),
                )
            rows = cursor.fetchall()
            return [
                SemanticFact(
                    key=row["key"],
                    category=row["category"],
                    content=row["content"],
                    source_ref=row["source_ref"],
                    metadata=json.loads(row["metadata_json"]),
                )
                for row in rows
            ]
