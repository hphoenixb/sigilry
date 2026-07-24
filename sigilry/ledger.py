"""The ledger — an append-only record that cannot be quietly rewritten.

Each entry carries the hash of the entry before it, and its own hash covers
that link. So the entries form a chain: altering anything in the past changes
its hash, which breaks every link that follows. You can still destroy a ledger,
but you cannot edit one and have it still verify — not even you.

This is the same structure git uses for commits, and blockchains for blocks.
Here it holds the life of a vessel: its binding, every charge, every time it
was attended, and its death.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional

GENESIS = "0" * 64


def _canonical(payload: Dict[str, Any]) -> str:
    """Deterministic JSON so hashes are reproducible."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def entry_hash(entry: Dict[str, Any]) -> str:
    """Hash of an entry, excluding its own hash field."""
    body = {k: v for k, v in entry.items() if k != "hash"}
    return hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()


@dataclass
class Ledger:
    """A vessel's life record, stored as one JSON object per line."""

    path: str
    _entries: List[Dict[str, Any]] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        self._entries = self._read_all()

    # ---------------------------------------------------------------- reading

    def _read_all(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.path):
            return []
        entries = []
        with open(self.path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries

    def __iter__(self) -> Iterator[Dict[str, Any]]:
        return iter(self._entries)

    def __len__(self) -> int:
        return len(self._entries)

    @property
    def entries(self) -> List[Dict[str, Any]]:
        return list(self._entries)

    @property
    def head(self) -> str:
        """Hash of the most recent entry, or the genesis value if empty."""
        return self._entries[-1]["hash"] if self._entries else GENESIS

    def of_kind(self, kind: str) -> List[Dict[str, Any]]:
        return [e for e in self._entries if e.get("kind") == kind]

    def last_of_kind(self, kind: str) -> Optional[Dict[str, Any]]:
        matches = self.of_kind(kind)
        return matches[-1] if matches else None

    # ---------------------------------------------------------------- writing

    def record(self, kind: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Append a sealed entry and return it."""
        entry = {
            "seq": len(self._entries),
            "at": datetime.now(timezone.utc).isoformat(),
            "kind": kind,
            "data": data or {},
            "prev": self.head,
        }
        entry["hash"] = entry_hash(entry)

        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(_canonical(entry) + "\n")
        self._entries.append(entry)
        return entry

    # ------------------------------------------------------------ verifying

    def verify(self) -> tuple[bool, Optional[str]]:
        """Walk the chain. Returns (ok, description_of_first_problem)."""
        prev = GENESIS
        for i, entry in enumerate(self._entries):
            if entry.get("seq") != i:
                return False, f"entry {i}: sequence number is {entry.get('seq')}"
            if entry.get("prev") != prev:
                return False, f"entry {i}: broken link to previous entry"
            expected = entry_hash(entry)
            if entry.get("hash") != expected:
                return False, f"entry {i}: contents do not match its seal"
            prev = entry["hash"]
        return True, None
