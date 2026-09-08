# Dofus Forgemage Helper

Desktop helper for **forgemagie / smithmagic (FM)** on Dofus Unity / Dofus 3. It recommends the next rune from community FM math (Fashionista-style weights) and can click **calibrated screen positions** on *your* client with the *your* mouse.

It does **not** read Dofus memory, inject into the process, sniff packets, or bypass anti-cheat.

---

## Ankama Terms of Service — read this first

**Ankama forbids bots and automation.** Using a clicker on the live game is against the Dofus Terms of Use and commonly leads to **account bans**. This project exists as a personal FM calculator plus an optional local mouse helper for people who accept that risk on their own machine.

- Do not use this to cheat other players, farm while AFK-unattended on a production account you care about, or run it on someone else's client.
- Do not ask this codebase for exploits, memory readers, or packet tools — they will not be added.
- If you only want the decision engine, use **Recommend only** (no clicks) or `python -m fm_bot.main --recommend`.

You are solely responsible for how you use it.

---

## Install

Python 3.10+ (3.12 tested).

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Mouse clicking needs `pyautogui` (and `pynput` for global F8/F12). The **engine and tests do not**.

On Linux, pyautogui may need `python3-tk` and an X11/Wayland screenshot backend. The GUI itself is Tkinter.

```bash
# Debian/Ubuntu GUI extras
sudo apt-get install python3-tk python3-dev
```

Run tests (no GUI, no mouse):

```bash
python -m pytest -q
```

---

## Launch

```bash
python -m fm_bot.main
```

Headless next-rune suggestion for a sample item:

```bash
python -m fm_bot.main --list-presets
python -m fm_bot.main --recommend --preset "Gelano (AP dropped, exo vita)"
python -m fm_bot.main --recommend --preset "Typical stuff cape" --mode perfect
```

Monte Carlo simulations of those items (community SC/SN/EC heuristics, **not** official Dofus odds — Ankama never published the formula). No GUI, no mouse:

```bash
python -m fm_bot.simulate
python -m fm_bot --simulate dist_exo_2pct --runs 300
```

Writes `docs/sim_results.md` and prints the same report. Use `--throw-cap`, `--seed`, `--preset`.

---

## Calibration (required before any clicking)

1. Open Dofus, open the smithmagic workshop, put the item in the slot.
2. In the helper, open the **Calibration** tab.
3. Pick a slot (`apply_button`, `item_slot`, a rune id such as `ra_fo`).
4. Hover that control in Dofus and click **Capture in 2s** (or **Capture now** if the helper is not covering the cursor).
5. Repeat for every rune you will throw, plus the **Apply / craft** button.
6. **Save layout** (JSON). A copy is also written to `~/.config/dofus-fm-helper/layout.json` on exit.

Layouts store **screen pixel coordinates** only:

```json
{
  "name": "1920x1080",
  "apply_button": [1400, 820],
  "item_slot": [960, 400],
  "runes": { "ra_fo": [420, 240], "ga_pa": [480, 240] },
  "animation_delay_s": 1.2,
  "click_offset_px": 3
}
```

Re-calibrate after moving the window, changing resolution, or switching monitors.

---

## How to mage with the UI

1. Load a **preset** (Gelano-like AP ring, stuff cape, Solomonk-like hat, exo AP ring, repair example) or add lines by hand.
2. Set **current / min / max / target** to match the item. Min/max are the item's natural roll range.
3. Set **session sink** if you counted a well (e.g. AP just dropped → ~100). **From dropped mins** estimates sink from lines that sit below their natural minimum.
4. Pick a mode: `perfect` (clean roll), `overmax`, `exo`, `repair`.
5. Read **Next rune** and the reasons.
6. Either throw the rune yourself (**Recommend only**) and press **S / N / E**, or use:
   - **Semi-auto** — clicks the calibrated rune (and Apply), then waits for you to report SC / SN / EC.
   - **Auto-repeat** — clicks the same recommendation N times and **assumes SC**. Only for low-risk grinding. Pause as soon as the line is no longer cheap.

After each real throw, update currents if other lines moved. The engine cannot see the game.

---

## Hotkeys and failsafes (mandatory)

| Input | Effect |
| --- | --- |
| **F8** or **F12** | Emergency stop (this window, and globally if `pynput` loaded) |
| Mouse into a **screen corner** | `pyautogui` FAILSAFE abort |
| **S** | Record critical success (SC) |
| **N** | Record neutral success (SN) |
| **E** | Record critical fail (EC) |
| Pause/Resume button | Halt between clicks without losing session state |

Clicks are skipped when **Require Dofus in foreground** is on and the active window title does not contain `dofus`. On Linux without `xdotool` / `pygetwindow` the check is skipped (degrades to “allow”).

Mouse travel is **humanized**: curved ease-in-out paths, Fitts-style timing (faster mid-move, slower near the target), landing jitter, and variable press holds. Pick **slow / natural / fast** in the Clicker panel. **F8** / **F12** and the **screen-corner failsafe** still abort immediately.

---

## How the FM logic works

