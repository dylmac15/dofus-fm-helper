"""Screen-position mouse helper for the user's own Dofus client.

Clicks calibrated pixel coordinates only. No memory reading, packet injection,
or client modification.

Failsafes:
  * pyautogui FAILSAFE — slam the mouse into a screen corner
  * F8 / F12 global hotkeys (when pynput is available)
  * Pause / resume
  * Optional "Dofus must be foreground" check (win32 / xdotool; skipped on
    Linux if those tools are missing)
"""

from __future__ import annotations

import json
import random
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from .humanize import (
    ClickSettings,
    MovePlan,
    ThrowTiming,
    build_move_plan,
    sample_throw_timing,
)

DEFAULT_LAYOUT_PATH = Path.home() / ".config" / "dofus-fm-helper" / "layout.json"

# Slots the calibrator knows about besides individual runes.
CONTROL_SLOTS = ("apply_button", "item_slot", "inventory")


class AutomationStopped(Exception):
    """Raised when a failsafe fires or the user hits stop."""


@dataclass
class Point:
    x: int
    y: int

    def as_tuple(self) -> tuple[int, int]:
        return (self.x, self.y)


@dataclass
class Layout:
    name: str = "default"
    apply_button: Optional[Point] = None
    item_slot: Optional[Point] = None
    inventory: Optional[Point] = None
    runes: dict[str, Point] = field(default_factory=dict)
    click_offset_px: int = 6
    animation_delay_s: float = 1.2
    move_duration_min: float = 0.12
    move_duration_max: float = 0.35
    pre_click_delay_min: float = 0.05
    pre_click_delay_max: float = 0.18
    window_title_substring: str = "dofus"
    speed_profile: str = "natural"

    def to_dict(self) -> dict:
        def pt(p: Optional[Point]) -> Optional[list[int]]:
            return None if p is None else [p.x, p.y]

        return {
            "name": self.name,
            "apply_button": pt(self.apply_button),
            "item_slot": pt(self.item_slot),
            "inventory": pt(self.inventory),
            "runes": {k: [v.x, v.y] for k, v in self.runes.items()},
            "click_offset_px": self.click_offset_px,
            "animation_delay_s": self.animation_delay_s,
            "move_duration_min": self.move_duration_min,
            "move_duration_max": self.move_duration_max,
            "pre_click_delay_min": self.pre_click_delay_min,
            "pre_click_delay_max": self.pre_click_delay_max,
            "window_title_substring": self.window_title_substring,
            "speed_profile": self.speed_profile,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Layout":
        def pt(value) -> Optional[Point]:
            if not value:
                return None
            return Point(int(value[0]), int(value[1]))

        runes = {k: Point(int(v[0]), int(v[1])) for k, v in (data.get("runes") or {}).items()}
        return cls(
            name=data.get("name", "default"),
            apply_button=pt(data.get("apply_button")),
            item_slot=pt(data.get("item_slot")),
            inventory=pt(data.get("inventory")),
            runes=runes,
            click_offset_px=int(data.get("click_offset_px", 6)),
            animation_delay_s=float(data.get("animation_delay_s", 1.2)),
            move_duration_min=float(data.get("move_duration_min", 0.12)),
            move_duration_max=float(data.get("move_duration_max", 0.35)),
            pre_click_delay_min=float(data.get("pre_click_delay_min", 0.05)),
            pre_click_delay_max=float(data.get("pre_click_delay_max", 0.18)),
            window_title_substring=str(data.get("window_title_substring", "dofus")),
            speed_profile=str(data.get("speed_profile") or "natural"),
        )

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "Layout":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(data)

    def slot_names(self) -> list[str]:
        names = list(CONTROL_SLOTS)
        names.extend(sorted(self.runes))
        return names

    def get_slot(self, name: str) -> Optional[Point]:
        if name == "apply_button":
            return self.apply_button
        if name == "item_slot":
            return self.item_slot
        if name == "inventory":
            return self.inventory
        return self.runes.get(name)

    def set_slot(self, name: str, point: Point) -> None:
        if name == "apply_button":
            self.apply_button = point
        elif name == "item_slot":
            self.item_slot = point
        elif name == "inventory":
            self.inventory = point
        else:
            self.runes[name] = point

    def make_click_settings(self) -> ClickSettings:
        settings = ClickSettings.from_profile(self.speed_profile)
        settings.landing_jitter_px = max(0, int(self.click_offset_px))
        return settings


def _load_pyautogui():
    try:
        import pyautogui
    except Exception as exc:  # pragma: no cover - optional in CI
        raise RuntimeError(
            "pyautogui is not installed. Mouse automation is unavailable. "
            "Install deps from requirements.txt."
        ) from exc
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0
    return pyautogui


def current_mouse_position() -> Point:
    pag = _load_pyautogui()
    x, y = pag.position()
    return Point(int(x), int(y))


def is_dofus_foreground(substring: str = "dofus") -> bool:
    """True if the foreground window looks like Dofus. Degrades to True."""
    needle = substring.lower()
    try:
        import win32gui  # type: ignore

        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd) or ""
        return needle in title.lower()
    except ImportError:
        pass
    except Exception:
        return True

    try:
        import shutil
        import subprocess

        if shutil.which("xdotool"):
            title = subprocess.check_output(
                ["xdotool", "getactivewindow", "getwindowname"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
            return needle in title.lower()
    except Exception:
        pass

    try:
        import pygetwindow as gw  # type: ignore

        active = gw.getActiveWindow()
        if active is None:
            return True
        title = getattr(active, "title", "") or ""
        return needle in title.lower()
    except Exception:
        return True


class Clicker:
    """Plays a :class:`MovePlan` with pyautogui. FAILSAFE stays on."""

    def __init__(
        self,
        settings: Optional[ClickSettings] = None,
        *,
        checkpoint: Optional[Callable[[], None]] = None,
        wait: Optional[Callable[[float], None]] = None,
        on_failsafe: Optional[Callable[[str], None]] = None,
        position: Optional[Callable[[], tuple[int, int]]] = None,
        rng: Optional[random.Random] = None,
    ) -> None:
        self.settings = settings or ClickSettings.from_profile("natural")
        self.rng = rng or random.Random()
        self._checkpoint = checkpoint or (lambda: None)
        self._wait = wait or time.sleep
        self._on_failsafe = on_failsafe
        self._position = position
        self._pag = None
        self._last_click_end = 0.0

    def _module(self):
        if self._pag is None:
            self._pag = _load_pyautogui()
        else:
            self._pag.FAILSAFE = True
            self._pag.PAUSE = 0
        return self._pag

    def current_xy(self) -> tuple[int, int]:
        if self._position is not None:
            return self._position()
        pag = self._module()
        x, y = pag.position()
        return (int(x), int(y))

    def _respect_gap(self) -> None:
        gap = self.settings.min_action_gap
        if self._last_click_end <= 0:
            return
        remain = gap - (time.monotonic() - self._last_click_end)
        if remain > 0:
            self._wait(remain)

    def _follow(self, path: tuple[tuple[float, float], ...], duration_s: float) -> None:
        pag = self._module()
        if not path:
            return
        n = len(path)
        step = duration_s / max(n - 1, 1) if n > 1 else 0.0
        for i, (x, y) in enumerate(path):
            self._checkpoint()
            pag.moveTo(int(round(x)), int(round(y)), duration=0)
            if i < n - 1 and step > 0:
                self._wait(step)

    def play(self, plan: MovePlan) -> None:
        pag = self._module()
        try:
            self._respect_gap()
            self._follow(plan.path, plan.duration_s)
            if plan.micro_path:
                self._follow(plan.micro_path, plan.micro_duration_s)
            self._wait(plan.pre_click_s)
            self._checkpoint()
            pag.mouseDown()
            self._wait(plan.click_hold_s)
            pag.mouseUp()
        except pag.FailSafeException as exc:
            if self._on_failsafe:
                self._on_failsafe("pyautogui FAILSAFE (mouse in corner)")
            raise AutomationStopped("failsafe") from exc
        finally:
            self._last_click_end = time.monotonic()

    def click(self, point: Point) -> MovePlan:
        """Move along a humanized path and press the button. Returns the plan used."""
        self._checkpoint()
        start = self.current_xy()
        plan = build_move_plan(start, (point.x, point.y), self.settings, self.rng)
        self.play(plan)
        return plan


class MouseController:
    """Human-like clicks with pause, stop, and corner failsafe."""

    def __init__(
        self,
        layout: Optional[Layout] = None,
        require_foreground: bool = True,
        log: Optional[Callable[[str], None]] = None,
        click_settings: Optional[ClickSettings] = None,
    ) -> None:
        self.layout = layout or Layout()
        self.require_foreground = require_foreground
        self._log = log or (lambda _msg: None)
        self._stop = threading.Event()
        self._pause = threading.Event()
        self._hotkey_listener = None
        self._pag = None
        self.click_settings = click_settings or self.layout.make_click_settings()
        self.clicker = Clicker(
            self.click_settings,
            checkpoint=self._checkpoint,
            wait=self.wait_interruptible,
            on_failsafe=lambda reason: self.emergency_stop(reason),
            position=self._cursor_xy,
        )

    def log(self, msg: str) -> None:
        self._log(msg)

    @property
    def stopped(self) -> bool:
        return self._stop.is_set()

    @property
    def paused(self) -> bool:
        return self._pause.is_set()

    def emergency_stop(self, reason: str = "hotkey") -> None:
        self._stop.set()
        self._pause.clear()
        self.log(f"EMERGENCY STOP ({reason}). Move the mouse to a corner also aborts.")

    def pause(self) -> None:
        self._pause.set()
        self.log("Paused.")

    def resume(self) -> None:
        self._pause.clear()
        self.log("Resumed.")

    def toggle_pause(self) -> None:
        if self._pause.is_set():
            self.resume()
        else:
            self.pause()

    def reset_flags(self) -> None:
        self._stop.clear()
        self._pause.clear()

    def start_hotkeys(self) -> None:
        """Listen for F8 / F12 (stop) globally. Best-effort if pynput missing."""
        if self._hotkey_listener is not None:
            return
        try:
            from pynput import keyboard
        except ImportError:
            self.log("pynput not installed — use the UI Stop button and pyautogui corner failsafe.")
            return

        def on_press(key) -> None:
            try:
                if key in (keyboard.Key.f8, keyboard.Key.f12):
                    self.emergency_stop(reason=str(key))
            except Exception:
                return

        self._hotkey_listener = keyboard.Listener(on_press=on_press)
        self._hotkey_listener.daemon = True
        self._hotkey_listener.start()
        self.log("Hotkeys armed: F8 / F12 emergency stop. Mouse-to-corner failsafe on.")

    def stop_hotkeys(self) -> None:
        if self._hotkey_listener is not None:
            try:
                self._hotkey_listener.stop()
            except Exception:
                pass
            self._hotkey_listener = None

    def _pag_mod(self):
        if self._pag is None:
            self._pag = _load_pyautogui()
        else:
            self._pag.FAILSAFE = True
            self._pag.PAUSE = 0
        return self._pag

    def _cursor_xy(self) -> tuple[int, int]:
        pag = self._pag_mod()
        x, y = pag.position()
        return (int(x), int(y))

    def apply_click_settings(self, settings: ClickSettings) -> None:
        self.click_settings = settings
        self.clicker.settings = settings

    def _checkpoint(self) -> None:
        if self._stop.is_set():
            raise AutomationStopped("stopped")
        while self._pause.is_set():
            if self._stop.is_set():
                raise AutomationStopped("stopped")
            time.sleep(0.05)

    def wait_interruptible(self, seconds: float) -> None:
        end = time.monotonic() + max(0.0, seconds)
        while time.monotonic() < end:
            self._checkpoint()
            time.sleep(min(0.05, end - time.monotonic()))

    def human_click(self, point: Point) -> None:
        self._checkpoint()
        if self.require_foreground and not is_dofus_foreground(
            self.layout.window_title_substring
        ):
            raise AutomationStopped(
                "Dofus window is not in the foreground — click skipped."
            )
        self.clicker.settings = self.click_settings
        self.clicker.click(point)

    def click_slot(self, name: str) -> None:
        point = self.layout.get_slot(name)
        if point is None:
            raise AutomationStopped(f"Slot {name!r} is not calibrated.")
        self.log(f"Click {name} at ({point.x}, {point.y})")
        self.human_click(point)

    def throw_rune(self, rune_id: str, click_apply: bool = True) -> None:
        """Click the calibrated rune, optionally the craft/apply button, then wait."""
        if rune_id not in self.layout.runes:
            raise AutomationStopped(
                f"Rune {rune_id!r} has no calibrated position. "
                "Open the Calibration tab and hover + capture."
            )
        timing: ThrowTiming = sample_throw_timing(
            self.click_settings,
            self.layout.animation_delay_s,
            self.clicker.rng,
        )
        if timing.think_s:
            self.wait_interruptible(timing.think_s)
        self.click_slot(rune_id)
        if click_apply and self.layout.apply_button is not None:
            self.wait_interruptible(timing.rune_to_craft_s)
            self.click_slot("apply_button")
        self.wait_interruptible(timing.after_craft_s)

    def repeat_throw(
        self,
        rune_id: str,
        times: int,
        click_apply: bool = True,
        between_callback: Optional[Callable[[int], None]] = None,
    ) -> int:
        """Auto-repeat a rune N times or until stop. Returns throws completed."""
        done = 0
        self.reset_flags()
        for i in range(max(0, times)):
            self._checkpoint()
            self.throw_rune(rune_id, click_apply=click_apply)
            done += 1
            if between_callback:
                between_callback(done)
        return done
