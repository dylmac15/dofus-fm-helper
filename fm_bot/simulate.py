"""Monte Carlo Forgemage simulations (community heuristics, not official odds).

Ankama has never published SC / SN / EC rates. This module samples a
documented heuristic, then applies it through ``ForgeSession`` so the next
rune, reliquat, and line drops match the helper the user actually runs.

Heuristic model
----------------
- Reliable window (current < 20 × rune bonus): mostly SC/SN, low EC
  (40% / 50% / 10%).
- Near the 20× edge (≥ 85% of that cap, still inside the window): more EC
  (28% / 47% / 25%).
- Past 20×: more EC/SN, fewer SC (12% / 38% / 50%).
- Heavy over/exo (≥ 30 weight past natural: AP/MP/PO/Invo, 2nd % dist
  point, …): ~1% SC, **no SN**, rest EC.
- Light exo (first +1% dist, density 15) is a normal rune, not SC-only.
- Reliquat absorbs SN/EC first; when empty, over/exo lines drop first, then
  dump (vita / ini / pods), then other lines.

Run::

    python -m fm_bot.simulate
    python -m fm_bot.simulate --preset dist_exo_2pct --runs 300
    python -m fm_bot --simulate simple_hat
"""

from __future__ import annotations

import argparse
import random
import statistics
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from .engine import (
    ForgeSession,
    MageMode,
    Outcome,
    Recommendation,
    SessionLimits,
    StatLine,
)
from .presets import PRESETS, load_preset
from .runes import (
    SC_ONLY_RATE,
    RuneDef,
    get_rune,
    get_stat,
    line_is_sc_only,
    rune_is_reliable_at,
)

# --- documented sampling rates ----------------------------------------------

RELIABLE_SC, RELIABLE_SN, RELIABLE_EC = 0.40, 0.50, 0.10
EDGE_SC, EDGE_SN, EDGE_EC = 0.28, 0.47, 0.25
UNRELIABLE_SC, UNRELIABLE_SN, UNRELIABLE_EC = 0.12, 0.38, 0.50

HEURISTIC_ONE_LINER = (
    "Reliable window (~20× bonus): 40% SC / 50% SN / 10% EC; near the 20× edge "
    "more EC; past 20× 12/38/50; heavy over/exo ≥30 weight past natural: 1% SC, no SN."
)

DEFAULT_RUNS = 300
DEFAULT_THROW_CAP = 120
DEFAULT_SEED = 20260908
DEFAULT_REPORT = Path("docs/sim_results.md")


def sample_outcome(rune: RuneDef, line: StatLine, rng: random.Random) -> Outcome:
    """Draw SC/SN/EC from the community heuristic for this rune on this line."""
    natural_max = line.natural_max if line.is_natural else None
    if line_is_sc_only(line.stat_id, line.current, natural_max, rune.bonus):
        return Outcome.SC if rng.random() < SC_ONLY_RATE else Outcome.EC

    roll = rng.random()
    if rune_is_reliable_at(rune, line.current):
        if rune.reliable_until > 0 and line.current >= int(0.85 * rune.reliable_until):
            return _from_thresholds(roll, EDGE_SC, EDGE_SN)
        return _from_thresholds(roll, RELIABLE_SC, RELIABLE_SN)
    return _from_thresholds(roll, UNRELIABLE_SC, UNRELIABLE_SN)


def _from_thresholds(roll: float, sc: float, sn: float) -> Outcome:
    if roll < sc:
        return Outcome.SC
    if roll < sc + sn:
        return Outcome.SN
    return Outcome.EC


@dataclass
class ThrowEvent:
    n: int
    rune_id: str
    short_name: str
    outcome: str
    stat_id: str
    risk: str
    current_after: int
    sink: float


@dataclass
class RunResult:
    success: bool
    throws: int
    stop_reason: str
    final_currents: dict[str, int]
    peak_currents: dict[str, int]
    sink: float
    trace: list[ThrowEvent] = field(default_factory=list)
    targets: dict[str, int] = field(default_factory=dict)


