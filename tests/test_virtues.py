"""Tests for virtues — what a sigil does while it is in force."""

import os

import pytest

from sigilry import virtues as virt
from sigilry.vessel import Vessel

CHICAGO = (41.8781, -87.6298)


@pytest.fixture
def sigil(tmp_path):
    p = tmp_path / "glyph.png"
    p.write_bytes(b"\x89PNG" + os.urandom(256))
    return str(p)


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setenv("SIGILRY_ROOT", str(tmp_path / "sigilry"))
    return str(tmp_path / "sigilry")


def bind(sigil, **overrides):
    kwargs = dict(
        name="s1",
        intent="IT IS MY WILL",
        sigil_path=sigil,
        lifespan="1d",
        latitude=CHICAGO[0],
        longitude=CHICAGO[1],
        difficulty=1,
    )
    kwargs.update(overrides)
    return Vessel.bind(**kwargs)


# ------------------------------------------------------------- registry

def test_known_virtues_are_registered():
    assert "warding" in virt.VIRTUES
    assert "manifesting" in virt.VIRTUES


def test_unknown_virtue_rejected():
    with pytest.raises(virt.UnknownVirtue):
        virt.validate("hexing")


def test_planned_virtue_says_so_honestly():
    with pytest.raises(virt.UnknownVirtue, match="not yet built"):
        virt.validate("drawing")


def test_no_virtue_is_allowed():
    virt.validate(None)
    assert virt.make(None) is None


# -------------------------------------------------------------- warding

def test_warding_requires_targets():
    with pytest.raises(virt.UnknownVirtue, match="needs targets"):
        virt.validate("warding", targets=[])


def test_warding_accepts_targets():
    virt.validate("warding", targets=["chrome"])


def test_warding_normalises_windows_process_names(monkeypatch):
    monkeypatch.setattr(virt, "WINDOWS", True)
    w = virt.Warding(targets=["chrome", "discord.exe"])
    assert w.targets == ["chrome.exe", "discord.exe"]


def test_warding_leaves_posix_names_alone(monkeypatch):
    monkeypatch.setattr(virt, "WINDOWS", False)
    w = virt.Warding(targets=["chrome"])
    assert w.targets == ["chrome"]


def test_warding_reports_when_nothing_was_closed(monkeypatch):
    monkeypatch.setattr(virt, "_run", lambda cmd, timeout=20.0: (1, "not found"))
    w = virt.Warding(targets=["definitely-not-running-xyz"])
    effect = w.take_effect()
    assert effect.acted is False
    assert "nothing to close" in effect.detail


def test_warding_reports_what_it_closed(monkeypatch):
    monkeypatch.setattr(virt, "WINDOWS", False)
    monkeypatch.setattr(virt, "_run", lambda cmd, timeout=20.0: (0, ""))
    w = virt.Warding(targets=["chrome"])
    effect = w.take_effect()
    assert effect.acted is True
    assert effect.data["closed"] == ["chrome"]


def test_warding_holds_nothing_when_withdrawn():
    w = virt.Warding(targets=["chrome"])
    assert w.withdraw().acted is False


# ---------------------------------------------------------- manifesting

def test_manifesting_sets_and_restores_wallpaper(sigil, monkeypatch):
    calls = []
    m = virt.Manifesting(sigil_path=sigil, intent="TEST", wallpaper=True)
    monkeypatch.setattr(m, "_current_wallpaper", lambda: "/old/paper.jpg")
    monkeypatch.setattr(m, "_set_wallpaper", lambda p: calls.append(p) or True)
    monkeypatch.setattr(os.path, "exists", lambda p: True)

    effect = m.take_effect()
    assert effect.acted is True
    assert calls[0] == os.path.abspath(sigil)

    pulled = m.withdraw()
    assert pulled.acted is True
    assert calls[1] == "/old/paper.jpg"


