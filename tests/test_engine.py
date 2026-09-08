"""Tests for sink math, outcomes, and next-rune policy."""

from __future__ import annotations

import pytest

from fm_bot.engine import (
    ForgeSession,
    ItemState,
    MageMode,
    Outcome,
    SessionLimits,
    StatLine,
    apply_outcome_preview,
    classify_risk,
    estimate_sink,
    next_rune,
    pick_rune_for_line,
)
from fm_bot.mouse import Layout, Point
from fm_bot.presets import load_preset
from fm_bot.runes import get_rune


def line(
    stat_id: str,
    current: int,
    mn: int,
    mx: int,
    target: int,
    *,
    natural: bool = True,
) -> StatLine:
    return StatLine(
        stat_id=stat_id,
        current=current,
        natural_min=mn,
        natural_max=mx,
        target=target,
        is_natural=natural,
    )


def item_of(*lines: StatLine, name: str = "test") -> ItemState:
    return ItemState(name=name, lines={ln.stat_id: ln for ln in lines})


def test_sink_from_dropped_min_not_from_fresh_min_roll():
    dropped_ap = item_of(line("ap", 0, 1, 1, 1))
    assert dropped_ap.implied_session_sink() == pytest.approx(100)
    assert estimate_sink(dropped_ap) == pytest.approx(100)

    fresh_cape = item_of(line("strength", 31, 31, 50, 50))
    assert fresh_cape.implied_session_sink() == pytest.approx(0)
    assert fresh_cape.roll_gap_weight() == pytest.approx(19)

    session = ForgeSession(dropped_ap, session_sink=None)
    assert session.sink == pytest.approx(100)


def test_explicit_session_sink_wins():
    it = item_of(line("ap", 0, 1, 1, 1))
    assert estimate_sink(it, session_sink=40) == pytest.approx(40)


def test_sc_adds_bonus_keeps_sink():
    it = item_of(line("strength", 10, 0, 50, 50), line("vitality", 100, 0, 200, 200))
    out, sink = apply_outcome_preview(it, sink=25, rune_id="ra_fo", outcome=Outcome.SC)
    assert out.get("strength").current == 20
    assert sink == pytest.approx(25)
    assert out.get("vitality").current == 100


def test_sn_consumes_sink_before_lines():
    it = item_of(line("strength", 10, 0, 50, 50), line("vitality", 100, 0, 200, 200))
    out, sink = apply_outcome_preview(it, sink=25, rune_id="pa_fo", outcome=Outcome.SN)
    assert out.get("strength").current == 13
    assert sink == pytest.approx(22)
    assert out.get("vitality").current == 100


def test_ec_no_bonus_and_empty_sink_drains_vitality():
    it = item_of(line("strength", 10, 0, 50, 50), line("vitality", 100, 0, 200, 200))
    out, sink = apply_outcome_preview(it, sink=0, rune_id="ra_fo", outcome=Outcome.EC)
    assert out.get("strength").current == 10
    assert sink == pytest.approx(0)
    # Ra Fo weighs 10; vitality is 0.2/pt → 50 vita.
    assert out.get("vitality").current == 50


def test_empty_sink_eats_over_exo_before_dump():
    """Huzounet: over/exo lines jump before vitality dump."""
    over = item_of(
        line("strength", 60, 0, 50, 50),
        line("vitality", 100, 0, 200, 200),
    )
    out, sink = apply_outcome_preview(over, sink=0, rune_id="fo", outcome=Outcome.EC)
    assert out.get("strength").current == 59
    assert out.get("vitality").current == 100
    assert sink == pytest.approx(0)

    exo = item_of(
        line("pct_ranged_damage", 1, 0, 0, 2, natural=False),
        line("vitality", 200, 0, 200, 200),
        line("strength", 40, 0, 40, 40),
    )
    out, sink = apply_outcome_preview(exo, sink=0, rune_id="do_per_di", outcome=Outcome.EC)
    # Do Per Di weighs 15; the exo 1% dist is exactly 15. Vita/str stay.
    assert out.get("pct_ranged_damage").current == 0
    assert out.get("vitality").current == 200
    assert out.get("strength").current == 40
    assert sink == pytest.approx(0)


def test_dropped_heavier_line_creates_sink():
    it = item_of(line("strength", 10, 0, 50, 50), line("ap", 1, 1, 1, 1))
    session = ForgeSession(it, session_sink=0)
    session.apply_outcome(Outcome.EC, "fo", dropped={"ap": 0})
    assert it.get("ap").current == 0
    assert it.get("strength").current == 10
    # Lost 100 weight for a 1-weight rune → 99 sink.
    assert session.sink == pytest.approx(99)


