"""Celestial conditions: sunrise/sunset, planetary hours, day rulers, moon phase.

Everything here is computed from first principles — no network, no API keys.
The sun calculations follow the standard NOAA solar-position algorithm; the
moon phase is derived from the mean synodic cycle.

Planetary hours
---------------
The tradition divides daylight into twelve equal parts and darkness into
twelve more. Because day length changes through the year, these hours are
*unequal* — a summer day-hour is longer than a winter one. The first hour of
the day begins at sunrise and is ruled by the planet that rules the weekday;
subsequent hours follow the Chaldean order, wrapping around forever.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

# Chaldean order — classical planets by apparent speed, slowest to fastest.
PLANETS = ["Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"]

# Ruler of each weekday. Python: Monday=0 ... Sunday=6.
_DAY_RULERS = {
    0: "Moon",     # Monday
    1: "Mars",     # Tuesday
    2: "Mercury",  # Wednesday
    3: "Jupiter",  # Thursday
    4: "Venus",    # Friday
    5: "Saturn",   # Saturday
    6: "Sun",      # Sunday
}

# Reference new moon: 2000-01-06 18:14 UTC. Mean synodic month in days.
_NEW_MOON_EPOCH = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)
_SYNODIC_MONTH = 29.530588853

MOON_PHASE_NAMES = [
    "new moon",
    "waxing crescent",
    "first quarter",
    "waxing gibbous",
    "full moon",
    "waning gibbous",
    "last quarter",
    "waning crescent",
]


# --------------------------------------------------------------------------
# Sun
# --------------------------------------------------------------------------

def _julian_day(dt: datetime) -> float:
    """Julian Day Number for a UTC datetime."""
    dt = dt.astimezone(timezone.utc)
    y, m = dt.year, dt.month
    d = (
        dt.day
        + (dt.hour + dt.minute / 60 + dt.second / 3600) / 24
    )
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4
    return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + b - 1524.5


def _solar_noon_and_hour_angle(
    jd_date: float, latitude: float, longitude: float, zenith: float
) -> Tuple[float, Optional[float]]:
    """Return (solar noon as fraction of day UTC, hour angle in degrees).

    Hour angle is None when the sun never reaches the given zenith that day
    (polar day or polar night).
    """
    # Julian century from J2000.0
    t = (jd_date - 2451545.0) / 36525.0

    # Geometric mean longitude and anomaly of the sun (degrees)
    mean_long = (280.46646 + t * (36000.76983 + t * 0.0003032)) % 360
    mean_anom = 357.52911 + t * (35999.05029 - 0.0001537 * t)

    # Eccentricity of Earth's orbit
    eccent = 0.016708634 - t * (0.000042037 + 0.0000001267 * t)

    # Equation of the centre
    m_rad = math.radians(mean_anom)
    centre = (
        math.sin(m_rad) * (1.914602 - t * (0.004817 + 0.000014 * t))
        + math.sin(2 * m_rad) * (0.019993 - 0.000101 * t)
        + math.sin(3 * m_rad) * 0.000289
    )

    true_long = mean_long + centre

    # Apparent longitude (corrected for nutation and aberration)
    omega = 125.04 - 1934.136 * t
    apparent_long = true_long - 0.00569 - 0.00478 * math.sin(math.radians(omega))

    # Obliquity of the ecliptic, with correction
    seconds = 21.448 - t * (46.8150 + t * (0.00059 - t * 0.001813))
    obliq = 23.0 + (26.0 + seconds / 60.0) / 60.0
    obliq_corr = obliq + 0.00256 * math.cos(math.radians(omega))

    # Solar declination
    decl = math.degrees(
        math.asin(
            math.sin(math.radians(obliq_corr)) * math.sin(math.radians(apparent_long))
        )
    )

    # Equation of time (minutes)
    var_y = math.tan(math.radians(obliq_corr / 2)) ** 2
    eq_time = 4 * math.degrees(
        var_y * math.sin(2 * math.radians(mean_long))
        - 2 * eccent * math.sin(m_rad)
        + 4 * eccent * var_y * math.sin(m_rad) * math.cos(2 * math.radians(mean_long))
        - 0.5 * var_y * var_y * math.sin(4 * math.radians(mean_long))
        - 1.25 * eccent * eccent * math.sin(2 * m_rad)
    )

    # Hour angle of sunrise (degrees)
    lat_rad = math.radians(latitude)
    decl_rad = math.radians(decl)
    cos_ha = (
        math.cos(math.radians(zenith)) / (math.cos(lat_rad) * math.cos(decl_rad))
        - math.tan(lat_rad) * math.tan(decl_rad)
    )
    hour_angle = None
    if -1.0 <= cos_ha <= 1.0:
        hour_angle = math.degrees(math.acos(cos_ha))

    # Solar noon as a fraction of the day, UTC
    solar_noon = (720 - 4 * longitude - eq_time) / 1440
    return solar_noon, hour_angle


def sun_times(
    date: datetime, latitude: float, longitude: float, zenith: float = 90.833
) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Sunrise and sunset (timezone-aware UTC) for the calendar date of `date`.

    The default zenith of 90.833° is the standard for sunrise/sunset: 90° plus
    refraction and the sun's apparent radius. Returns (None, None) during
    polar day or night.
    """
    if date.tzinfo is None:
        date = date.replace(tzinfo=timezone.utc)
    midnight = datetime(date.year, date.month, date.day, tzinfo=timezone.utc)
    jd = _julian_day(midnight)

    solar_noon, hour_angle = _solar_noon_and_hour_angle(jd, latitude, longitude, zenith)
    if hour_angle is None:
        return None, None

    sunrise_frac = solar_noon - hour_angle * 4 / 1440
    sunset_frac = solar_noon + hour_angle * 4 / 1440
    return (
        midnight + timedelta(days=sunrise_frac),
        midnight + timedelta(days=sunset_frac),
    )


