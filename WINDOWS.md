# sigilry on Windows — complete walkthrough

Written for an HP Windows laptop and for someone who has never used a command
line. Nothing is assumed and nothing is left out. Keep this open beside your
PowerShell window.

---

## What this is

You draw a sigil. You invest it with a **virtue** — what it does. You set the
conditions under which it is **in force**. It then acts on your computer, on its
own, during exactly those conditions, and keeps a sealed record of everything it
actually did.

The sigil is not a creature and does not work *for* you. It is your own will
given a form to act through. The power is yours; the virtue is how it reaches.

**Virtues available now:**

| virtue | what the sigil does |
|---|---|
| **warding** | closes the programs you name, while it is in force |
| **manifesting** | sets your wallpaper to your glyph, and can speak your intent aloud |

**Named and coming:** drawing, sealing, watching, intoning, divining. Asking for
one of these tells you plainly that it isn't built yet rather than pretending.

---

## The three words, untangled

| Word | What it actually is |
|---|---|
| **PowerShell** | An app on Windows. A window where you type commands instead of clicking. This is "the command line" / "the terminal". |
| **Python** | The language sigilry is written in. You install it in step 1. |
| **Git** | A *separate* tool for pushing code to GitHub. **Not needed to use sigilry at all.** Only for publishing the project. |

PowerShell is the room. Python, git and `sigil` are different tools you use in it.