@dataclass
class Scenario:
    id: str
    title: str
    factory: Callable[[], ForgeSession]
    goal: str
    heuristic: str = HEURISTIC_ONE_LINER
    throw_cap: int = DEFAULT_THROW_CAP
    # Heavy exo PA: the UI stops on empty sink. Simulations that exist to
    # measure the ~1% SC gamble disable that stop so Ga Pa is actually thrown.
    gamble_sc_only: bool = False


@dataclass
class BatchResult:
    scenario: Scenario
    family: str
    mode: str
    n: int
    throw_cap: int
    runs: list[RunResult]
    examples: list[RunResult]


def _stop_label(rec: Recommendation) -> str:
    reason = rec.stop_reason or rec.phase or rec.action
    mapping = {
        "targets reached": "done",
        "nothing to do in this mode": "done",
        "empty sink": "empty_sink",
        "attempt cap": "attempts",
        "budget": "budget",
    }
    return mapping.get(reason, reason)


def _snapshot(session: ForgeSession) -> dict[str, int]:
    return {sid: ln.current for sid, ln in session.item.lines.items()}


def _targets(session: ForgeSession) -> dict[str, int]:
    return {sid: ln.target for sid, ln in session.item.lines.items()}


def run_once(
    factory: Callable[[], ForgeSession],
    rng: random.Random,
    throw_cap: int = DEFAULT_THROW_CAP,
    gamble_sc_only: bool = False,
) -> RunResult:
    """Recommend → sample outcome → apply, until done / cap / empty sink."""
    session = factory()
    session.limits = SessionLimits(
        max_attempts=throw_cap,
        stop_on_empty_sink=not gamble_sc_only,
    )
    peaks = _snapshot(session)
    targets = _targets(session)
    trace: list[ThrowEvent] = []

    while True:
        rec = session.recommend()
        if rec.action != "throw" or not rec.rune_id:
            stop = _stop_label(rec) if rec.action == "stop" else rec.action
            return RunResult(
                success=session.item.all_at_target(),
                throws=session.limits.attempts,
                stop_reason=stop,
                final_currents=_snapshot(session),
                peak_currents=peaks,
                sink=session.sink,
                trace=trace,
                targets=targets,
            )

        rune = get_rune(rec.rune_id)
        line = session.item.lines[rec.stat_id] if rec.stat_id else None
        if line is None:
            return RunResult(
                success=False,
                throws=session.limits.attempts,
                stop_reason="missing_line",
                final_currents=_snapshot(session),
                peak_currents=peaks,
                sink=session.sink,
                trace=trace,
                targets=targets,
            )
        outcome = sample_outcome(rune, line, rng)
        session.apply_outcome(outcome, rec.rune_id)
        now = _snapshot(session)
        for sid, val in now.items():
            peaks[sid] = max(peaks.get(sid, 0), val)
        current_after = now.get(rec.stat_id or "", 0)
        trace.append(
            ThrowEvent(
                n=session.limits.attempts,
                rune_id=rune.id,
                short_name=rune.short_name,
                outcome=outcome.value,
                stat_id=rec.stat_id or "",
                risk=rec.risk,
                current_after=current_after,
                sink=session.sink,
            )
        )
        if session.item.all_at_target():
            return RunResult(
                success=True,
                throws=session.limits.attempts,
                stop_reason="done",
                final_currents=now,
                peak_currents=peaks,
                sink=session.sink,
                trace=trace,
                targets=targets,
            )


def run_batch(
    scenario: Scenario,
    n: int,
    rng: random.Random,
    example_count: int = 2,
) -> BatchResult:
    session0 = scenario.factory()
    family = session0.family.value
    mode = session0.mode.value
    runs: list[RunResult] = []
    examples: list[RunResult] = []
    have_success = False
    have_fail = False
    for _ in range(n):
        result = run_once(
            scenario.factory,
            rng,
            throw_cap=scenario.throw_cap,
            gamble_sc_only=scenario.gamble_sc_only,
        )
        runs.append(result)
        if len(examples) < example_count:
            if result.success and not have_success:
                examples.append(result)
                have_success = True
            elif not result.success and not have_fail:
                examples.append(result)
                have_fail = True
    if len(examples) < example_count:
        for result in runs:
            if result not in examples:
                examples.append(result)
            if len(examples) >= example_count:
                break
    return BatchResult(
        scenario=scenario,
        family=family,
        mode=mode,
        n=n,
        throw_cap=scenario.throw_cap,
        runs=runs,
        examples=examples,
    )


