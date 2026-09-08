"""Smithmagic decision engine: sink, over/exo, rune size, next-throw policy.

Community model (Fashionista / Dofus Unity), not an official Ankama formula.

Outcomes
--------
SC (critical success): bonus is added, nothing else moves.
SN (neutral success): bonus is added; equivalent weight is taken from the
    sink (puits / reliquat) first, then from other lines.
EC (critical fail): no bonus; the rune's weight is taken from sink, then lines.

Sink
----
When a lost line weighs more than the rune, the leftover is stored as sink and
absorbs later losses. The roll-gap estimate is the weight between current rolls
and each line's best natural roll. Session sink is what the mage actually has
this session (lost-below-min lines, plus manual corrections). Equipping,
trading, or listing an item is commonly reported to reset sink.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Optional

from .runes import (
    HEAVY_LINE_WEIGHT,
    OVER_EXO_WEIGHT_CAP,
    RELIABLE_MULTIPLIER,
    SC_ONLY_RATE,
    RuneDef,
    RuneSize,
    StatRole,
    get_rune,
    get_stat,
    is_filler_stat,
    is_heavy_stat,
    line_is_sc_only,
    rune_is_reliable_at,
    weight_of_points,
    weight_past_natural,
)

# Dump vitality (and other fillers) up to this over weight before restoring AP.
FILLER_DUMP_OVER_WEIGHT = 90.0
# Consider sink "enough" for a heavy restore when it covers most of the rune.
HEAVY_SINK_COVERAGE = 0.8
# Small-line stabilize: lines at or under this unit weight should sit at target
# before an exo / AP-MP throw.
STABILIZE_WEIGHT_LIMIT = 15.0


class MageMode(str, Enum):
    PERFECT = "perfect"  # clean roll: hit targets, no over/exo
    OVERMAX = "overmax"  # allow pushing past natural max
    EXO = "exo"  # allow adding stats the item does not have
    REPAIR = "repair"  # restore dropped lines after a fail
    TRANSCENDANCE = "transcendance"  # 100% lock rune; jet parfait only


class ItemFamily(str, Enum):
    """Huzounet: concession / puits / brisage."""

    CONCESSION = "concession"
    PUITS = "puits"
    BRISAGE = "brisage"


class Outcome(str, Enum):
    SC = "sc"
    SN = "sn"
    EC = "ec"


class Risk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    SC_ONLY = "sc_only"


@dataclass
class StatLine:
    stat_id: str
    current: int
    natural_min: int
    natural_max: int
    target: int
    is_natural: bool = True
    is_malus: bool = False

    def remaining(self) -> int:
        return self.target - self.current

    def fill_ratio(self) -> float:
        cap = self.natural_max if self.is_natural and self.natural_max else max(self.target, 1)
        if cap <= 0:
            return 1.0
        return self.current / cap

    def at_target(self) -> bool:
        return self.current >= self.target

    def over_points(self) -> int:
        if not self.is_natural:
            return max(0, self.current)
        return max(0, self.current - self.natural_max)

    def over_weight(self) -> float:
        return weight_of_points(self.stat_id, self.over_points())

    def missing_to_best_weight(self) -> float:
        """Weight gap vs best natural roll (0 for exo / malus-in-range)."""
        if not self.is_natural or self.is_malus:
            return 0.0
        missing = max(0, self.natural_max - self.current)
        return weight_of_points(self.stat_id, missing)

    def implied_lost_weight(self) -> float:
        """Weight of a natural bonus line that fell below its minimum."""
        if not self.is_natural or self.is_malus:
            return 0.0
        lost = max(0, self.natural_min - self.current)
        return weight_of_points(self.stat_id, lost)

    def hard_cap(self) -> int:
        """Absolute max this line can hold (natural max + over/exo cap)."""
        stat = get_stat(self.stat_id)
        if self.is_natural:
            return self.natural_max + stat.max_over_exo
        return stat.max_over_exo

    def copy(self) -> "StatLine":
        return StatLine(
            stat_id=self.stat_id,
            current=self.current,
            natural_min=self.natural_min,
            natural_max=self.natural_max,
            target=self.target,
            is_natural=self.is_natural,
            is_malus=self.is_malus,
        )

    def to_dict(self) -> dict:
        return {
            "stat_id": self.stat_id,
            "current": self.current,
            "natural_min": self.natural_min,
            "natural_max": self.natural_max,
            "target": self.target,
            "is_natural": self.is_natural,
            "is_malus": self.is_malus,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StatLine":
        return cls(
            stat_id=data["stat_id"],
            current=int(data["current"]),
            natural_min=int(data.get("natural_min", 0)),
            natural_max=int(data.get("natural_max", 0)),
            target=int(data["target"]),
            is_natural=bool(data.get("is_natural", True)),
            is_malus=bool(data.get("is_malus", False)),
        )


@dataclass
class ItemState:
    name: str
    lines: dict[str, StatLine] = field(default_factory=dict)

    def get(self, stat_id: str) -> StatLine:
        return self.lines[stat_id]

    def add_line(self, line: StatLine) -> None:
        self.lines[line.stat_id] = line

    def copy(self) -> "ItemState":
        return ItemState(
            name=self.name,
            lines={k: v.copy() for k, v in self.lines.items()},
        )

    def roll_gap_weight(self) -> float:
        return round(sum(line.missing_to_best_weight() for line in self.lines.values()), 6)

    def implied_session_sink(self) -> float:
        return round(sum(line.implied_lost_weight() for line in self.lines.values()), 6)

    def total_over_exo_weight(self) -> float:
        return round(sum(line.over_weight() for line in self.lines.values()), 6)

    def all_at_target(self) -> bool:
        return all(line.at_target() for line in self.lines.values())

    def to_dict(self) -> dict:
        return {"name": self.name, "lines": [line.to_dict() for line in self.lines.values()]}

    @classmethod
    def from_dict(cls, data: dict) -> "ItemState":
        item = cls(name=data.get("name", "Item"))
        for raw in data.get("lines", []):
            line = StatLine.from_dict(raw)
            item.lines[line.stat_id] = line
        return item


@dataclass
class SessionLimits:
    budget_kamas: Optional[float] = None
    spent_kamas: float = 0.0
    max_attempts: Optional[int] = None
    attempts: int = 0
    stop_on_empty_sink: bool = True
    assume_sc: bool = False
    rune_prices: dict[str, float] = field(default_factory=dict)

    def budget_exceeded(self) -> bool:
        if self.budget_kamas is None:
            return False
        return self.spent_kamas >= self.budget_kamas

    def attempts_exceeded(self) -> bool:
        if self.max_attempts is None:
            return False
        return self.attempts >= self.max_attempts


@dataclass(frozen=True)
class Recommendation:
    action: str  # throw | stop | wait
    rune_id: Optional[str]
    stat_id: Optional[str]
    size: Optional[str]
    reasons: tuple[str, ...]
    risk: str
    phase: str
    stop_reason: Optional[str] = None
    success_note: str = ""

    @property
    def rune(self) -> Optional[RuneDef]:
        if not self.rune_id:
            return None
        return get_rune(self.rune_id)

    def summary(self) -> str:
        if self.action == "stop":
            return f"STOP: {self.stop_reason or '; '.join(self.reasons)}"
        if self.action == "wait":
            return f"WAIT: {'; '.join(self.reasons)}"
        rune = self.rune
        label = rune.short_name if rune else self.rune_id
        return f"Throw {label} ({self.risk}) — {self.reasons[0] if self.reasons else ''}"

    def clicks(self) -> list[str]:
        if self.action != "throw" or not self.rune_id:
            return []
        return [self.rune_id, "craft_button"]

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "rune_id": self.rune_id,
            "stat_id": self.stat_id,
            "size": self.size,
            "reasons": list(self.reasons),
            "risk": self.risk,
            "phase": self.phase,
            "stop_reason": self.stop_reason,
            "success_note": self.success_note,
            "summary": self.summary(),
            "clicks": self.clicks(),
        }


_ROLE_ORDER = {
    StatRole.PRIMARY: 0,
    StatRole.SECONDARY: 1,
    StatRole.FILLER: 2,
    StatRole.HEAVY: 3,
    StatRole.SPECIAL: 4,
}

_SACRIFICE_ORDER = ("vitality", "initiative", "pods")


def _drain_points(line: StatLine, leftover: float, max_points: int) -> float:
    """Take up to `max_points` from `line` to pay `leftover` weight.

    A rune always eats whole points, so a leftover smaller than one point still
    removes one point and the extra density becomes reliquat (negative leftover).
    """
    if leftover <= 1e-9 or max_points <= 0 or line.current <= 0:
        return leftover
    wpp = get_stat(line.stat_id).weight_per_point
    if wpp <= 0:
        return leftover
    cap = min(line.current, max_points)
    affordable = cap * wpp
    if affordable <= leftover + 1e-9:
        line.current -= cap
        return round(leftover - affordable, 6)
    take = int(leftover / wpp)
    if take <= 0 and leftover > 0:
        take = 1
    take = min(take, cap)
    line.current -= take
    return round(leftover - take * wpp, 6)


def _simulate_line_drops(
    item: ItemState,
    leftover: float,
    protect: Optional[str] = None,
) -> float:
    """Pay remaining SN/EC weight from item lines (reliquat already empty).

    Huzounet: over/exo is eaten first, then dump (vita / ini / pods), then
    other natural lines from lightest density to heaviest.
    """
    if leftover <= 1e-9:
        return leftover

    def _skip(line: StatLine) -> bool:
        return bool(protect and line.stat_id == protect)

    over_lines = sorted(
        [ln for ln in item.lines.values() if ln.over_points() > 0 and not _skip(ln)],
        key=lambda ln: (-ln.over_weight(), ln.stat_id),
    )
    for line in over_lines:
        leftover = _drain_points(line, leftover, line.over_points())
        if leftover <= 1e-9:
            return leftover

    for stat_id in _SACRIFICE_ORDER:
        line = item.lines.get(stat_id)
        if line is None or _skip(line) or line.current <= 0:
            continue
        leftover = _drain_points(line, leftover, line.current)
        if leftover <= 1e-9:
            return leftover

    rest = sorted(
        [
            ln
            for ln in item.lines.values()
            if ln.current > 0 and not _skip(ln)
        ],
        key=lambda ln: (get_stat(ln.stat_id).weight_per_point, ln.stat_id),
    )
    for line in rest:
        leftover = _drain_points(line, leftover, line.current)
        if leftover <= 1e-9:
            return leftover
    return leftover


def estimate_sink(item: ItemState, session_sink: Optional[float] = None) -> float:
    """Effective sink for decisions.

    If the caller supplies a session sink, that value wins (they counted the
    well). Otherwise use implied losses (lines below natural min) — a dropped
    AP is ~100, a fresh min-roll is not treated as sink.
    """
    if session_sink is not None:
        return max(0.0, round(session_sink, 6))
    return item.implied_session_sink()


def pick_rune_for_line(
    line: StatLine,
    available: Optional[Iterable[str]] = None,
    allow_overshoot: bool = False,
) -> Optional[RuneDef]:
    """Choose rune size: big runes first while the stat is low, small to finish.

    Does not overshoot `target` unless `allow_overshoot` is set. Prefers a rune
    that is still in the ~20× reliable window.
    """
    stat = get_stat(line.stat_id)
    remaining = line.remaining()
    if remaining <= 0:
        return None

    allowed = set(available) if available is not None else None
    candidates = [
        r
        for r in stat.runes
        if (allowed is None or r.id in allowed)
        and r.bonus > 0
        and line.current + r.bonus <= line.hard_cap()
        and (allow_overshoot or r.bonus <= remaining)
    ]
    if not candidates:
        return None

    # Largest reliable rune that still fits.
    reliable = [r for r in candidates if rune_is_reliable_at(r, line.current)]
    pool = reliable if reliable else candidates
    # Prefer more bonus; among equals prefer still-reliable (already filtered).
    return max(pool, key=lambda r: (r.bonus, -r.weight))


def classify_risk(
    rune: RuneDef,
    line: StatLine,
    sink: float,
) -> Risk:
    natural_max = line.natural_max if line.is_natural else None
    if line_is_sc_only(line.stat_id, line.current, natural_max, rune.bonus):
        return Risk.SC_ONLY
    reliable = rune_is_reliable_at(rune, line.current)
    if rune.weight >= HEAVY_LINE_WEIGHT:
        if sink >= rune.weight * HEAVY_SINK_COVERAGE:
            return Risk.MEDIUM
        return Risk.HIGH
    if reliable and sink >= 0:
        # Near the 20× edge is a bit shakier.
        if line.current >= int(0.85 * rune.reliable_until):
            return Risk.MEDIUM
        return Risk.LOW
    if sink >= rune.weight:
        return Risk.MEDIUM
    return Risk.HIGH


def _stabilize_pending(item: ItemState) -> list[StatLine]:
    pending = []
    for line in item.lines.values():
        if line.at_target():
            continue
        if not line.is_natural:
            continue
        w = get_stat(line.stat_id).weight_per_point
        if w <= STABILIZE_WEIGHT_LIMIT and not is_heavy_stat(line.stat_id):
            pending.append(line)
    return pending


def classify_family(item: ItemState) -> ItemFamily:
    """Huzounet's three item families."""
    has_heavy = any(ln.is_natural and is_heavy_stat(ln.stat_id) for ln in item.lines.values())
    has_concession = any(
        ln.is_natural and ln.target < ln.natural_max for ln in item.lines.values()
    )
    if has_heavy:
        return ItemFamily.PUITS
    if has_concession:
        return ItemFamily.CONCESSION
    return ItemFamily.BRISAGE


