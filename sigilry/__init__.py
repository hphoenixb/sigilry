"""sigilry — bind a sigil into a living process.

A *vessel* is a sigil you drew, bound to an intent you wrote, running as a
background process. It keeps celestial hours, performs measurable labor,
records its own life in a tamper-evident ledger, and dissolves irrecoverably.

The library never composes a sigil or an intent. Those are yours.
"""

__version__ = "0.1.0"

from sigilry.naming import true_name, true_name_from_bytes
from sigilry.celestial import (
    sun_times,
    planetary_hour,
    day_ruler,
    moon_phase,
    PLANETS,
)
from sigilry.charge import perform_charge, verify_charge
from sigilry.ledger import Ledger
from sigilry.vessel import Vessel, VesselConfig, BindingRefused

__all__ = [
    "true_name",
    "true_name_from_bytes",
    "sun_times",
    "planetary_hour",
    "day_ruler",
    "moon_phase",
    "PLANETS",
    "perform_charge",
    "verify_charge",
    "Ledger",
    "Vessel",
    "VesselConfig",
    "BindingRefused",
    "__version__",
]