def _pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    xs = sorted(values)
    k = (len(xs) - 1) * (p / 100.0)
    lo = int(k)
    hi = min(lo + 1, len(xs) - 1)
    if lo == hi:
        return float(xs[lo])
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def _fmt_pct(count: int, n: int) -> str:
    if n <= 0:
        return "n/a"
    return f"{100.0 * count / n:.1f}% ({count}/{n})"


def _format_trace(result: RunResult, limit: int = 24) -> str:
    if not result.trace:
        return f"  (no throws — stop: {result.stop_reason})"
    events = result.trace
    if len(events) <= limit:
        chunks = [events]
        gaps: list[int] = []
    else:
        head_n = limit // 2
        tail_n = limit - head_n
        chunks = [events[:head_n], events[-tail_n:]]
        gaps = [len(events) - limit]
    lines = []
    for i, chunk in enumerate(chunks):
        if i and gaps:
            lines.append(f"  … {gaps[i - 1]} more throws …")
        for ev in chunk:
            lines.append(
                f"  {ev.n:>3}. {ev.short_name} {ev.outcome.upper()}  "
                f"{ev.stat_id} → {ev.current_after}  sink {ev.sink:g}  [{ev.risk}]"
            )
    lines.append(
        f"  stop={result.stop_reason}  throws={result.throws}  "
        f"success={result.success}  sink={result.sink:g}"
    )
    return "\n".join(lines)


def format_batch(batch: BatchResult) -> str:
    sc = batch.scenario
    n = batch.n
    successes = sum(1 for r in batch.runs if r.success)
    throws = [float(r.throws) for r in batch.runs]
    sinks = [r.sink for r in batch.runs]
    stops = Counter(r.stop_reason for r in batch.runs)

    lines = [
        f"## {sc.title}",
        "",
        f"- **Item / id:** {sc.id}",
        f"- **Goal:** {sc.goal}",
        f"- **Family:** {batch.family}  ·  **mode:** {batch.mode}",
        f"- **Heuristic:** {sc.heuristic}",
        f"- **Runs:** {n}  ·  **throw cap:** {batch.throw_cap}"
        + ("  ·  empty-sink stop off (SC-only exo gamble)" if sc.gamble_sc_only else ""),
        f"- **Success (all targets):** {_fmt_pct(successes, n)}",
        f"- **Throws:** median {statistics.median(throws):.0f}  ·  "
        f"p90 {_pct(throws, 90):.0f}  ·  mean {statistics.mean(throws):.1f}",
        f"- **Reliquat at end:** median {statistics.median(sinks):.1f}  ·  "
        f"p90 {_pct(sinks, 90):.1f}",
        f"- **Stop reasons:** "
        + ", ".join(f"{k} {_fmt_pct(v, n)}" for k, v in stops.most_common()),
    ]

    # Per-target hit rates (final current >= target).
    targets = batch.runs[0].targets if batch.runs else {}
    if targets:
        lines.append("- **Target lines reached (end of run):**")
        for sid, tgt in targets.items():
            hits = sum(1 for r in batch.runs if r.final_currents.get(sid, 0) >= tgt)
            peaks_ge = sum(1 for r in batch.runs if r.peak_currents.get(sid, 0) >= tgt)
            name = get_stat(sid).french
            extra = ""
            if peaks_ge != hits:
                extra = f"; ever reached {_fmt_pct(peaks_ge, n)}"
            lines.append(
                f"  - {name} (`{sid}`) ≥ {tgt}: {_fmt_pct(hits, n)}{extra}"
            )

    # Extra % dist breakdown (1% vs 2%).
    if "pct_ranged_damage" in targets:
        dist_final = Counter(r.final_currents.get("pct_ranged_damage", 0) for r in batch.runs)
        dist_peak = Counter(r.peak_currents.get("pct_ranged_damage", 0) for r in batch.runs)
        lines.append("- **% dommages distance (Do Per Di):**")
        for pts in range(0, 3):
            lines.append(
                f"  - ended at {pts}%: {_fmt_pct(dist_final.get(pts, 0), n)}; "
                f"peak ≥ {pts}%: {_fmt_pct(sum(v for k, v in dist_peak.items() if k >= pts), n)}"
            )

    if "ap" in targets:
        ap_hits = sum(1 for r in batch.runs if r.final_currents.get("ap", 0) >= 1)
        ap_peak = sum(1 for r in batch.runs if r.peak_currents.get("ap", 0) >= 1)
        lines.append(
            f"- **AP ≥ 1:** ended {_fmt_pct(ap_hits, n)}; ever {_fmt_pct(ap_peak, n)}"
        )

    lines.append("- **Example traces:**")
    for i, ex in enumerate(batch.examples, 1):
        tag = "success" if ex.success else "fail"
        lines.append(f"  Example {i} ({tag}):")
        lines.append(_format_trace(ex))
    lines.append("")
    return "\n".join(lines)


