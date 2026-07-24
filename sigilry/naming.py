"""True names.

A vessel's true name is the SHA-256 hash of the sigil file you drew. Because
the file contains the exact pixels your hand produced, the name belongs to that
one act of making and to nothing else. Redraw the same glyph and you get a
different name — the name is bound to the drawing, not to the design.

Nothing here can invent a sigil. It can only witness one.
"""

from __future__ import annotations

import hashlib
import os


def true_name_from_bytes(data: bytes) -> str:
    """Full 64-character true name for raw sigil bytes."""
    if not data:
        raise ValueError("A sigil cannot be empty — there is nothing to name.")
    return hashlib.sha256(data).hexdigest()


def true_name(sigil_path: str) -> str:
    """Full true name for a sigil file on disk."""
    if not os.path.exists(sigil_path):
        raise FileNotFoundError(f"No sigil at {sigil_path}")
    with open(sigil_path, "rb") as fh:
        return true_name_from_bytes(fh.read())


def short_name(full_name: str, length: int = 8) -> str:
    """The abbreviated form used in status output."""
    return full_name[:length]