Community model compiled from [Dofus Fashionista Smithmagic Lab](https://dofusfashionista.gg/forgemagie/) and Unity-era guides. **Ankama has never published the exact success formula.** Treat rates as estimates.

### Outcomes

- **SC** (succès critique) — the bonus is added, nothing else moves.
- **SN** (succès neutre) — the bonus is added; equivalent **weight** is taken from the **sink** first, then from other lines.
- **EC** (échec critique) — no bonus; the rune's weight is taken from sink, then from other lines.

### Sink (puits / reliquat)

When a lost line weighs more than the rune, the leftover is stored invisibly and absorbs later losses. Equipping, trading, or listing the item is commonly reported to **reset** the well.

The UI shows two numbers:

- **Roll-gap** — weight between your rolls and each natural best roll (useful as a “how far from perfect” meter, *not* always real sink).
- **Session sink** — what this session actually has. A Gelano whose AP jumped from 1 to 0 implies ~100. A brand-new min-roll is **not** treated as sink.

### Overmage vs exo, 101 cap

- **Overmage** — pushing a natural line past its best roll.
- **Exo** — adding a stat the item does not have.
- One line cannot hold more than **101 weight** of over/exo (so +101 Strength, +1 AP, but not +2 Range because 102 > 101).

A line that stands **≥ 30 weight past the item's own roll** mainly passes on SC, commonly estimated at **~1%** for AP / MP / PO / Summon exo. Lighter exos behave more like normal runes but still count against the cap.

### 20× rule of thumb

A rune lands **reliably** while the current stat is below about **20 × the rune's bonus**:

| Rune | Bonus | Reliable while below |
| --- | --- | --- |
| +1 (Fo, Ine, …) | 1 | ~20 |
| Pa (+3) | 3 | ~60 |
| Ra (+10) | 10 | ~200 |
| Vi (+5) | 5 | ~100 |

Above that, expect failures unless you have sink.

### Strategy the engine encodes

1. Mage **one stat at a time**.
2. **Big runes first** while the stat is low; **small runes to finish** so you do not overshoot the target (clean mode).
3. **Build / park sink** before expensive runes. Classic Gelano exo: AP drops → SN Ra/Pa Vi while the well lasts → Ga Pa last.
4. Keep **AP / MP / PO / Invo for the end**.
5. **Sacrifice vitality** (then initiative / pods) as filler.
6. **Stabilize small lines** before an exo so they do not eat the well.
7. **Stop** on budget, attempt cap, empty sink before a heavy rune, or when every line is at target.

### Rune table (Fashionista PC / Unity)

Vitality is **0.2 per point** (Vi +5/1, Pa Vi +15/3, Ra Vi +50/10, over +505) — not the Touch 0.25 table.

| Stat | Weight/pt | Small | Pa | Ra | Max over/exo |
| --- | --- | --- | --- | --- | --- |
| Vitality | 0.2 | Vi +5 / 1 | +15 / 3 | +50 / 10 | +505 |
| Strength / Intel / Chance / Agi | 1 | +1 / 1 | +3 / 3 | +10 / 10 | +101 |
| Wisdom | 3 | Sa +1 / 3 | +3 / 9 | +10 / 30 | +33 |
| Power | 2 | Pui +1 / 2 | +3 / 6 | +10 / 20 | +50 |
| Crit | 10 | Cri +1 / 10 | — | — | +10 |
| AP | 100 | Ga Pa +1 / 100 | — | — | +1 |
| MP | 90 | Ga Pme +1 / 90 | — | — | +1 |
| Range | 51 | Po +1 / 51 | — | — | +1 |
| Summon | 30 | Invo +1 / 30 | — | — | +3 |
| Initiative | 0.1 | Ini +10 / 1 | +30 / 3 | +100 / 10 | +1010 |
| Pods | 0.25 | Pod +10 / 2.5 | +30 / 7.5 | +100 / 25 | +404 |
| Prospecting | 3 | Prospe +1 / 3 | +3 / 9 | — | +33 |
| Damage | 20 | Do +1 / 20 | — | — | +5 |
| Elemental damages | 5 | +1 / 5 | +3 / 15 | — | +20 |
| Heals | 10 | So +1 / 10 | +3 / 30 | — | +10 |
| Fixed resists (elem / Cri / Pou) | 2 | +1 / 2 | +3 / 6 | +10 / 20 | +50 |
| % resists | 6 | Ré Per +1 / 6 | — | — | +16 |
| Lock / Dodge | 4 | Tac/Fui +1 / 4 | +3 / 12 | — | +25 |
| AP/MP reduction and dodge | 7 | +1 / 7 | +3 / 21 | — | +14 |
| Pushback / Crit / Trap damage | 5 | +1 / 5 | +3 / 15 | — | +20 |
| % trap damage | 2 | Per Pi +1 / 2 | +3 / 6 | +10 / 20 | +50 |
| Reflect | 10 | Do Ren +1 / 10 | +3 / 30 | — | +10 |
| % melee / ranged / weapon / spell damage | 15 | +1 / 15 | — | — | +6 |
| % melee / ranged resist | 10 | +1 / 10 | — | — | +10 |
| Hunting | 5 | Chasse (no characteristic) | | | |

The in-app **Rune table** tab lists every id the clicker can map.

---

## Project layout

```
fm_bot/runes.py     Fashionista rune database
fm_bot/engine.py    Sink, over/exo, next-rune policy
fm_bot/simulate.py  Monte Carlo FM runs (community SC/SN/EC heuristics)
fm_bot/mouse.py     Calibration, human-like clicks, failsafes
fm_bot/ui.py        Tkinter UI
fm_bot/presets.py   Sample items
fm_bot/main.py      Entry point
tests/              Engine, weights, and simulator (no GUI)
docs/sim_results.md Last full simulation report
```
---

## Disclaimer

Not affiliated with Ankama Games. Dofus is a trademark of Ankama. Rune weights and success comments are community estimates and can change after game updates — verify against current workshop behaviour before spending expensive runes.
