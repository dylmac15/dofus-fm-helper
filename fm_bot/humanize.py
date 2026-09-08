"""Pure mouse-humanization helpers (no GUI, no display).

Bezier paths, Fitts-style move times, and clipped-Gaussian delays so clicks
do not look like a straight lerp plus uniform sleep.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, replace
from typing import Sequence

PROFILE_NAMES = ("slow", "natural", "fast")

# Hard floors so even the "fast" profile cannot machine-gun clicks (~20/s).
ABSOLUTE_MIN_MOVE_S = 0.07
ABSOLUTE_MIN_HOLD_S = 0.032
ABSOLUTE_MIN_PRE_CLICK_S = 0.03
ABSOLUTE_MIN_GAP_S = 0.10
ABSOLUTE_MIN_BETWEEN_CLICKS_S = 0.07


@dataclass
class ClickSettings:
    """Tunable humanization. Build with :meth:`from_profile` for defaults."""

    profile: str = "natural"
    speed_scale: float = 1.0

    # Fitts's law: T = a + b * log2(D/W + 1). Rune icons / craft are large.
    fitts_a: float = 0.09
    fitts_b: float = 0.11
    target_width_px: float = 40.0
    min_move_duration: float = 0.10
    max_move_duration: float = 0.62

    # Spatial path
    wobble_frac: float = 0.055
    wobble_min_px: float = 3.5
    wobble_max_px: float = 16.0
    overshoot_prob: float = 0.32
    overshoot_frac: float = 0.07
    overshoot_min_distance: float = 48.0
    overshoot_min_px: float = 4.0
    overshoot_max_px: float = 14.0

    # Land a few pixels off the calibrated pixel, then maybe ease in.
    landing_jitter_px: int = 6
    micro_correct_prob: float = 0.62
    micro_correct_min_px: float = 1.0
    micro_duration_mean: float = 0.045
    micro_duration_std: float = 0.014
    micro_duration_min: float = 0.022
    micro_duration_max: float = 0.09

    # Mouse-down hold (not an instant click)
    click_hold_mean: float = 0.062
    click_hold_std: float = 0.018
    click_hold_min: float = 0.036
    click_hold_max: float = 0.15

    # Pause between arriving and pressing
    pre_click_mean: float = 0.075
    pre_click_std: float = 0.028
    pre_click_min: float = 0.038
    pre_click_max: float = 0.16
    confirm_pause_prob: float = 0.13
    confirm_mean: float = 0.22
    confirm_std: float = 0.06
    confirm_min: float = 0.14
    confirm_max: float = 0.38

    # Rune → craft gap
    rune_to_craft_mean: float = 0.18
    rune_to_craft_std: float = 0.055
    rune_to_craft_min: float = 0.08
    rune_to_craft_max: float = 0.42

    # Extra wait after craft, on top of the layout animation delay
    min_after_craft: float = 0.28
    after_craft_rel_std: float = 0.11

    # Rare "thinking" hesitation
    think_pause_prob: float = 0.035
    think_pause_mean: float = 0.48
    think_pause_std: float = 0.14
    think_pause_min: float = 0.25
    think_pause_max: float = 0.95

    # Floor between completed clicks (down+up finished → next move starts)
    min_action_gap: float = 0.13

    def __post_init__(self) -> None:
        self.min_move_duration = max(ABSOLUTE_MIN_MOVE_S, float(self.min_move_duration))
        self.click_hold_min = max(ABSOLUTE_MIN_HOLD_S, float(self.click_hold_min))
        self.pre_click_min = max(ABSOLUTE_MIN_PRE_CLICK_S, float(self.pre_click_min))
        self.min_action_gap = max(ABSOLUTE_MIN_GAP_S, float(self.min_action_gap))
        self.rune_to_craft_min = max(ABSOLUTE_MIN_BETWEEN_CLICKS_S, float(self.rune_to_craft_min))
        self.max_move_duration = max(self.min_move_duration, float(self.max_move_duration))
        self.click_hold_max = max(self.click_hold_min, float(self.click_hold_max))
        self.pre_click_max = max(self.pre_click_min, float(self.pre_click_max))

    @property
    def min_click_period_s(self) -> float:
        """Fastest possible down→up cycle including the post-click gap."""
        return self.min_action_gap + self.click_hold_min + self.pre_click_min

    @classmethod
    def from_profile(cls, name: str = "natural") -> "ClickSettings":
        key = (name or "natural").strip().lower()
        if key not in PROFILE_NAMES:
            key = "natural"
        base = cls(profile=key)
        tweaks = _PROFILE_TWEAKS[key]
        if tweaks:
            return replace(base, **tweaks)
        return base


_PROFILE_TWEAKS: dict[str, dict] = {
    "slow": {
        "speed_scale": 1.38,
        "fitts_a": 0.12,
        "fitts_b": 0.13,
        "min_move_duration": 0.15,
        "max_move_duration": 0.88,
        "min_action_gap": 0.18,
        "think_pause_prob": 0.07,
        "confirm_pause_prob": 0.22,
        "overshoot_prob": 0.4,
        "micro_correct_prob": 0.78,
        "landing_jitter_px": 7,
        "rune_to_craft_mean": 0.26,
        "rune_to_craft_std": 0.08,
        "rune_to_craft_min": 0.12,
        "rune_to_craft_max": 0.55,
        "pre_click_mean": 0.11,
        "click_hold_mean": 0.078,
        "min_after_craft": 0.4,
    },
    "natural": {},
    "fast": {
        "speed_scale": 0.8,
        "fitts_a": 0.07,
        "fitts_b": 0.09,
        "min_move_duration": 0.075,
        "max_move_duration": 0.42,
        "min_action_gap": 0.11,
        "think_pause_prob": 0.016,
        "confirm_pause_prob": 0.06,
        "overshoot_prob": 0.2,
        "micro_correct_prob": 0.45,
        "landing_jitter_px": 5,
        "rune_to_craft_mean": 0.12,
        "rune_to_craft_std": 0.04,
        "rune_to_craft_min": 0.07,
        "rune_to_craft_max": 0.28,
        "pre_click_mean": 0.052,
        "pre_click_std": 0.02,
        "pre_click_max": 0.12,
        "click_hold_mean": 0.048,
        "click_hold_std": 0.012,
        "click_hold_min": 0.032,
        "click_hold_max": 0.11,
        "min_after_craft": 0.2,
        "think_pause_mean": 0.32,
        "think_pause_max": 0.7,
    },
}


@dataclass(frozen=True)
class MovePlan:
    """One cursor trip plus the click that follows. Playback-only after this."""

    path: tuple[tuple[float, float], ...]
    landing: tuple[int, int]
    micro_path: tuple[tuple[float, float], ...]
    duration_s: float
    micro_duration_s: float
    pre_click_s: float
    click_hold_s: float
    overshot: bool = False


@dataclass(frozen=True)
class ThrowTiming:
    think_s: float
    rune_to_craft_s: float
    after_craft_s: float


def min_jerk(t: float) -> float:
    """Classic human reaching law: slow–fast–slow. ``t`` in [0, 1]."""
    t = 0.0 if t < 0.0 else 1.0 if t > 1.0 else t
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def hypot(dx: float, dy: float) -> float:
    return math.hypot(dx, dy)


def sample_delay(
    mean: float,
    std: float,
    lo: float,
    hi: float,
    rng: random.Random,
) -> float:
    """Gaussian delay clipped to ``[lo, hi]``. Never uniform-in-range."""
    lo = max(0.0, float(lo))
    hi = max(lo, float(hi))
    mean = min(hi, max(lo, float(mean)))
    if std <= 1e-9:
        return mean
    for _ in range(16):
        value = rng.gauss(mean, std)
        if lo <= value <= hi:
            return value
    return min(hi, max(lo, mean))


def fitts_move_duration(distance: float, settings: ClickSettings) -> float:
    """Deterministic Fitts duration (no noise). Short hops stay quick."""
    distance = max(0.0, float(distance))
    width = max(1.0, float(settings.target_width_px))
    raw = settings.fitts_a + settings.fitts_b * math.log2(distance / width + 1.0)
    scaled = raw * settings.speed_scale
    return min(settings.max_move_duration, max(settings.min_move_duration, scaled))


def sample_move_duration(
    distance: float,
    settings: ClickSettings,
    rng: random.Random,
) -> float:
    base = fitts_move_duration(distance, settings)
    return sample_delay(
        mean=base,
        std=max(0.012, base * 0.14),
        lo=max(settings.min_move_duration, base * 0.72),
        hi=min(settings.max_move_duration, base * 1.38),
        rng=rng,
    )


def sample_click_hold(settings: ClickSettings, rng: random.Random) -> float:
    return sample_delay(
        settings.click_hold_mean,
        settings.click_hold_std,
        settings.click_hold_min,
        settings.click_hold_max,
        rng,
    )


def sample_pre_click(settings: ClickSettings, rng: random.Random) -> float:
    if rng.random() < settings.confirm_pause_prob:
        return sample_delay(
            settings.confirm_mean,
            settings.confirm_std,
            settings.confirm_min,
            settings.confirm_max,
            rng,
        )
    return sample_delay(
        settings.pre_click_mean,
        settings.pre_click_std,
        settings.pre_click_min,
        settings.pre_click_max,
        rng,
    )


def sample_think_pause(settings: ClickSettings, rng: random.Random) -> float:
    if rng.random() >= settings.think_pause_prob:
        return 0.0
    return sample_delay(
        settings.think_pause_mean,
        settings.think_pause_std,
        settings.think_pause_min,
        settings.think_pause_max,
        rng,
    )


def sample_after_craft(
    animation_delay_s: float,
    settings: ClickSettings,
    rng: random.Random,
) -> float:
    mean = max(float(animation_delay_s), settings.min_after_craft)
    std = max(0.06, mean * settings.after_craft_rel_std)
    lo = max(settings.min_after_craft, mean * 0.78)
    hi = max(lo + 0.05, mean * 1.28)
    return sample_delay(mean, std, lo, hi, rng)


def sample_throw_timing(
    settings: ClickSettings,
    animation_delay_s: float,
    rng: random.Random,
) -> ThrowTiming:
    return ThrowTiming(
        think_s=sample_think_pause(settings, rng),
        rune_to_craft_s=sample_delay(
            settings.rune_to_craft_mean,
            settings.rune_to_craft_std,
            settings.rune_to_craft_min,
            settings.rune_to_craft_max,
            rng,
        ),
        after_craft_s=sample_after_craft(animation_delay_s, settings, rng),
    )


def landing_point(
    target: tuple[float, float],
    settings: ClickSettings,
    rng: random.Random,
) -> tuple[int, int]:
    jitter = max(0, int(settings.landing_jitter_px))
    tx, ty = float(target[0]), float(target[1])
    if jitter <= 0:
        return (int(round(tx)), int(round(ty)))
    sigma = jitter * 0.45
    dx = min(jitter, max(-jitter, rng.gauss(0.0, sigma)))
    dy = min(jitter, max(-jitter, rng.gauss(0.0, sigma)))
    return (int(round(tx + dx)), int(round(ty + dy)))


def cubic_bezier_point(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    t: float,
) -> tuple[float, float]:
    u = 1.0 - t
    uu, tt = u * u, t * t
    uuu, ttt = uu * u, tt * t
    x = uuu * p0[0] + 3.0 * uu * t * p1[0] + 3.0 * u * tt * p2[0] + ttt * p3[0]
    y = uuu * p0[1] + 3.0 * uu * t * p1[1] + 3.0 * u * tt * p2[1] + ttt * p3[1]
    return (x, y)


def bezier_controls(
    start: tuple[float, float],
    end: tuple[float, float],
    settings: ClickSettings,
    rng: random.Random,
    *,
    short: bool = False,
) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float], tuple[float, float]]:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    dist = math.hypot(dx, dy)
    if dist < 1e-6:
        return start, start, end, end
    px, py = -dy / dist, dx / dist
    cap = settings.wobble_max_px * (0.4 if short else 1.0)
    floor = settings.wobble_min_px * (0.35 if short else 1.0)
    amp = min(cap, max(floor, dist * settings.wobble_frac))
    sign = -1.0 if rng.random() < 0.5 else 1.0
    a1 = rng.uniform(0.45, 1.0) * amp * sign
    if rng.random() < 0.7:
        a2 = rng.uniform(0.3, 1.0) * amp * sign
    else:
        a2 = rng.uniform(0.3, 1.0) * amp * -sign
    t1 = rng.uniform(0.18, 0.38)
    t2 = rng.uniform(0.58, 0.82)
    p1 = (start[0] + dx * t1 + px * a1, start[1] + dy * t1 + py * a1)
    p2 = (start[0] + dx * t2 + px * a2, start[1] + dy * t2 + py * a2)
    return start, p1, p2, end


def point_count(distance: float, *, short: bool = False) -> int:
    if short:
        return max(4, min(12, int(4 + distance / 18.0)))
    return max(6, min(48, int(6 + distance / 12.0)))


def bezier_path(
    start: tuple[float, float],
    end: tuple[float, float],
    settings: ClickSettings,
    rng: random.Random,
    *,
    short: bool = False,
) -> list[tuple[float, float]]:
    dist = math.hypot(end[0] - start[0], end[1] - start[1])
    if dist < 2.0:
        return [start, end]
    p0, p1, p2, p3 = bezier_controls(start, end, settings, rng, short=short)
    n = point_count(dist, short=short)
    points: list[tuple[float, float]] = []
    for i in range(n):
        t = i / (n - 1)
        points.append(cubic_bezier_point(p0, p1, p2, p3, min_jerk(t)))
    return points


def overshoot_point(
    start: tuple[float, float],
    landing: tuple[float, float],
    settings: ClickSettings,
    rng: random.Random,
) -> tuple[float, float]:
    dx = landing[0] - start[0]
    dy = landing[1] - start[1]
    dist = math.hypot(dx, dy) or 1.0
    extra = rng.uniform(settings.overshoot_min_px, settings.overshoot_max_px)
    extra = min(extra, dist * settings.overshoot_frac)
    nx, ny = dx / dist, dy / dist
    px, py = -ny, nx
    lateral = rng.gauss(0.0, 1.8)
    return (landing[0] + nx * extra + px * lateral, landing[1] + ny * extra + py * lateral)


def toward_target(
    landing: tuple[int, int],
    target: tuple[float, float],
    rng: random.Random,
) -> tuple[int, int]:
    """Ease most of the way back toward the calibrated point, still not exact."""
    lx, ly = float(landing[0]), float(landing[1])
    tx, ty = float(target[0]), float(target[1])
    frac = rng.uniform(0.45, 0.85)
    mx = lx + (tx - lx) * frac + rng.gauss(0.0, 0.4)
    my = ly + (ty - ly) * frac + rng.gauss(0.0, 0.4)
    return (int(round(mx)), int(round(my)))


def max_deviation_from_segment(
    path: Sequence[tuple[float, float]],
    start: tuple[float, float],
    end: tuple[float, float],
) -> float:
    """Largest perpendicular distance from the chord — used by tests."""
    ax, ay = start
    dx, dy = end[0] - ax, end[1] - ay
    denom = math.hypot(dx, dy)
    if denom < 1e-6:
        return 0.0
    worst = 0.0
    for x, y in path:
        cross = abs((x - ax) * dy - (y - ay) * dx) / denom
        if cross > worst:
            worst = cross
    return worst


def path_speeds(path: Sequence[tuple[float, float]], duration_s: float) -> list[float]:
    """Approximate px/s between consecutive samples assuming equal time steps."""
    if len(path) < 2 or duration_s <= 0:
        return []
    dt = duration_s / (len(path) - 1)
    return [
        math.hypot(path[i][0] - path[i - 1][0], path[i][1] - path[i - 1][1]) / dt
        for i in range(1, len(path))
    ]


def build_move_plan(
    start: tuple[float, float],
    target: tuple[float, float],
    settings: ClickSettings,
    rng: random.Random,
) -> MovePlan:
    """Plan a curved trip from ``start`` to a jittered landing near ``target``."""
    start_f = (float(start[0]), float(start[1]))
    target_f = (float(target[0]), float(target[1]))
    land = landing_point(target_f, settings, rng)
    land_f = (float(land[0]), float(land[1]))
    dist = math.hypot(land_f[0] - start_f[0], land_f[1] - start_f[1])

    overshot = False
    main_end = land_f
    if dist >= settings.overshoot_min_distance and rng.random() < settings.overshoot_prob:
        overshot = True
        main_end = overshoot_point(start_f, land_f, settings, rng)

    path = bezier_path(start_f, main_end, settings, rng, short=dist < 28.0)
    if overshot:
        back = bezier_path(main_end, land_f, settings, rng, short=True)
        path = path + back[1:]

    duration = sample_move_duration(dist, settings, rng)
    if overshot:
        duration = min(settings.max_move_duration, duration * 1.08)

    micro_path: tuple[tuple[float, float], ...] = ()
    micro_duration = 0.0
    click_at = land
    if (
        settings.landing_jitter_px > 0
        and rng.random() < settings.micro_correct_prob
        and math.hypot(land[0] - target_f[0], land[1] - target_f[1]) >= settings.micro_correct_min_px
    ):
        corrected = toward_target(land, target_f, rng)
        if math.hypot(corrected[0] - land[0], corrected[1] - land[1]) >= 1.0:
            micro_path = (
                (float(land[0]), float(land[1])),
                (float(corrected[0]), float(corrected[1])),
            )
            micro_duration = sample_delay(
                settings.micro_duration_mean,
                settings.micro_duration_std,
                settings.micro_duration_min,
                settings.micro_duration_max,
                rng,
            )
            click_at = corrected

    return MovePlan(
        path=tuple(path),
        landing=click_at,
        micro_path=micro_path,
        duration_s=duration,
        micro_duration_s=micro_duration,
        pre_click_s=sample_pre_click(settings, rng),
        click_hold_s=sample_click_hold(settings, rng),
        overshot=overshot,
    )
