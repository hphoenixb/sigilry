"""Tests for true names, charges (proof-of-work), and the sealed ledger."""

import json

import pytest

from sigilry.ledger import Ledger, entry_hash
from sigilry.naming import short_name, true_name, true_name_from_bytes
from sigilry.charge import (
    Charge,
    expected_attempts,
    perform_charge,
    verify_charge,
)


# ---------------------------------------------------------------- true names

def test_true_name_is_stable():
    assert true_name_from_bytes(b"glyph") == true_name_from_bytes(b"glyph")


def test_true_name_changes_with_one_byte():
    a = true_name_from_bytes(b"glyph")
    b = true_name_from_bytes(b"glypi")
    assert a != b


def test_empty_sigil_refused():
    with pytest.raises(ValueError):
        true_name_from_bytes(b"")


def test_true_name_from_file(tmp_path):
    p = tmp_path / "sigil.png"
    p.write_bytes(b"\x89PNG fake drawing bytes")
    assert true_name(str(p)) == true_name_from_bytes(b"\x89PNG fake drawing bytes")


def test_missing_sigil_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        true_name(str(tmp_path / "nope.png"))


def test_short_name_length():
    assert len(short_name("a" * 64)) == 8


# ----------------------------------------------------------------- charges

def test_charge_meets_difficulty():
    off = perform_charge("seed", 2)
    assert off is not None
    assert off.digest.startswith("00")


def test_charge_verifies():
    off = perform_charge("seed", 2)
    assert verify_charge("seed", off) is True


def test_forged_charge_fails_verification():
    off = perform_charge("seed", 2)
    forged = Charge(nonce=off.nonce + 1, digest=off.digest, difficulty=2, iterations=1)
    assert verify_charge("seed", forged) is False


def test_claimed_but_unperformed_charge_fails():
    """A digest that was never actually produced cannot verify."""
    fake = Charge(nonce=0, digest="0" * 64, difficulty=3, iterations=999999)
    assert verify_charge("seed", fake) is False


def test_charge_can_be_sliced():
    """With a tiny iteration budget the search returns None instead of blocking."""
    assert perform_charge("seed", 8, max_iterations=5) is None


def test_different_seeds_give_different_charges():
    a = perform_charge("seed-a", 2)
    b = perform_charge("seed-b", 2)
    assert a.digest != b.digest


def test_difficulty_must_be_positive():
    with pytest.raises(ValueError):
        perform_charge("seed", 0)


def test_expected_attempts_grows_sixteenfold():
    assert expected_attempts(3) == expected_attempts(2) * 16


# ------------------------------------------------------------------- ledger

def test_ledger_records_and_reads(tmp_path):
    led = Ledger(str(tmp_path / "l.jsonl"))
    led.record("bound", {"intent": "x"})
    led.record("charge", {"iterations": 10})
    assert len(led) == 2
    assert led.entries[0]["kind"] == "bound"


def test_ledger_chain_verifies(tmp_path):
    led = Ledger(str(tmp_path / "l.jsonl"))
    for i in range(5):
        led.record("charge", {"n": i})
    ok, problem = led.verify()
    assert ok is True and problem is None


def test_ledger_detects_tampering(tmp_path):
    path = tmp_path / "l.jsonl"
    led = Ledger(str(path))
    led.record("bound", {"intent": "original"})
    led.record("charge", {"n": 1})
    led.record("charge", {"n": 2})

    # Rewrite history: change the first entry's data but keep its old hash.
    lines = path.read_text().strip().split("\n")
    first = json.loads(lines[0])
    first["data"]["intent"] = "tampered"
    lines[0] = json.dumps(first, sort_keys=True, separators=(",", ":"))
    path.write_text("\n".join(lines) + "\n")

    ok, problem = Ledger(str(path)).verify()
    assert ok is False
    assert "seal" in problem or "link" in problem


def test_ledger_detects_deleted_entry(tmp_path):
    path = tmp_path / "l.jsonl"
    led = Ledger(str(path))
    for i in range(4):
        led.record("charge", {"n": i})
    lines = path.read_text().strip().split("\n")
    del lines[1]                     # excise an entry
    path.write_text("\n".join(lines) + "\n")
    ok, _ = Ledger(str(path)).verify()
    assert ok is False


def test_each_entry_links_to_the_previous(tmp_path):
    led = Ledger(str(tmp_path / "l.jsonl"))
    a = led.record("bound", {})
    b = led.record("charge", {})
    assert b["prev"] == a["hash"]
    assert a["hash"] == entry_hash(a)


def test_empty_ledger_verifies(tmp_path):
    ok, _ = Ledger(str(tmp_path / "empty.jsonl")).verify()
    assert ok is True