def format_report(batches: list[BatchResult], *, seed: int) -> str:
    parts = [
        "# Forgemage simulation results",
        "",
        "Community-estimate Monte Carlo, **not official Dofus odds**. "
        "Ankama has never published SC/SN/EC rates. The helper's "
        "`ForgeSession.recommend()` picks each rune; a heuristic model "
        "samples the outcome; `apply_outcome` updates the item (reliquat "
        "first, then over/exo, then dump lines).",
        "",
        f"**Model:** {HEURISTIC_ONE_LINER}",
        "",
        f"**RNG seed:** {seed}. Re-run with "
        f"`python -m fm_bot.simulate --seed {seed}`.",
        "",
        "## How 2% dommages distance (Do Per Di) works here",
        "",
        "Do Per Di is **+1% dist at 15 weight**. That sits under the 30-weight "
        "SC-only line, so the **first exo point** is a normal rune (SC/SN/EC "
        "in the 20× window). The **second exo point** is 2 × 15 = 30 weight "
        "past natural: **~1% SC, no SN** — the same family as exo PA/MP/PO. "
        "A **native 0–2%** line never crosses that 30-weight threshold, so "
        "both points stay normal. Once +1% or +2% exo is on the item, later "
        "SN/EC eat that over/exo first (Huzounet), which is why “ever reached "
        "2%” is much higher than “ended at 2%”.",
        "",
    ]
    for batch in batches:
        parts.append(format_batch(batch))
    parts.append(
        "---\n\n"
        "If a real workshop disagrees with a rate here, trust the game — "
        "the model is a teaching aid for rune order and over/exo risk, "
        "not a kama forecast."
    )
    return "\n".join(parts) + "\n"


def _factory(name: str) -> Callable[[], ForgeSession]:
    return lambda n=name: load_preset(n)