# --------------------------------------------------------------------------
# Planetary hours
# --------------------------------------------------------------------------

def day_ruler(date: datetime, latitude: float, longitude: float) -> str:
    """The planet ruling the *planetary day* containing `date`.

    A planetary day runs sunrise-to-sunrise, so the hours between midnight and
    sunrise still belong to the previous calendar day's ruler.
    """
    dt = date if date.tzinfo else date.replace(tzinfo=timezone.utc)
    sunrise, _ = sun_times(dt, latitude, longitude)
    if sunrise is not None and dt < sunrise:
        dt = dt - timedelta(days=1)
    return _DAY_RULERS[dt.weekday()]


@dataclass
class PlanetaryHour:
    planet: str
    index: int          # 1..24 within the planetary day
    is_day_hour: bool   # True between sunrise and sunset
    start: datetime
    end: datetime
    ruler_of_day: str

    @property
    def remaining(self) -> timedelta:
        return self.end - datetime.now(timezone.utc)


def planetary_hour(
    moment: datetime, latitude: float, longitude: float
) -> Optional[PlanetaryHour]:
    """Which planetary hour contains `moment`.

    Returns None where sunrise/sunset are undefined (polar regions in season).
    """
    dt = moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)

    sunrise, sunset = sun_times(dt, latitude, longitude)
    if sunrise is None or sunset is None:
        return None

    if dt < sunrise:
        # Still in the night hours that began at yesterday's sunset.
        prev = dt - timedelta(days=1)
        _, prev_sunset = sun_times(prev, latitude, longitude)
        next_sunrise = sunrise
        if prev_sunset is None:
            return None
        night_length = (next_sunrise - prev_sunset) / 12
        offset = dt - prev_sunset
        idx_in_night = int(offset / night_length)
        idx_in_night = min(idx_in_night, 11)
        start = prev_sunset + night_length * idx_in_night
        end = start + night_length
        hour_index = 13 + idx_in_night
        ruler = _DAY_RULERS[prev.weekday()]
        is_day = False
    elif dt < sunset:
        day_length = (sunset - sunrise) / 12
        idx = int((dt - sunrise) / day_length)
        idx = min(idx, 11)
        start = sunrise + day_length * idx
        end = start + day_length
        hour_index = 1 + idx
        ruler = _DAY_RULERS[dt.weekday()]
        is_day = True
    else:
        # Night hours following today's sunset.
        nxt = dt + timedelta(days=1)
        next_sunrise, _ = sun_times(nxt, latitude, longitude)
        if next_sunrise is None:
            return None
        night_length = (next_sunrise - sunset) / 12
        idx_in_night = int((dt - sunset) / night_length)
        idx_in_night = min(idx_in_night, 11)
        start = sunset + night_length * idx_in_night
        end = start + night_length
        hour_index = 13 + idx_in_night
        ruler = _DAY_RULERS[dt.weekday()]
        is_day = False

    # First hour of the planetary day is ruled by the day's ruler; the rest
    # follow the Chaldean order.
    ruler_pos = PLANETS.index(ruler)
    planet = PLANETS[(ruler_pos + hour_index - 1) % 7]

    return PlanetaryHour(
        planet=planet,
        index=hour_index,
        is_day_hour=is_day,
        start=start,
        end=end,
        ruler_of_day=ruler,
    )


def next_hour_of(
    planet: str, after: datetime, latitude: float, longitude: float, limit_days: int = 8
) -> Optional[datetime]:
    """When the next hour ruled by `planet` begins, searching forward.

    Steps forward in 10-minute increments — coarse but exact enough to name a
    start time, and cheap to compute.
    """
    planet = planet.title()
    dt = after if after.tzinfo else after.replace(tzinfo=timezone.utc)
    current = planetary_hour(dt, latitude, longitude)
    if current and current.planet == planet:
        return current.start

    step = timedelta(minutes=10)
    horizon = dt + timedelta(days=limit_days)
    probe = dt
    while probe < horizon:
        probe += step
        ph = planetary_hour(probe, latitude, longitude)
        if ph and ph.planet == planet:
            return ph.start
    return None


# --------------------------------------------------------------------------
# Moon
# --------------------------------------------------------------------------

@dataclass
class MoonState:
    age_days: float      # days since the last new moon
    phase: float         # 0.0 = new, 0.5 = full, approaching 1.0 = new again
    illumination: float  # 0.0 to 1.0
    name: str
    waxing: bool


def moon_phase(moment: datetime) -> MoonState:
    """Moon phase from the mean synodic cycle.

    Accurate to roughly a few hours — the true cycle wobbles by up to ~13
    hours either side of the mean, which is well within tolerance for naming a
    phase or gating on waxing versus waning.
    """
    dt = moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)
    elapsed = (dt - _NEW_MOON_EPOCH).total_seconds() / 86400.0
    age = elapsed % _SYNODIC_MONTH
    phase = age / _SYNODIC_MONTH
    illumination = (1 - math.cos(2 * math.pi * phase)) / 2

    # Eight named phases, centred on their boundaries.
    idx = int((phase * 8) + 0.5) % 8
    return MoonState(
        age_days=age,
        phase=phase,
        illumination=illumination,
        name=MOON_PHASE_NAMES[idx],
        waxing=phase < 0.5,
    )
