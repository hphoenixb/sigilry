# sigilry

**Invest a sigil you drew with a virtue, and set it in force.**

You draw a sigil. You invest it with a **virtue** — what it does. You set the conditions under which it is **in force**. It then acts on your machine, on its own, during exactly those conditions, keeping celestial hours and a sealed record of everything it actually did.

A sigil here is not a creature and holds no office. It is your own will given a form to act through — the power is yours, the virtue is how it reaches. In the older sense of the word, a *virtue* is the inherent power of a thing, as an herb or a stone has virtues.

`sigilry` never composes a sigil and never writes an intent. It cannot. Those are yours; it only carries them.

## Virtues

| virtue | what the sigil does |
|---|---|
| **warding** | closes the programs you name, while it is in force |
| **manifesting** | sets your wallpaper to your glyph; optionally speaks your intent aloud |

Withdrawn automatically the moment conditions lapse — a warding sigil bound to
Mercury hours releases its hold when the hour turns, and manifesting restores
your previous wallpaper. Nothing is left changed behind your back.

Named and planned: `drawing`, `sealing`, `watching`, `intoning`, `divining`.
Asking for one says plainly that it isn't built yet.

```
$ sigil hours
╭──────────────────── the present hour ─────────────────────╮
│ hour     of Moon — day hour 10 of 24                      │
│ ends     in 12m                                           │
│ day      ruled by Venus                                   │
│ sun      rises 05:36, sets 20:17                          │
│ moon     waxing gibbous, 78% lit, waxing (day 10.2 of 29.5)│
╰───────────────────────────────────────────────────────────╯
```

## Why the vocabulary matters

Deliberately impersonal. A sigil is **in force** or **latent**, never "working" or "resting"; it accumulates **charges**, not offerings; **you renew** your will in it rather than feeding it. It is a vehicle, not an entity — the grammar should not smuggle in a servant.

## What it actually does

Charging by repetition is limited by the body — you can only hold attention so long. A process has no such limit. It does not tire, does not lose focus, does not forget on day nine. What `sigilry` adds to a working is **persistence and proof**: labor that continues while you sleep, timed to the hours your tradition asks for, recorded in a form that cannot be falsified after the fact.

It does not reach into the world and cause an outcome. It holds a working and sustains it. The will is yours.

## Install

```bash
git clone https://github.com/<you>/sigilry.git
cd sigilry
pip install -e .
```

Runs on Windows, macOS and Linux. **New to the command line, or on Windows?**
[**WINDOWS.md**](WINDOWS.md) is a complete step-by-step walkthrough that assumes
no prior experience whatsoever.

## A working, start to finish

**Draw your sigil** in whatever tool you like, and save it. This part stays entirely yours.

**Bind it.** The drawing is hashed into a *true name* — an identity derived from the exact bytes your hand produced. Redraw the same glyph and you get a different name; the name belongs to that one act of making.

```bash
sigil bind arrival \
  --sigil arrival.png \
  --intent "IT IS MY WILL TO ARRIVE WHOLE" \
  --ruler mercury \
  --when hour:ruler --when moon:waxing \
  --lifespan 28d \
  --difficulty 5 \
  --attend-every 3d
```

```
╭──────────────────────── bound · arrival ─────────────────────────╮
│ true name  1f7c49425222a81a957b9b610a840bdca63aac63183fecda52…   │
│ intent     IT IS MY WILL TO ARRIVE WHOLE                         │
│ ruler      Mercury                                               │
│ labors     hour:ruler, moon:waxing                               │
│ difficulty 5  (~1,048,576 hashes per charge)                    │
│ lifespan   28d 0h                                                │
│ attend     every 3d 0h                                           │
│ dissolution erase                                                │
│                                                                  │
│ born under the hour of Moon (hour 10), a Venus day,              │
│ waxing gibbous at 78% lit                                        │
╰──────────────────────────────────────────────────────────────────╯
```

Leave out the intent, the sigil, the lifespan, or the means of dissolution and it **refuses to bind**. The terms of a working are part of the working.

**Wake it.** It detaches into the background and keeps its own hours.

```bash
sigil raise arrival --detach
```

```
  15:39:00 charge #1 · 00003c3f47b46e04… · 11,892 attempts · under Mercury
  15:39:01 charge #2 · 0000d7f99bc03a14… · 33,304 attempts · under Mercury
  15:41:20 resting — awaiting: hour:ruler
```

**Check on it.**

```bash
sigil status arrival
```

```
╭──────────────────────────────────────────────────────╮
│ arrival · 1f7c4942                                   │
│ IT IS MY WILL TO ARRIVE WHOLE                        │
│                                                      │
│ state      LATENT                                   │
│ ruler      Mercury                                   │
│ labors     hour:ruler, moon:waxing                   │
│ now        hour of Moon (hour 10) · waxing gibbous 78%│
│ charges  19 completed · 1,419,396 repetitions      │
│ age        3d 4h                                     │
│ remains    24d 19h                                   │
│ attended   2d 1h ago                                 │
│ next       labor at Sat 03:12                        │
╰──────────────────────────────────────────────────────╯
```

**Attend it.** If you set `--attend-every`, your witness is part of the mechanism: neglect it past that interval and it weakens; neglect it for twice the interval and it dies.

