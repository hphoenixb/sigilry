"""Conditions — the circumstances under which a vessel will labor.

A condition is written as a short string. A vessel labors only when *every*
condition it holds is satisfied; otherwise it rests. The vocabulary is
deliberately open so it can be shaped to whatever practice you settle into.

    always                  no restriction
    hour:mercury            during a planetary hour ruled by Mercury
    hour:ruler              during an hour ruled by the vessel's own ruler
    day-hours               between sunrise and sunset
    night-hours             between sunset and sunrise
    day:friday              on a given weekday
    day-ruler:venus         on a day ruled by a given planet
    moon:waxing             while the moon is waxing
    moon:waning             while the moon is waning
    moon:full               within ~1.8 days of full
    moon:dark               within ~1.8 days of new
    illumination>0.75       moon at least this lit (also < and >=, <=)
    clock:22:00-02:00       within a wall-clock window (local time, wraps midnight)

Unknown conditions raise an error at binding time rather than being silently
ignored, so a working never runs on a rule the machine didn't understand.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sigilry.celestial import (
    PLANETS,
    day_ruler,
    moon_phase,
    planetary_hour,
    sun_times,
)

_PLANET_SET = {p.lower() for p in PLANETS}
_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

_CLOCK_RE = re.compile(r"^clock:(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})$")
_ILLUM_RE = re.compile(r"^illumination(>=|<=|>|<)([01](?:\.\d+)?)$")


class UnknownCondition(ValueError):
    """Raised when a condition string cannot be understood."""


@dataclass
class Circumstance:
    """A snapshot of the conditions at a moment — used for evaluation and display."""

    moment: datetime
    latitude: float
    longitude: float
    hour_planet: Optional[str]
    hour_index: Optional[int]
    is_day_hour: Optional[bool]
    ruler_of_day: Optional[str]
    moon_name: str
    moon_waxing: bool
    moon_phase_value: float
    illumination: float


def observe(moment: datetime, latitude: float, longitude: float) -> Circumstance:
    """Read the current celestial circumstance."""
    dt = moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)
    ph = planetary_hour(dt, latitude, longitude)
    moon = moon_phase(dt)
    return Circumstance(
        moment=dt,
        latitude=latitude,
        longitude=longitude,
        hour_planet=ph.planet if ph else None,
        hour_index=ph.index if ph else None,
        is_day_hour=ph.is_day_hour if ph else None,
        ruler_of_day=ph.ruler_of_day if ph else day_ruler(dt, latitude, longitude),
        moon_name=moon.name,
        moon_waxing=moon.waxing,
        moon_phase_value=moon.phase,
        illumination=moon.illumination,
    )


def validate(condition: str, ruler: Optional[str] = None) -> None:
    """Raise UnknownCondition if the string isn't a condition we implement."""
    c = condition.strip().lower()
    if c in ("always", "day-hours", "night-hours", "moon:waxing", "moon:waning",
             "moon:full", "moon:dark", "moon:new"):
        return
    if c == "hour:ruler":
        if not ruler:
            raise UnknownCondition(
                "'hour:ruler' needs the vessel to have a ruling planet."
            )
        return
    if c.startswith("hour:"):
        if c.split(":", 1)[1] in _PLANET_SET:
            return
        raise UnknownCondition(f"'{condition}' — unknown planet.")
    if c.startswith("day-ruler:"):
        if c.split(":", 1)[1] in _PLANET_SET:
            return
        raise UnknownCondition(f"'{condition}' — unknown planet.")
    if c.startswith("day:"):
        if c.split(":", 1)[1] in _WEEKDAYS:
            return
        raise UnknownCondition(f"'{condition}' — unknown weekday.")
    if _CLOCK_RE.match(c) or _ILLUM_RE.match(c):
        return
    raise UnknownCondition(f"'{condition}' is not a condition I understand.")


def satisfied(condition: str, circ: Circumstance, ruler: Optional[str] = None) -> bool:
    """Is a single condition met in this circumstance?"""
    c = condition.strip().lower()

    if c == "always":
        return True

    if c == "hour:ruler":
        if not ruler or circ.hour_planet is None:
            return False
        return circ.hour_planet.lower() == ruler.lower()

    if c.startswith("hour:"):
        want = c.split(":", 1)[1]
        return circ.hour_planet is not None and circ.hour_planet.lower() == want

    if c == "day-hours":
        return circ.is_day_hour is True
    if c == "night-hours":
        return circ.is_day_hour is False

    if c.startswith("day-ruler:"):
        want = c.split(":", 1)[1]
        return circ.ruler_of_day is not None and circ.ruler_of_day.lower() == want

    if c.startswith("day:"):
        want = c.split(":", 1)[1]
        return _WEEKDAYS[circ.moment.weekday()] == want

    if c == "moon:waxing":
        return circ.moon_waxing
    if c == "moon:waning":
        return not circ.moon_waxing
    if c == "moon:full":
        return abs(circ.moon_phase_value - 0.5) < 0.0625   # ~1.85 days either side
    if c in ("moon:dark", "moon:new"):
        return circ.moon_phase_value < 0.0625 or circ.moon_phase_value > 0.9375

    m = _ILLUM_RE.match(c)
    if m:
        op, value = m.group(1), float(m.group(2))
        lit = circ.illumination
        return {
            ">": lit > value,
            "<": lit < value,
            ">=": lit >= value,
            "<=": lit <= value,
        }[op]

    m = _CLOCK_RE.match(c)
    if m:
        h1, m1, h2, m2 = (int(g) for g in m.groups())
        local = circ.moment.astimezone()  # system local time
        minutes = local.hour * 60 + local.minute
        start, end = h1 * 60 + m1, h2 * 60 + m2
        if start <= end:
            return start <= minutes < end
        return minutes >= start or minutes < end  # window wraps midnight

    raise UnknownCondition(f"'{condition}' is not a condition I understand.")


def all_satisfied(
    conditions: List[str], circ: Circumstance, ruler: Optional[str] = None
) -> Tuple[bool, List[str]]:
    """Evaluate every condition. Returns (all_met, list_of_unmet)."""
    unmet = [c for c in conditions if not satisfied(c, circ, ruler)]
    return (len(unmet) == 0, unmet)