def test_manifesting_is_idempotent_while_in_force(sigil, monkeypatch):
    m = virt.Manifesting(sigil_path=sigil)
    monkeypatch.setattr(m, "_current_wallpaper", lambda: "/old.jpg")
    monkeypatch.setattr(m, "_set_wallpaper", lambda p: True)
    monkeypatch.setattr(os.path, "exists", lambda p: True)
    assert m.take_effect().acted is True
    assert m.take_effect().acted is False      # already manifest


def test_manifesting_reports_missing_sigil(tmp_path):
    m = virt.Manifesting(sigil_path=str(tmp_path / "gone.png"))
    effect = m.take_effect()
    assert effect.acted is False
    assert "not found" in effect.detail


def test_manifesting_speaks_once_per_turn(sigil, monkeypatch):
    spoken = []
    m = virt.Manifesting(sigil_path=sigil, intent="I WILL", speak=True, wallpaper=False)
    monkeypatch.setattr(m, "_speak_intent", lambda: spoken.append(1) or True)
    m.take_effect()
    m.take_effect()
    assert len(spoken) == 1
    m.withdraw()
    m.take_effect()
    assert len(spoken) == 2      # a new turn in force speaks again


def test_manifesting_without_intent_does_not_speak(sigil):
    m = virt.Manifesting(sigil_path=sigil, intent="", speak=True, wallpaper=False)
    assert m._speak_intent() is False


# ------------------------------------------------- carried by the vessel

def test_bind_refuses_warding_without_targets(sigil, root):
    with pytest.raises(virt.UnknownVirtue):
        bind(sigil, virtue="warding", virtue_targets=[])


def test_bind_refuses_unbuilt_virtue(sigil, root):
    with pytest.raises(virt.UnknownVirtue):
        bind(sigil, virtue="sealing")


def test_vessel_records_its_virtue(sigil, root):
    v = bind(sigil, virtue="warding", virtue_targets=["chrome"])
    assert v.config.virtue == "warding"
    assert v.config.virtue_targets == ["chrome"]
    assert v.ledger.last_of_kind("bound")["data"]["virtue"] == "warding"


def test_vessel_without_virtue_carries_none(sigil, root):
    v = bind(sigil)
    assert v.virtue() is None
    assert v.exert() is None
    assert v.withdraw() is None


def test_exert_is_recorded_in_the_ledger(sigil, root, monkeypatch):
    monkeypatch.setattr(virt, "WINDOWS", False)
    monkeypatch.setattr(virt, "_run", lambda cmd, timeout=20.0: (0, ""))
    v = bind(sigil, virtue="warding", virtue_targets=["chrome"])
    entry = v.exert()
    assert entry is not None
    assert entry["kind"] == "exerted"
    assert entry["data"]["virtue"] == "warding"


def test_nothing_recorded_when_virtue_did_nothing(sigil, root, monkeypatch):
    monkeypatch.setattr(virt, "_run", lambda cmd, timeout=20.0: (1, "no such process"))
    v = bind(sigil, virtue="warding", virtue_targets=["nope"])
    assert v.exert() is None
    assert len(v.ledger.of_kind("exerted")) == 0


def test_virtue_is_withdrawn_on_dissolution(sigil, root, monkeypatch):
    withdrawn = []
    v = bind(sigil, virtue="manifesting")
    m = v.virtue()
    monkeypatch.setattr(m, "_current_wallpaper", lambda: "/old.jpg")
    monkeypatch.setattr(m, "_set_wallpaper", lambda p: withdrawn.append(p) or True)
    monkeypatch.setattr(os.path, "exists", lambda p: True)
    v.exert()
    v.dissolve_now()
    assert withdrawn[-1] == "/old.jpg"       # restored before erasure
    assert v.is_dissolved is True


def test_run_loop_never_exerts_when_conditions_cannot_be_met(sigil, root):
    v = bind(
        sigil,
        virtue="warding",
        virtue_targets=["chrome"],
        labor_conditions=["day-hours", "night-hours"],
    )
    cause = v.run(poll_seconds=0.05, max_seconds=0.3)
    assert cause == "suspended"
    assert len(v.ledger.of_kind("exerted")) == 0
