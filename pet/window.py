"""桌面宠物窗口：无边框、置顶、透明键、可拖动、点击穿透（Windows）。

点击穿透方案：定时轮询鼠标位置，光标落在宠物身体上时窗口可交互，
否则给窗口加 WS_EX_TRANSPARENT 让点击穿过（不影响下方的程序）。
"""
from __future__ import annotations

import ctypes
import tkinter as tk
from typing import Callable

from .config import MAGENTA, PetConfig

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020

_user32 = ctypes.windll.user32
_user32.GetWindowLongPtrW.restype = ctypes.c_longlong
_user32.GetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int]
_user32.SetWindowLongPtrW.restype = ctypes.c_longlong
_user32.SetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_longlong]


class PetWindow:
    def __init__(
        self,
        cfg: PetConfig,
        hit_test: Callable[[int, int], bool] | None = None,
    ) -> None:
        self.cfg = cfg
        self.hit_test = hit_test
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True if cfg.topmost else False)
        self.root.attributes("-transparentcolor", MAGENTA)
        try:
            self.root.attributes("-toolwindow", True)  # 不出现在任务栏
        except tk.TclError:
            pass
        self.root.configure(bg=MAGENTA)
        self._place(cfg.window_w, cfg.window_h)

        self.canvas = tk.Canvas(
            self.root,
            width=cfg.window_w,
            height=cfg.window_h,
            bg=MAGENTA,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(fill="both", expand=True)

        self._drag = {"active": False, "pointer_down": False, "dx": 0, "dy": 0}
        if cfg.click_through and hit_test is not None:
            self._apply_click_through()  # 先设置一次
            self.root.after(80, self._click_through_loop)

    # ---- 位置 ----

    def set_click_through(self, enable: bool):
        self.cfg.click_through = enable
        self._apply_click_through()

    def _place(self, w: int, h: int) -> None:
        if self.cfg.start_x is not None and self.cfg.start_y is not None:
            x, y = self.cfg.start_x, self.cfg.start_y
        else:
            x = self.root.winfo_screenwidth() - w - 48
            y = self.root.winfo_screenheight() - h - 96
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    # ---- 拖动 ----

    def bind_drag(
        self,
        on_start: Callable[[tk.Event], None] | None = None,
        on_move: Callable[[tk.Event], None] | None = None,
        on_end: Callable[[tk.Event], None] | None = None,
    ) -> None:
        self._on_drag_start = on_start
        self._on_drag_move = on_move
        self._on_drag_end = on_end
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._motion)
        self.canvas.bind("<ButtonRelease-1>", self._release)

    def _press(self, event: tk.Event) -> None:
        self._drag["active"] = True
        self._drag["pointer_down"] = True
        self._drag["dx"] = event.x_root - self.root.winfo_x()
        self._drag["dy"] = event.y_root - self.root.winfo_y()
        if self._on_drag_start:
            self._on_drag_start(event)

    def _motion(self, event: tk.Event) -> None:
        if not self._drag["active"]:
            return
        nx = event.x_root - self._drag["dx"]
        ny = event.y_root - self._drag["dy"]
        self.root.geometry(f"+{nx}+{ny}")
        if self._on_drag_move:
            self._on_drag_move(event)

    def _release(self, event: tk.Event) -> None:
        self._drag["pointer_down"] = False
        if self._drag["active"] and self._on_drag_end:
            self._on_drag_end(event)
        self._drag["active"] = False

    # ---- 点击穿透 ----

    def _click_through_loop(self) -> None:
        self._apply_click_through()
        self.root.after(80, self._click_through_loop)

    def _apply_click_through(self) -> None:
        hwnd = _user32.GetParent(self.root.winfo_id())  # 顶层 HWND
        if not hwnd:
            return
        style = _user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
        if self._cursor_over_pet():
            style &= ~WS_EX_TRANSPARENT
        else:
            style |= WS_EX_TRANSPARENT
        _user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, style)

    def _cursor_over_pet(self) -> bool:
        if self._drag.get("pointer_down") or self._drag.get("active"):
            return True
        if self.hit_test is None:
            return False
        px, py = self.root.winfo_pointerxy()
        wx, wy = self.root.winfo_rootx(), self.root.winfo_rooty()
        lx, ly = px - wx, py - wy
        if not (0 <= lx < self.cfg.window_w and 0 <= ly < self.cfg.window_h):
            return False
        return self.hit_test(lx, ly)