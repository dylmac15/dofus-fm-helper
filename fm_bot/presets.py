"""Sample items so the helper is usable immediately.

Includes clean-roll / Gelano / exo examples plus Huzounet family illustrations
(concession, puits, brisage / transcendance). Values are typical, not live
encyclopedia dumps — edit currents in the UI to match the item on screen.
"""

from __future__ import annotations

from .engine import ForgeSession, ItemState, MageMode, StatLine


def _line(
    stat_id: str,
    current: int,
    natural_min: int,
    natural_max: int,
    target: int,
    *,
    is_natural: bool = True,
    is_malus: bool = False,
) -> StatLine:
    return StatLine(
        stat_id=stat_id,
        current=current,
        natural_min=natural_min,
        natural_max=natural_max,
        target=target,
        is_natural=is_natural,
        is_malus=is_malus,
    )


def _session(
    name: str,
    mode: MageMode,
    lines: list[StatLine],
    sink: float = 0.0,
    notes: str = "",
) -> ForgeSession:
    item = ItemState(name=name, lines={ln.stat_id: ln for ln in lines})
    session = ForgeSession(item, mode=mode, session_sink=sink)
    session.notes = notes  # type: ignore[attr-defined]
    return session


def typical_stuff_cape() -> ForgeSession:
    return _session(
        "Typical stuff cape",
        MageMode.PERFECT,
        [
            _line("vitality", 180, 150, 250, 250),
            _line("strength", 32, 31, 50, 50),
            _line("intelligence", 31, 31, 50, 50),
            _line("wisdom", 18, 16, 25, 25),
            _line("crit", 3, 3, 5, 5),
            _line("prospecting", 7, 7, 10, 10),
        ],
        notes="Clean-roll a multi-line cape. Primary stats first, AP-class last (none here).",
    )


def gelano_ap_dropped() -> ForgeSession:
    return _session(
        "Gelano-like AP ring (AP dropped)",
        MageMode.EXO,
        [
            _line("ap", 0, 1, 1, 1),
            _line("vitality", 0, 0, 0, 200, is_natural=False),
        ],
        sink=100.0,
        notes="PA jumped (~100 sink). Park the well into vita, then restore Ga Pa.",
    )


def gelano() -> ForgeSession:
    return _session(
        "Gelano-like (puits / PA)",
        MageMode.PERFECT,
        [_line("ap", 1, 1, 1, 1)],
        notes="Classic 1 AP ring. If PA drops, spend the reliquat then land Ga Pa on SC.",
    )


def solomonk_like_hat() -> ForgeSession:
    return _session(
        "Solomonk-like MP hat",
        MageMode.PERFECT,
        [
            _line("mp", 1, 1, 1, 1),
            _line("vitality", 220, 200, 300, 300),
            _line("initiative", 200, 150, 400, 400),
            _line("wisdom", 20, 20, 30, 30),
        ],
        notes="Keep MP for last; push vita / initiative / wisdom first.",
    )


def exo_ap_ring() -> ForgeSession:
    return _session(
        "Exo AP ring (no native AP)",
        MageMode.EXO,
        [
            _line("vitality", 80, 50, 80, 80),
            _line("strength", 25, 21, 30, 30),
            _line("agility", 21, 21, 30, 30),
            _line("crit", 4, 3, 5, 5),
            _line("ap", 0, 0, 0, 1, is_natural=False),
        ],
        notes="Stabilize small lines, then Ga Pa exo (~1% SC).",
    )


def repair_after_fail() -> ForgeSession:
    return _session(
        "Stuff piece (repair after fail)",
        MageMode.REPAIR,
        [
            _line("vitality", 140, 150, 200, 200),
            _line("strength", 12, 40, 60, 60),
            _line("power", 18, 16, 25, 25),
            _line("ap", 1, 1, 1, 1),
        ],
        notes="Restore the dropped primary before touching AP.",
    )


def gloursonne_exo_pa() -> ForgeSession:
    return _session(
        "Gloursonne-like (exo PA)",
        MageMode.EXO,
        [
            _line("vitality", 120, 80, 150, 150),
            _line("strength", 28, 20, 40, 40),
            _line("wisdom", 16, 10, 20, 10),  # concession / dump
            _line("ap", 0, 0, 0, 1, is_natural=False),
        ],
        notes="Huzounet: exo PA on a ring with no PA. Heavy exo = 1% SC, no SN.",
    )


def koutoulou_over_vita() -> ForgeSession:
    return _session(
        "Koutoulou-like (puits → over vita)",
        MageMode.OVERMAX,
        [
            _line("ap", 1, 1, 1, 1),
            _line("vitality", 180, 150, 250, 350),
            _line("intelligence", 30, 20, 40, 40),
            _line("wisdom", 20, 15, 25, 15),
        ],
        notes="Huzounet: over vita using a PA drop as reliquat, then land PA on SC.",
    )


