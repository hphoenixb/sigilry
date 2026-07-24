"""Command line interface.

    sigil bind NAME --sigil FILE --intent "..." [terms]
    sigil raise NAME [--detach]
    sigil status [NAME]
    sigil renew NAME [--note "..."]
    sigil ledger NAME [--verify]
    sigil dissolve NAME
    sigil hours            # the current planetary hour and moon, standalone
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from sigilry import conditions as cond
from sigilry.celestial import PLANETS, moon_phase, planetary_hour, sun_times
from sigilry.ledger import Ledger
from sigilry.vessel import BindingRefused, Vessel, parse_duration

console = Console()

# Default location. Override per vessel with --lat/--lon, or set
# SIGILRY_LAT / SIGILRY_LON in your environment.
DEFAULT_LAT = float(os.environ.get("SIGILRY_LAT", "41.8781"))   # Chicago
DEFAULT_LON = float(os.environ.get("SIGILRY_LON", "-87.6298"))

PLANET_COLOR = {
    "Saturn": "grey62",
    "Jupiter": "gold3",
    "Mars": "red3",
    "Sun": "yellow1",
    "Venus": "green3",
    "Mercury": "cyan1",
    "Moon": "plum2",
}
STATE_COLOR = {
    "IN FORCE": "bright_green",
    "LATENT": "cyan",
    "FADING": "yellow",
    "SPENT": "grey62",
    "DISSOLVED": "red3",
}


def _fmt_delta(delta) -> str:
    if delta is None:
        return "—"
    total = int(delta.total_seconds())
    sign = "-" if total < 0 else ""
    total = abs(total)
    d, rem = divmod(total, 86400)
    h, rem = divmod(rem, 3600)
    m, _ = divmod(rem, 60)
    if d:
        return f"{sign}{d}d {h}h"
    if h:
        return f"{sign}{h}h {m}m"
    return f"{sign}{m}m"


def _planet(name) -> str:
    if not name:
        return "—"
    return f"[{PLANET_COLOR.get(name, 'white')}]{name}[/]"


def _explain_missing(name: str) -> str:
    """Distinguish 'never existed' from 'dissolved, ledger remains'."""
    ledger_path = os.path.join(Vessel.directory_for(name), "ledger.jsonl")
    if os.path.exists(ledger_path):
        led = Ledger(ledger_path)
        died = led.last_of_kind("dissolved")
        if died:
            d = died["data"]
            when = datetime.fromisoformat(died["at"]).astimezone().strftime("%b %d %H:%M")
            return (
                f"'{name}' is dissolved — {d['cause']} on {when}, after "
                f"{d['charges']:,} charges. It cannot be recalled.\n"
                f"  Its record remains:  [bold]sigil ledger {name}[/bold]"
            )
        return (
            f"'{name}' has a ledger but no living state. It may have been "
            f"partly dissolved.\n  Read it with:  [bold]sigil ledger {name}[/bold]"
        )
    return f"No vessel named '{name}'."


# ---------------------------------------------------------------- bind

def cmd_bind(args) -> int:
    try:
        vessel = Vessel.bind(
            name=args.name,
            intent=args.intent,
            sigil_path=args.sigil,
            lifespan=args.lifespan,
            latitude=args.lat,
            longitude=args.lon,
            difficulty=args.difficulty,
            ruler=args.ruler,
            labor_conditions=args.when or ["always"],
            renew_every=args.renew_every,
            virtue=args.virtue,
            virtue_targets=args.against,
            virtue_speak=args.speak,
            dissolution=args.dissolution,
        )
    except (BindingRefused, cond.UnknownCondition, ValueError) as e:
        console.print(f"[red]✗ {e}[/red]")
        return 1

    c = vessel.config
    born = vessel.ledger.last_of_kind("bound")["data"]["born_under"]
    body = (
        f"[bold]true name[/bold]  {c.sigil_name}\n"
        f"[bold]intent[/bold]     {c.intent}\n"
        f"[bold]ruler[/bold]      {c.ruler or '—'}\n"
        f"[bold]conditions[/bold] {', '.join(c.labor_conditions)}\n"
        f"[bold]difficulty[/bold] {c.difficulty}  "
        f"([dim]~{16 ** c.difficulty:,} hashes per charge[/dim])\n"
        f"[bold]lifespan[/bold]   {_fmt_delta(c.lifespan)}\n"
        f"[bold]renew[/bold]      "
        f"{('every ' + _fmt_delta(c.renew_every)) if c.renew_every else 'not required'}\n"
        f"[bold]virtue[/bold]     "
        f"{(c.virtue + (' against ' + ', '.join(c.virtue_targets) if c.virtue_targets else '')) if c.virtue else 'none — it charges only'}\n"
        f"[bold]dissolution[/bold] {c.dissolution}\n\n"
        f"[dim]born under the hour of {born['planetary_hour']} "
        f"(hour {born['hour_index']}), a {born['day_ruler']} day, "
        f"{born['moon']} at {born['illumination']:.0%} lit[/dim]"
    )
    console.print(Panel(body, title=f"bound · {c.name}", border_style="magenta"))
    console.print(f"\nRaise it with:  [bold]sigil raise {c.name}[/bold]")
    return 0


# ---------------------------------------------------------------- wake

def cmd_raise(args) -> int:
    try:
        vessel = Vessel.load(args.name)
    except FileNotFoundError:
        console.print(f"[red]✗ {_explain_missing(args.name)}[/red]")
        return 1
    if vessel.is_dissolved:
        console.print(f"[red]✗ {_explain_missing(args.name)}[/red]")
        return 1

    if args.detach:
        cmd = [sys.executable, "-m", "sigilry.cli", "raise", args.name]
        # Detaching differs by platform. On Windows there is no setsid(), so we
        # ask the OS for a genuinely detached, window-less process; otherwise the
        # vessel would die with the terminal that started it.
        spawn_kwargs = {}
        if os.name == "nt":
            # DETACHED_PROCESS gives the child no console of its own, so it
            # survives PowerShell closing. CREATE_NEW_PROCESS_GROUP keeps a
            # Ctrl-C in the parent terminal from reaching it.
            DETACHED_PROCESS = 0x00000008
            CREATE_NEW_PROCESS_GROUP = 0x00000200
            spawn_kwargs["creationflags"] = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        else:
            spawn_kwargs["start_new_session"] = True

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            **spawn_kwargs,
        )
        console.print(
            f"[magenta]○[/magenta] '{args.name}' is in force in the background "
            f"(pid {proc.pid})."
        )
        console.print(f"  Check on it with:  [bold]sigil status {args.name}[/bold]")
        return 0

    console.print(
        f"[magenta]○[/magenta] '{args.name}' wakes. "
        f"[dim]Ctrl-C to let it sleep without ending it.[/dim]\n"
    )

    def on_event(kind, payload):
        stamp = datetime.now().strftime("%H:%M:%S")
        if kind == "charge":
            d = payload["data"]
            console.print(
                f"  [dim]{stamp}[/dim] [green]charge[/green] "
                f"#{vessel.charges_completed} · {d['digest'][:16]}… · "
                f"{d['iterations']:,} attempts · under {d['under']['planetary_hour']}"
            )
        elif kind == "latent":
            console.print(
                f"  [dim]{stamp}[/dim] [cyan]resting[/cyan] "
                f"[dim]— awaiting: {', '.join(payload)}[/dim]"
            )
        elif kind == "fading":
            console.print(f"  [dim]{stamp}[/dim] [yellow]weakened — unattended[/yellow]")

    cause = vessel.run(
        poll_seconds=args.poll,
        max_seconds=args.for_seconds,
        on_event=on_event,
    )
    if cause == "suspended":
        console.print("\n[cyan]It is set down. Raise it again to continue.[/cyan]")
    else:
        console.print(f"\n[red3]It has ended — {cause}.[/red3] Its ledger remains.")
    return 0


# ---------------------------------------------------------------- status

def _status_one(vessel: Vessel) -> None:
    s = vessel.summary()
    state = s["state"]
    lines = [
        f"[bold]{s['name']}[/bold] · [dim]{s['short']}[/dim]",
        f"[italic]{s['intent']}[/italic]",
        "",
        f"state      [{STATE_COLOR.get(state,'white')}]{state}[/]",
        f"ruler      {_planet(s['ruler'])}",
        f"conditions {', '.join(s['conditions'])}",
        f"virtue     "
        + (
            f"{s['virtue']}"
            + (f" against {', '.join(s['virtue_targets'])}" if s['virtue_targets'] else "")
            if s['virtue'] else "none — charges only"
        ),
        f"now        hour of {_planet(s['hour_planet'])} "
        f"(hour {s['hour_index']}) · {s['moon']} {s['illumination']:.0%}",
        f"charges  {s['charges']:,} completed · {s['repetitions']:,} repetitions",
        f"age        {_fmt_delta(s['age'])}",
        f"remains    {_fmt_delta(s['remaining'])}",
    ]
    if s["last_renewed"]:
        lines.append(f"renewed    {_fmt_delta(datetime.now(timezone.utc) - s['last_renewed'])} ago")
    if s["next_labor"] and state == "LATENT":
        lines.append(
            f"next       labor at {s['next_labor'].astimezone().strftime('%a %H:%M')}"
        )
    if s["dead"]:
        lines.append("[red3]this vessel is dead[/red3]")
    console.print(
        Panel("\n".join(lines), border_style="magenta" if not s["dead"] else "red3")
    )


def cmd_status(args) -> int:
    if args.name:
        try:
            _status_one(Vessel.load(args.name))
        except FileNotFoundError:
            console.print(f"[red]✗ {_explain_missing(args.name)}[/red]")
            return 1
        return 0

    names = Vessel.all_names()
    if not names:
        console.print("[dim]No vessels bound. Start with:  sigil bind …[/dim]")
        return 0

    table = Table(box=box.SIMPLE_HEAVY, title="vessels", title_style="bold magenta")
    for col in ["Name", "Sigil", "State", "Hour", "Offerings", "Age", "Remains"]:
        table.add_column(col)
    for name in names:
        v = Vessel.load(name)
        s = v.summary()
        st = s["state"]
        table.add_row(
            s["name"],
            f"[dim]{s['short']}[/dim]",
            f"[{STATE_COLOR.get(st,'white')}]{st}[/]",
            _planet(s["hour_planet"]),
            f"{s['charges']:,}",
            _fmt_delta(s["age"]),
            _fmt_delta(s["remaining"]),
        )
    console.print(table)
    return 0


# ---------------------------------------------------------------- attend

def cmd_renew(args) -> int:
    try:
        vessel = Vessel.load(args.name)
        entry = vessel.renew(note=args.note)
    except FileNotFoundError:
        console.print(f"[red]✗ {_explain_missing(args.name)}[/red]")
        return 1
    except RuntimeError as e:
        console.print(f"[red]✗ {e}[/red]")
        return 1
    recovered = entry["data"].get("recovered")
    console.print(
        f"[magenta]○[/magenta] '{args.name}' renewed."
        + ("  [green]It recovers from weakening.[/green]" if recovered else "")
    )
    return 0


# ---------------------------------------------------------------- ledger

_KIND_STYLE = {
    "bound": "magenta",
    "exerted": "bright_magenta",
    "withdrawn": "plum4",
    "raised": "cyan",
    "charge": "green",
    "renewed": "blue",
    "fading": "yellow",
    "suspended": "grey62",
    "dissolved": "red3",
}


def cmd_ledger(args) -> int:
    directory = Vessel.directory_for(args.name)
    path = os.path.join(directory, "ledger.jsonl")
    if not os.path.exists(path):
        console.print(f"[red]✗ No ledger for '{args.name}'.[/red]")
        return 1
    ledger = Ledger(path)

    ok, problem = ledger.verify()
    if args.verify:
        if ok:
            console.print(
                f"[green]✓ The chain is intact — {len(ledger)} entries, "
                f"none altered.[/green]"
            )
        else:
            console.print(f"[red]✗ The chain is broken: {problem}[/red]")
        return 0 if ok else 1

    table = Table(box=box.SIMPLE, title=f"ledger · {args.name}", title_style="bold magenta")
    table.add_column("#", justify="right")
    table.add_column("When")
    table.add_column("Event")
    table.add_column("Detail")
    table.add_column("Seal")

    entries = ledger.entries
    if args.tail:
        entries = entries[-args.tail:]
    for e in entries:
        when = datetime.fromisoformat(e["at"]).astimezone().strftime("%m-%d %H:%M:%S")
        kind = e["kind"]
        d = e["data"]
        if kind == "charge":
            detail = f"{d['digest'][:20]}… · {d['iterations']:,} attempts"
        elif kind == "bound":
            b = d["born_under"]
            detail = f"{b['moon']}, hour of {b['planetary_hour']}"
        elif kind == "dissolved":
            detail = f"{d['cause']} · {d['charges']} charges"
        elif kind in ("exerted", "withdrawn"):
            detail = f"{d.get('virtue','')} · {d.get('detail','')}"
        elif kind == "renewed":
            detail = d.get("note") or "witnessed"
        else:
            detail = ", ".join(f"{k}={v}" for k, v in d.items()) or "—"
        table.add_row(
            str(e["seq"]),
            when,
            f"[{_KIND_STYLE.get(kind,'white')}]{kind}[/]",
            detail,
            f"[dim]{e['hash'][:8]}[/dim]",
        )
    console.print(table)
    console.print(
        f"[green]✓ chain intact[/green]" if ok else f"[red]✗ chain broken: {problem}[/red]"
    )
    return 0


# ---------------------------------------------------------------- banish

def cmd_dissolve(args) -> int:
    try:
        vessel = Vessel.load(args.name)
    except FileNotFoundError as e:
        console.print(f"[red]✗ {e}[/red]")
        return 1

    if not args.yes:
        console.print(
            Panel(
                f"[bold]{vessel.config.name}[/bold] · [dim]{vessel.short}[/dim]\n"
                f"[italic]{vessel.config.intent}[/italic]\n\n"
                f"{vessel.charges_completed:,} charges over "
                f"{_fmt_delta(vessel.age)}.\n\n"
                f"Dissolution is [bold]{vessel.config.dissolution}[/bold]. "
                f"The sigil and its state will be overwritten and destroyed.\n"
                f"The ledger will remain as the record.",
                title="banish?",
                border_style="red3",
            )
        )
        reply = input("Type the vessel's name to confirm: ").strip()
        if reply != vessel.config.name:
            console.print("[cyan]Left alive.[/cyan]")
            return 1

    vessel.dissolve_now()
    console.print(
        f"[red3]○[/red3] '{args.name}' is dissolved. "
        f"Its ledger remains at [dim]{vessel.ledger.path}[/dim]"
    )
    return 0


# ---------------------------------------------------------------- hours

def cmd_hours(args) -> int:
    now = datetime.now(timezone.utc)
    ph = planetary_hour(now, args.lat, args.lon)
    moon = moon_phase(now)
    sr, ss = sun_times(now, args.lat, args.lon)

    if ph is None:
        console.print("[yellow]The sun does not rise or set here today.[/yellow]")
        return 0

    body = (
        f"[bold]hour[/bold]     of {_planet(ph.planet)} — "
        f"{'day' if ph.is_day_hour else 'night'} hour {ph.index} of 24\n"
        f"[bold]ends[/bold]     in {_fmt_delta(ph.remaining)}\n"
        f"[bold]day[/bold]      ruled by {_planet(ph.ruler_of_day)}\n"
        f"[bold]sun[/bold]      rises {sr.astimezone().strftime('%H:%M')}, "
        f"sets {ss.astimezone().strftime('%H:%M')}\n"
        f"[bold]moon[/bold]     {moon.name}, {moon.illumination:.0%} lit, "
        f"{'waxing' if moon.waxing else 'waning'} "
        f"[dim](day {moon.age_days:.1f} of {29.53:.1f})[/dim]"
    )
    console.print(Panel(body, title="the present hour", border_style="magenta"))
    return 0


# ---------------------------------------------------------------- parser

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="sigil",
        description="Invest a sigil you drew with a virtue, and set it in force.",
    )
    p.add_argument("--lat", type=float, default=DEFAULT_LAT, help="latitude")
    p.add_argument("--lon", type=float, default=DEFAULT_LON, help="longitude")
    sub = p.add_subparsers(dest="command", required=True)

    b = sub.add_parser("bind", help="bind a sigil, investing it with a virtue")
    b.add_argument("name")
    b.add_argument("--sigil", required=True, help="path to the sigil you drew")
    b.add_argument("--intent", required=True, help="your statement of intent")
    b.add_argument("--lifespan", required=True, help="e.g. 28d, 12h, 4w")
    b.add_argument("--difficulty", type=int, default=5, help="charge difficulty, 1-8")
    b.add_argument("--ruler", default=None, help=f"ruling planet: {', '.join(PLANETS)}")
    b.add_argument(
        "--when", action="append", default=None,
        help="a labor condition; repeat for several (all must hold). "
             "e.g. --when hour:ruler --when moon:waxing",
    )
    b.add_argument("--renew-every", default=None, help="require your renewal this often, e.g. 3d")
    b.add_argument(
        "--virtue", default=None,
        help="what the sigil does while in force: warding, manifesting",
    )
    b.add_argument(
        "--against", action="append", default=None,
        help="for warding: a program to close; repeat for several "
             "(e.g. --against chrome --against discord)",
    )
    b.add_argument(
        "--speak", action="store_true",
        help="for manifesting: speak the intent aloud when it comes into force",
    )
    b.add_argument(
        "--dissolution", choices=["erase", "release"], default="erase",
        help="erase = overwrite and destroy; release = delete, keep ledger",
    )
    b.set_defaults(func=cmd_bind)

    w = sub.add_parser("raise", help="bring the sigil into force")
    w.add_argument("name")
    w.add_argument("--detach", action="store_true", help="run in the background")
    w.add_argument("--poll", type=float, default=5.0, help="seconds between condition checks")
    w.add_argument(
        "--for-seconds", type=float, default=None, dest="for_seconds",
        help="run only this long, then sleep (for testing)",
    )
    w.set_defaults(func=cmd_raise)

    s = sub.add_parser("status", help="see your vessels")
    s.add_argument("name", nargs="?")
    s.set_defaults(func=cmd_status)

    a = sub.add_parser("renew", help="renew your will in a sigil")
    a.add_argument("name")
    a.add_argument("--note", default=None)
    a.set_defaults(func=cmd_renew)

    l = sub.add_parser("ledger", help="read a vessel's life record")
    l.add_argument("name")
    l.add_argument("--verify", action="store_true", help="check the chain only")
    l.add_argument("--tail", type=int, default=None, help="show only the last N entries")
    l.set_defaults(func=cmd_ledger)

    x = sub.add_parser("dissolve", help="dissolve a sigil early")
    x.add_argument("name")
    x.add_argument("--yes", action="store_true", help="skip confirmation")
    x.set_defaults(func=cmd_dissolve)

    h = sub.add_parser("hours", help="the current planetary hour and moon")
    h.set_defaults(func=cmd_hours)

    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
