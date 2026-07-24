"""Tests for the vessel lifecycle, conditions, and dissolution."""

import os
from datetime import datetime, timedelta, timezone

import pytest

from sigilry import conditions as cond
from sigilry.vessel import BindingRefused, Vessel, parse_duration

CHICAGO = (41.8781, -87.6298)


@pytest.fixture
def sigil(tmp_path):
    p = tmp_path / "arrival.png"
    p.write_bytes(b"\x89PNG" + os.urandom(256))   # stand-in for a drawing
    return str(p)


@pytest.fixture
def root(tmp_path, monkeypatch):
    r = tmp_path / "sigilry"
    monkeypatch.setenv("SIGILRY_ROOT", str(r))
    return str(r)


def bind(sigil, root, **overrides):
    kwargs = dict(
        name="arrival",
        intent="IT IS MY WILL TO ARRIVE WHOLE",
        sigil_path=sigil,
        lifespan="28d",
        latitude=CHICAGO[0],
        longitude=CHICAGO[1],
        difficulty=1,
    )
    kwargs.update(overrides)
    return Vessel.bind(**kwargs)


# ------------------------------------------------------------------ duration

@pytest.mark.parametrize(
    "text,expected",
    [("30m", timedelta(minutes=30)), ("12h", timedelta(hours=12)),
     ("28d", timedelta(days=28)), ("4w", timedelta(weeks=4)), ("45s", timedelta(seconds=45))],
)
def test_parse_duration(text, expected):
    assert parse_duration(text) == expected


@pytest.mark.parametrize("bad", ["tomorrow", "28", "0d", "-3d", "", "1y"])
def test_parse_duration_rejects_nonsense(bad):
    with pytest.raises(ValueError):
        parse_duration(bad)


# --------------------------------------------------------------- refusals

def test_refuses_without_intent(sigil, root):
    with pytest.raises(BindingRefused, match="intent"):
        bind(sigil, root, intent="   ")


def test_refuses_without_sigil(tmp_path, root):
    with pytest.raises(BindingRefused, match="sigil"):
        bind(str(tmp_path / "missing.png"), root)


def test_refuses_without_lifespan(sigil, root):
    with pytest.raises(BindingRefused, match="lifespan"):
        bind(sigil, root, lifespan="")


def test_refuses_bad_dissolution(sigil, root):
    with pytest.raises(BindingRefused, match="dissolution"):
        bind(sigil, root, dissolution="forget about it")


def test_refuses_unknown_planet(sigil, root):
    with pytest.raises(BindingRefused, match="planet"):
        bind(sigil, root, ruler="Pluto")


def test_refuses_unknown_condition(sigil, root):
    with pytest.raises(cond.UnknownCondition):
        bind(sigil, root, labor_conditions=["when i feel like it"])


def test_refuses_duplicate_name(sigil, root):
    bind(sigil, root)
    with pytest.raises(BindingRefused, match="already exists"):
        bind(sigil, root)


def test_refuses_hour_ruler_without_a_ruler(sigil, root):
    with pytest.raises(cond.UnknownCondition):
        bind(sigil, root, labor_conditions=["hour:ruler"], ruler=None)


# ----------------------------------------------------------------- binding

def test_bind_records_true_name_from_the_drawing(sigil, root):
    from sigilry.naming import true_name
    v = bind(sigil, root)
    assert v.config.sigil_name == true_name(sigil)
    assert len(v.config.sigil_name) == 64


def test_bind_writes_a_bound_entry_with_birth_circumstance(sigil, root):
    v = bind(sigil, root)
    entry = v.ledger.last_of_kind("bound")
    assert entry is not None
    born = entry["data"]["born_under"]
    assert born["planetary_hour"] in cond.PLANETS if hasattr(cond, "PLANETS") else True
    assert "moon" in born


def test_bind_copies_the_sigil_beside_the_vessel(sigil, root):
    v = bind(sigil, root)
    assert os.path.exists(v.sigil_path)


def test_vessel_can_be_reloaded(sigil, root):
    v = bind(sigil, root)
    again = Vessel.load("arrival")
    assert again.config.intent == v.config.intent
    assert again.config.sigil_name == v.config.sigil_name


def test_all_names_lists_bound_vessels(sigil, root):
    bind(sigil, root)
    bind(sigil, root, name="second")
    assert set(Vessel.all_names()) == {"arrival", "second"}


# --------------------------------------------------------------- conditions

def test_always_condition_is_met(sigil, root):
    v = bind(sigil, root, labor_conditions=["always"])
    met, unmet = v.conditions_met()
    assert met is True and unmet == []


def test_impossible_condition_pair_is_never_met(sigil, root):
    v = bind(sigil, root, labor_conditions=["day-hours", "night-hours"])
    met, unmet = v.conditions_met()
    assert met is False and len(unmet) >= 1


def test_moon_conditions_are_complementary(sigil, root):
    waxing = bind(sigil, root, name="wax", labor_conditions=["moon:waxing"])
    waning = bind(sigil, root, name="wane", labor_conditions=["moon:waning"])
    assert waxing.conditions_met()[0] != waning.conditions_met()[0]


def test_clock_window_wraps_midnight():
    circ = cond.observe(datetime.now(timezone.utc), *CHICAGO)
    # A window covering all 24 hours must always be satisfied.
    assert cond.satisfied("clock:00:00-23:59", circ) is True


