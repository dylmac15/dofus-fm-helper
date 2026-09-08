"""Tkinter desktop UI for the Forgemage helper."""

from __future__ import annotations

import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Optional

from . import __version__
from .engine import ItemState, MageMode, Outcome, StatLine
from .mouse import (
    DEFAULT_LAYOUT_PATH,
    AutomationStopped,
    ClickSettings,
    Layout,
    MouseController,
    Point,
    current_mouse_position,
)
from .presets import load_preset, preset_names
from .runes import all_runes, all_stats, get_stat

TOS_BANNER = (
    "Ankama forbids bots. Using this clicker on the live Dofus client can get "
    "the account banned. This tool only moves YOUR mouse on YOUR screen."
)


class FMApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"Dofus Forgemage Helper v{__version__}")
        self.geometry("1180x780")
        self.minsize(960, 640)

        self.session = load_preset("Typical stuff cape")
        self.layout = Layout()
        if DEFAULT_LAYOUT_PATH.exists():
            try:
                self.layout = Layout.load(DEFAULT_LAYOUT_PATH)
            except Exception:
                pass
        self.mouse = MouseController(self.layout, require_foreground=True, log=self._log)
        self._stat_vars: dict[str, dict[str, tk.Variable]] = {}
        self._worker: Optional[threading.Thread] = None
        self._awaiting_outcome = threading.Event()
        self._pending_outcome: Optional[Outcome] = None

        self._build()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<F8>", lambda _e: self._stop())
        self.bind("<F12>", lambda _e: self._stop())
        self.bind("<Key-s>", lambda _e: self._report(Outcome.SC))
        self.bind("<Key-S>", lambda _e: self._report(Outcome.SC))
        self.bind("<Key-n>", lambda _e: self._report(Outcome.SN))
        self.bind("<Key-N>", lambda _e: self._report(Outcome.SN))
        self.bind("<Key-e>", lambda _e: self._report(Outcome.EC))
        self.bind("<Key-E>", lambda _e: self._report(Outcome.EC))
        self.after(200, self._refresh_recommendation)

    # --- layout ----------------------------------------------------------

    def _build(self) -> None:
        banner = tk.Label(
            self,
            text=TOS_BANNER,
            bg="#7a1f1f",
            fg="white",
            wraplength=1100,
            pady=6,
            font=("TkDefaultFont", 9, "bold"),
        )
        banner.pack(fill=tk.X)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self.tab_mage = ttk.Frame(self.notebook)
        self.tab_cal = ttk.Frame(self.notebook)
        self.tab_settings = ttk.Frame(self.notebook)
        self.tab_runes = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_mage, text="Mage")
        self.notebook.add(self.tab_cal, text="Calibration")
        self.notebook.add(self.tab_settings, text="Settings")
        self.notebook.add(self.tab_runes, text="Rune table")

        self._build_mage()
        self._build_calibration()
        self._build_settings()
        self._build_runes()

        status = ttk.Frame(self)
        status.pack(fill=tk.X, padx=6, pady=(0, 6))
        self.status_var = tk.StringVar(value="Idle — F8/F12 emergency stop. Corner failsafe on.")
        ttk.Label(status, textvariable=self.status_var).pack(side=tk.LEFT)

    def _build_mage(self) -> None:
        top = ttk.Frame(self.tab_mage)
        top.pack(fill=tk.X, pady=4)
        ttk.Label(top, text="Preset").pack(side=tk.LEFT)
        self.preset_var = tk.StringVar(value="Typical stuff cape")
        box = ttk.Combobox(
            top,
            textvariable=self.preset_var,
            values=preset_names(),
            state="readonly",
            width=36,
        )
        box.pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Load", command=self._load_preset).pack(side=tk.LEFT)
        ttk.Label(top, text="Mode").pack(side=tk.LEFT, padx=(16, 4))
        self.mode_var = tk.StringVar(value=self.session.mode.value)
        mode = ttk.Combobox(
            top,
            textvariable=self.mode_var,
            values=[m.value for m in MageMode],
            state="readonly",
            width=12,
        )
        mode.pack(side=tk.LEFT)
        mode.bind("<<ComboboxSelected>>", lambda _e: self._apply_mode())
        ttk.Button(top, text="Add stat", command=self._add_stat_dialog).pack(side=tk.RIGHT)

        body = ttk.Panedwindow(self.tab_mage, orient=tk.HORIZONTAL)
        body.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(body)
        right = ttk.Frame(body)
        body.add(left, weight=3)
        body.add(right, weight=2)

        cols = ("stat", "current", "min", "max", "target", "w/pt", "over")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", height=14)
        headings = {
            "stat": "Stat",
            "current": "Current",
            "min": "Min",
            "max": "Max",
            "target": "Target",
            "w/pt": "Weight/pt",
            "over": "Over/exo",
        }
        widths = {"stat": 160, "current": 70, "min": 50, "max": 50, "target": 70, "w/pt": 80, "over": 80}
        for col in cols:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=widths[col], anchor=tk.CENTER)
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        scroll = ttk.Scrollbar(left, command=self.tree.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.bind("<<TreeviewSelect>>", self._on_select_line)

        edit = ttk.LabelFrame(right, text="Edit selected line")
        edit.pack(fill=tk.X, padx=4, pady=4)
        self.edit_stat = tk.StringVar()
        self.edit_current = tk.IntVar(value=0)
        self.edit_min = tk.IntVar(value=0)
        self.edit_max = tk.IntVar(value=0)
        self.edit_target = tk.IntVar(value=0)
        ttk.Label(edit, textvariable=self.edit_stat).grid(row=0, column=0, columnspan=4, sticky=tk.W)
        for i, (label, var) in enumerate(
            (("Current", self.edit_current), ("Min", self.edit_min), ("Max", self.edit_max), ("Target", self.edit_target)),
            start=1,
        ):
            ttk.Label(edit, text=label).grid(row=i, column=0, sticky=tk.W, padx=4)
            ttk.Spinbox(edit, from_=-50, to=2000, textvariable=var, width=8).grid(
                row=i, column=1, sticky=tk.W
            )
        ttk.Button(edit, text="Apply line", command=self._apply_line_edits).grid(
            row=5, column=0, columnspan=2, pady=4
        )

        sink_fr = ttk.LabelFrame(right, text="Sink / puits / reliquat")
        sink_fr.pack(fill=tk.X, padx=4, pady=4)
        self.sink_var = tk.DoubleVar(value=self.session.sink)
        self.gap_var = tk.StringVar()
        ttk.Label(sink_fr, text="Session sink").grid(row=0, column=0, sticky=tk.W, padx=4)
        ttk.Spinbox(sink_fr, from_=0, to=5000, increment=1, textvariable=self.sink_var, width=10).grid(
            row=0, column=1
        )
        ttk.Button(sink_fr, text="Set", command=self._apply_sink).grid(row=0, column=2, padx=4)
        ttk.Button(sink_fr, text="From dropped mins", command=self._recompute_sink).grid(
            row=0, column=3, padx=4
        )
        ttk.Label(sink_fr, textvariable=self.gap_var, wraplength=360).grid(
            row=1, column=0, columnspan=4, sticky=tk.W, padx=4, pady=4
        )

        rec_fr = ttk.LabelFrame(right, text="Next rune")
        rec_fr.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.rec_title = tk.StringVar(value="—")
        self.rec_body = tk.StringVar(value="")
        ttk.Label(rec_fr, textvariable=self.rec_title, font=("TkDefaultFont", 11, "bold"), wraplength=380).pack(
            anchor=tk.W, padx=6, pady=(6, 2)
        )
        ttk.Label(rec_fr, textvariable=self.rec_body, wraplength=380, justify=tk.LEFT).pack(
            anchor=tk.W, padx=6, pady=2
        )

        ctrl = ttk.LabelFrame(right, text="Clicker")
        ctrl.pack(fill=tk.X, padx=4, pady=4)
        self.click_mode = tk.StringVar(value="semi")
        ttk.Radiobutton(ctrl, text="Recommend only", variable=self.click_mode, value="manual").grid(
            row=0, column=0, sticky=tk.W
        )
        ttk.Radiobutton(
            ctrl, text="Semi-auto (click, then S/N/E)", variable=self.click_mode, value="semi"
        ).grid(row=0, column=1, sticky=tk.W)
        ttk.Radiobutton(
            ctrl, text="Auto-repeat (assume SC)", variable=self.click_mode, value="auto"
        ).grid(row=1, column=0, sticky=tk.W)
        ttk.Label(ctrl, text="Repeat N").grid(row=1, column=1, sticky=tk.E)
        self.repeat_n = tk.IntVar(value=10)
        ttk.Spinbox(ctrl, from_=1, to=500, textvariable=self.repeat_n, width=6).grid(
            row=1, column=2, sticky=tk.W
        )
        ttk.Label(ctrl, text="Humanization").grid(row=2, column=0, sticky=tk.W, padx=4)
        self.feel_var = tk.StringVar(value=self.layout.speed_profile or "natural")
        feel = ttk.Combobox(
            ctrl,
            textvariable=self.feel_var,
            values=("slow", "natural", "fast"),
            state="readonly",
            width=10,
        )
        feel.grid(row=2, column=1, sticky=tk.W)
        feel.bind("<<ComboboxSelected>>", lambda _e: self._apply_settings())
        btns = ttk.Frame(ctrl)
        btns.grid(row=3, column=0, columnspan=3, pady=6)
        ttk.Button(btns, text="Start", command=self._start).pack(side=tk.LEFT, padx=3)
        ttk.Button(btns, text="Pause/Resume", command=self._toggle_pause).pack(side=tk.LEFT, padx=3)
        ttk.Button(btns, text="Stop", command=self._stop).pack(side=tk.LEFT, padx=3)
        out = ttk.Frame(ctrl)
        out.grid(row=4, column=0, columnspan=3, pady=4)
        ttk.Button(out, text="SC (S)", command=lambda: self._report(Outcome.SC)).pack(side=tk.LEFT, padx=3)
        ttk.Button(out, text="SN (N)", command=lambda: self._report(Outcome.SN)).pack(side=tk.LEFT, padx=3)
        ttk.Button(out, text="EC (E)", command=lambda: self._report(Outcome.EC)).pack(side=tk.LEFT, padx=3)
        ttk.Button(out, text="Refresh", command=self._refresh_recommendation).pack(side=tk.LEFT, padx=3)

        log_fr = ttk.LabelFrame(self.tab_mage, text="Log")
        log_fr.pack(fill=tk.BOTH, padx=4, pady=4)
        self.log_text = tk.Text(log_fr, height=8, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _build_calibration(self) -> None:
        hint = ttk.Label(
            self.tab_cal,
            text=(
                "Hover the Dofus rune (or Apply / item slot) and click Capture. "
                "A 2s countdown lets you switch windows. Positions are screen pixels."
            ),
            wraplength=1000,
        )
        hint.pack(anchor=tk.W, padx=8, pady=8)

        bar = ttk.Frame(self.tab_cal)
        bar.pack(fill=tk.X, padx=8)
        ttk.Label(bar, text="Slot").pack(side=tk.LEFT)
        self.cal_slot = tk.StringVar(value="apply_button")
        slots = ["apply_button", "item_slot", "inventory"] + [r.id for r in all_runes()]
        self.cal_combo = ttk.Combobox(bar, textvariable=self.cal_slot, values=slots, width=28)
        self.cal_combo.pack(side=tk.LEFT, padx=4)
        ttk.Button(bar, text="Capture in 2s", command=self._capture_slot).pack(side=tk.LEFT, padx=4)
        ttk.Button(bar, text="Capture now", command=self._capture_now).pack(side=tk.LEFT)
        ttk.Button(bar, text="Save layout", command=self._save_layout).pack(side=tk.LEFT, padx=8)
        ttk.Button(bar, text="Load layout", command=self._load_layout).pack(side=tk.LEFT)

        cols = ("slot", "x", "y")
        self.cal_tree = ttk.Treeview(self.tab_cal, columns=cols, show="headings", height=18)
        for col, w in (("slot", 220), ("x", 80), ("y", 80)):
            self.cal_tree.heading(col, text=col.upper())
            self.cal_tree.column(col, width=w)
        self.cal_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.cal_tree.bind("<<TreeviewSelect>>", self._on_select_cal)
        self._refresh_cal_tree()

    def _build_settings(self) -> None:
        frm = ttk.Frame(self.tab_settings)
        frm.pack(anchor=tk.NW, padx=16, pady=16)

        self.require_fg = tk.BooleanVar(value=True)
        self.click_apply = tk.BooleanVar(value=True)
        self.stop_empty = tk.BooleanVar(value=True)
        self.assume_sc = tk.BooleanVar(value=False)
        self.budget = tk.StringVar(value="")
        self.max_attempts = tk.StringVar(value="")
        self.anim_delay = tk.DoubleVar(value=self.layout.animation_delay_s)
        self.click_offset = tk.IntVar(value=self.layout.click_offset_px)
        self.window_sub = tk.StringVar(value=self.layout.window_title_substring)

        row = 0

        def check(text, var):
            nonlocal row
            ttk.Checkbutton(frm, text=text, variable=var, command=self._apply_settings).grid(
                row=row, column=0, columnspan=2, sticky=tk.W, pady=2
            )
            row += 1

        check("Require Dofus window in foreground (win32 / xdotool; ignored if unavailable)", self.require_fg)
        check("Click Apply / craft button after the rune", self.click_apply)
        check("Stop when sink is empty before a heavy rune", self.stop_empty)
        check("Assume SC until pause (low-risk grinding only)", self.assume_sc)

        for label, var in (
            ("Budget kamas (empty = none)", self.budget),
            ("Max attempts (empty = none)", self.max_attempts),
            ("Craft animation delay (s)", self.anim_delay),
            ("Click offset (px)", self.click_offset),
            ("Foreground title contains", self.window_sub),
        ):
            ttk.Label(frm, text=label).grid(row=row, column=0, sticky=tk.W, pady=3)
            ttk.Entry(frm, textvariable=var, width=18).grid(row=row, column=1, sticky=tk.W)
            row += 1
        ttk.Button(frm, text="Apply settings", command=self._apply_settings).grid(
            row=row, column=0, pady=8, sticky=tk.W
        )

        help_txt = (
            "Hotkeys (this window): F8 / F12 stop · S = SC · N = SN · E = EC\n"
            "Global (if pynput is installed): F8 / F12 still stop while Dofus is focused.\n"
            "Mouse paths are humanized (curved, variable speed). "
            "pyautogui FAILSAFE: shove the mouse into any screen corner."
        )
        ttk.Label(frm, text=help_txt, justify=tk.LEFT).grid(
            row=row + 1, column=0, columnspan=2, sticky=tk.W, pady=12
        )

    def _build_runes(self) -> None:
        cols = ("stat", "wpt", "small", "pa", "ra", "over")
        tree = ttk.Treeview(self.tab_runes, columns=cols, show="headings")
        headers = {
            "stat": "Stat",
            "wpt": "Weight/pt",
            "small": "Small (bonus/weight)",
            "pa": "Pa",
            "ra": "Ra",
            "over": "Max over/exo",
        }
        for col in cols:
            tree.heading(col, text=headers[col])
            tree.column(col, width=160 if col != "wpt" else 90)
        for stat in all_stats():
            by_size = {r.size.value: r for r in stat.runes}

            def fmt(key: str) -> str:
                r = by_size.get(key)
                return f"+{r.bonus} / {r.weight:g}" if r else "—"

            tree.insert(
                "",
                tk.END,
                values=(
                    f"{stat.name} ({stat.french})",
                    f"{stat.weight_per_point:g}",
                    fmt("small"),
                    fmt("pa"),
                    fmt("ra"),
                    f"+{stat.max_over_exo}",
                ),
            )
        tree.insert("", tk.END, values=("Hunting rune", "5", "Chasse / 5", "—", "—", "—"))
        tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

    # --- data / ui sync --------------------------------------------------

    def _log(self, msg: str) -> None:
        def _append() -> None:
            self.log_text.configure(state=tk.NORMAL)
            self.log_text.insert(tk.END, msg + "\n")
            self.log_text.see(tk.END)
            self.log_text.configure(state=tk.DISABLED)
            self.status_var.set(msg[:120])

        if threading.current_thread() is threading.main_thread():
            _append()
        else:
            self.after(0, _append)

    def _reload_tree(self) -> None:
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for line in self.session.item.lines.values():
            stat = get_stat(line.stat_id)
            exo = "exo" if not line.is_natural else f"{line.over_points()} pts"
            self.tree.insert(
                "",
                tk.END,
                iid=line.stat_id,
                values=(
                    stat.name,
                    line.current,
                    line.natural_min,
                    line.natural_max,
                    line.target,
                    f"{stat.weight_per_point:g}",
                    exo,
                ),
            )
        self.sink_var.set(self.session.sink)
        self.gap_var.set(
            f"Roll-gap (vs best natural rolls): {self.session.roll_gap:g} weight. "
            f"Session sink used for decisions: {self.session.sink:g}."
        )

    def _on_select_line(self, _evt=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        line = self.session.item.lines[sel[0]]
        self.edit_stat.set(get_stat(line.stat_id).name)
        self.edit_current.set(line.current)
        self.edit_min.set(line.natural_min)
        self.edit_max.set(line.natural_max)
        self.edit_target.set(line.target)

    def _apply_line_edits(self) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        line = self.session.item.lines[sel[0]]
        new_current = int(self.edit_current.get())
        if new_current != line.current:
            self.session.note_stat_change(line.stat_id, new_current)
        line.natural_min = int(self.edit_min.get())
        line.natural_max = int(self.edit_max.get())
        line.target = int(self.edit_target.get())
        self._reload_tree()
        self._refresh_recommendation()

    def _apply_sink(self) -> None:
        self.session.set_sink(float(self.sink_var.get()))
        self._reload_tree()
        self._refresh_recommendation()

    def _recompute_sink(self) -> None:
        self.session.recompute_implied_sink()
        self._reload_tree()
        self._refresh_recommendation()

    def _apply_mode(self) -> None:
        self.session.set_mode(MageMode(self.mode_var.get()))
        self._refresh_recommendation()

    def _load_preset(self) -> None:
        limits = self.session.limits
        self.session = load_preset(self.preset_var.get())
        self.session.limits = limits
        self.mode_var.set(self.session.mode.value)
        self._reload_tree()
        self._refresh_recommendation()
        self._log(
            f"Loaded preset {self.preset_var.get()} "
            f"(mode {self.session.mode.value}, sink {self.session.sink:g})."
        )

    def _add_stat_dialog(self) -> None:
        win = tk.Toplevel(self)
        win.title("Add stat")
        var = tk.StringVar(value="strength")
        names = [s.id for s in all_stats()]
        ttk.Combobox(win, textvariable=var, values=names, width=28).pack(padx=8, pady=8)
        natural = tk.BooleanVar(value=True)

        def ok() -> None:
            sid = var.get()
            if sid in self.session.item.lines:
                messagebox.showinfo("Exists", "That line is already on the item.")
                win.destroy()
                return
            is_nat = natural.get()
            self.session.item.add_line(
                StatLine(
                    stat_id=sid,
                    current=0,
                    natural_min=0 if not is_nat else 0,
                    natural_max=0 if not is_nat else 0,
                    target=1,
                    is_natural=is_nat,
                )
            )
            win.destroy()
            self._reload_tree()
            self._refresh_recommendation()

        ttk.Checkbutton(win, text="Natural line (uncheck for exo)", variable=natural).pack()
        ttk.Button(win, text="Add", command=ok).pack(pady=8)

    def _refresh_recommendation(self) -> None:
        self._apply_settings()
        rec = self.session.recommend()
        self.rec_title.set(rec.summary())
        body = []
        if rec.success_note:
            body.append(rec.success_note)
        body.extend(rec.reasons)
        self.rec_body.set("\n".join(body))
        self._reload_tree()
        if rec.stat_id and rec.stat_id in self.session.item.lines:
            try:
                self.tree.selection_set(rec.stat_id)
                self.tree.see(rec.stat_id)
            except tk.TclError:
                pass

    def _apply_settings(self) -> None:
        self.mouse.require_foreground = bool(self.require_fg.get())
        self.mouse.layout = self.layout
        self.layout.animation_delay_s = float(self.anim_delay.get())
        self.layout.click_offset_px = int(self.click_offset.get())
        self.layout.window_title_substring = self.window_sub.get().strip() or "dofus"
        profile = (self.feel_var.get() or "natural").strip().lower()
        if profile not in ("slow", "natural", "fast"):
            profile = "natural"
        self.layout.speed_profile = profile
        settings = ClickSettings.from_profile(profile)
        settings.landing_jitter_px = max(0, int(self.click_offset.get()))
        self.mouse.apply_click_settings(settings)
        self.session.limits.stop_on_empty_sink = bool(self.stop_empty.get())
        self.session.limits.assume_sc = bool(self.assume_sc.get())
        b = self.budget.get().strip()
        self.session.limits.budget_kamas = float(b) if b else None
        a = self.max_attempts.get().strip()
        self.session.limits.max_attempts = int(a) if a else None

    # --- clicker ---------------------------------------------------------

    def _start(self) -> None:
        if self._worker and self._worker.is_alive():
            self._log("Already running.")
            return
        self._apply_settings()
        rec = self.session.recommend()
        if rec.action != "throw" or not rec.rune_id:
            self._log(rec.summary())
            return
        mode = self.click_mode.get()
        if mode == "manual":
            self._log("Recommend-only: throw this rune yourself, then press SC/SN/EC.")
            self._refresh_recommendation()
            return
        self.mouse.reset_flags()
        self.mouse.start_hotkeys()
        if mode == "auto":
            self.session.limits.assume_sc = True
            self.assume_sc.set(True)
            n = int(self.repeat_n.get())
            self._worker = threading.Thread(
                target=self._run_auto, args=(rec.rune_id, n), daemon=True
            )
        else:
            self._worker = threading.Thread(target=self._run_semi, daemon=True)
        self._worker.start()
        self._log(f"Started ({mode}). F8/F12 or mouse-to-corner to abort.")

    def _run_semi(self) -> None:
        try:
            while not self.mouse.stopped:
                rec = self.session.recommend()
                if rec.action != "throw" or not rec.rune_id:
                    self._log(rec.summary())
                    break
                self.after(0, self._refresh_recommendation)
                self._log(f"Clicking {rec.rune_id} … then press S/N/E")
                self.mouse.throw_rune(rec.rune_id, click_apply=self.click_apply.get())
                self.session.last_rune_id = rec.rune_id
                self._pending_outcome = None
                self._awaiting_outcome.set()
                while self._awaiting_outcome.is_set() and not self.mouse.stopped:
                    self.mouse._checkpoint()
                    time.sleep(0.05)
                if self.mouse.stopped:
                    break
                outcome = self._pending_outcome
                if outcome is None:
                    break
                self.session.apply_outcome(outcome, rec.rune_id)
                self.after(0, self._refresh_recommendation)
        except AutomationStopped as exc:
            self._log(f"Stopped: {exc}")
        except Exception as exc:
            self._log(f"Clicker error: {exc}")
        finally:
            self._awaiting_outcome.clear()
            self.after(0, lambda: self.status_var.set("Idle"))

    def _run_auto(self, rune_id: str, times: int) -> None:
        try:
            for i in range(times):
                if self.mouse.stopped:
                    break
                rec = self.session.recommend()
                target = rec.rune_id or rune_id
                if rec.action != "throw":
                    self._log(rec.summary())
                    break
                self.mouse.throw_rune(target, click_apply=self.click_apply.get())
                self.session.last_rune_id = target
                self.session.apply_outcome(Outcome.SC, target)
                self._log(f"Assumed SC #{i + 1}/{times} for {target}")
                self.after(0, self._refresh_recommendation)
        except AutomationStopped as exc:
            self._log(f"Stopped: {exc}")
        except Exception as exc:
            self._log(f"Clicker error: {exc}")
        finally:
            self.after(0, lambda: self.status_var.set("Idle"))

    def _toggle_pause(self) -> None:
        self.mouse.toggle_pause()

    def _stop(self) -> None:
        self.mouse.emergency_stop("ui")
        self._awaiting_outcome.clear()
        self._log("Stop requested.")

    def _report(self, outcome: Outcome) -> None:
        if self._awaiting_outcome.is_set():
            self._pending_outcome = outcome
            self._awaiting_outcome.clear()
            self._log(f"Recorded {outcome.value.upper()}")
            return
        if not self.session.last_rune_id:
            rec = self.session.recommend()
            if rec.rune_id:
                self.session.last_rune_id = rec.rune_id
        if not self.session.last_rune_id:
            self._log("No rune to attach this outcome to.")
            return
        self.session.apply_outcome(outcome, self.session.last_rune_id)
        self._log(f"Recorded {outcome.value.upper()} on {self.session.last_rune_id}")
        self._refresh_recommendation()

    # --- calibration -----------------------------------------------------

    def _refresh_cal_tree(self) -> None:
        for iid in self.cal_tree.get_children():
            self.cal_tree.delete(iid)
        rows = [
            ("apply_button", self.layout.apply_button),
            ("item_slot", self.layout.item_slot),
            ("inventory", self.layout.inventory),
        ]
        for rune_id, pt in sorted(self.layout.runes.items()):
            rows.append((rune_id, pt))
        for name, pt in rows:
            if pt is None:
                continue
            self.cal_tree.insert("", tk.END, iid=name, values=(name, pt.x, pt.y))

    def _on_select_cal(self, _evt=None) -> None:
        sel = self.cal_tree.selection()
        if sel:
            self.cal_slot.set(sel[0])

    def _capture_now(self) -> None:
        try:
            pt = current_mouse_position()
        except RuntimeError as exc:
            messagebox.showerror("Mouse", str(exc))
            return
        self.layout.set_slot(self.cal_slot.get().strip(), pt)
        self.mouse.layout = self.layout
        self._refresh_cal_tree()
        self._log(f"Calibrated {self.cal_slot.get()} → ({pt.x}, {pt.y})")

    def _capture_slot(self) -> None:
        self._log("Hover the target — capturing in 2 seconds…")
        self.after(2000, self._capture_now)

    def _save_layout(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            initialfile="layout.json",
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            try:
                self.layout.save(DEFAULT_LAYOUT_PATH)
                self._log(f"Saved layout to {DEFAULT_LAYOUT_PATH}")
            except Exception as exc:
                messagebox.showerror("Save", str(exc))
            return
        self.layout.save(Path(path))
        self._log(f"Saved layout to {path}")

    def _load_layout(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        self.layout = Layout.load(Path(path))
        self.mouse.layout = self.layout
        self.anim_delay.set(self.layout.animation_delay_s)
        self.click_offset.set(self.layout.click_offset_px)
        self.window_sub.set(self.layout.window_title_substring)
        self.feel_var.set(self.layout.speed_profile or "natural")
        self._refresh_cal_tree()
        self._log(f"Loaded layout {path}")

    def _on_close(self) -> None:
        self.mouse.emergency_stop("quit")
        self.mouse.stop_hotkeys()
        try:
            self.layout.save(DEFAULT_LAYOUT_PATH)
        except Exception:
            pass
        self.destroy()


def run_app() -> None:
    app = FMApp()
    app._reload_tree()
    app.mainloop()