> **One Windows quirk, upfront:** PowerShell continues a long command with a
> **backtick** (`` ` ``), not a backslash (`\`). Backslashes will error. So every
> long command below is written as **one single line** — let it wrap on screen.

---

# PART 1 — Setup (once)

## Step 1 — Install Python

1. Go to **https://www.python.org/downloads/**
2. Click the big yellow **Download Python** button.
3. Open the downloaded file to start the installer.

> ### ⚠ THE ONE THING YOU MUST NOT SKIP
> On the **first screen** of the installer, at the **bottom**, there is a
> checkbox: **"Add python.exe to PATH"**.
>
> **Tick it before clicking Install.**
>
> If you miss it, PowerShell cannot find Python and nothing else in this guide
> will work. Already installed without it? Re-run the installer, choose
> **Modify**, click Next, and make sure that box is ticked.

4. Click **Install Now** and wait for it to finish.
5. Click **Close**.

*(Don't install Python from the Microsoft Store — its sandboxing causes odd
problems with installed commands.)*

## Step 2 — Open PowerShell

Press the **Windows key**, type `powershell`, press **Enter**.

A window opens with a line ending in `>`. That's the **prompt** — it's waiting.
You type a command, press Enter, it runs.

*(Windows 11 may open "Windows Terminal" instead. Either works; Terminal draws
the boxes and colours more cleanly.)*

## Step 3 — Check Python is found

Type this and press Enter:

```powershell
python --version
```

**Expected:** `Python 3.13.x` — any 3.9 or higher is fine.

**If you get an error, or the Microsoft Store opens:** PATH wasn't set. Go back
to Step 1, re-run the installer, choose **Modify**, tick **"Add python.exe to
PATH"**. Then **close PowerShell, open it again**, and retry.

## Step 4 — Unzip the project

1. Open **File Explorer** and go to **Downloads**.
2. Right-click `sigilry-project.zip` → **Extract All…** → **Extract**.
3. Open the folder that appears. Inside is another folder named **`sigilry`** —
   the one containing `README.md` and `pyproject.toml`. **That** is the project.
4. Drag that `sigilry` folder into your **Documents** folder.

## Step 5 — Move PowerShell into that folder

`cd` means "change directory" — it tells PowerShell which folder to work in.

Type `cd` and a space. **Do not press Enter yet:**

```powershell
cd 
```

Now **drag the `sigilry` folder from File Explorer into the PowerShell window.**
The full path types itself in. **Now** press Enter.

> Remember this trick. Any time a command needs a file or folder path, type the
> flag and then drag the item in. It's exact every time.

Confirm you're in the right place:

```powershell
ls
```

You should see `README.md`, `WINDOWS.md`, `pyproject.toml`, `sigilry`, `tests`.

## Step 6 — Install it

```powershell
pip install -e .
```

Lots of text scrolls past — normal. This registers `sigil` as a command.

If `pip` isn't recognised, use this instead (identical result):

```powershell
python -m pip install -e .
```

## Step 7 — Tell it where you are

Planetary hours are built from your local sunrise and sunset, so it needs your
coordinates. **Chicago:**

```powershell
$env:SIGILRY_LAT = "41.8781"
$env:SIGILRY_LON = "-87.6298"
```

*(Other cities: search "latitude longitude <city>". West longitude and southern
latitude are negative numbers.)*

**That only lasts while this window is open.** To set it permanently, run these
two lines **once**:

```powershell
[Environment]::SetEnvironmentVariable("SIGILRY_LAT", "41.8781", "User")
[Environment]::SetEnvironmentVariable("SIGILRY_LON", "-87.6298", "User")
```

Then close and reopen PowerShell. Every new window will know where you are.

## Step 8 — First command

```powershell
sigil hours
```

```
╭──────────────────── the present hour ─────────────────────╮
│ hour     of Moon — day hour 10 of 24                      │
│ ends     in 12m                                           │
│ day      ruled by Venus                                   │
│ sun      rises 05:36, sets 20:17                          │
│ moon     waxing gibbous, 78% lit, waxing                  │
╰───────────────────────────────────────────────────────────╯
```

**Setup is complete.** If it says `sigil : The term 'sigil' is not
recognized`, jump to Troubleshooting — there's a fallback that always works.

---

# PART 2 — Draw your sigil

1. Open the **sigil companion** HTML file in your browser (double-click it).
2. Type your statement of intent, e.g. `IT IS MY WILL TO STUDY UNDISTURBED`.
3. Click **Distill letters** — vowels and repeats are stripped, leaving your
   working letters as reference.
4. Draw your glyph on the canvas. This is yours; nothing draws it for you.
5. Click **Save sigil**.

It saves to **Downloads** as something like `sigil-2026-07-24.png`.
**Rename it** to something you'll recognise — `study.png`.

---

# PART 3 — A test run first (2 minutes)

Before committing to a 28-day working, watch one act so you understand what
you're looking at. This one closes **Notepad**, which is harmless and obvious.

**Open Notepad now** (Windows key → type `notepad` → Enter). Leave it open.

Back in PowerShell, **all on one line:**

```powershell
sigil bind test --sigil "$HOME\Downloads\study.png" --intent "A TEST OF THE WORKING" --when always --lifespan 1h --difficulty 3 --virtue warding --against notepad
```

`$HOME` means `C:\Users\<your name>`, so `$HOME\Downloads\study.png` is your
Downloads folder. Or type `--sigil ` and drag the PNG in.

Now set it in force, in front of you:

```powershell
sigil raise test
```

**Watch Notepad close by itself.** You'll see:

```
○ 'test' is raised. Ctrl-C to set it down without ending it.

  16:46:50 in force warding — closed notepad.exe
  16:46:50 charge #1 · 0000b2bd936c0f1f… · 2,097 attempts · under Saturn
  16:46:51 charge #2 · 000e2579eb19eabe… · 1,467 attempts · under Saturn
```

Try opening Notepad again — it closes again within a couple of seconds. That's
the ward holding.

Press **Ctrl + C** to stop watching. Then clear it away:

```powershell
sigil dissolve test --yes
```

---

# PART 4 — The real workings

## Warding — for study

Closes your distractions during Mercury hours (Mercury governs study, memory
and language — including your Korean).

**One line:**

```powershell
sigil bind study --sigil "$HOME\Downloads\study.png" --intent "IT IS MY WILL TO STUDY UNDISTURBED" --ruler mercury --when hour:ruler --lifespan 28d --difficulty 5 --virtue warding --against chrome --against discord --against steam --renew-every 3d
```

Then:

```powershell
sigil raise study --detach
```

`--detach` sends it fully into the background. You can close PowerShell; it
keeps running.

## Manifesting — for confidence

Sets your wallpaper to your glyph during hours of the Sun (the Sun governs
confidence, vitality and recognition), and restores your old wallpaper when the
hour turns.

Draw a second sigil for this intent, save it as `confidence.png`, then **one
line:**

```powershell
sigil bind confidence --sigil "$HOME\Downloads\confidence.png" --intent "IT IS MY WILL TO MOVE THROUGH THE WORLD WITH CONFIDENCE" --ruler sun --when hour:ruler --lifespan 28d --difficulty 5 --virtue manifesting --speak --renew-every 3d
```

```powershell
sigil raise confidence --detach
```

`--speak` also reads your intent aloud through your speakers each time it comes
into force. Leave `--speak` off if you'd rather it be silent.

---

# PART 5 — Living with it

## See everything

```powershell
sigil status
```

## See one in detail

```powershell
sigil status study
```

```
╭────────────────────────────────────────────────────────╮
│ study · d42036e5                                       │
│ IT IS MY WILL TO STUDY UNDISTURBED                     │
│                                                        │
│ state      IN FORCE                                    │
│ ruler      Mercury                                     │
│ conditions hour:ruler                                  │
│ virtue     warding against chrome, discord, steam      │
│ now        hour of Mercury (hour 3) · waxing gibbous 78%│
│ charges    412 completed · 1,419,396 repetitions       │
│ age        3d 4h                                       │
│ remains    24d 19h                                     │
│ renewed    2d 1h ago                                   │
╰────────────────────────────────────────────────────────╯
```

**States:**

| State | Meaning |
|---|---|
| **IN FORCE** | conditions are met — the virtue is acting right now |
| **LATENT** | conditions are not met — waiting, nothing acting |
| **FADING** | you haven't renewed it within your interval |
| **SPENT** | its term has run out |
| **DISSOLVED** | ended and erased |

## Renew your will in it

```powershell
sigil renew study --note "midterms week"
```

The note is optional. Miss your interval and it **fades**; miss twice the
interval and it **ends**. The dependency runs on you, not on any appetite of
its own.

## Read its record

```powershell
sigil ledger study
sigil ledger study --tail 10
sigil ledger study --verify
```

```
  #   When             Event     Detail                                   Seal
  2   07-24 16:46:50   exerted   warding · closed chrome.exe              41e7f18e
  3   07-24 16:46:50   charge    0000b2bd936c0f1f945c… · 2,097 attempts   f610d4a9
✓ chain intact
```

Every entry is sealed with a hash of the entry before it. Alter anything in the
past and the chain breaks — `--verify` will say so. You can destroy the record,
but you cannot edit it and have it still verify. Not even you.

## End it

It ends by itself after 28 days. To end it early:

```powershell
sigil dissolve study
```

It asks you to type the name to confirm. The virtue is withdrawn first — your
wallpaper is put back, wards release — then the sigil copy and its state are
**overwritten with random bytes** and destroyed. The ledger survives as the
record. Nothing can recall it:

```
✗ 'study' is dissolved — dissolved on Jul 24 16:52, after 412 charges.
  It cannot be recalled.
```

---

# Planetary correspondences

For choosing `--ruler`. Traditional Western attributions.

| Planet | Domain | Uses |
|---|---|---|
| **Sun** | vitality, success, recognition, self-possession | confidence, presence, being seen |
| **Moon** | intuition, dreams, cycles, emotion | dreamwork, inner clarity |
| **Mars** | courage, drive, conflict, energy | pushing through, discipline under pressure |
| **Mercury** | language, memory, communication, travel | study, exams, Korean, writing |
| **Jupiter** | expansion, opportunity, abundance | "everything comes to me", luck, growth |
| **Venus** | attraction, harmony, art, relationships | connection, creative work |
| **Saturn** | boundaries, endurance, structure, banishing | long discipline, warding, cutting off |

The planet ruling each weekday: Sunday–Sun, Monday–Moon, Tuesday–Mars,
Wednesday–Mercury, Thursday–Jupiter, Friday–Venus, Saturday–Saturn.

---

# Conditions reference

Repeat `--when` to require several. **All** must hold for it to be in force.

```powershell
--when hour:ruler --when moon:waxing
```

| Condition | Meaning |
|---|---|
| `always` | no restriction |
| `hour:ruler` | during an hour ruled by this sigil's own planet |
| `hour:mercury` | during an hour ruled by a named planet |
| `day-hours` | between sunrise and sunset |
| `night-hours` | between sunset and sunrise |
| `day:friday` | on a given weekday |
| `day-ruler:venus` | on a day ruled by a given planet |
| `moon:waxing` | while the moon is growing |
| `moon:waning` | while the moon is shrinking |
| `moon:full` | within ~1.8 days of full |
| `moon:dark` | within ~1.8 days of new |
| `illumination>0.75` | moon at least this lit (`>`, `<`, `>=`, `<=`) |
| `clock:22:00-02:00` | a wall-clock window (wraps midnight correctly) |

An unrecognised condition is **refused at binding time** rather than silently
ignored — a working never runs on a rule the machine didn't understand.

Narrow conditions mean long waits. `hour:ruler` plus `moon:waxing` is in force
maybe two hours a day, half the month. Expect to see **LATENT** most times you
look. That may be exactly right.

---

# How planetary hours actually work

Daylight is divided into twelve equal parts, and darkness into twelve more — so
the hours are **unequal**. A summer day-hour is longer than a winter one. The
first hour begins at **sunrise** and belongs to the planet ruling that weekday;
the rest follow the Chaldean order — Saturn, Jupiter, Mars, Sun, Venus, Mercury,
Moon — wrapping around forever.

Sunrise and sunset are computed from your latitude and longitude using the
standard NOAA solar-position algorithm. No network, no API key, no account.

---

# Difficulty guide

A **charge** is proof-of-work: the sigil searches for a number that, hashed with
its true name and intent, gives a result starting with a run of zeros. There's no
shortcut — the only way is to try. So the labor is real, it costs real time and
electricity, and anyone can verify afterwards that it was genuinely performed.
A charge that was claimed but never made will not verify.

Measured at roughly 120,000 hashes per second on a typical laptop.

| Difficulty | Hashes per charge | Roughly |
|---|---|---|
| 3 | ~4,000 | instant |
| 4 | ~65,000 | under a second |
| **5** | ~1 million | ~10 seconds — **good default** |
| 6 | ~17 million | ~2 minutes |
| 7 | ~270 million | ~40 minutes |
| 8 | ~4.3 billion | ~10 hours |

Higher means a heavier charge and a warmer, more battery-hungry laptop. Start
at 5.

---

# Command cheat-sheet

```powershell
sigil hours                                  # current planetary hour + moon
sigil bind NAME --sigil … --intent … --lifespan … --virtue …
sigil raise NAME --detach                    # set in force, in the background
sigil status                                 # all sigils
sigil status NAME                            # one, in detail
sigil renew NAME --note "…"                  # renew your will
sigil ledger NAME                            # read the record
sigil ledger NAME --verify                   # confirm nothing was altered
sigil dissolve NAME                          # end it early
```

**All bind options:**

| Flag | Meaning |
|---|---|
| `--sigil PATH` | your drawing (required) |
| `--intent "…"` | your words (required) |
| `--lifespan 28d` | how long it lives — `30m`, `12h`, `28d`, `4w` (required) |
| `--virtue warding` | what it does — `warding` or `manifesting` |
| `--against chrome` | for warding: a program to close. Repeat for several. |
| `--speak` | for manifesting: also speak the intent aloud |
| `--ruler sun` | its ruling planet |
| `--when hour:ruler` | a condition. Repeat for several; all must hold. |
| `--difficulty 5` | weight of each charge, 1–8 |
| `--renew-every 3d` | how often it needs your renewal |
| `--dissolution erase` | `erase` (overwrite and destroy) or `release` (delete) |
| `--lat` / `--lon` | override your location for this command |

---

# Troubleshooting

**`sigil : The term 'sigil' is not recognized...`**
Two fixes. First, **close PowerShell and open a new window** — new windows pick
up newly installed commands. If that fails, `cd` into the sigilry folder and use
this equivalent form, which always works:

```powershell
python -m sigilry.cli hours
```

Everything works the same way: `python -m sigilry.cli status`,
`python -m sigilry.cli bind …`, and so on.

**`python` opens the Microsoft Store instead of running**
Python isn't properly installed. Re-run the python.org installer → **Modify** →
tick **"Add python.exe to PATH"**.

**`pip : The term 'pip' is not recognized`**
Use `python -m pip install -e .`

**`The system cannot find the path specified` for the sigil**
The path is wrong. Type `--sigil ` then **drag the PNG file into PowerShell**.

**My long command errored with something about `\`**
PowerShell doesn't use `\` for line continuation — that's Mac/Linux. Put the
whole command on one line.

**The boxes and lines look like garbage characters**
You're in the old `cmd.exe`. Use PowerShell, or install **Windows Terminal**
from the Microsoft Store.

**It says LATENT every time I check**
Working as designed if your conditions are narrow. `sigil status NAME` shows a
`next` line with when it comes back into force. To watch one act right now, bind
a test with `--when always`.

**Warding isn't closing something**
Check the process name in **Task Manager** (Ctrl+Shift+Esc) → **Details** tab →
the **Name** column. Use exactly that name without `.exe` — e.g. `msedge`,
`chrome`, `Discord`. Some programs relaunch themselves; the ward closes them
again on its next pass, every few seconds.

**Warding can't close something even so**
A few programs run with higher privileges than your user. Right-click PowerShell
→ **Run as Administrator**, then raise the sigil from there.

**My wallpaper didn't change**
Manifesting needs the PNG to still exist where it was bound from, and Windows
sometimes refuses very large images. If it fails, `sigil ledger NAME` will show
what happened instead of pretending it worked.

**Charges stopped overnight**
When the laptop sleeps, the process pauses and resumes when you open the lid.
Expected.

**`Refused: a vessel cannot be bound without …`**
That's the safeguard. Supply the missing term — intent, sigil, lifespan or
dissolution.

**`'drawing' is named but not yet built`**
Honest message: that virtue is planned, not implemented. Use `warding` or
`manifesting`.

**I want to wipe everything and start over**
Delete the folder `C:\Users\<your name>\.sigilry`. To see it in File Explorer,
turn on **View → Show → Hidden items**.

---

# Where things live

| What | Where |
|---|---|
| The program | `Documents\sigilry` (wherever you unzipped) |
| Your sigils | `C:\Users\<you>\.sigilry\vessels\<name>\` |
| Their records | `C:\Users\<you>\.sigilry\vessels\<name>\ledger.jsonl` |

Nothing is ever sent anywhere. No account, no server, no network access.

---

# Publishing to GitHub (optional, separate)

Nothing to do with running the tool.

**Website — easiest, no git needed.** github.com → **+** (top right) → **New
repository** → name it `sigilry`, choose **Private** → **Create repository**.
Then **Add file** → **Upload files**, drag the project files in, scroll down,
**Commit changes**. You are the only contributor.

**With git.** The project already contains a full history — 12 commits, all in
your name. Install git from **https://git-scm.com/download/win**, then:

```powershell
cd $HOME\Documents\sigilry
git remote add origin https://github.com/<your-username>/sigilry.git
git push -u origin main
```

Your actual sigils and records live in `C:\Users\<you>\.sigilry`, outside the
project folder and excluded from git. Your practice is never published by
accident.

---

# A note on what this is

The tool makes no claim about outcomes. What it can honestly promise: the labor
is real and verifiable, the timing is correct, the record cannot be quietly
rewritten, the dissolution is thorough — and every sigil it carries was drawn by
your own hand.
