"""Dissolution — deletion that leaves nothing behind.

Ordinary deletion only removes a file's entry from the index; the bytes remain
on the disk until something else happens to overwrite them. That is a poor
banishing. Here the file's contents are overwritten with random bytes, flushed
to the physical device, truncated, and only then unlinked.

Caveat worth knowing: on copy-on-write and flash-based filesystems (APFS, SSDs
with wear levelling) the drive may write to new physical blocks rather than the
originals, so overwriting is not an absolute guarantee at the hardware level.
It is a genuine and deliberate destruction, not a mathematical certainty.
"""

from __future__ import annotations

import os
import shutil


def erase_file(path: str, passes: int = 3) -> bool:
    """Overwrite a file with random bytes, then remove it."""
    if not os.path.isfile(path):
        return False
    length = os.path.getsize(path)
    try:
        with open(path, "r+b", buffering=0) as fh:
            for _ in range(max(1, passes)):
                fh.seek(0)
                fh.write(os.urandom(length))
                fh.flush()
                os.fsync(fh.fileno())
            fh.seek(0)
            fh.truncate(0)
            fh.flush()
            os.fsync(fh.fileno())
    except OSError:
        # Even if overwriting fails, still remove the file.
        pass
    os.remove(path)
    return True


def erase_tree(directory: str, passes: int = 3, keep: tuple = ()) -> int:
    """Erase every file beneath `directory`, then remove the directory.

    Files whose basename appears in `keep` are left untouched — used to
    preserve a vessel's ledger, which outlives the vessel as its record.
    """
    if not os.path.isdir(directory):
        return 0
    erased = 0
    kept = False
    for root, _dirs, files in os.walk(directory, topdown=False):
        for fname in files:
            if fname in keep:
                kept = True
                continue
            if erase_file(os.path.join(root, fname), passes=passes):
                erased += 1
    if not kept:
        shutil.rmtree(directory, ignore_errors=True)
    return erased
