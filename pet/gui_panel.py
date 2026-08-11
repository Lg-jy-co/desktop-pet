# gui_panel.py

"""桌面宠物控制面板。

通过右键菜单打开，提供状态监控、快捷操作、参数设置、高级选项。
"""
from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk, messagebox
from dataclasses import asdict
from typing import TYPE_CHECKING

from .config import CONFIG_FILE, PetConfig, MoveAtlasConfig
from .foods import FOODS
from .stats import DecayRates

if TYPE_CHECKING:
    from .app import PetApp


class ControlPanel:
    """控制面板 Toplevel 窗口。"""

    def __init__(self, app: PetApp) -> None:
        self.app = app
        self.cfg = app.cfg
        self.stats = app.stats

        self.win = tk.Toplevel(app.window.root)
        self.win.title("宠物控制面板")
        self.win.geometry("520x440")
        self.win.resizable(False, False)
        self.win.configure(bg="#f0f0f0")
        self.win.transient(app.window.root)
        self.win.protocol("WM_DELETE_WINDOW", self._close)

        # 左侧导航
        self.nav_frame = tk.Frame(self.win, bg="#e0e0e0", width=120)
        self.nav_frame.pack(side="left", fill="y")
        self.nav_frame.pack_propagate(False)

        self.nav_btns: dict[str, tk.Button] = {}
        categories = ["状态监控", "快捷操作", "参数设置", "高级选项"]
        for cat in categories:
            btn = tk.Button(
                self.nav_frame, text=cat, relief="flat", bg="#e0e0e0",
                activebackground="#d0d0d0", anchor="w", padx=10, pady=4,
                font=("Microsoft YaHei UI", 10),
                command=lambda c=cat: self._show_page(c),
            )
            btn.pack(fill="x", pady=1, padx=2)
            self.nav_btns[cat] = btn

        # 右侧内容区域
        self.content_frame = tk.Frame(self.win, bg="#f0f0f0")
        self.content_frame.pack(side="left", fill="both", expand=True)

        self.current_page: str | None = None
        self._status_widgets: dict[str, tk.Widget] = {}

        self._show_page("状态监控")  # 默认页

        # 定时刷新状态监控
        self._refresh_status()

    # ---- 页面切换 ----

    def _show_page(self, page: str) -> None:
        if self.current_page == page:
            return
        if self.current_page and self.current_page in self.nav_btns:
            self.nav_btns[self.current_page].config(bg="#e0e0e0")
        self.nav_btns[page].config(bg="#d0d0d0")
        self.current_page = page

        for w in self.content_frame.winfo_children():
            w.destroy()

        if page == "状态监控":
            self._build_status_page()
        elif page == "快捷操作":
            self._build_action_page()
        elif page == "参数设置":
            self._build_params_page()
        elif page == "高级选项":
            self._build_advanced_page()

    # ---- 状态监控 ----

    def _build_status_page(self) -> None:
        f = tk.Frame(self.content_frame, bg="#f0f0f0")
        f.pack(fill="both", expand=True, padx=20, pady=15)

        tk.Label(f, text="实时属性", font=("Microsoft YaHei UI", 12, "bold"), bg="#f0f0f0").pack(anchor="w")

        self._status_widgets["hunger_bar"] = self._make_status_bar(f, "饱食度", 100)
        self._status_widgets["mood_bar"] = self._make_status_bar(f, "心情", 100)
        self._status_widgets["energy_bar"] = self._make_status_bar(f, "精力", 100)

    def _make_status_bar(self, parent: tk.Frame, label: str, maximum: float) -> ttk.Progressbar:
        row = tk.Frame(parent, bg="#f0f0f0")
        row.pack(fill="x", pady=6)
        tk.Label(row, text=label, width=6, anchor="e", bg="#f0f0f0", font=("Microsoft YaHei UI", 10)).pack(side="left", padx=(0, 8))
        bar = ttk.Progressbar(row, orient="horizontal", length=280, mode="determinate", maximum=maximum)
        bar.pack(side="left", fill="x", expand=True)
        lbl_val = tk.Label(row, text="0.0 / 100.0", width=12, anchor="w", bg="#f0f0f0", font=("Microsoft YaHei UI", 10))
        lbl_val.pack(side="left", padx=8)
        bar.label_widget = lbl_val
        return bar

    def _refresh_status(self) -> None:
        if not self.win.winfo_exists():
            return
        if self.current_page == "状态监控":
            hunger = max(0, min(100, self.stats.hunger))
            mood = max(0, min(100, self.stats.mood))
            energy = max(0, min(100, self.stats.energy))

            self._update_bar("hunger_bar", hunger, "饱食度")
            self._update_bar("mood_bar", mood, "心情")
            self._update_bar("energy_bar", energy, "精力")
        self.win.after(1000, self._refresh_status)

    def _update_bar(self, key: str, value: float, label: str) -> None:
        bar = self._status_widgets.get(key)
        if bar and bar.winfo_exists():
            bar["value"] = value
            # 颜色提醒（可选）
            if value < 20:
                bar.configure(style="red.Horizontal.TProgressbar")
            else:
                bar.configure(style="TProgressbar")
            if hasattr(bar, "label_widget"):
                bar.label_widget.config(text=f"{value:.1f} / 100.0")

    # ---- 快捷操作 ----

    def _build_action_page(self) -> None:
        f = tk.Frame(self.content_frame, bg="#f0f0f0")
        f.pack(fill="both", expand=True, padx=20, pady=15)

        tk.Label(f, text="快捷操作", font=("Microsoft YaHei UI", 12, "bold"), bg="#f0f0f0").pack(anchor="w", pady=(0, 12))

        btn_frame = tk.Frame(f, bg="#f0f0f0")
        btn_frame.pack(fill="x")

        tk.Button(btn_frame, text="👋 互动", command=self._interact,
                  font=("Microsoft YaHei UI", 10), width=14).pack(side="left", padx=4)
        tk.Button(btn_frame, text="😴 睡眠/唤醒", command=self._toggle_sleep,
                  font=("Microsoft YaHei UI", 10), width=14).pack(side="left", padx=4)

        feed_frame = tk.Frame(f, bg="#f0f0f0")
        feed_frame.pack(fill="x", pady=12)

        tk.Label(feed_frame, text="投喂食物：", bg="#f0f0f0", font=("Microsoft YaHei UI", 10)).pack(side="left")
        self._feed_var = tk.StringVar(value=FOODS[0].name if FOODS else "")
        food_names = [food.name for food in FOODS]
        if food_names:
            ttk.Combobox(feed_frame, textvariable=self._feed_var, values=food_names,
                         state="readonly", width=14).pack(side="left", padx=6)
            tk.Button(feed_frame, text="喂食", command=self._feed,
                      font=("Microsoft YaHei UI", 10), width=8).pack(side="left", padx=4)

        tk.Button(f, text="📊 查看状态文字", command=self._show_status_text,
                  font=("Microsoft YaHei UI", 10), width=20).pack(pady=10)

    def _interact(self) -> None:
        self.app._interact()

    def _feed(self) -> None:
        name = self._feed_var.get()
        food = next((f for f in FOODS if f.name == name), None)
        if food:
            self.app._feed(food)

    def _toggle_sleep(self) -> None:
        self.app._toggle_sleep()

    def _show_status_text(self) -> None:
        self.app._show_status()

    # ---- 参数设置 ----

    def _build_params_page(self) -> None:
        f = tk.Frame(self.content_frame, bg="#f0f0f0")
        f.pack(fill="both", expand=True, padx=20, pady=15)

        tk.Label(f, text="属性变化速率", font=("Microsoft YaHei UI", 12, "bold"), bg="#f0f0f0").pack(anchor="w")

        self._sliders: dict[str, tuple[tk.Scale, tk.StringVar]] = {}
        self._add_slider(f, "饥饿速度 (每小时)", "hunger_per_hour", 0.0, 5.0, 0.1, self.cfg.hunger_per_hour)
        self._add_slider(f, "心情降低 (每小时)", "mood_per_hour", 0.0, 5.0, 0.1, self.cfg.mood_per_hour)
        self._add_slider(f, "精力降低 (每小时)", "energy_per_hour", 0.0, 5.0, 0.1, self.cfg.energy_per_hour)
        self._add_slider(f, "睡眠精力恢复 (每小时)", "energy_recover_per_hour", 1.0, 100.0, 1.0, self.cfg.energy_recover_per_hour)

        ttk.Separator(f, orient="horizontal").pack(fill="x", pady=10)

        tk.Label(f, text="行为设置", font=("Microsoft YaHei UI", 12, "bold"), bg="#f0f0f0").pack(anchor="w")
        self._add_slider(f, "随机行为间隔 (秒)", "random_action_interval", 5.0, 120.0, 1.0, self.cfg.random_action_interval)
        self._add_slider(f, "随机行为概率", "random_action_chance", 0.0, 1.0, 0.05, self.cfg.random_action_chance)
        self._add_slider(f, "拖拽阈值 (像素)", "drag_threshold", 1, 10, 1, self.cfg.drag_threshold)
        self._add_slider(f, "气泡显示秒数", "bubble_seconds", 2.0, 30.0, 0.5, self.cfg.bubble_seconds)
        self._add_slider(f, "随机移动间隔 (秒)", "random_move_interval", 1.0, 60.0, 1.0, self.cfg.random_move_interval)
        self._add_slider(f, "移动速度 (像素/帧)", "move_speed", 1, 30, 1, self.cfg.move_speed)

        tk.Button(f, text="💾 保存参数", command=self._save_params,
                  font=("Microsoft YaHei UI", 10), width=14).pack(pady=10)

    def _add_slider(self, parent: tk.Frame, label: str, key: str,
                    from_: float, to_: float, resolution: float, default: float) -> None:
        row = tk.Frame(parent, bg="#f0f0f0")
        row.pack(fill="x", pady=3)
        tk.Label(row, text=label, bg="#f0f0f0", width=20, anchor="w",
                 font=("Microsoft YaHei UI", 9)).pack(side="left")

        var = tk.StringVar(value=f"{default:.1f}" if isinstance(default, float) else str(default))
        s = tk.Scale(row, from_=from_, to=to_, resolution=resolution, orient="horizontal",
                     variable=var, length=180, showvalue=False, bg="#f0f0f0")
        s.pack(side="left", padx=4)
        val_lbl = tk.Label(row, textvariable=var, width=6, bg="#f0f0f0",
                           font=("Microsoft YaHei UI", 9))
        val_lbl.pack(side="left")
        self._sliders[key] = (s, var)

    def _save_params(self) -> None:
        new = {}
        for key, (_, var) in self._sliders.items():
            val_str = var.get()
            try:
                val = float(val_str) if '.' in val_str else int(val_str)
            except ValueError:
                val = 0.0
            new[key] = val

        for k, v in new.items():
            setattr(self.app.cfg, k, v)

        # 让应用即时同步（包括移动速度、间隔）
        if hasattr(self.app, 'apply_config'):
            self.app.apply_config()

        self._save_config_to_file()
        messagebox.showinfo("成功", "参数已保存并立即生效！", parent=self.win)

    def _save_config_to_file(self) -> None:
        try:
            CONFIG_FILE.write_text(
                json.dumps(asdict(self.app.cfg), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            messagebox.showerror("保存失败", f"无法写入配置文件：{e}", parent=self.win)

    # ---- 高级选项 ----

    def _build_advanced_page(self) -> None:
        f = tk.Frame(self.content_frame, bg="#f0f0f0")
        f.pack(fill="both", expand=True, padx=20, pady=15)

        tk.Label(f, text="窗口与行为", font=("Microsoft YaHei UI", 12, "bold"), bg="#f0f0f0").pack(anchor="w")

        self._click_through_var = tk.BooleanVar(value=self.cfg.click_through)
        ttk.Checkbutton(f, text="点击穿透 (光标不在宠物上时)", variable=self._click_through_var,
                        command=self._toggle_click_through).pack(anchor="w", pady=4)

        self._topmost_var = tk.BooleanVar(value=self.cfg.topmost)
        ttk.Checkbutton(f, text="窗口置顶", variable=self._topmost_var,
                        command=self._toggle_topmost).pack(anchor="w", pady=4)

        self._beep_var = tk.BooleanVar(value=self.cfg.beep_on_message)
        ttk.Checkbutton(f, text="消息提示音", variable=self._beep_var,
                        command=self._toggle_beep).pack(anchor="w", pady=4)

        ttk.Separator(f, orient="horizontal").pack(fill="x", pady=10)

        # 移动图集设置
        tk.Label(f, text="移动图集设置", font=("Microsoft YaHei UI", 12, "bold"), bg="#f0f0f0").pack(anchor="w", pady=(0, 4))
        grid_f = tk.Frame(f, bg="#f0f0f0")
        grid_f.pack(fill="x", pady=4)

        self._atlas_vars = {}
        row1 = tk.Frame(grid_f, bg="#f0f0f0")
        row1.pack(fill="x")
        self._add_atlas_entry(row1, "cols", "列数", self.cfg.move_atlas.cols)
        self._add_atlas_entry(row1, "rows", "行数", self.cfg.move_atlas.rows)

        row2 = tk.Frame(grid_f, bg="#f0f0f0")
        row2.pack(fill="x", pady=4)
        self._add_atlas_entry(row2, "cell_w", "格子宽 (px)", self.cfg.move_atlas.cell_w)
        self._add_atlas_entry(row2, "cell_h", "格子高 (px)", self.cfg.move_atlas.cell_h)

        tk.Button(f, text="💾 保存图集设置", command=self._save_atlas,
                  font=("Microsoft YaHei UI", 10), width=16).pack(pady=6)

        ttk.Separator(f, orient="horizontal").pack(fill="x", pady=10)

        # 系统托盘预留
        tk.Label(f, text="系统托盘（预留接口）", font=("Microsoft YaHei UI", 12, "bold"), bg="#f0f0f0").pack(anchor="w")
        tk.Label(f, text="后续系统托盘将提供与右键菜单相同的选项。\n目前请使用右键菜单操作。",
                 bg="#f0f0f0", fg="#555555", font=("Microsoft YaHei UI", 9), justify="left").pack(anchor="w", pady=4)

        # 配置管理按钮
        btn_frame = tk.Frame(f, bg="#f0f0f0")
        btn_frame.pack(fill="x", pady=12)
        tk.Button(btn_frame, text="💾 保存当前配置", command=self._save_current,
                  font=("Microsoft YaHei UI", 10), width=16).pack(side="left", padx=4)
        tk.Button(btn_frame, text="↩️ 恢复默认配置", command=self._restore_defaults,
                  font=("Microsoft YaHei UI", 10), width=16).pack(side="left", padx=4)

    def _add_atlas_entry(self, parent: tk.Frame, key: str, label: str, default_val: int) -> None:
        f = tk.Frame(parent, bg="#f0f0f0")
        f.pack(side="left", padx=10)
        tk.Label(f, text=label, bg="#f0f0f0", font=("Microsoft YaHei UI", 9)).pack(anchor="w")
        var = tk.IntVar(value=default_val)
        sb = tk.Spinbox(f, from_=1, to=999, textvariable=var, width=6, font=("Microsoft YaHei UI", 9))
        sb.pack()
        self._atlas_vars[key] = var

    def _save_atlas(self) -> None:
        new_cols = self._atlas_vars["cols"].get()
        new_rows = self._atlas_vars["rows"].get()
        new_cw = self._atlas_vars["cell_w"].get()
        new_ch = self._atlas_vars["cell_h"].get()

        self.cfg.move_atlas = MoveAtlasConfig(
            file=self.cfg.move_atlas.file,
            cols=new_cols,
            rows=new_rows,
            cell_w=new_cw,
            cell_h=new_ch,
            row_map=self.cfg.move_atlas.row_map,
        )
        self._save_config_to_file()
        messagebox.showinfo("成功", "移动图集设置已保存，重启后生效。", parent=self.win)

    # ---- 开关回调 ----

    def _toggle_click_through(self) -> None:
        self.cfg.click_through = self._click_through_var.get()
        self.app.window.set_click_through(self.cfg.click_through)

    def _toggle_topmost(self) -> None:
        self.cfg.topmost = self._topmost_var.get()
        self.app.window.root.attributes("-topmost", self.cfg.topmost)

    def _toggle_beep(self) -> None:
        self.cfg.beep_on_message = self._beep_var.get()

    # ---- 保存与恢复 ----

    def _save_current(self) -> None:
        self._save_config_to_file()
        messagebox.showinfo("保存", "配置已保存！", parent=self.win)

    def _restore_defaults(self) -> None:
        if not messagebox.askyesno("恢复默认", "确定要恢复默认配置吗？\n当前修改将丢失。", parent=self.win):
            return
        default = PetConfig()
        self.app.cfg = default
        self.app.rates = DecayRates()  # 默认参数
        self.app.window.set_click_through(default.click_through)
        self.app.window.root.attributes("-topmost", default.topmost)
        self._save_config_to_file()
        self._close()

    def _close(self) -> None:
        self.win.destroy()