def builtin_scenarios() -> list[Scenario]:
    return [
        Scenario(
            id="simple_hat",
            title="Simple hat — perfect the natural lines",
            factory=_factory("simple_hat"),
            goal="Raise strength, intelligence, vitality (and keep initiative) to target.",
        ),
        Scenario(
            id="gelano",
            title="Gelano — PA already on",
            factory=_factory("gelano"),
            goal="Item already at target (1 AP). Sanity check: 0 throws, done.",
        ),
        Scenario(
            id="gelano_restore_pa",
            title="Gelano — PA dropped, put it back",
            factory=_factory("gelano_restore_pa"),
            goal="Spend the ~100 well landing Ga Pa (native restore, not exo).",
        ),
        Scenario(
            id="gloursonne_exo_pa",
            title="Gloursonne-like — exo PA (~1% SC)",
            factory=_factory("gloursonne_exo_pa"),
            goal="Stabilize natural lines, then exo +1 PA. Heavy exo = 1% SC, no SN.",
            gamble_sc_only=True,
        ),
        Scenario(
            id="koutoulou_over_vita",
            title="Koutoulou-like — over vita with PA on",
            factory=_factory("koutoulou_over_vita"),
            goal="Over vitality to 350 while keeping native PA. SN/EC can eat PA.",
        ),
        Scenario(
            id="koutoulou_over_vita_pa_dropped",
            title="Koutoulou-like — PA dropped + sink 100, over vita",
            factory=_factory("koutoulou_over_vita_pa_dropped"),
            goal="Park the PA well into vita, restore PA, then keep overmaging vita.",
        ),
        Scenario(
            id="strigide_concession",
            title="Strigide-like — over ré cri, dump heals",
            factory=_factory("strigide_concession"),
            goal="Concede heals at 8 and push critical resist to 12 (over).",
        ),
        Scenario(
            id="dist_exo_2pct",
            title="Custom — exo 2% dommages distance",
            factory=_factory("dist_exo_2pct"),
            goal=(
                "Generic vita/str/wisdom piece with no native % dist. "
                "Target +2% dist (Do Per Di, 15 weight/pt). First point is a "
                "normal rune; the 2nd is ≥30 weight past natural (~1% SC)."
            ),
            throw_cap=150,
        ),
        Scenario(
            id="dist_natural_2pct",
            title="Same item — native max 2% dist (perfect the line)",
            factory=_factory("dist_natural_2pct"),
            goal=(
                "Same vita/str/wisdom, but % dist is a natural 0–2 line at 0. "
                "Both points stay under the 30-weight SC-only threshold."
            ),
        ),
    ]


def scenario_by_id(name: str) -> Scenario:
    for sc in builtin_scenarios():
        if sc.id == name:
            return sc
    if name not in PRESETS:
        known = ", ".join(sc.id for sc in builtin_scenarios())
        raise KeyError(f"Unknown scenario {name!r}. Built-ins: {known}")
    session = load_preset(name)
    notes = getattr(session, "notes", "") or f"Preset {name}"
    return Scenario(
        id=name,
        title=session.item.name,
        factory=_factory(name),
        goal=notes,
        gamble_sc_only=session.mode is MageMode.EXO
        and any(
            (not ln.is_natural) and get_stat(ln.stat_id).weight_per_point >= 30
            for ln in session.item.lines.values()
        ),
    )


def run_suite(
    names: Optional[list[str]] = None,
    n: int = DEFAULT_RUNS,
    throw_cap: Optional[int] = None,
    seed: int = DEFAULT_SEED,
) -> list[BatchResult]:
    rng = random.Random(seed)
    scenarios = builtin_scenarios() if not names else [scenario_by_id(n_) for n_ in names]
    if throw_cap is not None:
        for sc in scenarios:
            sc.throw_cap = throw_cap
    return [run_batch(sc, n=n, rng=rng) for sc in scenarios]


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m fm_bot.simulate",
        description=(
            "Monte Carlo Forgemage simulations using community SC/SN/EC "
            "heuristics. Not official Dofus odds. No GUI, no mouse."
        ),
    )
    parser.add_argument(
        "--preset",
        metavar="NAME",
        help="Run one scenario/preset (default: the built-in suite)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=DEFAULT_RUNS,
        help=f"Runs per scenario (default {DEFAULT_RUNS})",
    )
    parser.add_argument(
        "--throw-cap",
        type=int,
        default=None,
        help=f"Max throws per run (default {DEFAULT_THROW_CAP}, 150 for exo dist)",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--report",
        default=str(DEFAULT_REPORT),
        help="Markdown file to write (in addition to stdout)",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Print only; do not write the report file",
    )
    args = parser.parse_args(argv)

    names = [args.preset] if args.preset else None
    batches = run_suite(
        names=names,
        n=args.runs,
        throw_cap=args.throw_cap,
        seed=args.seed,
    )
    report = format_report(batches, seed=args.seed)
    print(report)
    if not args.no_write:
        path = Path(args.report)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(report, encoding="utf-8")
        print(f"Wrote {path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
