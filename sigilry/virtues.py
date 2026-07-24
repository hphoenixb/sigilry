"""Virtues — what a sigil does when it is in force.

A virtue is not an entity and holds no office. It is the manner in which a
sigil acts: the inherent power the seal carries, in the older sense of the
*virtues* of an herb or a stone. The will is yours; the virtue is how it reaches.

    warding      closes what you have named, while the sigil is in force
    manifesting  puts the glyph in your sight and the intent into the air

A virtue takes effect when the sigil's conditions are met, and is withdrawn the
moment they are not — so a warding sigil bound to Mercury hours releases its
hold when the hour turns, without you doing anything.

Every virtue reports plainly what it did. Nothing is claimed that did not happen.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

WINDOWS = os.name == "nt"
MACOS = sys.platform == "darwin"


class UnknownVirtue(ValueError):
    """Raised when a virtue name is not one we implement."""


@dataclass
class Effect:
    """A plain record of what actually happened when a virtue took effect."""

    acted: bool
    detail: str
    data: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _run(cmd: List[str], timeout: float = 20.0) -> tuple[int, str]:
    """Run a command quietly. Returns (returncode, combined output)."""
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            text=True,
        )
        return proc.returncode, (proc.stdout or "").strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        return 1, str(e)


def _powershell(script: str, timeout: float = 20.0) -> tuple[int, str]:
    return _run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        timeout=timeout,
    )


def _normalise_process(name: str) -> str:
    """'chrome' -> 'chrome.exe' on Windows; left alone elsewhere."""
    name = name.strip()
    if WINDOWS and not name.lower().endswith(".exe"):
        return name + ".exe"
    return name


# ---------------------------------------------------------------------------
# warding — close what has been named
# ---------------------------------------------------------------------------

class Warding:
    """While the sigil is in force, the named programs are not permitted to run.

    Closing a program you own needs no administrator rights. Each pass closes
    whatever it finds; a program reopened during the sigil's hours is closed
    again on the next pass.
    """

    name = "warding"
    needs_targets = True
    target_label = "programs to close (e.g. chrome, discord, steam)"

    def __init__(self, targets: List[str], **_ignored):
        if not targets:
            raise UnknownVirtue(
                "Warding needs something to ward against. Use --against chrome "
                "--against discord, and so on."
            )
        self.targets = [_normalise_process(t) for t in targets]

    def take_effect(self) -> Effect:
        closed = []
        for target in self.targets:
            if WINDOWS:
                code, out = _run(["taskkill", "/IM", target, "/F", "/T"])
                # taskkill returns non-zero when the process simply isn't running
                if code == 0 and "SUCCESS" in out.upper():
                    closed.append(target)
            else:
                # -x matches the process name exactly. Never use -f here: it
                # matches whole command lines, which would let a ward kill the
                # very shell that invoked it.
                code, _ = _run(["pkill", "-x", target])
                if code == 0:
                    closed.append(target)
        if closed:
            return Effect(
                True,
                f"closed {', '.join(closed)}",
                {"closed": closed, "warded": self.targets},
            )
        return Effect(False, "nothing to close", {"warded": self.targets})

    def withdraw(self) -> Effect:
        # Warding holds nothing when it lapses; it simply stops closing things.
        return Effect(False, "hold released", {"warded": self.targets})


# ---------------------------------------------------------------------------
# manifesting — put the glyph in sight, the intent into the air
# ---------------------------------------------------------------------------

class Manifesting:
    """While the sigil is in force, the glyph is your wallpaper and — if you ask
    — the intent is spoken aloud when it comes into force.

    The previous wallpaper is remembered and restored when the sigil goes latent,
    so nothing is left changed behind your back.
    """

    name = "manifesting"
    needs_targets = False
    target_label = None

    def __init__(
        self,
        sigil_path: str,
        intent: str = "",
        speak: bool = False,
        wallpaper: bool = True,
        **_ignored,
    ):
        self.sigil_path = os.path.abspath(sigil_path)
        self.intent = intent
        self.speak = speak
        self.wallpaper = wallpaper
        self._previous_wallpaper: Optional[str] = None
        self._spoken_this_turn = False

    # -- wallpaper ---------------------------------------------------------

    def _current_wallpaper(self) -> Optional[str]:
        if WINDOWS:
            code, out = _powershell(
                "(Get-ItemProperty -Path 'HKCU:\\Control Panel\\Desktop' "
                "-Name WallPaper).WallPaper"
            )
            return out if code == 0 and out else None
        if MACOS:
            code, out = _run([
                "osascript", "-e",
                'tell application "System Events" to get picture of current desktop',
            ])
            return out if code == 0 and out else None
        return None

    def _set_wallpaper(self, path: str) -> bool:
        if WINDOWS:
            import ctypes
            SPI_SETDESKWALLPAPER = 20
            SPIF_UPDATEINIFILE = 0x01
            SPIF_SENDCHANGE = 0x02
            ok = ctypes.windll.user32.SystemParametersInfoW(
                SPI_SETDESKWALLPAPER, 0, str(path),
                SPIF_UPDATEINIFILE | SPIF_SENDCHANGE,
            )
            return bool(ok)
        if MACOS:
            code, _ = _run([
                "osascript", "-e",
                f'tell application "System Events" to set picture of '
                f'every desktop to "{path}"',
            ])
            return code == 0
        code, _ = _run(["gsettings", "set", "org.gnome.desktop.background",
                        "picture-uri", f"file://{path}"])
        return code == 0

    # -- speech ------------------------------------------------------------

    def _speak_intent(self) -> bool:
        if not self.intent:
            return False
        safe = self.intent.replace("'", "''")
        if WINDOWS:
            code, _ = _powershell(
                "Add-Type -AssemblyName System.Speech; "
                "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                f"$s.Speak('{safe}')",
                timeout=60,
            )
            return code == 0
        if MACOS:
            code, _ = _run(["say", self.intent], timeout=60)
            return code == 0
        code, _ = _run(["spd-say", self.intent], timeout=60)
        return code == 0

    # -- lifecycle ---------------------------------------------------------

    def take_effect(self) -> Effect:
        done = []
        data: Dict[str, Any] = {}

        if self.wallpaper and self._previous_wallpaper is None:
            if not os.path.exists(self.sigil_path):
                return Effect(False, f"sigil not found at {self.sigil_path}")
            self._previous_wallpaper = self._current_wallpaper() or ""
            if self._set_wallpaper(self.sigil_path):
                done.append("glyph set as wallpaper")
                data["wallpaper"] = self.sigil_path
                data["restored_to"] = self._previous_wallpaper

        if self.speak and not self._spoken_this_turn:
            if self._speak_intent():
                done.append("intent spoken")
                data["spoke"] = self.intent
            self._spoken_this_turn = True

        if done:
            return Effect(True, "; ".join(done), data)
        return Effect(False, "already manifest", data)

    def withdraw(self) -> Effect:
        self._spoken_this_turn = False
        if self._previous_wallpaper is not None:
            previous = self._previous_wallpaper
            self._previous_wallpaper = None
            if previous and os.path.exists(previous):
                if self._set_wallpaper(previous):
                    return Effect(True, "wallpaper restored",
                                  {"restored_to": previous})
            return Effect(True, "glyph withdrawn (no previous wallpaper to restore)")
        return Effect(False, "nothing to withdraw")


# ---------------------------------------------------------------------------
# registry
# ---------------------------------------------------------------------------

VIRTUES = {
    "warding": Warding,
    "manifesting": Manifesting,
}

# Named but not yet implemented — listed so the vocabulary is visible and the
# error message can be honest about it.
PLANNED = ["drawing", "sealing", "watching", "intoning", "divining"]


def validate(name: Optional[str], targets: Optional[List[str]] = None) -> None:
    """Raise UnknownVirtue if this virtue can't be carried as asked."""
    if name is None:
        return
    key = name.strip().lower()
    if key in PLANNED:
        raise UnknownVirtue(
            f"'{key}' is named but not yet built. Available now: "
            f"{', '.join(sorted(VIRTUES))}."
        )
    if key not in VIRTUES:
        raise UnknownVirtue(
            f"'{name}' is not a virtue I carry. Choose from: "
            f"{', '.join(sorted(VIRTUES))}."
        )
    cls = VIRTUES[key]
    if getattr(cls, "needs_targets", False) and not targets:
        raise UnknownVirtue(f"'{key}' needs targets: {cls.target_label}")


def make(
    name: Optional[str],
    targets: Optional[List[str]] = None,
    sigil_path: str = "",
    intent: str = "",
    speak: bool = False,
):
    """Build a virtue, or None if the sigil carries none."""
    if name is None:
        return None
    validate(name, targets)
    key = name.strip().lower()
    return VIRTUES[key](
        targets=targets or [],
        sigil_path=sigil_path,
        intent=intent,
        speak=speak,
    )