def reliquat_from_drop(outgoing_density: float, rune_density: float) -> float:
    """Huzounet: reliquat = densités sortantes − densité de la rune placée."""
    return max(0.0, round(outgoing_density - rune_density, 4))


def brisage_focus_density(focus_density: float, other_density: float) -> float:
    """Huzounet: densité de brisage focus = focus + (autres / 2)."""
    return focus_density + other_density / 2.0


def should_focus_brisage(focus_price_per_density: float, others_price_per_density: float) -> bool:
    """Focus if the target rune's kama/density is at least 2× the others' average."""
    if others_price_per_density <= 0:
        return True
    return focus_price_per_density >= 2 * others_price_per_density


def _work_queue(item: ItemState, mode: MageMode) -> list[StatLine]:
    """Lines that still need work: one-stat-at-a-time order, heavy last."""
    needed = [ln for ln in item.lines.values() if not ln.at_target()]
    if mode is MageMode.PERFECT:
        needed = [
            ln
            for ln in needed
            if ln.is_natural and ln.target <= ln.natural_max
        ]
    elif mode is MageMode.OVERMAX:
        needed = [
            ln
            for ln in needed
            if ln.is_natural or ln.target > 0
        ]
    elif mode is MageMode.TRANSCENDANCE:
        needed = [
            ln
            for ln in needed
            if ln.is_natural and ln.target <= ln.natural_max
        ]

    def sort_key(line: StatLine) -> tuple:
        role = get_stat(line.stat_id).role
        if mode in (MageMode.REPAIR, MageMode.EXO) and is_heavy_stat(line.stat_id):
            role_rank = 5
        elif not line.is_natural:
            role_rank = 4
        else:
            role_rank = _ROLE_ORDER[role]
        remaining_w = weight_of_points(line.stat_id, max(0, line.remaining()))
        return (role_rank, -remaining_w, line.stat_id)

    needed.sort(key=sort_key)
    return needed


