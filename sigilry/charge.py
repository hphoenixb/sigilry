"""Offerings — labor that can be proven.

An charge is a proof-of-work: the vessel searches for a number (a *nonce*)
which, when hashed together with its true name and intent, produces a digest
beginning with a required run of zeros. There is no shortcut. The only way to
find one is to try, and the difficulty sets how many attempts it takes on
average — each additional zero multiplies the expected effort by sixteen.

This is the same mechanism that secures Bitcoin. Here it serves a different
purpose: the work is real, it costs real time and real electricity, and anyone
can verify afterwards that it was genuinely performed. An charge that was
claimed but not made will not verify.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Optional


@dataclass
class Charge:
    nonce: int
    digest: str
    difficulty: int
    iterations: int

    def as_dict(self) -> dict:
        return {
            "nonce": self.nonce,
            "digest": self.digest,
            "difficulty": self.difficulty,
            "iterations": self.iterations,
        }


def _digest(seed: str, nonce: int) -> str:
    return hashlib.sha256(f"{seed}:{nonce}".encode("utf-8")).hexdigest()


def perform_charge(
    seed: str,
    difficulty: int,
    start_nonce: int = 0,
    max_iterations: Optional[int] = None,
) -> Optional[Charge]:
    """Search for a digest with `difficulty` leading zeros.

    Returns the Charge when found, or None if `max_iterations` is reached
    first — which lets a long search be broken into slices so the vessel stays
    responsive to its conditions and to being banished.
    """
    if difficulty < 1:
        raise ValueError("Difficulty must be at least 1.")
    target = "0" * difficulty
    nonce = start_nonce
    iterations = 0
    while True:
        digest = _digest(seed, nonce)
        iterations += 1
        if digest.startswith(target):
            return Charge(
                nonce=nonce, digest=digest, difficulty=difficulty, iterations=iterations
            )
        nonce += 1
        if max_iterations is not None and iterations >= max_iterations:
            return None


def verify_charge(seed: str, charge: Charge) -> bool:
    """Independently confirm an charge was truly performed."""
    digest = _digest(seed, charge.nonce)
    return digest == charge.digest and digest.startswith("0" * charge.difficulty)


def expected_attempts(difficulty: int) -> int:
    """Average number of hashes needed at a given difficulty."""
    return 16 ** difficulty