def test_pick_big_runes_while_low_small_to_finish():
    low = line("strength", 5, 0, 80, 80)
    assert pick_rune_for_line(low).id == "ra_fo"  # +10, 5 < 200

    mid = line("strength", 55, 0, 80, 80)
    assert pick_rune_for_line(mid).id == "ra_fo"  # still < 200

    near = line("strength", 75, 0, 80, 80)
    # remaining 5, Ra would overshoot
    assert pick_rune_for_line(near).id == "pa_fo"

    finish = line("strength", 79, 0, 80, 80)
    assert pick_rune_for_line(finish).id == "fo"

    past_window = line("strength", 70, 0, 72, 72)
    # remaining 2, only small fits
    assert pick_rune_for_line(past_window).id == "fo"


def test_does_not_overshoot_target_in_clean_mode():
    it = item_of(line("strength", 45, 30, 50, 50))
    rec = next_rune(it, mode=MageMode.PERFECT)
    assert rec.action == "throw"
    assert rec.rune_id == "pa_fo"  # remaining 5, not Ra +10
    assert rec.size == "pa"


def test_mages_one_stat_at_a_time():
    it = item_of(
        line("strength", 10, 0, 50, 50),
        line("intelligence", 10, 0, 80, 80),
    )
    session = ForgeSession(it, mode=MageMode.PERFECT)
    first = session.recommend()
    assert first.stat_id == "intelligence"  # more remaining weight
    second = session.recommend()
    assert second.stat_id == "intelligence"  # stick to focus
    session.apply_outcome(Outcome.SC, first.rune_id)
    # Still not at target → still intelligence
    third = session.recommend()
    assert third.stat_id == "intelligence"


def test_ap_mp_kept_for_the_end():
    it = item_of(
        line("strength", 40, 30, 50, 50),
        line("ap", 0, 1, 1, 1),
        line("vitality", 200, 150, 200, 200),
    )
    rec = next_rune(it, mode=MageMode.PERFECT, session_sink=100)
    assert rec.action == "throw"
    assert rec.stat_id == "strength"
    # Finish strength
    it.get("strength").current = 50
    rec2 = next_rune(it, mode=MageMode.PERFECT, session_sink=100)
    assert rec2.stat_id == "ap"
    assert rec2.rune_id == "ga_pa"


def test_exo_stabilizes_small_lines_before_ga_pa():
    session = load_preset("Exo AP ring")
    rec = session.recommend()
    assert rec.action == "throw"
    assert rec.stat_id != "ap"
    for ln in session.item.lines.values():
        if ln.stat_id != "ap":
            ln.current = ln.target
    session.focus_stat = None
    rec2 = session.recommend()
    assert rec2.action == "stop"
    assert rec2.stop_reason == "empty sink"


def test_exo_ap_is_sc_only_when_sink_and_assume_sc():
    it = item_of(
        line("vitality", 80, 50, 80, 80),
        line("ap", 0, 0, 0, 1, natural=False),
    )
    rec = next_rune(
        it,
        mode=MageMode.EXO,
        session_sink=0,
        limits=SessionLimits(stop_on_empty_sink=False, assume_sc=True),
    )
    assert rec.action == "throw"
    assert rec.rune_id == "ga_pa"
    assert rec.risk == "sc_only"


def test_gelano_exo_parks_sink_into_vita():
    session = load_preset("Gelano (AP dropped, exo vita)")
    rec = session.recommend()
    assert rec.action == "throw"
    assert rec.rune_id == "ra_vi"
    assert rec.phase in ("dump_sink", "filler", "progress", "exo")


def test_gelano_repair_restores_ap_with_the_well():
    session = load_preset("Gelano (AP dropped, exo vita)")
    session.item.get("vitality").target = 0
    session.set_mode(MageMode.REPAIR)
    rec = session.recommend()
    assert rec.action == "throw"
    assert rec.rune_id == "ga_pa"
    assert rec.stat_id == "ap"
    assert rec.risk in ("medium", "low")


def test_overmax_respects_101_cap():
    it = item_of(line("strength", 50, 0, 50, 160))
    rec = next_rune(it, mode=MageMode.OVERMAX, session_sink=50)
    # hard cap is 50 + 101 = 151, target 160 is clipped by rune hard_cap
    assert rec.action == "throw"
    # current 50, Ra still reliable and remaining huge
    assert rec.rune_id == "ra_fo"
    it.get("strength").current = 151
    rec2 = next_rune(it, mode=MageMode.OVERMAX)
    # at hard cap, remaining target 160 but cannot fit a rune
    assert rec2.action in ("wait", "stop")


def test_budget_and_attempt_stops():
    it = item_of(line("strength", 0, 0, 50, 50))
    rec = next_rune(
        it,
        limits=SessionLimits(budget_kamas=10, spent_kamas=10),
    )
    assert rec.action == "stop" and rec.stop_reason == "budget"
    rec = next_rune(it, limits=SessionLimits(max_attempts=5, attempts=5))
    assert rec.action == "stop" and rec.stop_reason == "attempt cap"


