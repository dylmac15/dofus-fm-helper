"""Tests for Fashionista-style rune weights and over/exo caps."""

from __future__ import annotations

import pytest

from fm_bot.runes import (
    HEAVY_LINE_WEIGHT,
    HUNTING_RUNE,
    OVER_EXO_WEIGHT_CAP,
    RELIABLE_MULTIPLIER,
    RuneSize,
    get_rune,
    get_stat,
    line_is_sc_only,
    max_over_points,
    over_cap_points,
    rune_is_reliable_at,
    weight_of_points,
    weight_past_natural,
)


def test_vitality_fashionista_weights():
    vita = get_stat("vitality")
    assert vita.weight_per_point == pytest.approx(0.2)
    vi, pa, ra = vita.rune(RuneSize.SMALL), vita.rune(RuneSize.PA), vita.rune(RuneSize.RA)
    assert vi is not None and vi.bonus == 5 and vi.weight == pytest.approx(1)
    assert pa is not None and pa.bonus == 15 and pa.weight == pytest.approx(3)
    assert ra is not None and ra.bonus == 50 and ra.weight == pytest.approx(10)
    assert vita.max_over_exo == 505
    assert over_cap_points("vitality") == 505


@pytest.mark.parametrize(
    "stat_id,wpp,small,pa,ra,over,small_id",
    [
        ("strength", 1, (1, 1), (3, 3), (10, 10), 101, "fo"),
        ("intelligence", 1, (1, 1), (3, 3), (10, 10), 101, "ine"),
        ("chance", 1, (1, 1), (3, 3), (10, 10), 101, "cha"),
        ("agility", 1, (1, 1), (3, 3), (10, 10), 101, "age"),
        ("wisdom", 3, (1, 3), (3, 9), (10, 30), 33, "sa"),
        ("power", 2, (1, 2), (3, 6), (10, 20), 50, "pui"),
        ("initiative", 0.1, (10, 1), (30, 3), (100, 10), 1010, "ini"),
        ("pods", 0.25, (10, 2.5), (30, 7.5), (100, 25), 404, "pod"),
        ("prospecting", 3, (1, 3), (3, 9), None, 33, "prospe"),
        ("pct_trap_damage", 2, (1, 2), (3, 6), (10, 20), 50, "per_pi"),
        ("heals", 10, (1, 10), (3, 30), None, 10, "so"),
        ("lock", 4, (1, 4), (3, 12), None, 25, "tac"),
        ("dodge", 4, (1, 4), (3, 12), None, 25, "fui"),
        ("earth_resist", 2, (1, 2), (3, 6), (10, 20), 50, "re_terre"),
        ("neutral_damage", 5, (1, 5), (3, 15), None, 20, "do_neutre"),
        ("reflect", 10, (1, 10), (3, 30), None, 10, "do_ren"),
        ("ap_reduction", 7, (1, 7), (3, 21), None, 14, "ret_pa"),
        ("mp_dodge", 7, (1, 7), (3, 21), None, 14, "re_pme"),
    ],
)
def test_stat_rune_table(stat_id, wpp, small, pa, ra, over, small_id):
    stat = get_stat(stat_id)
    assert stat.weight_per_point == pytest.approx(wpp)
    assert stat.max_over_exo == over
    s = stat.rune(RuneSize.SMALL)
    assert s is not None and s.id == small_id
    assert (s.bonus, s.weight) == pytest.approx(small)
    if pa is None:
        assert stat.rune(RuneSize.PA) is None
    else:
        p = stat.rune(RuneSize.PA)
        assert p is not None
        assert (p.bonus, p.weight) == pytest.approx(pa)
    if ra is None:
        assert stat.rune(RuneSize.RA) is None
    else:
        r = stat.rune(RuneSize.RA)
        assert r is not None
        assert (r.bonus, r.weight) == pytest.approx(ra)