```bash
sigil renew arrival --note "before the move"
```

**Read its life.**

```bash
sigil ledger arrival --tail 4
```

```
   #   When             Event      Detail                                   Seal
  20   07-24 15:39:02   charge   0000eca75ec73d728615… · 1,820 attempts   9d29fd5f
  21   07-24 15:39:02   attended   before the move                          bd5b7e8d
  22   07-24 15:39:21   died       banished · 19 charges                  80b063d0
✓ chain intact
```

**End it.** Either it dies on its own when its lifespan is spent, or you end it early.

```bash
sigil dissolve arrival
```

The sigil copy and the vessel's state are overwritten with random bytes and destroyed. The ledger survives as the record of the working. Nothing can call it back:

```
✗ 'arrival' is dissolved — banished on Jul 24 15:39, after 19 charges.
  It cannot be recalled.
```

## Conditions

A vessel labors only while **every** one of its conditions holds, and rests otherwise. Repeat `--when` to require several. An unrecognized condition is rejected at binding time rather than silently ignored, so a working never runs on a rule the machine didn't understand.

| Condition | Meaning |
|---|---|
| `always` | no restriction |
| `hour:mercury` | during a planetary hour ruled by that planet |
| `hour:ruler` | during an hour ruled by the vessel's own ruler |
| `day-hours` / `night-hours` | between sunrise and sunset, or the reverse |
| `day:friday` | on a given weekday |
| `day-ruler:venus` | on a day ruled by a given planet |
| `moon:waxing` / `moon:waning` | by the direction of the cycle |
| `moon:full` / `moon:dark` | within ~1.8 days of the exact phase |
| `illumination>0.75` | by how lit the moon is (`>`, `<`, `>=`, `<=`) |
| `clock:22:00-02:00` | a wall-clock window, wrapping midnight |

## How the pieces work

**Planetary hours.** Daylight is divided into twelve equal parts and darkness into twelve more, so the hours are *unequal* — a summer day-hour is longer than a winter one. The first hour begins at sunrise and belongs to the planet ruling that weekday; the rest follow the Chaldean order (Saturn, Jupiter, Mars, Sun, Venus, Mercury, Moon), wrapping forever. Sunrise and sunset are computed from your latitude and longitude with the standard NOAA solar-position algorithm — no network, no API key.

**Offerings** are proof-of-work. The vessel searches for a number which, hashed with its true name and intent, yields a digest beginning with a required run of zeros. There is no shortcut; the only way through is to try. Each extra zero multiplies the expected effort sixteenfold, so difficulty sets the depth of the charge. This is the mechanism that secures Bitcoin, used here for a different end: the labor is real, it costs real time and electricity, and anyone can verify afterwards that it was genuinely performed. **An charge that was claimed but not made will not verify.**

**The ledger** is append-only, and every entry carries the hash of the one before it while its own hash covers that link. The entries form a chain: alter anything in the past and its hash changes, which breaks every link after it. You can destroy a ledger, but you cannot edit one and have it still verify — not even you. Git's commit history and blockchains use the same structure.

**Dissolution** overwrites a file's contents with random bytes, flushes to the device, truncates, and only then unlinks it. Ordinary deletion just removes the index entry and leaves the bytes lying on the disk, which is a poor banishing.

> On copy-on-write and flash filesystems (APFS, SSDs with wear levelling) the drive may write to fresh physical blocks rather than the originals, so overwriting is a deliberate and genuine destruction rather than an absolute hardware guarantee.

## Your location

Planetary hours depend on where you are. Set it per command with `--lat` / `--lon`, or once in your environment:

```bash
export SIGILRY_LAT=41.8781
export SIGILRY_LON=-87.6298
```

Vessels are stored under `~/.sigilry/` — override with `SIGILRY_ROOT`. Nothing is ever sent anywhere; there is no account and no server.

## Development

```bash
pip install -e ".[dev]"
pytest
```

121 tests. The celestial math is checked against known real-world values — solstice sunrise and sunset for Chicago to the minute, four known new and full moons, and the classical rule that the first planetary hour of each weekday belongs to that day's ruler. The ledger tests confirm that tampering with or deleting a past entry is detected, and the charge tests confirm that a claimed-but-unperformed charge fails verification.

## Layout

```
sigilry/
├── sigilry/
│   ├── celestial.py    # sunrise/sunset, planetary hours, moon phase
│   ├── naming.py       # true names from the drawing's bytes
│   ├── charge.py     # proof-of-work and its verification
│   ├── conditions.py   # the condition vocabulary and evaluation
│   ├── ledger.py       # hash-chained, append-only life record
│   ├── erasure.py      # overwrite-then-delete dissolution
│   ├── virtues.py      # warding, manifesting — what a sigil does in force
│   ├── vessel.py       # binding, the loop, renewal, dissolution
│   └── cli.py          # the sigil command
└── tests/
```

## A note on what this is

This is a tool for a practice, built to serve it rather than to simulate it. It makes no claims about outcomes. What it can honestly promise is that the labor is real, the timing is correct, the record is honest, and the dissolution is thorough — and that every sigil it carries was drawn by your own hand.

## License

MIT — see [LICENSE](LICENSE).