def _dump_filler_line(item: ItemState) -> Optional[StatLine]:
    """Vitality (then ini/pods) still able to absorb sink as over/exo filler."""
    for stat_id in _SACRIFICE_ORDER:
        line = item.lines.get(stat_id)
        if line is None:
            continue
        if line.over_weight() >= FILLER_DUMP_OVER_WEIGHT:
            continue
        if line.current >= line.hard_cap():
            continue
        return line
    # If the item has no filler line, we cannot dump.
    return None


def _success_note(risk: Risk, rune: RuneDef, line: StatLine) -> str:
    if risk is Risk.SC_ONLY:
        return (
            f"Heavy over/exo ({rune.weight} weight past natural ≥ {HEAVY_LINE_WEIGHT:g}). "
            f"Passes mainly on SC, commonly estimated at {SC_ONLY_RATE:.0%} per attempt "
            f"for AP/MP/PO/Invo exo."
        )
    if rune_is_reliable_at(rune, line.current):
        return (
            f"Reliable window: {rune.short_name} while {line.stat_id} is below "
            f"~{RELIABLE_MULTIPLIER}×{rune.bonus} = {rune.reliable_until}."
        )
    return (
        f"Past the ~{RELIABLE_MULTIPLIER}× bonus rule of thumb; expect failures "
        "unless sink covers the rune weight."
    )


