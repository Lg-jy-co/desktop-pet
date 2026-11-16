"""久坐提醒：设置对话框 + 提醒弹窗 + 休息弹窗。

流程：
  SitReminderDialog（开/关设置）
    → [到时间] SitAlertDialog（"好的！"）
    → [点好的] SitRestDialog（实时计时 + "我休息好了！"）
    → [点我休息好了] 回调 app，开始新一轮计时
"""
from __future__ import annotations

import json
import time
import tkinter as tk
from dataclasses import asdict
from tkinter import messagebox
from typing import TYPE_CHECKING, Callable

from .config import CONFIG_FILE, DATA_DIR

if TYPE_CHECKING:
    from .app import PetApp


def _save_config(cfg) -> None:
    """就地写回 CONFIG_FILE（不依赖 gui_panel，避免耦合）。"""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(
            json.dumps(asdict(cfg), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as exc:
        print(f"[sit_reminder] 保存配置失败：{exc}")


def format_rest_duration_message(seconds: float) -> str:
    """根据休息时长生成收尾气泡文案。"""
    total = max(0, int(seconds))
    m, s = divmod(total, 60)
    if m < 1:
        return f"休息了 {s} 秒，下次多动一动哦~"
    if m < 10:
        return f"休息了 {m} 分 {s} 秒，真棒！继续加油！"
    return f"休息了 {m} 分钟，身体会感谢你的~"


# ---------------------------------------------------------------------------
# 设置 / 关闭对话框
# ---------------------------------------------------------------------------

class SitReminderDialog(tk.Toplevel):
    """久坐提醒设置对话框。

    - 未开启时：小时/分钟输入（Spinbox），确认后开启并重置计时。
    - 已开启时：显示确认消息，确认后关闭功能。
    """

    def __init__(self, app: "PetApp") -> None:
        super().__init__(app.window.root)
        self.app = app
        self.cfg = app.cfg
        self.resizable(False, False)
        self.attributes("-topmost", True)

        if self.cfg.sit_reminder_enabled:
            self.title("关闭久坐提醒")
            self._build_confirm_off()
        else:
            self.title("设置久坐提醒")
            self._build_settings()

        self.update_idletasks()
        self._center()
        self.grab_set()  # 模态，防止误操作

    # ---- 布局 ----

    def _center(self) -> None:
        w, h = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

    def _build_settings(self) -> None:
        wrap = tk.Frame(self, padx=20, pady=16)
        wrap.pack(fill="both", expand=True)

        tk.Label(
            wrap, text="设置久坐提醒间隔：",
            font=("Microsoft YaHei UI", 11, "bold"),
        ).pack(anchor="w")

        time_row = tk.Frame(wrap)
        time_row.pack(pady=12)

        total_minutes = max(1, int(self.cfg.sit_reminder_interval_minutes))
        hours, minutes = divmod(total_minutes, 60)

        tk.Label(time_row, text="小时", font=("Microsoft YaHei UI", 10)).pack(side="left", padx=(0, 2))
        self._hour_var = tk.IntVar(value=hours)
        tk.Spinbox(
            time_row, from_=0, to=999, textvariable=self._hour_var,
            width=4, font=("Microsoft YaHei UI", 10),
        ).pack(side="left", padx=(0, 12))

        tk.Label(time_row, text="分钟", font=("Microsoft YaHei UI", 10)).pack(side="left", padx=(0, 2))
        self._minute_var = tk.IntVar(value=minutes)
        tk.Spinbox(
            time_row, from_=0, to=59, textvariable=self._minute_var,
            width=4, font=("Microsoft YaHei UI", 10),
        ).pack(side="left")

        btn_row = tk.Frame(wrap)
        btn_row.pack(fill="x", pady=(12, 0))
        tk.Button(btn_row, text="确认", width=8, font=("Microsoft YaHei UI", 10),
                  command=self._on_confirm).pack(side="right", padx=4)
        tk.Button(btn_row, text="取消", width=8, font=("Microsoft YaHei UI", 10),
                  command=self.destroy).pack(side="right", padx=4)

        tk.Label(
            wrap,
            text="提示：至少设置 1 分钟，循环提醒会按此间隔重复触发。",
            fg="#666666", font=("Microsoft YaHei UI", 9),
            wraplength=320, justify="left",
        ).pack(anchor="w", pady=(10, 0))

    def _build_confirm_off(self) -> None:
        wrap = tk.Frame(self, padx=22, pady=18)
        wrap.pack(fill="both", expand=True)

        tk.Label(
            wrap, text="是否确认关闭久坐提醒功能？",
            font=("Microsoft YaHei UI", 11, "bold"),
        ).pack(anchor="w")

        btn_row = tk.Frame(wrap)
        btn_row.pack(fill="x", pady=(16, 0))
        tk.Button(btn_row, text="确认", width=8, font=("Microsoft YaHei UI", 10),
                  command=self._on_confirm_off).pack(side="right", padx=4)
        tk.Button(btn_row, text="取消", width=8, font=("Microsoft YaHei UI", 10),
                  command=self.destroy).pack(side="right", padx=4)

    # ---- 回调 ----

    def _on_confirm(self) -> None:
        try:
            hours = int(self._hour_var.get())
            minutes = int(self._minute_var.get())
        except (tk.TclError, ValueError):
            messagebox.showerror("错误", "请输入有效的时间数值。", parent=self)
            return
        if hours < 0 or minutes < 0:
            messagebox.showerror("错误", "时间不能为负数。", parent=self)
            return
        total = hours * 60 + minutes
        if total < 1:
            messagebox.showerror("错误", "提醒间隔至少为 1 分钟。", parent=self)
            return

        self.cfg.sit_reminder_interval_minutes = total
        self.cfg.sit_reminder_enabled = True
        self.app._reset_sit_reminder_timer()  # 从现在开始计时
        _save_config(self.cfg)
        self.destroy()

    def _on_confirm_off(self) -> None:
        self.cfg.sit_reminder_enabled = False
        _save_config(self.cfg)
        self.destroy()


# ---------------------------------------------------------------------------
# 提醒弹窗
# ---------------------------------------------------------------------------

class SitAlertDialog(tk.Toplevel):
    """到达久坐时限后弹出的提醒窗口。"""

    def __init__(self, app: "PetApp", on_close: Callable[[], None]) -> None:
        super().__init__(app.window.root)
        self.app = app
        self._on_close = on_close
        self._closed = False
        self.title("久坐提醒")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self._close)

        wrap = tk.Frame(self, padx=24, pady=20)
        wrap.pack(fill="both", expand=True)

        tk.Label(
            wrap, text="⏰ 久坐提醒",
            font=("Microsoft YaHei UI", 14, "bold"),
        ).pack(anchor="w")

        msg = (
            "你已经坐了挺久啦，站起来走一走、\n"
            "活动一下肩颈和眼睛吧~\n\n"
            "喝口水、伸个懒腰，照顾好自己哦！"
        )
        tk.Label(
            wrap, text=msg, justify="left", wraplength=340,
            font=("Microsoft YaHei UI", 10),
        ).pack(anchor="w", pady=(10, 16))

        btn_row = tk.Frame(wrap)
        btn_row.pack(fill="x")
        tk.Button(
            btn_row, text="好的！", width=10,
            font=("Microsoft YaHei UI", 10),
            command=self._close,
        ).pack(side="right")

        self.update_idletasks()
        self._center()

    def _center(self) -> None:
        w, h = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

    def _close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self.destroy()
        finally:
            self._on_close()


# ---------------------------------------------------------------------------
# 休息弹窗（方案 C：实时显示 + 收尾气泡）
# ---------------------------------------------------------------------------

class SitRestDialog(tk.Toplevel):
    """点"好的"后弹出的休息窗口。

    - 实时显示已休息时间（每秒刷新）
    - 点"我休息好了！"或关闭窗口 → 回调 app，开始新一轮计时
    """

    def __init__(self, app: "PetApp", on_close: Callable[[float], None]) -> None:
        super().__init__(app.window.root)
        self.app = app
        self._on_close = on_close
        self._start = time.time()
        self._closed = False
        self._after_id: str | None = None

        self.title("休息中")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self._close)

        wrap = tk.Frame(self, padx=24, pady=20)
        wrap.pack(fill="both", expand=True)

        tk.Label(
            wrap, text="🛋️ 休息中....",
            font=("Microsoft YaHei UI", 14, "bold"),
        ).pack(anchor="w")

        self._timer_label = tk.Label(
            wrap, text="已休息 00:00",
            font=("Consolas", 16, "bold"), fg="#2c7a2c",
        )
        self._timer_label.pack(anchor="w", pady=(10, 6))

        tk.Label(
            wrap,
            text="起来走走，看看远处，\n喝完这杯水再回来~",
            justify="left", font=("Microsoft YaHei UI", 10),
        ).pack(anchor="w", pady=(4, 16))

        btn_row = tk.Frame(wrap)
        btn_row.pack(fill="x")
        tk.Button(
            btn_row, text="我休息好了！", width=14,
            font=("Microsoft YaHei UI", 10),
            command=self._close,
        ).pack(side="right")

        self.update_idletasks()
        self._center()
        self._tick()

    def _center(self) -> None:
        w, h = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

    def _tick(self) -> None:
        if self._closed:
            return
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        elapsed = int(time.time() - self._start)
        m, s = divmod(max(0, elapsed), 60)
        try:
            self._timer_label.config(text=f"已休息 {m:02d}:{s:02d}")
            self._after_id = self.after(1000, self._tick)
        except tk.TclError:
            pass

    def _close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._after_id:
            try:
                self.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None
        elapsed = time.time() - self._start
        try:
            self.destroy()
        finally:
            self._on_close(elapsed)