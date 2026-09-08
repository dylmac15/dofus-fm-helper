"""Path generation and delay sampling — no display, no pyautogui."""

from __future__ import annotations

import json
import math
import random
from pathlib import Path

import pytest

from fm_bot.humanize import (
    ABSOLUTE_MIN_GAP_S,
    ClickSettings,
    bezier_path,
    build_move_plan,
    cubic_bezier_point,
    fitts_move_duration,
    landing_point,
    max_deviation_from_segment,
    min_jerk,
    path_speeds,
    sample_after_craft,
    sample_click_hold,
    sample_delay,
    sample_move_duration,
    sample_pre_click,
    sample_think_pause,
    sample_throw_timing,
)
from fm_bot.mouse import Layout, Point


def test_humanize_source_does_not_import_pyautogui():
    src = Path("fm_bot/humanize.py").read_text(encoding="utf-8")
    assert "import pyautogui" not in src
    assert "from pyautogui" not in src


def test_min_jerk_is_ease_in_out():
    assert min_jerk(0.0) == pytest.approx(0.0)
    assert min_jerk(1.0) == pytest.approx(1.0)
    # Slow at the ends, faster in the middle.
    assert min_jerk(0.1) < 0.1
    assert min_jerk(0.9) > 0.9
    mid_step = min_jerk(0.55) - min_jerk(0.45)
    end_step = min_jerk(0.1) - min_jerk(0.0)
    assert mid_step > end_step