class ForgeSession:
    """Mutable maging session: item rolls, sink, limits, next-rune policy."""

    def __init__(
        self,
        item: ItemState,
        mode: MageMode = MageMode.PERFECT,
        limits: Optional[SessionLimits] = None,
        available_runes: Optional[Iterable[str]] = None,
        session_sink: Optional[float] = None,
        focus_stat: Optional[str] = None,
    ) -> None:
        self.item = item
        self.mode = mode
        self.limits = limits or SessionLimits()
        self.available_runes: Optional[set[str]] = (
            set(available_runes) if available_runes is not None else None
        )
        self.session_sink = (
            item.implied_session_sink() if session_sink is None else float(session_sink)
        )
        self.focus_stat = focus_stat
        self.log: list[str] = []
        self.last_rune_id: Optional[str] = None

    @property
    def sink(self) -> float:
        return estimate_sink(self.item, self.session_sink)

    @property
    def roll_gap(self) -> float:
        return self.item.roll_gap_weight()

    def set_mode(self, mode: MageMode) -> None:
        self.mode = MageMode(mode)
        self.focus_stat = None

    @property
    def family(self) -> ItemFamily:
        return classify_family(self.item)

    @property
    def reliquat(self) -> float:
        return self.sink

    def recommend(self) -> Recommendation:
        stop = self._stop_rules()
        if stop is not None:
            return stop

        if self.mode in (MageMode.EXO, MageMode.TRANSCENDANCE):
            smooth = self._smooth_high_rule()
            if smooth is not None:
                return smooth

        if self.item.all_at_target():
            return self._stop("targets reached", "done", "Every line is at its target.")

        queue = _work_queue(self.item, self.mode)
        if not queue:
            return self._stop(
                "nothing to do in this mode",
                "done",
                f"No remaining work for mode {self.mode.value}.",
            )

        # Keep AP/MP/PO for the end; stabilize small lines before exo/heavy.
        if self._needs_stabilize_before_heavy(queue):
            queue = [ln for ln in queue if not is_heavy_stat(ln.stat_id) and ln.is_natural] or queue

        line = self._pick_focus(queue)
        phase = self._phase(line)

        # Exo/overmax: park a dropped-AP well into vitality before the restore.
        # Perfect/repair keep the sink and put the heavy line back immediately.
        if (
            is_heavy_stat(line.stat_id)
            and self.mode in (MageMode.EXO, MageMode.OVERMAX)
        ):
            dump = self._maybe_dump_sink(line)
            if dump is not None:
                return dump

        allow_overshoot = self.mode in (MageMode.OVERMAX, MageMode.EXO) and (
            not line.is_natural or line.target > line.natural_max
        )
        rune = pick_rune_for_line(line, self.available_runes, allow_overshoot=allow_overshoot)
        if rune is None:
            return Recommendation(
                action="wait",
                rune_id=None,
                stat_id=line.stat_id,
                size=None,
                reasons=(
                    f"No available rune fits {get_stat(line.stat_id).name} "
                    f"(remaining {line.remaining()}, cap {line.hard_cap()}).",
                ),
                risk=Risk.HIGH.value,
                phase=phase,
            )

        risk = classify_risk(rune, line, self.sink)
        reasons = self._reasons(line, rune, risk, phase)

        if (
            self.limits.stop_on_empty_sink
            and not self.limits.assume_sc
            and risk in (Risk.HIGH, Risk.SC_ONLY)
            and self.sink < rune.weight
            and rune.weight >= HEAVY_LINE_WEIGHT
        ):
            return self._stop(
                "empty sink",
                "empty_sink",
                (
                    f"Sink is {self.sink:g}; {rune.short_name} weighs {rune.weight:g}. "
                    "Failures will eat placed stats. Rebuild sink or enable "
                    "'assume SC' only for low-risk grinding."
                ),
            )

        return Recommendation(
            action="throw",
            rune_id=rune.id,
            stat_id=line.stat_id,
            size=rune.size.value,
            reasons=tuple(reasons),
            risk=risk.value,
            phase=phase,
            success_note=_success_note(risk, rune, line),
        )

    def apply_outcome(
        self,
        outcome: Outcome,
        rune_id: Optional[str] = None,
        dropped: Optional[dict[str, int]] = None,
    ) -> None:
        """Apply SC/SN/EC. Optional `dropped` maps stat_id -> new current value.

        Without `dropped`, SN/EC consume session sink by the rune weight (floor
        0). The user should update the stats table when other lines move.
        """
        rune_id = rune_id or self.last_rune_id
        if not rune_id:
            raise ValueError("No rune to apply an outcome to")
        rune = get_rune(rune_id)
        self.limits.attempts += 1
        price = self.limits.rune_prices.get(rune_id, 0.0)
        self.limits.spent_kamas += price
        self.last_rune_id = rune_id

        if rune.stat_id and outcome in (Outcome.SC, Outcome.SN):
            line = self.item.lines.get(rune.stat_id)
            if line is not None:
                line.current += rune.bonus
                if line.current > line.hard_cap():
                    line.current = line.hard_cap()

        if outcome is Outcome.SC:
            # Bonus added, sink unchanged.
            self.log.append(f"SC {rune.short_name}: +{rune.bonus} {rune.stat_id or ''}".strip())
        elif outcome is Outcome.SN:
            self._consume_weight(rune.weight, protect=rune.stat_id, dropped=dropped)
            self.log.append(
                f"SN {rune.short_name}: +{rune.bonus}, consumed {rune.weight:g} from sink/lines"
            )
        elif outcome is Outcome.EC:
            self._consume_weight(rune.weight, protect=None, dropped=dropped)
            self.log.append(f"EC {rune.short_name}: no bonus, consumed {rune.weight:g}")

        if rune.stat_id and self.focus_stat == rune.stat_id:
            line = self.item.lines.get(rune.stat_id)
            if line is not None and line.at_target():
                self.focus_stat = None

    def note_stat_change(self, stat_id: str, new_current: int) -> None:
        """User-edited roll. Extra lost weight above the rune consumption becomes sink."""
        line = self.item.lines[stat_id]
        old = line.current
        if new_current < old:
            gained = weight_of_points(stat_id, old - new_current)
            self.session_sink = round(self.session_sink + gained, 6)
        line.current = new_current

    def set_sink(self, value: float) -> None:
        self.session_sink = max(0.0, float(value))

    def recompute_implied_sink(self) -> float:
        self.session_sink = self.item.implied_session_sink()
        return self.sink

    # --- internals -------------------------------------------------------

    def _stop_rules(self) -> Optional[Recommendation]:
        if self.limits.budget_exceeded():
            return self._stop(
                "budget",
                "budget",
                f"Spent {self.limits.spent_kamas:g} kamas, budget "
                f"{self.limits.budget_kamas:g}.",
            )
        if self.limits.attempts_exceeded():
            return self._stop(
                "attempt cap",
                "attempts",
                f"Reached {self.limits.attempts} attempts "
                f"(cap {self.limits.max_attempts}).",
            )
        return None

    def _stop(self, reason: str, phase: str, detail: str, **extra) -> Recommendation:
        return Recommendation(
            action="stop",
            rune_id=None,
            stat_id=extra.get("stat_id"),
            size=None,
            reasons=(detail,),
            risk=Risk.HIGH.value,
            phase=phase,
            stop_reason=reason,
        )

    def _pick_focus(self, queue: list[StatLine]) -> StatLine:
        """Mage one stat at a time: keep the current line until it hits target."""
        if self.focus_stat:
            focused = self.item.lines.get(self.focus_stat)
            if focused is not None and not focused.at_target():
                return focused
        chosen = queue[0]
        self.focus_stat = chosen.stat_id
        return chosen

    def _smooth_high_rule(self) -> Optional[Recommendation]:
        """Règle du haut: shave accidental over before exo / transcendance."""
        overs = [
            ln
            for ln in self.item.lines.values()
            if ln.is_natural and ln.current > ln.natural_max
        ]
        if not overs:
            return None
        victim = max(overs, key=lambda ln: ln.over_weight())
        extra = victim.over_weight()
        from .runes import all_runes, get_rune

        best = None
        best_diff = 10**9
        for rune in all_runes(include_special=False):
            if rune.stat_id == victim.stat_id:
                continue
            if self.available_runes is not None and rune.id not in self.available_runes:
                continue
            if rune.weight > extra + 0.05:
                continue
            diff = abs(rune.weight - extra)
            if diff < best_diff:
                best = rune
                best_diff = diff
        if best is None:
            best = get_rune("pod")
        return Recommendation(
            action="throw",
            rune_id=best.id,
            stat_id=best.stat_id,
            size=best.size.value,
            reasons=(
                f"Règle du haut (Huzounet): {get_stat(victim.stat_id).french} is "
                f"{victim.current}/{victim.natural_max}. Throw {best.short_name} "
                f"(density {best.weight:g}) to lisser before exo or transcendance.",
                "Over/exo lines are eaten first. Example: 213/200 vita shaved by a Pods rune of 2.5.",
            ),
            risk=Risk.MEDIUM.value,
            phase="smooth",
            success_note="This throw is meant to fail onto the over.",
        )

    def _needs_stabilize_before_heavy(self, queue: list[StatLine]) -> bool:
        if self.mode not in (MageMode.EXO, MageMode.OVERMAX, MageMode.REPAIR):
            # Perfect: still keep heavy last via role order; no extra filter.
            return False
        pending = _stabilize_pending(self.item)
        if not pending:
            return False
        next_line = None
        if self.focus_stat:
            next_line = self.item.lines.get(self.focus_stat)
        if next_line is None:
            next_line = queue[0]
        return is_heavy_stat(next_line.stat_id) or (
            not next_line.is_natural and self.mode is MageMode.EXO
        )

    def _phase(self, line: StatLine) -> str:
        if self.mode is MageMode.REPAIR:
            return "repair"
        if not line.is_natural:
            return "exo"
        if is_heavy_stat(line.stat_id) and line.current < line.natural_min:
            return "restore_heavy"
        if line.target > line.natural_max:
            return "overmax"
        if is_filler_stat(line.stat_id):
            return "filler"
        if is_heavy_stat(line.stat_id):
            return "heavy"
        return "progress"

    def _maybe_dump_sink(self, heavy_line: StatLine) -> Optional[Recommendation]:
        """Park an existing well into vitality before restoring AP/MP/PO.

        Classic Gelano exo: AP drops (~100 sink) → SN Ra/Pa Vi while the well
        lasts → then Ga Pa last. Perfect/repair skip this and spend the well
        putting the heavy line back.
        """
        if self.mode in (MageMode.PERFECT, MageMode.REPAIR):
            return None
        if heavy_line.is_natural and heavy_line.current >= heavy_line.natural_min:
            return None
        filler = _dump_filler_line(self.item)
        if filler is None or filler.at_target():
            return None
        if self.sink <= 0:
            return None
        dump_rune = pick_rune_for_line(
            filler, self.available_runes, allow_overshoot=False
        )
        if dump_rune is None:
            return None
        if self.sink < dump_rune.weight:
            return None
        risk = classify_risk(dump_rune, filler, self.sink)
        self.focus_stat = filler.stat_id
        heavy_name = get_stat(heavy_line.stat_id).name
        return Recommendation(
            action="throw",
            rune_id=dump_rune.id,
            stat_id=filler.stat_id,
            size=dump_rune.size.value,
            reasons=(
                f"Park sink ({self.sink:g}) into {get_stat(filler.stat_id).name} "
                f"before restoring {heavy_name}.",
                "Sacrifice vitality as filler; keep AP/MP for the very end.",
                f"{dump_rune.short_name} (+{dump_rune.bonus}, weight {dump_rune.weight:g}).",
            ),
            risk=risk.value,
            phase="dump_sink",
            success_note=_success_note(risk, dump_rune, filler),
        )

    def _reasons(
        self,
        line: StatLine,
        rune: RuneDef,
        risk: Risk,
        phase: str,
    ) -> list[str]:
        stat = get_stat(line.stat_id)
        remaining = line.remaining()
        reasons = [
            f"Mage {stat.name} ({line.current} → {line.target}, remaining {remaining}).",
            f"Chose {rune.short_name} (+{rune.bonus}, weight {rune.weight:g}).",
        ]
        if rune_is_reliable_at(rune, line.current):
            reasons.append(
                f"Big-rune-first: current {line.current} is below ~"
                f"{rune.reliable_until} ({RELIABLE_MULTIPLIER}×{rune.bonus})."
            )
        else:
            reasons.append(
                f"Past the reliable window for {rune.short_name}; finishing with "
                "smaller runes or relying on sink."
            )
        if remaining < rune.bonus * 2 and rune.size is not RuneSize.SMALL:
            reasons.append("Still using a larger rune because it does not overshoot the target.")
        if remaining <= rune.bonus and rune.size is RuneSize.SMALL:
            reasons.append("Small rune to finish near the cap.")
        if phase == "heavy":
            reasons.append("Heavy line last: AP/MP/PO/Invo after other stats are placed.")
        if phase == "exo":
            reasons.append("Exotic line: counts against the 101 over/exo cap.")
        if phase == "overmax":
            reasons.append(
                f"Overmage: {stat.name} past natural {line.natural_max}, "
                f"cap {stat.max_over_exo} pts / {OVER_EXO_WEIGHT_CAP:g} weight."
            )
        if phase == "repair":
            reasons.append("Repair after fail: restore this line before continuing.")
        if phase == "restore_heavy":
            reasons.append(
                f"Heavy stat dropped (implied sink {line.implied_lost_weight():g}). "
                "Dump filler then restore."
            )
        if risk is Risk.SC_ONLY:
            reasons.append(
                "This line sits ≥30 weight past natural; expect ~1% SC for AP/MP/PO/Invo."
            )
        reasons.append(
            f"Session sink (puits/reliquat) {self.sink:g}; roll-gap estimate {self.roll_gap:g}. "
            f"Family: {self.family.value}."
        )
        if phase == "progress":
            reasons.append("One stat at a time: finish this line before switching.")
        return reasons

    def _consume_weight(
        self,
        amount: float,
        protect: Optional[str],
        dropped: Optional[dict[str, int]],
    ) -> None:
        remaining = amount
        if dropped:
            lost_total = 0.0
            for stat_id, new_val in dropped.items():
                line = self.item.lines[stat_id]
                if new_val < line.current:
                    lost_total += weight_of_points(stat_id, line.current - new_val)
                    line.current = new_val
            remaining = round(amount - lost_total, 6)
            if remaining < 0:
                # A heavier line jumped than the rune required → leftover well.
                self.session_sink = round(self.session_sink - remaining, 6)
                return
            if remaining == 0:
                return

        if self.session_sink >= remaining:
            self.session_sink = round(self.session_sink - remaining, 6)
            return
        leftover = round(remaining - self.session_sink, 6)
        self.session_sink = 0.0
        leftover = _simulate_line_drops(self.item, leftover, protect=protect)
        if leftover < 0:
            self.session_sink = round(self.session_sink - leftover, 6)


def apply_outcome_preview(
    item: ItemState,
    sink: float,
    rune_id: str,
    outcome: Outcome,
) -> tuple[ItemState, float]:
    """Pure helper used by tests: copy, apply, return (item, sink)."""
    session = ForgeSession(item.copy(), session_sink=sink)
    session.last_rune_id = rune_id
    session.apply_outcome(outcome, rune_id)
    return session.item, session.sink


def next_rune(
    item: ItemState,
    *,
    mode: MageMode = MageMode.PERFECT,
    session_sink: Optional[float] = None,
    available_runes: Optional[Iterable[str]] = None,
    limits: Optional[SessionLimits] = None,
    focus_stat: Optional[str] = None,
) -> Recommendation:
    """Stateless convenience wrapper around ForgeSession.recommend()."""
    session = ForgeSession(
        item,
        mode=mode,
        limits=limits,
        available_runes=available_runes,
        session_sink=session_sink,
        focus_stat=focus_stat,
    )
    rec = session.recommend()
    return rec
