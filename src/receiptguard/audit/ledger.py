"""Append-only, hash-chained audit ledger.

Each entry stores SHA-256(prev_hash + payload + ts). Tampering with any row
breaks the chain from that row onward -> tamper-evident. SQLite locally; the
same schema/DSN works against Alibaba RDS PostgreSQL in production.

Supports the EU AI Act Art. 12 (record-keeping) auditability story.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from dataclasses import dataclass

GENESIS = "0" * 64


def _hash(prev_hash: str, payload: str, ts: float) -> str:
    return hashlib.sha256(f"{prev_hash}{payload}{ts}".encode()).hexdigest()


@dataclass
class LedgerEntry:
    idx: int
    ts: float
    kind: str
    payload: str
    prev_hash: str
    entry_hash: str


class AuditLedger:
    def __init__(self, path: str = ":memory:") -> None:
        self.conn = sqlite3.connect(path)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS entries ("
            "idx INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, kind TEXT, "
            "payload TEXT, prev_hash TEXT, entry_hash TEXT)"
        )
        self.conn.commit()

    def _last_hash(self) -> str:
        row = self.conn.execute("SELECT entry_hash FROM entries ORDER BY idx DESC LIMIT 1").fetchone()
        return row[0] if row else GENESIS

    def append(self, kind: str, payload: dict, ts: float | None = None) -> LedgerEntry:
        ts = time.time() if ts is None else ts
        body = json.dumps(payload, sort_keys=True, default=str)
        prev = self._last_hash()
        h = _hash(prev, body, ts)
        cur = self.conn.execute(
            "INSERT INTO entries (ts, kind, payload, prev_hash, entry_hash) VALUES (?,?,?,?,?)",
            (ts, kind, body, prev, h),
        )
        self.conn.commit()
        return LedgerEntry(cur.lastrowid, ts, kind, body, prev, h)

    def all(self) -> list[LedgerEntry]:
        rows = self.conn.execute(
            "SELECT idx, ts, kind, payload, prev_hash, entry_hash FROM entries ORDER BY idx"
        ).fetchall()
        return [LedgerEntry(*r) for r in rows]

    def verify_chain(self) -> tuple[bool, int]:
        """Return (ok, broken_idx). broken_idx == -1 when intact."""
        prev = GENESIS
        for e in self.all():
            if e.prev_hash != prev or _hash(prev, e.payload, e.ts) != e.entry_hash:
                return False, e.idx
            prev = e.entry_hash
        return True, -1

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "AuditLedger":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