def test_empty_sink_stops_expensive_rune():
    it = item_of(line("ap", 0, 1, 1, 1))
    rec = next_rune(it, mode=MageMode.REPAIR, session_sink=0)
    assert rec.action == "stop"
    assert rec.stop_reason == "empty sink"


def test_available_runes_filter():
    it = item_of(line("strength", 5, 0, 50, 50))
    rec = next_rune(it, available_runes=["fo"])
    assert rec.rune_id == "fo"


def test_repair_mode_prioritizes_dropped_primary():
    session = load_preset("Repair after fail")
    rec = session.recommend()
    assert rec.action == "throw"
    assert rec.stat_id == "strength"
    assert rec.rune_id == "ra_fo"


def test_targets_reached_stops():
    it = item_of(line("strength", 50, 30, 50, 50))
    rec = next_rune(it)
    assert rec.action == "stop"
    assert rec.stop_reason == "targets reached"


def test_classify_risk_heavy_with_sink_is_medium():
    ln = line("ap", 0, 1, 1, 1)
    risk = classify_risk(get_rune("ga_pa"), ln, sink=100)
    assert risk.value == "medium"
    risk2 = classify_risk(get_rune("ga_pa"), ln, sink=0)
    assert risk2.value == "high"


def test_layout_json_roundtrip(tmp_path):
    layout = Layout(name="test-1080")
    layout.set_slot("apply_button", Point(100, 200))
    layout.set_slot("ra_fo", Point(300, 400))
    layout.animation_delay_s = 1.5
    path = tmp_path / "layout.json"
    layout.save(path)
    loaded = Layout.load(path)
    assert loaded.apply_button == Point(100, 200)
    assert loaded.runes["ra_fo"] == Point(300, 400)
    assert loaded.animation_delay_s == pytest.approx(1.5)


def test_session_attempt_and_price_tracking():
    it = item_of(line("strength", 0, 0, 20, 20))
    session = ForgeSession(it, session_sink=0)
    rec = session.recommend()
    assert rec.rune_id
    session.limits.rune_prices[rec.rune_id] = 100
    session.apply_outcome(Outcome.SC, rec.rune_id)
    assert session.limits.attempts == 1
    assert session.limits.spent_kamas == pytest.approx(100)


def test_huzounet_reliquat_invo_drop():
    from fm_bot.engine import reliquat_from_drop

    assert reliquat_from_drop(30, 3) == 27
    it = item_of(line("intelligence", 0, 0, 80, 80), line("summon", 1, 1, 1, 1))
    session = ForgeSession(it, session_sink=0)
    session.apply_outcome(Outcome.SN, "pa_ine", dropped={"summon": 0})
    assert it.get("intelligence").current == 3
    assert it.get("summon").current == 0
    assert session.sink == pytest.approx(27)


def test_simple_hat_starts_with_biggest_primary():
    rec = load_preset("simple_hat").recommend()
    assert rec.action == "throw"
    assert rec.stat_id == "strength"
    assert rec.rune_id == "ra_fo"


def test_item_families():
    from fm_bot.engine import ItemFamily, classify_family

    assert classify_family(load_preset("gelano").item) is ItemFamily.PUITS
    assert classify_family(load_preset("strigide_concession").item) is ItemFamily.CONCESSION
    assert classify_family(load_preset("koutoulou_over_vita").item) is ItemFamily.PUITS
    assert classify_family(load_preset("gloursonne_exo_pa").item) is ItemFamily.CONCESSION


def test_high_rule_smooth_before_exo():
    it = item_of(
        line("vitality", 213, 50, 200, 200),
        line("ap", 0, 0, 0, 1, natural=False),
    )
    rec = ForgeSession(
        it,
        mode=MageMode.EXO,
        session_sink=0,
        available_runes=["pod", "ga_pa"],
    ).recommend()
    assert rec.phase == "smooth"
    assert rec.rune_id == "pod"


def test_over_after_natural_lines():
    it = item_of(
        line("strength", 40, 0, 80, 80),
        line("vitality", 250, 50, 250, 350),
    )
    rec = ForgeSession(it, mode=MageMode.OVERMAX, session_sink=20).recommend()
    assert rec.stat_id == "strength"


def test_brisage_focus_formula():
    from fm_bot.engine import brisage_focus_density, should_focus_brisage

    assert brisage_focus_density(10, 20) == 20
    assert should_focus_brisage(4, 1) is True
    assert should_focus_brisage(1, 1) is False


def test_vita_alias_and_over_cap_weight():
    from fm_bot.runes import get_stat, weight_of_points

    assert get_stat("vita").id == "vitality"
    assert weight_of_points("vitality", 505) == pytest.approx(101)
    assert get_stat("strength").max_over_exo == 101