def test_bezier_is_not_a_straight_lerp():
    settings = ClickSettings.from_profile("natural")
    start, end = (80.0, 90.0), (640.0, 420.0)
    path = bezier_path(start, end, settings, random.Random(7))
    assert path[0] == pytest.approx(start, abs=0.6)
    assert path[-1] == pytest.approx(end, abs=0.6)
    assert max_deviation_from_segment(path, start, end) > 4.0
    # Not a linear resampling of the chord.
    mid = path[len(path) // 2]
    chord_mid = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
    assert math.hypot(mid[0] - chord_mid[0], mid[1] - chord_mid[1]) > 2.0


def test_cubic_bezier_endpoints():
    p0, p1, p2, p3 = (0, 0), (10, 80), (90, 80), (100, 0)
    assert cubic_bezier_point(p0, p1, p2, p3, 0.0) == pytest.approx(p0)
    assert cubic_bezier_point(p0, p1, p2, p3, 1.0) == pytest.approx(p3)


def test_fitts_short_hops_are_quicker_but_not_linear():
    settings = ClickSettings.from_profile("natural")
    t_short = fitts_move_duration(40, settings)
    t_mid = fitts_move_duration(250, settings)
    t_long = fitts_move_duration(900, settings)
    assert t_short < t_mid < t_long
    assert t_long / t_short < (900 / 40)
    assert t_long / t_short < 8
    assert t_short >= settings.min_move_duration


def test_move_durations_are_not_identical():
    settings = ClickSettings.from_profile("natural")
    values = {
        round(sample_move_duration(380, settings, random.Random(i)), 4)
        for i in range(24)
    }
    assert len(values) > 8


def test_long_path_is_faster_in_the_middle():
    settings = ClickSettings.from_profile("natural")
    path = bezier_path((50.0, 80.0), (820.0, 510.0), settings, random.Random(3))
    speeds = path_speeds(path, duration_s=0.5)
    assert len(speeds) >= 8
    third = max(1, len(speeds) // 3)
    start_avg = sum(speeds[:third]) / third
    mid_avg = sum(speeds[third : 2 * third]) / third
    end_avg = sum(speeds[-third:]) / third
    assert mid_avg > start_avg
    assert mid_avg > end_avg


def test_landing_jitter_is_near_target_not_always_exact():
    settings = ClickSettings.from_profile("natural")
    settings.landing_jitter_px = 6
    target = (400.0, 300.0)
    lands = [landing_point(target, settings, random.Random(i)) for i in range(40)]
    offsets = [math.hypot(x - 400, y - 300) for x, y in lands]
    assert all(off <= 6 * math.sqrt(2) + 0.1 for off in offsets)
    assert any(off > 0.5 for off in offsets)


def test_move_plan_starts_at_cursor_and_lands_nearby():
    settings = ClickSettings.from_profile("natural")
    start, target = (120.0, 140.0), (500.0, 360.0)
    plan = build_move_plan(start, target, settings, random.Random(11))
    assert plan.path[0] == pytest.approx(start, abs=0.6)
    assert math.hypot(plan.landing[0] - target[0], plan.landing[1] - target[1]) <= (
        settings.landing_jitter_px * math.sqrt(2) + 1
    )
    assert plan.duration_s >= settings.min_move_duration
    assert settings.click_hold_min <= plan.click_hold_s <= settings.click_hold_max
    assert plan.pre_click_s >= settings.pre_click_min


def test_micro_correct_moves_closer_to_calibrated_point():
    settings = ClickSettings.from_profile("natural")
    settings.micro_correct_prob = 1.0
    settings.landing_jitter_px = 8
    target = (300.0, 240.0)
    closer = 0
    for i in range(25):
        plan = build_move_plan((10, 10), target, settings, random.Random(i + 50))
        if not plan.micro_path:
            continue
        land = plan.micro_path[0]
        click = plan.landing
        d_land = math.hypot(land[0] - target[0], land[1] - target[1])
        d_click = math.hypot(click[0] - target[0], click[1] - target[1])
        assert d_click <= d_land + 0.5
        closer += 1
    assert closer >= 8


def test_sample_delay_stays_in_range_and_is_not_uniform():
    xs = [
        sample_delay(0.20, 0.05, 0.08, 0.45, random.Random(i)) for i in range(400)
    ]
    assert all(0.08 <= x <= 0.45 for x in xs)
    mean = sum(xs) / len(xs)
    assert 0.17 < mean < 0.23
    within_one_std = sum(1 for x in xs if abs(x - 0.20) <= 0.05)
    # Uniform on [0.08, 0.45] would put only ~27% in that window.
    assert within_one_std / len(xs) > 0.5


def test_click_hold_never_instant():
    settings = ClickSettings.from_profile("fast")
    holds = [sample_click_hold(settings, random.Random(i)) for i in range(80)]
    assert all(h >= settings.click_hold_min for h in holds)
    assert min(holds) < max(holds)


def test_confirm_pause_is_occasional_and_longer():
    settings = ClickSettings.from_profile("natural")
    settings.confirm_pause_prob = 0.2
    samples = [sample_pre_click(settings, random.Random(i)) for i in range(300)]
    longish = [s for s in samples if s > settings.pre_click_max]
    assert 0.05 < len(longish) / len(samples) < 0.4


def test_think_pause_is_rare():
    settings = ClickSettings.from_profile("natural")
    pauses = [sample_think_pause(settings, random.Random(i)) for i in range(600)]
    nonzero = [p for p in pauses if p > 0]
    assert 0.005 < len(nonzero) / len(pauses) < 0.12
    assert all(settings.think_pause_min <= p <= settings.think_pause_max for p in nonzero)


def test_throw_timing_respects_animation_and_floors():
    settings = ClickSettings.from_profile("natural")
    timing = sample_throw_timing(settings, 1.2, random.Random(4))
    assert timing.rune_to_craft_s >= settings.rune_to_craft_min
    assert timing.after_craft_s >= settings.min_after_craft
    assert timing.after_craft_s >= 0.9
    fast = ClickSettings.from_profile("fast")
    after = [sample_after_craft(1.2, fast, random.Random(i)) for i in range(20)]
    assert all(a >= fast.min_after_craft for a in after)


def test_profiles_change_speed_and_cannot_spam():
    slow = ClickSettings.from_profile("slow")
    natural = ClickSettings.from_profile("natural")
    fast = ClickSettings.from_profile("fast")
    assert fitts_move_duration(500, slow) > fitts_move_duration(500, natural)
    assert fitts_move_duration(500, natural) > fitts_move_duration(500, fast)
    assert slow.min_action_gap >= natural.min_action_gap >= fast.min_action_gap
    assert fast.min_action_gap >= ABSOLUTE_MIN_GAP_S
    # 20 clicks/s would be a 0.05s period.
    assert fast.min_click_period_s > 0.12
    assert ClickSettings.from_profile("weird").profile == "natural"


def test_layout_persists_speed_profile(tmp_path):
    layout = Layout(name="humanized")
    layout.set_slot("apply_button", Point(100, 200))
    layout.speed_profile = "fast"
    layout.click_offset_px = 8
    path = tmp_path / "layout.json"
    layout.save(path)
    loaded = Layout.load(path)
    assert loaded.speed_profile == "fast"
    assert loaded.click_offset_px == 8
    settings = loaded.make_click_settings()
    assert settings.profile == "fast"
    assert settings.landing_jitter_px == 8


def test_old_layout_json_defaults_profile(tmp_path):
    path = tmp_path / "old.json"
    path.write_text(
        json.dumps({"name": "old", "apply_button": [1, 2], "runes": {}}),
        encoding="utf-8",
    )
    loaded = Layout.load(path)
    assert loaded.speed_profile == "natural"
    assert loaded.apply_button == Point(1, 2)