@pytest.mark.parametrize(
    "stat_id,wpp,bonus,weight,over,rune_id",
    [
        ("crit", 10, 1, 10, 10, "cri"),
        ("ap", 100, 1, 100, 1, "ga_pa"),
        ("mp", 90, 1, 90, 1, "ga_pme"),
        ("range", 51, 1, 51, 1, "po"),
        ("summon", 30, 1, 30, 3, "invo"),
        ("damage", 20, 1, 20, 5, "do"),
        ("pct_melee_damage", 15, 1, 15, 6, "do_per_me"),
        ("pct_ranged_damage", 15, 1, 15, 6, "do_per_di"),
        ("pct_weapon_damage", 15, 1, 15, 6, "do_per_ar"),
        ("pct_spell_damage", 15, 1, 15, 6, "do_per_so"),
        ("pct_melee_resist", 10, 1, 10, 10, "re_per_me"),
        ("pct_ranged_resist", 10, 1, 10, 10, "re_per_di"),
        ("pct_earth_resist", 6, 1, 6, 16, "re_per_terre"),
    ],
)
def test_single_size_runes(stat_id, wpp, bonus, weight, over, rune_id):
    stat = get_stat(stat_id)
    assert stat.weight_per_point == pytest.approx(wpp)
    assert stat.max_over_exo == over
    rune = get_rune(rune_id)
    assert rune.bonus == bonus and rune.weight == pytest.approx(weight)
    assert rune.stat_id == stat_id


def test_hunting_rune_weight():
    assert HUNTING_RUNE.weight == pytest.approx(5)
    assert HUNTING_RUNE.stat_id is None
    assert get_rune("chasse").weight == pytest.approx(5)


def test_over_exo_cap_is_101_weight():
    assert OVER_EXO_WEIGHT_CAP == 101
    assert over_cap_points("strength") == 101
    assert over_cap_points("ap") == 1
    assert over_cap_points("mp") == 1
    assert over_cap_points("range") == 1  # 2 PO = 102 > 101
    assert over_cap_points("summon") == 3
    assert over_cap_points("wisdom") == 33
    assert max_over_points("power") == 50
    assert weight_of_points("ap", 1) == pytest.approx(100)
    assert weight_of_points("range", 2) == pytest.approx(102)


def test_twenty_x_reliability_rule():
    fo = get_rune("fo")
    pa_fo = get_rune("pa_fo")
    ra_fo = get_rune("ra_fo")
    assert fo.reliable_until == RELIABLE_MULTIPLIER * 1 == 20
    assert pa_fo.reliable_until == 60
    assert ra_fo.reliable_until == 200
    assert rune_is_reliable_at(fo, 19)
    assert not rune_is_reliable_at(fo, 20)
    assert rune_is_reliable_at(pa_fo, 59)
    assert not rune_is_reliable_at(pa_fo, 60)
    assert rune_is_reliable_at(ra_fo, 199)
    assert not rune_is_reliable_at(ra_fo, 200)
    vi = get_rune("vi")
    assert vi.reliable_until == 100  # 20 × 5


def test_heavy_over_is_sc_only():
    assert HEAVY_LINE_WEIGHT == 30
    # Exo AP: 100 weight past a natural max of 0.
    assert line_is_sc_only("ap", current=0, natural_max=0, bonus=1)
    # Restoring native AP to 1 is not past natural.
    assert not line_is_sc_only("ap", current=0, natural_max=1, bonus=1)
    # Range exo.
    assert line_is_sc_only("range", 0, 0, 1)
    # Light exo (strength) is not SC-only.
    assert not line_is_sc_only("strength", 0, None, 1)
    # Summon exo of +1 is exactly 30 weight.
    assert line_is_sc_only("summon", 0, 0, 1)


def test_weight_past_natural_and_aliases():
    assert weight_past_natural("strength", 120, 50) == pytest.approx(70)
    assert get_stat("Force").id == "strength"
    assert get_stat("PA").id == "ap"
    assert get_stat("vi").id == "vitality"


def test_elemental_and_pct_resist_families_exist():
    for sid in (
        "neutral_damage",
        "earth_damage",
        "fire_damage",
        "water_damage",
        "air_damage",
        "neutral_resist",
        "crit_resist",
        "pushback_resist",
        "pushback_damage",
        "crit_damage",
        "trap_damage",
        "trap_power",
    ):
        get_stat(sid)
    assert get_rune("do_pou").weight == pytest.approx(5)
    assert get_rune("pa_do_cri").bonus == 3
