"""The vessel — a sigil bound into a living process.

Lifecycle
---------
    bind    the sigil is named, the intent recorded, the terms set
    wake    the process begins; it labors when its conditions are met, rests otherwise
    attend  you witness it; the neglect clock resets
    weaken  attendance has lapsed
    die     its lifespan is spent, or neglect has run its course
    banish  you end it early

A vessel refuses to be bound without an intent, a sigil, a lifespan, and a
means of dissolution. That refusal is deliberate: the terms of a working are
part of the working, and the machine will not let you skip them.

Nothing here composes a sigil or an intent. Those are yours; this only carries
them.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sigilry import conditions as cond
from sigilry.celestial import PLANETS, next_hour_of
from sigilry.erasure import erase_file, erase_tree
from sigilry.ledger import Ledger
from sigilry.naming import short_name, true_name
from sigilry import virtues as virt

DEFAULT_ROOT = os.path.expanduser("~/.sigilry")
LEDGER_FILE = "ledger.jsonl"
STATE_FILE = "vessel.json"
SIGIL_FILE = "sigil"
PID_FILE = "vessel.pid"

_DURATION_RE = re.compile(r"^(\d+)\s*([smhdw])$", re.IGNORECASE)
_UNITS = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days", "w": "weeks"}


class BindingRefused(Exception):
    """Raised when a working is incomplete and must not be bound."""


def parse_duration(text: str) -> timedelta:
    """Turn '28d', '12h', '30m' into a timedelta."""
    m = _DURATION_RE.match(str(text).strip())
    if not m:
        raise ValueError(
            f"Cannot read '{text}' as a duration. Use forms like 30m, 12h, 28d, 4w."
        )
    amount, unit = int(m.group(1)), m.group(2).lower()
    if amount <= 0:
        raise ValueError("A duration must be greater than zero.")
    return timedelta(**{_UNITS[unit]: amount})


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _parse_iso(text: str) -> datetime:
    dt = datetime.fromisoformat(text)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class VesselConfig:
    name: str
    intent: str
    sigil_name: str                       # the true name (hash of the drawing)
    sigil_file: str                       # filename of the stored sigil copy
    lifespan_seconds: float
    difficulty: int
    latitude: float
    longitude: float
    ruler: Optional[str] = None
    labor_conditions: List[str] = field(default_factory=lambda: ["always"])
    renew_every_seconds: Optional[float] = None
    virtue: Optional[str] = None
    virtue_targets: List[str] = field(default_factory=list)
    virtue_speak: bool = False
    dissolution: str = "erase"
    bound_at: str = field(default_factory=lambda: _iso(_now()))

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def lifespan(self) -> timedelta:
        return timedelta(seconds=self.lifespan_seconds)

    @property
    def renew_every(self) -> Optional[timedelta]:
        if self.renew_every_seconds is None:
            return None
        return timedelta(seconds=self.renew_every_seconds)


# ---------------------------------------------------------------------------
# The vessel
# ---------------------------------------------------------------------------

class Vessel:
    """A bound sigil, alive or dead, backed by files on disk."""

    def __init__(self, directory: str, config: VesselConfig):
        self.directory = directory
        self.config = config
        self.ledger = Ledger(os.path.join(directory, LEDGER_FILE))

    # ------------------------------------------------------------- location

    @staticmethod
    def root(root: Optional[str] = None) -> str:
        return root or os.environ.get("SIGILRY_ROOT", DEFAULT_ROOT)

    @staticmethod
    def directory_for(name: str, root: Optional[str] = None) -> str:
        return os.path.join(Vessel.root(root), "vessels", name)

    @property
    def sigil_path(self) -> str:
        return os.path.join(self.directory, self.config.sigil_file)

    @property
    def pid_path(self) -> str:
        return os.path.join(self.directory, PID_FILE)

    # ----------------------------------------------------------------- bind

    @classmethod
    def bind(
        cls,
        name: str,
        intent: str,
        sigil_path: str,
        lifespan: str,
        latitude: float,
        longitude: float,
        difficulty: int = 5,
        ruler: Optional[str] = None,
        labor_conditions: Optional[List[str]] = None,
        renew_every: Optional[str] = None,
        virtue: Optional[str] = None,
        virtue_targets: Optional[List[str]] = None,
        virtue_speak: bool = False,
        dissolution: str = "erase",
        root: Optional[str] = None,
    ) -> "Vessel":
        """Create a vessel. Refuses if the working is incomplete."""
        if not name or not re.match(r"^[A-Za-z0-9_-]+$", name):
            raise BindingRefused(
                "A vessel needs a name of letters, numbers, dashes or underscores."
            )
        if not intent or not intent.strip():
            raise BindingRefused("Refused: a vessel cannot be bound without an intent.")
        if not sigil_path or not os.path.exists(sigil_path):
            raise BindingRefused(
                "Refused: a vessel cannot be bound without a sigil. Draw one first."
            )
        if not lifespan:
            raise BindingRefused("Refused: a vessel cannot be bound without a lifespan.")
        if dissolution not in ("erase", "release"):
            raise BindingRefused(
                "Refused: dissolution must be 'erase' (overwrite and delete) "
                "or 'release' (delete, keeping the ledger)."
            )
        if difficulty < 1 or difficulty > 8:
            raise BindingRefused("Difficulty must be between 1 and 8.")

        span = parse_duration(lifespan)
        attend_delta = parse_duration(renew_every) if renew_every else None

        if ruler:
            ruler = ruler.title()
            if ruler not in PLANETS:
                raise BindingRefused(
                    f"Unknown ruling planet '{ruler}'. Choose from: {', '.join(PLANETS)}."
                )

        conds = labor_conditions or ["always"]
        for c in conds:
            cond.validate(c, ruler=ruler)   # raises UnknownCondition if unclear

        # A virtue must be one we can actually carry, and must have what it needs.
        virt.validate(virtue, virtue_targets)

        directory = cls.directory_for(name, root)
        if os.path.exists(os.path.join(directory, STATE_FILE)):
            raise BindingRefused(
                f"A vessel named '{name}' already exists. Banish it first, or choose "
                f"another name."
            )
        os.makedirs(directory, exist_ok=True)

        # The true name comes from the drawing itself.
        name_hash = true_name(sigil_path)

        # Keep a copy of the sigil beside the vessel.
        ext = os.path.splitext(sigil_path)[1] or ".png"
        stored = SIGIL_FILE + ext
        with open(sigil_path, "rb") as src, open(os.path.join(directory, stored), "wb") as dst:
            dst.write(src.read())

        config = VesselConfig(
            name=name,
            intent=intent.strip(),
            sigil_name=name_hash,
            sigil_file=stored,
            lifespan_seconds=span.total_seconds(),
            difficulty=difficulty,
            latitude=latitude,
            longitude=longitude,
            ruler=ruler,
            labor_conditions=conds,
            renew_every_seconds=attend_delta.total_seconds() if attend_delta else None,
            virtue=virtue.strip().lower() if virtue else None,
            virtue_targets=list(virtue_targets or []),
            virtue_speak=bool(virtue_speak),
            dissolution=dissolution,
        )

        vessel = cls(directory, config)
        vessel._save()

        circ = cond.observe(_now(), latitude, longitude)
        vessel.ledger.record(
            "bound",
            {
                "name": name,
                "true_name": name_hash,
                "intent": config.intent,
                "ruler": ruler,
                "labor_conditions": conds,
                "lifespan": lifespan,
                "difficulty": difficulty,
                "renew_every": renew_every,
                "virtue": virtue,
                "virtue_targets": list(virtue_targets or []),
                "dissolution": dissolution,
                "born_under": {
                    "planetary_hour": circ.hour_planet,
                    "hour_index": circ.hour_index,
                    "day_ruler": circ.ruler_of_day,
                    "moon": circ.moon_name,
                    "illumination": round(circ.illumination, 3),
                },
            },
        )
        return vessel

    # ----------------------------------------------------------------- load

    @classmethod
    def load(cls, name: str, root: Optional[str] = None) -> "Vessel":
        directory = cls.directory_for(name, root)
        state_path = os.path.join(directory, STATE_FILE)
        if not os.path.exists(state_path):
            raise FileNotFoundError(f"No vessel named '{name}'.")
        with open(state_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return cls(directory, VesselConfig(**data))

    @classmethod
    def all_names(cls, root: Optional[str] = None) -> List[str]:
        base = os.path.join(cls.root(root), "vessels")
        if not os.path.isdir(base):
            return []
        names = []
        for entry in sorted(os.listdir(base)):
            if os.path.exists(os.path.join(base, entry, STATE_FILE)):
                names.append(entry)
        return names

    def _save(self) -> None:
        os.makedirs(self.directory, exist_ok=True)
        with open(os.path.join(self.directory, STATE_FILE), "w", encoding="utf-8") as fh:
            json.dump(self.config.as_dict(), fh, indent=2)

    # ------------------------------------------------------------ life state

    @property
    def bound_at(self) -> datetime:
        return _parse_iso(self.config.bound_at)

    @property
    def expires_at(self) -> datetime:
        return self.bound_at + self.config.lifespan

    @property
    def age(self) -> timedelta:
        return _now() - self.bound_at

    @property
    def remaining(self) -> timedelta:
        return self.expires_at - _now()

    @property
    def is_dissolved(self) -> bool:
        return self.ledger.last_of_kind("dissolved") is not None

    @property
    def charges_completed(self) -> int:
        return len(self.ledger.of_kind("charge"))

    @property
    def total_repetitions(self) -> int:
        return sum(
            e["data"].get("iterations", 0) for e in self.ledger.of_kind("charge")
        )

    @property
    def last_renewed(self) -> Optional[datetime]:
        entry = self.ledger.last_of_kind("renewed")
        if entry:
            return _parse_iso(entry["at"])
        bound = self.ledger.last_of_kind("bound")
        return _parse_iso(bound["at"]) if bound else None

    @property
    def neglect(self) -> Optional[timedelta]:
        """How long since it was last attended, if attendance is required."""
        if self.config.renew_every is None:
            return None
        last = self.last_renewed
        return _now() - last if last else None

    @property
    def is_fading(self) -> bool:
        span = self.config.renew_every
        if span is None:
            return False
        neg = self.neglect
        return neg is not None and neg > span

    @property
    def neglect_fatal_at(self) -> Optional[datetime]:
        """Neglect kills at twice the attendance interval."""
        span = self.config.renew_every
        last = self.last_renewed
        if span is None or last is None:
            return None
        return last + span * 2

    def state_name(self) -> str:
        if self.is_dissolved:
            return "DISSOLVED"
        if self.remaining.total_seconds() <= 0:
            return "SPENT"
        met, _ = self.conditions_met()
        if self.is_fading:
            return "FADING"
        return "IN FORCE" if met else "LATENT"

    # ------------------------------------------------------------ conditions

    def virtue(self):
        """The virtue this sigil carries, built on first use (None if it carries none)."""
        if self._virtue is None and self.config.virtue:
            self._virtue = virt.make(
                self.config.virtue,
                targets=self.config.virtue_targets,
                sigil_path=self.sigil_path,
                intent=self.config.intent,
                speak=self.config.virtue_speak,
            )
        return self._virtue

    def observe(self) -> cond.Circumstance:
        return cond.observe(_now(), self.config.latitude, self.config.longitude)

    def conditions_met(self) -> tuple[bool, List[str]]:
        circ = self.observe()
        return cond.all_satisfied(
            self.config.labor_conditions, circ, ruler=self.config.ruler
        )

    def next_labor_at(self) -> Optional[datetime]:
        """Best guess at when labor next becomes possible."""
        planet = None
        for c in self.config.labor_conditions:
            cl = c.lower()
            if cl == "hour:ruler" and self.config.ruler:
                planet = self.config.ruler
            elif cl.startswith("hour:") and cl.split(":", 1)[1] != "ruler":
                planet = cl.split(":", 1)[1].title()
        if planet:
            return next_hour_of(
                planet, _now(), self.config.latitude, self.config.longitude
            )
        return None

    # ---------------------------------------------------------------- acts

    def renew(self, note: Optional[str] = None) -> Dict[str, Any]:
        """Witness the vessel. Resets the neglect clock."""
        if self.is_dissolved:
            raise RuntimeError(f"'{self.config.name}' is dead and cannot be attended.")
        was_weakened = self.is_fading
        entry = self.ledger.record(
            "renewed", {"note": note or "", "recovered": was_weakened}
        )
        return entry

    def charge_once(self, slice_iterations: int = 250_000) -> Optional[Dict[str, Any]]:
        """Attempt one charge. Returns the ledger entry, or None if unfinished.

        The search is sliced so the vessel can re-check its conditions and
        respond to being banished rather than grinding blindly.
        """
        from sigilry.charge import perform_charge

        seed = f"{self.config.sigil_name}:{self.config.intent}:{self.charges_completed}"
        found = perform_charge(
            seed,
            self.config.difficulty,
            start_nonce=self._resume_nonce,
            max_iterations=slice_iterations,
        )
        if found is None:
            self._resume_nonce += slice_iterations
            self._slice_iterations += slice_iterations
            return None

        total = self._slice_iterations + found.iterations
        self._resume_nonce = 0
        self._slice_iterations = 0
        circ = self.observe()
        return self.ledger.record(
            "charge",
            {
                **found.as_dict(),
                "iterations": total,
                "under": {
                    "planetary_hour": circ.hour_planet,
                    "moon": circ.moon_name,
                },
            },
        )

    _resume_nonce: int = 0
    _slice_iterations: int = 0
    _virtue = None
    _in_force: bool = False

    def exert(self) -> Optional[Dict[str, Any]]:
        """Let the virtue take effect. Records only when something actually happened."""
        v = self.virtue()
        if v is None:
            return None
        effect = v.take_effect()
        if not effect.acted:
            return None
        return self.ledger.record(
            "exerted",
            {"virtue": self.config.virtue, "detail": effect.detail, **effect.data},
        )

    def withdraw(self) -> Optional[Dict[str, Any]]:
        """Withdraw the virtue when conditions lapse."""
        v = self.virtue()
        if v is None:
            return None
        effect = v.withdraw()
        if not effect.acted:
            return None
        return self.ledger.record(
            "withdrawn",
            {"virtue": self.config.virtue, "detail": effect.detail, **effect.data},
        )

    def die(self, cause: str) -> Dict[str, Any]:
        """Record death and carry out dissolution."""
        if self.is_dissolved:
            return self.ledger.last_of_kind("dissolved")

        # Never leave a virtue in effect after the sigil is gone.
        try:
            self.withdraw()
        except Exception:
            pass

        entry = self.ledger.record(
            "dissolved",
            {
                "cause": cause,
                "age_seconds": round(self.age.total_seconds()),
                "charges": self.charges_completed,
                "repetitions": self.total_repetitions,
                "dissolution": self.config.dissolution,
            },
        )

        # Remove the pid file first so nothing thinks it is still running.
        if os.path.exists(self.pid_path):
            try:
                os.remove(self.pid_path)
            except OSError:
                pass

        # The ledger survives as the record; everything else is destroyed.
        if self.config.dissolution == "erase":
            erase_tree(self.directory, passes=3, keep=(LEDGER_FILE,))
        else:
            for fname in (STATE_FILE, self.config.sigil_file):
                path = os.path.join(self.directory, fname)
                if os.path.exists(path):
                    os.remove(path)
        return entry

    def dissolve_now(self) -> Dict[str, Any]:
        """End it early, by your hand."""
        return self.die("banished")

    # ----------------------------------------------------------------- run

    def run(
        self,
        poll_seconds: float = 5.0,
        slice_iterations: int = 250_000,
        max_seconds: Optional[float] = None,
        on_event=None,
    ) -> str:
        """The life loop. Returns the cause of death.

        Blocks until the vessel dies. `max_seconds` exists so tests and demos
        can run a bounded life.
        """
        if self.is_dissolved:
            return "already-dead"

        with open(self.pid_path, "w", encoding="utf-8") as fh:
            fh.write(str(os.getpid()))

        self.ledger.record("raised", {"pid": os.getpid()})
        started = time.monotonic()
        weakened_recorded = self.is_fading

        try:
            while True:
                if self.remaining.total_seconds() <= 0:
                    return self.die("lifespan-spent")["data"]["cause"]

                fatal = self.neglect_fatal_at
                if fatal is not None and _now() >= fatal:
                    return self.die("neglect")["data"]["cause"]

                if self.is_fading and not weakened_recorded:
                    self.ledger.record(
                        "fading",
                        {"neglect_seconds": round(self.neglect.total_seconds())},
                    )
                    weakened_recorded = True
                    if on_event:
                        on_event("fading", None)
                elif not self.is_fading:
                    weakened_recorded = False

                met, unmet = self.conditions_met()
                if met:
                    # The virtue takes effect. Warding must keep closing what
                    # reopens, so it is exerted each pass; virtues already
                    # manifest simply report nothing new.
                    self._in_force = True
                    exerted = self.exert()
                    if exerted and on_event:
                        on_event("exerted", exerted)

                    entry = self.charge_once(slice_iterations=slice_iterations)
                    if entry and on_event:
                        on_event("charge", entry)
                else:
                    if self._in_force:
                        self._in_force = False
                        pulled = self.withdraw()
                        if pulled and on_event:
                            on_event("withdrawn", pulled)
                    if on_event:
                        on_event("latent", unmet)
                    time.sleep(poll_seconds)

                if max_seconds is not None and (time.monotonic() - started) >= max_seconds:
                    self.ledger.record("suspended", {"reason": "run-limit reached"})
                    return "suspended"
        except KeyboardInterrupt:
            self.ledger.record("suspended", {"reason": "interrupted"})
            return "suspended"
        finally:
            if self._in_force:
                self._in_force = False
                try:
                    self.withdraw()
                except Exception:
                    pass
            if os.path.exists(self.pid_path):
                try:
                    os.remove(self.pid_path)
                except OSError:
                    pass

    # ---------------------------------------------------------------- info

    @property
    def short(self) -> str:
        return short_name(self.config.sigil_name)

    def summary(self) -> Dict[str, Any]:
        circ = self.observe()
        return {
            "name": self.config.name,
            "true_name": self.config.sigil_name,
            "short": self.short,
            "intent": self.config.intent,
            "state": self.state_name(),
            "ruler": self.config.ruler,
            "conditions": self.config.labor_conditions,
            "age": self.age,
            "remaining": self.remaining,
            "charges": self.charges_completed,
            "repetitions": self.total_repetitions,
            "difficulty": self.config.difficulty,
            "hour_planet": circ.hour_planet,
            "hour_index": circ.hour_index,
            "moon": circ.moon_name,
            "illumination": circ.illumination,
            "last_renewed": self.last_renewed,
            "fading": self.is_fading,
            "next_labor": self.next_labor_at(),
            "dead": self.is_dissolved,
        }