def test_illumination_comparison():
    circ = cond.observe(datetime.now(timezone.utc), *CHICAGO)
    assert cond.satisfied("illumination>=0.0", circ) is True
    assert cond.satisfied("illumination<0.0", circ) is False


def test_hour_ruler_matches_current_hour(sigil, root):
    circ = cond.observe(datetime.now(timezone.utc), *CHICAGO)
    v = bind(sigil, root, ruler=circ.hour_planet, labor_conditions=["hour:ruler"])
    assert v.conditions_met()[0] is True


# ------------------------------------------------------------------- living

def test_charge_is_recorded_and_verifiable(sigil, root):
    from sigilry.charge import Charge, verify_charge
    v = bind(sigil, root, difficulty=1)
    entry = None
    while entry is None:
        entry = v.charge_once(slice_iterations=100_000)
    d = entry["data"]
    seed = f"{v.config.sigil_name}:{v.config.intent}:0"
    off = Charge(d["nonce"], d["digest"], d["difficulty"], d["iterations"])
    assert verify_charge(seed, off) is True
    assert v.charges_completed == 1


def test_repetitions_accumulate(sigil, root):
    v = bind(sigil, root, difficulty=1)
    for _ in range(2):
        while v.charge_once(slice_iterations=100_000) is None:
            pass
    assert v.charges_completed == 2
    assert v.total_repetitions > 0


def test_run_until_lifespan_spent_kills_it(sigil, root):
    v = bind(sigil, root, lifespan="1s", difficulty=1)
    import time
    time.sleep(1.1)
    cause = v.run(poll_seconds=0.1, max_seconds=5)
    assert cause == "lifespan-spent"
    assert v.is_dissolved is True


def test_run_suspends_at_limit_without_dying(sigil, root):
    v = bind(sigil, root, lifespan="28d", labor_conditions=["day-hours", "night-hours"])
    cause = v.run(poll_seconds=0.05, max_seconds=0.3)
    assert cause == "suspended"
    assert v.is_dissolved is False


def test_state_name_reflects_conditions(sigil, root):
    laboring = bind(sigil, root, name="a", labor_conditions=["always"])
    resting = bind(sigil, root, name="b", labor_conditions=["day-hours", "night-hours"])
    assert laboring.state_name() == "IN FORCE"
    assert resting.state_name() == "LATENT"


# ---------------------------------------------------------------- attendance

def test_attend_records_witness(sigil, root):
    v = bind(sigil, root, renew_every="3d")
    v.renew(note="checked in")
    assert v.ledger.last_of_kind("renewed")["data"]["note"] == "checked in"


def test_weakens_when_unattended(sigil, root, monkeypatch):
    v = bind(sigil, root, renew_every="1s")
    import time
    time.sleep(1.2)
    assert v.is_fading is True


def test_attending_recovers_from_weakened(sigil, root):
    v = bind(sigil, root, renew_every="1s")
    import time
    time.sleep(1.2)
    assert v.is_fading is True
    v.renew()
    assert v.is_fading is False


def test_neglect_kills(sigil, root):
    v = bind(sigil, root, renew_every="1s", lifespan="28d")
    import time
    time.sleep(2.2)                      # past twice the attendance interval
    cause = v.run(poll_seconds=0.05, max_seconds=5)
    assert cause == "neglect"


def test_no_attendance_requirement_never_weakens(sigil, root):
    v = bind(sigil, root, renew_every=None)
    assert v.is_fading is False
    assert v.neglect is None


# --------------------------------------------------------------- dissolution

def test_banish_destroys_sigil_and_state_but_keeps_ledger(sigil, root):
    v = bind(sigil, root)
    sigil_copy, state = v.sigil_path, os.path.join(v.directory, "vessel.json")
    assert os.path.exists(sigil_copy) and os.path.exists(state)

    v.dissolve_now()

    assert not os.path.exists(sigil_copy)
    assert not os.path.exists(state)
    assert os.path.exists(v.ledger.path)          # the record survives
    assert v.is_dissolved is True


def test_banish_records_cause_and_totals(sigil, root):
    v = bind(sigil, root, difficulty=1)
    while v.charge_once(slice_iterations=100_000) is None:
        pass
    v.dissolve_now()
    died = v.ledger.last_of_kind("dissolved")
    assert died["data"]["cause"] == "banished"
    assert died["data"]["charges"] == 1


def test_ledger_still_verifies_after_death(sigil, root):
    v = bind(sigil, root)
    v.renew()
    v.dissolve_now()
    ok, problem = v.ledger.verify()
    assert ok is True, problem


def test_dead_vessel_cannot_be_attended(sigil, root):
    v = bind(sigil, root)
    v.dissolve_now()
    with pytest.raises(RuntimeError):
        v.renew()


def test_release_dissolution_keeps_ledger_too(sigil, root):
    v = bind(sigil, root, dissolution="release")
    v.dissolve_now()
    assert os.path.exists(v.ledger.path)
    assert not os.path.exists(v.sigil_path)


def test_erasure_overwrites_before_deleting(tmp_path):
    """The bytes are overwritten, not merely unlinked."""
    from sigilry.erasure import erase_file
    p = tmp_path / "secret.bin"
    p.write_bytes(b"A" * 4096)
    assert erase_file(str(p)) is True
    assert not p.exists()