def strigide_concession() -> ForgeSession:
    return _session(
        "Strigide-like (concession)",
        MageMode.OVERMAX,
        [
            _line("crit_resist", 5, 4, 7, 12),
            _line("heals", 10, 8, 12, 8),
            _line("vitality", 120, 100, 150, 150),
            _line("power", 18, 15, 25, 25),
        ],
        notes="Huzounet: no heavy line — concede heals to push ré cri.",
    )


def dragoeuf_transcendance() -> ForgeSession:
    return _session(
        "Dragoeuf-like (brisage then transcendance)",
        MageMode.TRANSCENDANCE,
        [
            _line("vitality", 240, 200, 300, 300),
            _line("strength", 48, 40, 70, 70),
            _line("intelligence", 55, 40, 70, 70),
            _line("crit", 4, 3, 5, 5),
        ],
        notes="Huzounet: perfect the jet (no over, no exo) then lock with a transcendance rune.",
    )


def simple_hat() -> ForgeSession:
    return _session(
        "Simple hat (one stat at a time)",
        MageMode.PERFECT,
        [
            _line("strength", 8, 0, 80, 80),
            _line("intelligence", 70, 0, 80, 80),
            _line("vitality", 200, 50, 250, 250),
            _line("initiative", 300, 0, 400, 200),
        ],
        notes="Start with the biggest remaining primary (strength), then finish that line.",
    )


def gelano_restore_pa() -> ForgeSession:
    return _session(
        "Gelano-like (PA dropped, restore)",
        MageMode.REPAIR,
        [_line("ap", 0, 1, 1, 1)],
        sink=100.0,
        notes="PA dropped with ~100 reliquat. SN Ga Pa spends the well; EC empties it.",
    )


def koutoulou_over_vita_pa_dropped() -> ForgeSession:
    return _session(
        "Koutoulou-like (PA dropped, over vita)",
        MageMode.OVERMAX,
        [
            _line("ap", 0, 1, 1, 1),
            _line("vitality", 180, 150, 250, 350),
            _line("intelligence", 30, 20, 40, 40),
            _line("wisdom", 20, 15, 25, 15),
        ],
        sink=100.0,
        notes="Park the PA well into vita, then try to land PA again.",
    )


def dist_exo_2pct() -> ForgeSession:
    return _session(
        "Generic stuff (exo 2% dommages distance)",
        MageMode.EXO,
        [
            _line("vitality", 150, 100, 200, 200),
            _line("strength", 20, 15, 40, 40),
            _line("wisdom", 15, 10, 25, 20),
            _line("pct_ranged_damage", 0, 0, 0, 2, is_natural=False),
        ],
        notes=(
            "No native % dist. First Do Per Di (density 15) behaves like a normal "
            "rune; the 2nd point is 30 weight past natural → ~1% SC, no SN."
        ),
    )


def dist_natural_2pct() -> ForgeSession:
    return _session(
        "Generic stuff (native 2% dommages distance)",
        MageMode.PERFECT,
        [
            _line("vitality", 150, 100, 200, 200),
            _line("strength", 20, 15, 40, 40),
            _line("wisdom", 15, 10, 25, 20),
            _line("pct_ranged_damage", 0, 0, 2, 2),
        ],
        notes="Native max 2% dist at current 0. Both points sit in the normal window, not SC-only.",
    )


PRESETS: dict[str, callable] = {
    "Typical stuff cape": typical_stuff_cape,
    "Gelano (AP dropped, exo vita)": gelano_ap_dropped,
    "Gelano (intact AP)": gelano,
    "Solomonk-like MP hat": solomonk_like_hat,
    "Exo AP ring": exo_ap_ring,
    "Repair after fail": repair_after_fail,
    "simple_hat": simple_hat,
    "gelano": gelano,
    "gelano_restore_pa": gelano_restore_pa,
    "gloursonne_exo_pa": gloursonne_exo_pa,
    "koutoulou_over_vita": koutoulou_over_vita,
    "koutoulou_over_vita_pa_dropped": koutoulou_over_vita_pa_dropped,
    "strigide_concession": strigide_concession,
    "dragoeuf_transcendance": dragoeuf_transcendance,
    "dist_exo_2pct": dist_exo_2pct,
    "dist_natural_2pct": dist_natural_2pct,
}


def preset_names() -> list[str]:
    return list(PRESETS)


def list_presets() -> list[str]:
    return preset_names()


def load_preset(name: str) -> ForgeSession:
    factory = PRESETS[name]
    return factory()
