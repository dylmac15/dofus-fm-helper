"""Launch the Forgemage helper UI (or print a recommendation without a display)."""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fm-helper",
        description=(
            "Dofus Forgemage helper: recommends runes from community FM math "
            "and can click calibrated screen positions on YOUR client. "
            "Ankama bans bots — use at your own risk."
        ),
    )
    parser.add_argument(
        "--preset",
        default="Typical stuff cape",
        help="Preset name for --recommend (see --list-presets)",
    )
    parser.add_argument(
        "--list-presets",
        action="store_true",
        help="Print sample item presets and exit",
    )
    parser.add_argument(
        "--recommend",
        action="store_true",
        help="Print the next-rune recommendation for a preset (no GUI, no clicks)",
    )
    parser.add_argument(
        "--mode",
        choices=["perfect", "overmax", "exo", "repair", "transcendance"],
        help="Override preset maging mode for --recommend",
    )
    parser.add_argument(
        "--simulate",
        nargs="?",
        const="ALL",
        default=None,
        metavar="PRESET",
        help=(
            "Monte Carlo FM simulation (community heuristics, no GUI). "
            "Omit PRESET to run the built-in item suite."
        ),
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=None,
        help="Simulations per scenario (with --simulate)",
    )
    parser.add_argument(
        "--throw-cap",
        type=int,
        default=None,
        help="Max rune throws per simulated run",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="RNG seed for --simulate",
    )
    parser.add_argument(
        "--report",
        default=None,
        help="Markdown path for --simulate (default docs/sim_results.md)",
    )
    args = parser.parse_args(argv)

    if args.simulate is not None:
        from .simulate import main as sim_main

        sim_argv: list[str] = []
        if args.simulate != "ALL":
            sim_argv += ["--preset", args.simulate]
        if args.runs is not None:
            sim_argv += ["--runs", str(args.runs)]
        if args.throw_cap is not None:
            sim_argv += ["--throw-cap", str(args.throw_cap)]
        if args.seed is not None:
            sim_argv += ["--seed", str(args.seed)]
        if args.report:
            sim_argv += ["--report", args.report]
        return sim_main(sim_argv)

    from .presets import load_preset, preset_names

    if args.list_presets:
        for name in preset_names():
            session = load_preset(name)
            print(
                f"{name}: mode={session.mode.value} sink={session.sink:g} "
                f"lines={len(session.item.lines)}"
            )
        return 0

    if args.recommend:
        from .engine import MageMode

        session = load_preset(args.preset)
        if args.mode:
            session.set_mode(MageMode(args.mode))
        rec = session.recommend()
        print(f"Item: {session.item.name}")
        print(
            f"Mode: {session.mode.value}  sink={session.sink:g}  "
            f"roll-gap={session.roll_gap:g}"
        )
        print(rec.summary())
        for reason in rec.reasons:
            print(f"  - {reason}")
        if rec.success_note:
            print(f"Note: {rec.success_note}")
        return 0

    try:
        from .ui import run_app
    except Exception as exc:
        print(
            "Could not start the GUI. Use --recommend for a headless suggestion.\n"
            f"({exc})",
            file=sys.stderr,
        )
        return 1
    run_app()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
