"""Fashionista-style Dofus Unity / Dofus 3 smithmagic rune table.

Weights follow The Dofus Fashionista Smithmagic Lab (PC: Dofus 2 / Dofus 3):
Vitality is 0.2/pt (Vi +5/1, Pa Vi +15/3, Ra Vi +50/10), not the Touch 0.25 table.

Over/exo cap is 101 weight on a single line. Community estimates, not an
official Ankama formula.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Optional

OVER_EXO_WEIGHT_CAP = 101.0
RELIABLE_MULTIPLIER = 20
HEAVY_LINE_WEIGHT = 30.0
SC_ONLY_RATE = 0.01
AP_EXO_SC_RATE = 0.01


class RuneSize(str, Enum):
    SMALL = "small"
    PA = "pa"
    RA = "ra"
    SPECIAL = "special"


class StatRole(str, Enum):
    """Decision-engine priority band."""

    PRIMARY = "primary"
    SECONDARY = "secondary"
    FILLER = "filler"
    HEAVY = "heavy"
    SPECIAL = "special"


@dataclass(frozen=True)
class RuneDef:
    id: str
    name: str
    short_name: str
    stat_id: Optional[str]
    size: RuneSize
    bonus: int
    weight: float
    description: str = ""

    @property
    def reliable_until(self) -> int:
        """Stat value below which this rune is considered reliable (~20× bonus)."""
        if self.bonus <= 0:
            return 0
        return RELIABLE_MULTIPLIER * self.bonus


@dataclass(frozen=True)
class StatDef:
    id: str
    name: str
    french: str
    weight_per_point: float
    max_over_exo: int
    role: StatRole
    aliases: tuple[str, ...] = ()
    runes: tuple[RuneDef, ...] = field(default_factory=tuple)
    has_rune: bool = True

    def rune(self, size: RuneSize) -> Optional[RuneDef]:
        for rune in self.runes:
            if rune.size is size:
                return rune
        return None

    def largest_rune(self) -> Optional[RuneDef]:
        if not self.runes:
            return None
        return max(self.runes, key=lambda r: (r.bonus, r.weight))

    def weight_of(self, points: int) -> float:
        return round(self.weight_per_point * points, 10)


def _r(
    rune_id: str,
    name: str,
    short_name: str,
    stat_id: str,
    size: RuneSize,
    bonus: int,
    weight: float,
) -> RuneDef:
    return RuneDef(
        id=rune_id,
        name=name,
        short_name=short_name,
        stat_id=stat_id,
        size=size,
        bonus=bonus,
        weight=weight,
    )


def _stat(
    stat_id: str,
    name: str,
    french: str,
    weight_per_point: float,
    max_over_exo: int,
    role: StatRole,
    runes: Iterable[RuneDef],
    aliases: tuple[str, ...] = (),
) -> StatDef:
    return StatDef(
        id=stat_id,
        name=name,
        french=french,
        weight_per_point=weight_per_point,
        max_over_exo=max_over_exo,
        role=role,
        aliases=aliases,
        runes=tuple(runes),
    )


# --- Full PC / Unity table (Fashionista) ---------------------------------

_STATS: list[StatDef] = [
    _stat(
        "vitality",
        "Vitality",
        "Vitalité",
        0.2,
        505,
        StatRole.FILLER,
        [
            _r("vi", "Rune Vi", "Vi", "vitality", RuneSize.SMALL, 5, 1),
            _r("pa_vi", "Rune Pa Vi", "Pa Vi", "vitality", RuneSize.PA, 15, 3),
            _r("ra_vi", "Rune Ra Vi", "Ra Vi", "vitality", RuneSize.RA, 50, 10),
        ],
        aliases=("vita", "vi", "vitalite"),
    ),
    _stat(
        "strength",
        "Strength",
        "Force",
        1,
        101,
        StatRole.PRIMARY,
        [
            _r("fo", "Rune Fo", "Fo", "strength", RuneSize.SMALL, 1, 1),
            _r("pa_fo", "Rune Pa Fo", "Pa Fo", "strength", RuneSize.PA, 3, 3),
            _r("ra_fo", "Rune Ra Fo", "Ra Fo", "strength", RuneSize.RA, 10, 10),
        ],
        aliases=("fo", "force", "str"),
    ),
    _stat(
        "intelligence",
        "Intelligence",
        "Intelligence",
        1,
        101,
        StatRole.PRIMARY,
        [
            _r("ine", "Rune Ine", "Ine", "intelligence", RuneSize.SMALL, 1, 1),
            _r("pa_ine", "Rune Pa Ine", "Pa Ine", "intelligence", RuneSize.PA, 3, 3),
            _r("ra_ine", "Rune Ra Ine", "Ra Ine", "intelligence", RuneSize.RA, 10, 10),
        ],
        aliases=("ine", "int"),
    ),
    _stat(
        "chance",
        "Chance",
        "Chance",
        1,
        101,
        StatRole.PRIMARY,
        [
            _r("cha", "Rune Cha", "Cha", "chance", RuneSize.SMALL, 1, 1),
            _r("pa_cha", "Rune Pa Cha", "Pa Cha", "chance", RuneSize.PA, 3, 3),
            _r("ra_cha", "Rune Ra Cha", "Ra Cha", "chance", RuneSize.RA, 10, 10),
        ],
        aliases=("cha",)
    ),
    _stat(
        "agility",
        "Agility",
        "Agilité",
        1,
        101,
        StatRole.PRIMARY,
        [
            _r("age", "Rune Age", "Age", "agility", RuneSize.SMALL, 1, 1),
            _r("pa_age", "Rune Pa Age", "Pa Age", "agility", RuneSize.PA, 3, 3),
            _r("ra_age", "Rune Ra Age", "Ra Age", "agility", RuneSize.RA, 10, 10),
        ],
        aliases=("age", "agi", "agilite"),
    ),
    _stat(
        "wisdom",
        "Wisdom",
        "Sagesse",
        3,
        33,
        StatRole.SECONDARY,
        [
            _r("sa", "Rune Sa", "Sa", "wisdom", RuneSize.SMALL, 1, 3),
            _r("pa_sa", "Rune Pa Sa", "Pa Sa", "wisdom", RuneSize.PA, 3, 9),
            _r("ra_sa", "Rune Ra Sa", "Ra Sa", "wisdom", RuneSize.RA, 10, 30),
        ],
        aliases=("sa", "sagesse"),
    ),
    _stat(
        "power",
        "Power",
        "Puissance",
        2,
        50,
        StatRole.PRIMARY,
        [
            _r("pui", "Rune Pui", "Pui", "power", RuneSize.SMALL, 1, 2),
            _r("pa_pui", "Rune Pa Pui", "Pa Pui", "power", RuneSize.PA, 3, 6),
            _r("ra_pui", "Rune Ra Pui", "Ra Pui", "power", RuneSize.RA, 10, 20),
        ],
        aliases=("pui", "puissance"),
    ),
    _stat(
        "crit",
        "Critical Hits",
        "Critique",
        10,
        10,
        StatRole.SECONDARY,
        [_r("cri", "Rune Cri", "Cri", "crit", RuneSize.SMALL, 1, 10)],
        aliases=("cri", "critique", "critical"),
    ),
    _stat(
        "ap",
        "AP",
        "PA",
        100,
        1,
        StatRole.HEAVY,
        [_r("ga_pa", "Rune Ga Pa", "Ga Pa", "ap", RuneSize.SMALL, 1, 100)],
        aliases=("pa", "ga_pa", "action"),
    ),
    _stat(
        "mp",
        "MP",
        "PM",
        90,
        1,
        StatRole.HEAVY,
        [_r("ga_pme", "Rune Ga Pme", "Ga Pme", "mp", RuneSize.SMALL, 1, 90)],
        aliases=("pm", "ga_pme", "movement"),
    ),
    _stat(
        "range",
        "Range",
        "Portée",
        51,
        1,
        StatRole.HEAVY,
        [_r("po", "Rune Po", "Po", "range", RuneSize.SMALL, 1, 51)],
        aliases=("po", "porte", "portée"),
    ),
    _stat(
        "summon",
        "Summon",
        "Invocation",
        30,
        3,
        StatRole.HEAVY,
        [_r("invo", "Rune Invo", "Invo", "summon", RuneSize.SMALL, 1, 30)],
        aliases=("invo", "invocation"),
    ),
    _stat(
        "initiative",
        "Initiative",
        "Initiative",
        0.1,
        1010,
        StatRole.FILLER,
        [
            _r("ini", "Rune Ini", "Ini", "initiative", RuneSize.SMALL, 10, 1),
            _r("pa_ini", "Rune Pa Ini", "Pa Ini", "initiative", RuneSize.PA, 30, 3),
            _r("ra_ini", "Rune Ra Ini", "Ra Ini", "initiative", RuneSize.RA, 100, 10),
        ],
        aliases=("ini",)
    ),
    _stat(
        "pods",
        "Pods",
        "Pods",
        0.25,
        404,
        StatRole.FILLER,
        [
            _r("pod", "Rune Pod", "Pod", "pods", RuneSize.SMALL, 10, 2.5),
            _r("pa_pod", "Rune Pa Pod", "Pa Pod", "pods", RuneSize.PA, 30, 7.5),
            _r("ra_pod", "Rune Ra Pod", "Ra Pod", "pods", RuneSize.RA, 100, 25),
        ],
        aliases=("pod",)
    ),
    _stat(
        "prospecting",
        "Prospecting",
        "Prospection",
        3,
        33,
        StatRole.SECONDARY,
        [
            _r("prospe", "Rune Prospe", "Prospe", "prospecting", RuneSize.SMALL, 1, 3),
            _r("pa_prospe", "Rune Pa Prospe", "Pa Prospe", "prospecting", RuneSize.PA, 3, 9),
        ],
        aliases=("prospe", "pp"),
    ),
    _stat(
        "damage",
        "Damage",
        "Dommage",
        20,
        5,
        StatRole.PRIMARY,
        [_r("do", "Rune Do", "Do", "damage", RuneSize.SMALL, 1, 20)],
        aliases=("do", "dommage"),
    ),
    _stat(
        "neutral_damage",
        "Neutral Damage",
        "Dommage Neutre",
        5,
        20,
        StatRole.PRIMARY,
        [
            _r("do_neutre", "Rune Do Neutre", "Do Neutre", "neutral_damage", RuneSize.SMALL, 1, 5),
            _r("pa_do_neutre", "Rune Pa Do Neutre", "Pa Do Neutre", "neutral_damage", RuneSize.PA, 3, 15),
        ],
    ),
    _stat(
        "earth_damage",
        "Earth Damage",
        "Dommage Terre",
        5,
        20,
        StatRole.PRIMARY,
        [
            _r("do_terre", "Rune Do Terre", "Do Terre", "earth_damage", RuneSize.SMALL, 1, 5),
            _r("pa_do_terre", "Rune Pa Do Terre", "Pa Do Terre", "earth_damage", RuneSize.PA, 3, 15),
        ],
    ),
    _stat(
        "fire_damage",
        "Fire Damage",
        "Dommage Feu",
        5,
        20,
        StatRole.PRIMARY,
        [
            _r("do_feu", "Rune Do Feu", "Do Feu", "fire_damage", RuneSize.SMALL, 1, 5),
            _r("pa_do_feu", "Rune Pa Do Feu", "Pa Do Feu", "fire_damage", RuneSize.PA, 3, 15),
        ],
    ),
    _stat(
        "water_damage",
        "Water Damage",
        "Dommage Eau",
        5,
        20,
        StatRole.PRIMARY,
        [
            _r("do_eau", "Rune Do Eau", "Do Eau", "water_damage", RuneSize.SMALL, 1, 5),
            _r("pa_do_eau", "Rune Pa Do Eau", "Pa Do Eau", "water_damage", RuneSize.PA, 3, 15),
        ],
    ),
    _stat(
        "air_damage",
        "Air Damage",
        "Dommage Air",
        5,
        20,
        StatRole.PRIMARY,
        [
            _r("do_air", "Rune Do Air", "Do Air", "air_damage", RuneSize.SMALL, 1, 5),
            _r("pa_do_air", "Rune Pa Do Air", "Pa Do Air", "air_damage", RuneSize.PA, 3, 15),
        ],
    ),
    _stat(
        "heals",
        "Heals",
        "Soin",
        10,
        10,
        StatRole.SECONDARY,
        [
            _r("so", "Rune So", "So", "heals", RuneSize.SMALL, 1, 10),
            _r("pa_so", "Rune Pa So", "Pa So", "heals", RuneSize.PA, 3, 30),
        ],
        aliases=("so", "soin"),
    ),
    _stat(
        "neutral_resist",
        "Neutral Resist",
        "Résistance Neutre",
        2,
        50,
        StatRole.SECONDARY,
        [
            _r("re_neutre", "Rune Ré Neutre", "Ré Neutre", "neutral_resist", RuneSize.SMALL, 1, 2),
            _r("pa_re_neutre", "Rune Pa Ré Neutre", "Pa Ré Neutre", "neutral_resist", RuneSize.PA, 3, 6),
            _r("ra_re_neutre", "Rune Ra Ré Neutre", "Ra Ré Neutre", "neutral_resist", RuneSize.RA, 10, 20),
        ],
    ),
    _stat(
        "earth_resist",
        "Earth Resist",
        "Résistance Terre",
        2,
        50,
        StatRole.SECONDARY,
        [
            _r("re_terre", "Rune Ré Terre", "Ré Terre", "earth_resist", RuneSize.SMALL, 1, 2),
            _r("pa_re_terre", "Rune Pa Ré Terre", "Pa Ré Terre", "earth_resist", RuneSize.PA, 3, 6),
            _r("ra_re_terre", "Rune Ra Ré Terre", "Ra Ré Terre", "earth_resist", RuneSize.RA, 10, 20),
        ],
    ),
    _stat(
        "fire_resist",
        "Fire Resist",
        "Résistance Feu",
        2,
        50,
        StatRole.SECONDARY,
        [
            _r("re_feu", "Rune Ré Feu", "Ré Feu", "fire_resist", RuneSize.SMALL, 1, 2),
            _r("pa_re_feu", "Rune Pa Ré Feu", "Pa Ré Feu", "fire_resist", RuneSize.PA, 3, 6),
            _r("ra_re_feu", "Rune Ra Ré Feu", "Ra Ré Feu", "fire_resist", RuneSize.RA, 10, 20),
        ],
    ),
    _stat(
        "water_resist",
        "Water Resist",
        "Résistance Eau",
        2,
        50,
        StatRole.SECONDARY,
        [
            _r("re_eau", "Rune Ré Eau", "Ré Eau", "water_resist", RuneSize.SMALL, 1, 2),
            _r("pa_re_eau", "Rune Pa Ré Eau", "Pa Ré Eau", "water_resist", RuneSize.PA, 3, 6),
            _r("ra_re_eau", "Rune Ra Ré Eau", "Ra Ré Eau", "water_resist", RuneSize.RA, 10, 20),
        ],
    ),
    _stat(
        "air_resist",
        "Air Resist",
        "Résistance Air",
        2,
        50,
        StatRole.SECONDARY,
        [
            _r("re_air", "Rune Ré Air", "Ré Air", "air_resist", RuneSize.SMALL, 1, 2),
            _r("pa_re_air", "Rune Pa Ré Air", "Pa Ré Air", "air_resist", RuneSize.PA, 3, 6),
            _r("ra_re_air", "Rune Ra Ré Air", "Ra Ré Air", "air_resist", RuneSize.RA, 10, 20),
        ],
    ),
    _stat(
        "crit_resist",
        "Critical Resist",
        "Résistance Critique",
        2,
        50,
        StatRole.SECONDARY,
        [
            _r("re_cri", "Rune Ré Cri", "Ré Cri", "crit_resist", RuneSize.SMALL, 1, 2),
            _r("pa_re_cri", "Rune Pa Ré Cri", "Pa Ré Cri", "crit_resist", RuneSize.PA, 3, 6),
            _r("ra_re_cri", "Rune Ra Ré Cri", "Ra Ré Cri", "crit_resist", RuneSize.RA, 10, 20),
        ],
    ),
    _stat(
        "pushback_resist",
        "Pushback Resist",
        "Résistance Poussée",
        2,
        50,
        StatRole.SECONDARY,
        [
            _r("re_pou", "Rune Ré Pou", "Ré Pou", "pushback_resist", RuneSize.SMALL, 1, 2),
            _r("pa_re_pou", "Rune Pa Ré Pou", "Pa Ré Pou", "pushback_resist", RuneSize.PA, 3, 6),
            _r("ra_re_pou", "Rune Ra Ré Pou", "Ra Ré Pou", "pushback_resist", RuneSize.RA, 10, 20),
        ],
    ),
    _stat(
        "pct_neutral_resist",
        "% Neutral Resist",
        "% Résistance Neutre",
        6,
        16,
        StatRole.SECONDARY,
        [_r("re_per_neutre", "Rune Ré Per Neutre", "Ré Per Neutre", "pct_neutral_resist", RuneSize.SMALL, 1, 6)],
    ),
    _stat(
        "pct_earth_resist",
        "% Earth Resist",
        "% Résistance Terre",
        6,
        16,
        StatRole.SECONDARY,
        [_r("re_per_terre", "Rune Ré Per Terre", "Ré Per Terre", "pct_earth_resist", RuneSize.SMALL, 1, 6)],
    ),
    _stat(
        "pct_fire_resist",
        "% Fire Resist",
        "% Résistance Feu",
        6,
        16,
        StatRole.SECONDARY,
        [_r("re_per_feu", "Rune Ré Per Feu", "Ré Per Feu", "pct_fire_resist", RuneSize.SMALL, 1, 6)],
    ),
    _stat(
        "pct_water_resist",
        "% Water Resist",
        "% Résistance Eau",
        6,
        16,
        StatRole.SECONDARY,
        [_r("re_per_eau", "Rune Ré Per Eau", "Ré Per Eau", "pct_water_resist", RuneSize.SMALL, 1, 6)],
    ),
    _stat(
        "pct_air_resist",
        "% Air Resist",
        "% Résistance Air",
        6,
        16,
        StatRole.SECONDARY,
        [_r("re_per_air", "Rune Ré Per Air", "Ré Per Air", "pct_air_resist", RuneSize.SMALL, 1, 6)],
    ),
    _stat(
        "lock",
        "Lock",
        "Tacle",
        4,
        25,
        StatRole.SECONDARY,
        [
            _r("tac", "Rune Tac", "Tac", "lock", RuneSize.SMALL, 1, 4),
            _r("pa_tac", "Rune Pa Tac", "Pa Tac", "lock", RuneSize.PA, 3, 12),
        ],
        aliases=("tac", "tacle"),
    ),
    _stat(
        "dodge",
        "Dodge",
        "Fuite",
        4,
        25,
        StatRole.SECONDARY,
        [
            _r("fui", "Rune Fui", "Fui", "dodge", RuneSize.SMALL, 1, 4),
            _r("pa_fui", "Rune Pa Fui", "Pa Fui", "dodge", RuneSize.PA, 3, 12),
        ],
        aliases=("fui", "fuite"),
    ),
    _stat(
        "ap_reduction",
        "AP Reduction",
        "Retrait PA",
        7,
        14,
        StatRole.SECONDARY,
        [
            _r("ret_pa", "Rune Ret Pa", "Ret Pa", "ap_reduction", RuneSize.SMALL, 1, 7),
            _r("pa_ret_pa", "Rune Pa Ret Pa", "Pa Ret Pa", "ap_reduction", RuneSize.PA, 3, 21),
        ],
        aliases=("ret_pa",),
    ),
    _stat(
        "mp_reduction",
        "MP Reduction",
        "Retrait PM",
        7,
        14,
        StatRole.SECONDARY,
        [
            _r("ret_pme", "Rune Ret Pme", "Ret Pme", "mp_reduction", RuneSize.SMALL, 1, 7),
            _r("pa_ret_pme", "Rune Pa Ret Pme", "Pa Ret Pme", "mp_reduction", RuneSize.PA, 3, 21),
        ],
        aliases=("ret_pm", "ret_pme"),
    ),
    _stat(
        "ap_dodge",
        "AP Loss Resist",
        "Esquive PA",
        7,
        14,
        StatRole.SECONDARY,
        [
            _r("re_pa", "Rune Ré Pa", "Ré Pa", "ap_dodge", RuneSize.SMALL, 1, 7),
            _r("pa_re_pa", "Rune Pa Ré Pa", "Pa Ré Pa", "ap_dodge", RuneSize.PA, 3, 21),
        ],
        aliases=("re_pa",),
    ),
    _stat(
        "mp_dodge",
        "MP Loss Resist",
        "Esquive PM",
        7,
        14,
        StatRole.SECONDARY,
        [
            _r("re_pme", "Rune Ré Pme", "Ré Pme", "mp_dodge", RuneSize.SMALL, 1, 7),
            _r("pa_re_pme", "Rune Pa Ré Pme", "Pa Ré Pme", "mp_dodge", RuneSize.PA, 3, 21),
        ],
        aliases=("re_pm", "re_pme"),
    ),
    _stat(
        "pushback_damage",
        "Pushback Damage",
        "Dommage Poussée",
        5,
        20,
        StatRole.PRIMARY,
        [
            _r("do_pou", "Rune Do Pou", "Do Pou", "pushback_damage", RuneSize.SMALL, 1, 5),
            _r("pa_do_pou", "Rune Pa Do Pou", "Pa Do Pou", "pushback_damage", RuneSize.PA, 3, 15),
        ],
        aliases=("do_pou",),
    ),
    _stat(
        "crit_damage",
        "Critical Damage",
        "Dommage Critique",
        5,
        20,
        StatRole.PRIMARY,
        [
            _r("do_cri", "Rune Do Cri", "Do Cri", "crit_damage", RuneSize.SMALL, 1, 5),
            _r("pa_do_cri", "Rune Pa Do Cri", "Pa Do Cri", "crit_damage", RuneSize.PA, 3, 15),
        ],
        aliases=("do_cri",),
    ),
    _stat(
        "trap_damage",
        "Trap Damage",
        "Dommage Piège",
        5,
        20,
        StatRole.PRIMARY,
        [
            _r("do_pi", "Rune Do Pi", "Do Pi", "trap_damage", RuneSize.SMALL, 1, 5),
            _r("pa_do_pi", "Rune Pa Do Pi", "Pa Do Pi", "trap_damage", RuneSize.PA, 3, 15),
        ],
        aliases=("do_pi",),
    ),
    _stat(
        "pct_trap_damage",
        "% Trap Damage",
        "% Dommage Piège",
        2,
        50,
        StatRole.PRIMARY,
        [
            _r("per_pi", "Rune Per Pi", "Per Pi", "pct_trap_damage", RuneSize.SMALL, 1, 2),
            _r("pa_per_pi", "Rune Pa Per Pi", "Pa Per Pi", "pct_trap_damage", RuneSize.PA, 3, 6),
            _r("ra_per_pi", "Rune Ra Per Pi", "Ra Per Pi", "pct_trap_damage", RuneSize.RA, 10, 20),
        ],
        aliases=("per_pi", "pui_pi"),
    ),
    _stat(
        "trap_power",
        "Trap Power",
        "Puissance Piège",
        2,
        50,
        StatRole.PRIMARY,
        [
            _r("pui_pi", "Rune Pui Pi", "Pui Pi", "trap_power", RuneSize.SMALL, 1, 2),
            _r("pa_pui_pi", "Rune Pa Pui Pi", "Pa Pui Pi", "trap_power", RuneSize.PA, 3, 6),
            _r("ra_pui_pi", "Rune Ra Pui Pi", "Ra Pui Pi", "trap_power", RuneSize.RA, 10, 20),
        ],
    ),
    _stat(
        "reflect",
        "Reflect",
        "Renvoi de Dommage",
        10,
        10,
        StatRole.SECONDARY,
        [
            _r("do_ren", "Rune Do Ren", "Do Ren", "reflect", RuneSize.SMALL, 1, 10),
            _r("pa_do_ren", "Rune Pa Do Ren", "Pa Do Ren", "reflect", RuneSize.PA, 3, 30),
        ],
        aliases=("do_ren",),
    ),
    _stat(
        "pct_melee_damage",
        "% Melee Damage",
        "% Dommage Mêlée",
        15,
        6,
        StatRole.SECONDARY,
        [_r("do_per_me", "Rune Do Per Mé", "Do Per Mé", "pct_melee_damage", RuneSize.SMALL, 1, 15)],
    ),
    _stat(
        "pct_ranged_damage",
        "% Ranged Damage",
        "% Dommage Distance",
        15,
        6,
        StatRole.SECONDARY,
        [_r("do_per_di", "Rune Do Per Di", "Do Per Di", "pct_ranged_damage", RuneSize.SMALL, 1, 15)],
    ),
    _stat(
        "pct_weapon_damage",
        "% Weapon Damage",
        "% Dommage Arme",
        15,
        6,
        StatRole.SECONDARY,
        [_r("do_per_ar", "Rune Do Per Ar", "Do Per Ar", "pct_weapon_damage", RuneSize.SMALL, 1, 15)],
    ),
    _stat(
        "pct_spell_damage",
        "% Spell Damage",
        "% Dommage Sort",
        15,
        6,
        StatRole.SECONDARY,
        [_r("do_per_so", "Rune Do Per So", "Do Per So", "pct_spell_damage", RuneSize.SMALL, 1, 15)],
    ),
    _stat(
        "pct_melee_resist",
        "% Melee Resist",
        "% Résistance Mêlée",
        10,
        10,
        StatRole.SECONDARY,
        [_r("re_per_me", "Rune Ré Per Mé", "Ré Per Mé", "pct_melee_resist", RuneSize.SMALL, 1, 10)],
    ),
    _stat(
        "pct_ranged_resist",
        "% Ranged Resist",
        "% Résistance Distance",
        10,
        10,
        StatRole.SECONDARY,
        [_r("re_per_di", "Rune Ré Per Di", "Ré Per Di", "pct_ranged_resist", RuneSize.SMALL, 1, 10)],
    ),
]


HUNTING_RUNE = RuneDef(
    id="chasse",
    name="Hunting Rune",
    short_name="Chasse",
    stat_id=None,
    size=RuneSize.SPECIAL,
    bonus=0,
    weight=5,
    description="Turns a weapon into a hunting weapon. Does not raise a characteristic.",
)

SIGNATURE_RUNE = RuneDef(
    id="signature",
    name="Signature Rune",
    short_name="Signature",
    stat_id=None,
    size=RuneSize.SPECIAL,
    bonus=0,
    weight=0,
    description="Applied at craft time, never during smithmagic.",
)

STAT_BY_ID: dict[str, StatDef] = {s.id: s for s in _STATS}

RUNE_BY_ID: dict[str, RuneDef] = {}
for _stat_def in _STATS:
    for _rune in _stat_def.runes:
        RUNE_BY_ID[_rune.id] = _rune
RUNE_BY_ID[HUNTING_RUNE.id] = HUNTING_RUNE
RUNE_BY_ID[SIGNATURE_RUNE.id] = SIGNATURE_RUNE

_ALIAS_TO_STAT: dict[str, str] = {}
for _stat_def in _STATS:
    _ALIAS_TO_STAT[_stat_def.id] = _stat_def.id
    _ALIAS_TO_STAT[_stat_def.name.lower()] = _stat_def.id
    _ALIAS_TO_STAT[_stat_def.french.lower()] = _stat_def.id
    for _alias in _stat_def.aliases:
        _ALIAS_TO_STAT[_alias.lower()] = _stat_def.id


def all_stats() -> list[StatDef]:
    return list(_STATS)


def all_runes(include_special: bool = True) -> list[RuneDef]:
    runes = [RUNE_BY_ID[r] for r in RUNE_BY_ID if RUNE_BY_ID[r].stat_id]
    if include_special:
        runes.append(HUNTING_RUNE)
    return runes


def all_rune_ids(include_special: bool = False) -> list[str]:
    return [rune.id for rune in all_runes(include_special=include_special)]


def get_stat(stat_id: str) -> StatDef:
    key = stat_id.lower().strip()
    if key in STAT_BY_ID:
        return STAT_BY_ID[key]
    if key in _ALIAS_TO_STAT:
        return STAT_BY_ID[_ALIAS_TO_STAT[key]]
    raise KeyError(f"Unknown stat: {stat_id}")


def get_rune(rune_id: str) -> RuneDef:
    key = rune_id.lower().strip().replace(" ", "_")
    if key in RUNE_BY_ID:
        return RUNE_BY_ID[key]
    raise KeyError(f"Unknown rune: {rune_id}")


def resolve_stat_id(name: str) -> str:
    return get_stat(name).id


def weight_of_points(stat_id: str, points: int) -> float:
    return get_stat(stat_id).weight_of(points)


def max_over_points(stat_id: str) -> int:
    """Max points of over/exo on this line from the 101-weight cap."""
    return get_stat(stat_id).max_over_exo


def over_cap_points(stat_id: str) -> int:
    """Integer over/exo cap from the 101-weight rule (matches the published table)."""
    return get_stat(stat_id).max_over_exo


def is_heavy_stat(stat_id: str) -> bool:
    return get_stat(stat_id).role is StatRole.HEAVY


def is_filler_stat(stat_id: str) -> bool:
    return get_stat(stat_id).role is StatRole.FILLER


def rune_is_reliable_at(rune: RuneDef, current_value: int) -> bool:
    """True while current stat is below ~20× the rune bonus."""
    if rune.bonus <= 0:
        return True
    return current_value < rune.reliable_until


def weight_past_natural(stat_id: str, current: int, natural_max: Optional[int]) -> float:
    """Weight of the portion of `current` that sits past the item's own max roll."""
    if natural_max is None:
        return weight_of_points(stat_id, max(0, current))
    over = max(0, current - natural_max)
    return weight_of_points(stat_id, over)


def line_is_sc_only(
    stat_id: str,
    current: int,
    natural_max: Optional[int],
    bonus: int = 0,
) -> bool:
    """Heavy over/exo (>=30 weight past natural) mainly passes on SC (~1%)."""
    projected = current + bonus
    past = weight_past_natural(stat_id, projected, natural_max)
    return past >= HEAVY_LINE_WEIGHT
