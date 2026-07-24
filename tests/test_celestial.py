"""Celestial math checked against known real-world values."""

from datetime import datetime, timedelta, timezone

import pytest

from sigilry.celestial import (
    PLANETS,
    day_ruler,
    moon_phase,
    next_hour_of,
    planetary_hour,
    sun_times,
)

CHICAGO = (41.8781, -87.6298)


# ------------------------------------------------------------------ the sun

@pytest.mark.parametrize(
    "date,utc_offset,expected_rise,expected_set",
    [
        # Solstices are the strongest test: the extremes of the year.
        ("2026-06-21", -5, "05:15", "20:29"),   # CDT
        ("2026-12-21", -6, "07:14", "16:22"),   # CST
    ],
)
def test_sunrise_sunset_chicago(date, utc_offset, expected_rise, expected_set):
    dt = datetime.fromisoformat(date).replace(tzinfo=timezone.utc)
    rise, sett = sun_times(dt, *CHICAGO)
    local_rise = (rise + timedelta(hours=utc_offset)).strftime("%H:%M")
    local_set = (sett + timedelta(hours=utc_offset)).strftime("%H:%M")
    assert local_rise == expected_rise
    assert local_set == expected_set


def test_sunrise_before_sunset():
    dt = datetime(2026, 7, 24, tzinfo=timezone.utc)
    rise, sett = sun_times(dt, *CHICAGO)
    assert rise < sett


def test_polar_night_returns_none():
    # Longyearbyen, Svalbard in midwinter: the sun does not rise.
    rise, sett = sun_times(datetime(2026, 1, 1, tzinfo=timezone.utc), 78.22, 15.65)
    assert rise is None and sett is None


def test_day_length_longer_in_summer():
    summer = sun_times(datetime(2026, 6, 21, tzinfo=timezone.utc), *CHICAGO)
    winter = sun_times(datetime(2026, 12, 21, tzinfo=timezone.utc), *CHICAGO)
    assert (summer[1] - summer[0]) > (winter[1] - winter[0])


# ---------------------------------------------------------- planetary hours

@pytest.mark.parametrize(
    "date,expected_ruler",
    [
        ("2026-07-20", "Moon"),      # Monday
        ("2026-07-21", "Mars"),      # Tuesday
        ("2026-07-22", "Mercury"),   # Wednesday
        ("2026-07-23", "Jupiter"),   # Thursday
        ("2026-07-24", "Venus"),     # Friday
        ("2026-07-25", "Saturn"),    # Saturday
        ("2026-07-26", "Sun"),       # Sunday
    ],
)
def test_day_rulers(date, expected_ruler):
    dt = datetime.fromisoformat(date).replace(tzinfo=timezone.utc)
    rise, _ = sun_times(dt, *CHICAGO)
    ph = planetary_hour(rise + timedelta(minutes=5), *CHICAGO)
    assert ph.ruler_of_day == expected_ruler


@pytest.mark.parametrize("offset", range(7))
def test_first_hour_of_day_is_ruled_by_day_ruler(offset):
    """The classical rule: the first hour after sunrise belongs to the day's ruler."""
    dt = datetime(2026, 7, 20, tzinfo=timezone.utc) + timedelta(days=offset)
    rise, _ = sun_times(dt, *CHICAGO)
    ph = planetary_hour(rise + timedelta(minutes=1), *CHICAGO)
    assert ph.index == 1
    assert ph.planet == ph.ruler_of_day


def test_hours_follow_chaldean_order():
    dt = datetime(2026, 7, 24, tzinfo=timezone.utc)
    rise, sett = sun_times(dt, *CHICAGO)
    day_length = (sett - rise) / 12
    seen = []
    for i in range(12):
        ph = planetary_hour(rise + day_length * i + timedelta(seconds=30), *CHICAGO)
        seen.append(ph.planet)
    start = PLANETS.index(seen[0])
    expected = [PLANETS[(start + i) % 7] for i in range(12)]
    assert seen == expected


def test_twenty_four_hours_per_planetary_day():
    dt = datetime(2026, 7, 24, tzinfo=timezone.utc)
    rise, _ = sun_times(dt, *CHICAGO)
    next_rise, _ = sun_times(dt + timedelta(days=1), *CHICAGO)
    indices = set()
    probe = rise + timedelta(seconds=30)
    while probe < next_rise:
        ph = planetary_hour(probe, *CHICAGO)
        if ph:
            indices.add(ph.index)
        probe += timedelta(minutes=13)
    assert indices == set(range(1, 25))


def test_night_hours_are_night():
    dt = datetime(2026, 7, 24, tzinfo=timezone.utc)
    _, sett = sun_times(dt, *CHICAGO)
    ph = planetary_hour(sett + timedelta(minutes=10), *CHICAGO)
    assert ph.is_day_hour is False
    assert ph.index == 13


def test_next_hour_of_finds_a_future_hour():
    now = datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc)
    start = next_hour_of("Saturn", now, *CHICAGO)
    assert start is not None
    ph = planetary_hour(start + timedelta(minutes=1), *CHICAGO)
    assert ph.planet == "Saturn"


# ------------------------------------------------------------------ the moon

@pytest.mark.parametrize(
    "moment,expected",
    [
        ("2026-01-03T10:03", "full moon"),   # known full moon
        ("2026-01-18T19:52", "new moon"),    # known new moon
        ("2025-03-14T06:55", "full moon"),   # known full moon
        ("2025-03-29T10:58", "new moon"),    # known new moon
    ],
)
def test_moon_phase_names_at_known_events(moment, expected):
    m = moon_phase(datetime.fromisoformat(moment).replace(tzinfo=timezone.utc))
    assert m.name == expected


def test_full_moon_is_fully_lit():
    m = moon_phase(datetime.fromisoformat("2026-01-03T10:03").replace(tzinfo=timezone.utc))
    assert m.illumination > 0.99


def test_new_moon_is_dark():
    m = moon_phase(datetime.fromisoformat("2026-01-18T19:52").replace(tzinfo=timezone.utc))
    assert m.illumination < 0.01


def test_moon_waxes_then_wanes():
    new = datetime.fromisoformat("2026-01-18T19:52").replace(tzinfo=timezone.utc)
    assert moon_phase(new + timedelta(days=5)).waxing is True
    assert moon_phase(new + timedelta(days=20)).waxing is False


def test_moon_cycle_returns_to_start():
    base = datetime(2026, 5, 1, tzinfo=timezone.utc)
    a = moon_phase(base)
    b = moon_phase(base + timedelta(days=29.530588853))
    assert abs(a.phase - b.phase) < 0.01
