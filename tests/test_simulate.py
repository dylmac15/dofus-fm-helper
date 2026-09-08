"""RNG / heuristic tests for the Forgemage Monte Carlo simulator."""

from __future__ import annotations

import random
from collections import Counter

import pytest

from fm_bot.engine import Outcome, StatLine
from fm_bot.presets import load_preset
from fm_bot.runes import SC_ONLY_RATE, get_rune, line_is_sc_only
from fm_bot.simulate import (
    run_once,
    run_suite,
    sample_outcome,
    scenario_by_id,
)


def test_heavy_exo_is_about_one_percent_sc_no_sn():
    rng = random.Random(0)
    line = StatLine("ap", 0, 0, 0, 1, is_natural=False)
    rune = get_rune("ga_pa")
    n = 20_000
    counts = Counter(sample_outcome(rune, line, rng) for _ in range(n))
    assert counts[Outcome.SN] == 0
    rate = counts[Outcome.SC] / n
    assert counts[Outcome.EC] + counts[Outcome.SC] == n
    assert 0.007 <= rate <= 0.013
    assert SC_ONLY_RATE == pytest.approx(0.01)


def test_second_pct_dist_exo_is_sc_only_first_is_not():
    rune = get_rune("do_per_di")
    first = StatLine("pct_ranged_damage", 0, 0, 0, 2, is_natural=False)
    second = StatLine("pct_ranged_damage", 1, 0, 0, 2, is_natural=False)
    assert not line_is_sc_only("pct_ranged_damage", 0, None, rune.bonus)
    assert line_is_sc_only("pct_ranged_damage", 1, None, rune.bonus)

    rng = random.Random(1)
    first_counts = Counter(sample_outcome(rune, first, rng) for _ in range(4_000))
    assert first_counts[Outcome.SN] > 0
    assert first_counts[Outcome.SC] > 0
    assert first_counts[Outcome.EC] > 0

    rng = random.Random(1)
    second_counts = Counter(sample_outcome(rune, second, rng) for _ in range(8_000))
    assert second_counts[Outcome.SN] == 0
    assert 0.005 <= second_counts[Outcome.SC] / 8_000 <= 0.015


def test_native_pct_dist_is_not_sc_only():
    assert not line_is_sc_only("pct_ranged_damage", 0, 2, 1)
    assert not line_is_sc_only("pct_ranged_damage", 1, 2, 1)


def test_reliquat_absorbs_sn_before_lines():
    session = load_preset("gelano_restore_pa")
    assert session.sink == pytest.approx(100)
    rec = session.recommend()
    assert rec.rune_id == "ga_pa"
    session.apply_outcome(Outcome.SN, rec.rune_id)
    assert session.item.get("ap").current == 1
    assert session.sink == pytest.approx(0)


def test_recommend_apply_loop_terminates():
    rng = random.Random(7)
    result = run_once(lambda: load_preset("simple_hat"), rng, throw_cap=40)
    assert result.throws <= 40
    assert result.stop_reason in {"done", "empty_sink", "attempts", "wait"}
    assert len(result.trace) == result.throws


def test_loop_is_deterministic_with_seed():
    a = run_once(lambda: load_preset("simple_hat"), random.Random(42), throw_cap=30)
    b = run_once(lambda: load_preset("simple_hat"), random.Random(42), throw_cap=30)
    assert [e.outcome for e in a.trace] == [e.outcome for e in b.trace]
    assert [e.rune_id for e in a.trace] == [e.rune_id for e in b.trace]
    assert a.stop_reason == b.stop_reason


def test_gelano_intact_is_already_done():
    result = run_once(lambda: load_preset("gelano"), random.Random(0), throw_cap=10)
    assert result.throws == 0
    assert result.success
    assert result.stop_reason == "done"


def test_suite_tiny_seed_runs():
    batches = run_suite(names=["gelano", "gelano_restore_pa"], n=8, seed=3, throw_cap=20)
    assert len(batches) == 2
    assert all(len(b.runs) == 8 for b in batches)
    restore = batches[1]
    # With a full well, native Ga Pa is not SC-only — most runs should land it.
    hits = sum(1 for r in restore.runs if r.final_currents.get("ap", 0) >= 1)
    assert hits >= 4


def test_scenario_lookup():
    sc = scenario_by_id("dist_exo_2pct")
    session = sc.factory()
    assert session.item.lines["pct_ranged_damage"].target == 2
    assert session.item.lines["pct_ranged_damage"].is_natural is False
