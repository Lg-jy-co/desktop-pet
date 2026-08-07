"""渲染器。

两种模式：
- 图集模式：assets/sprites/spritesheet.png 存在时，按帧显示图片；
- 矢量模式：没有图片时，用 canvas 画一个占位小宠物（同样会随状态变化）。

气泡（消息提醒 / 反馈文字）也在这里绘制。
"""
from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass

from .config import MAGENTA, PetConfig
from .spritesheet import Spritesheet
from .states import PetState

# 身体中心（相对窗口的比例）与大小，矢量模式和命中测试共用
BODY_CX = 0.5
BODY_CY = 0.55
BODY_RX = 0.34
BODY_RY = 0.27

BODY_COLORS: dict[PetState, str] = {
    PetState.IDLE: "#ffd28a",
    PetState.HAPPY: "#ffd28a",
    PetState.WAVING: "#ffd28a",
    PetState.EATING: "#ffd9a0",
    PetState.SLEEPING: "#c9b6e8",
    PetState.SAD: "#a8bfe0",
    PetState.BUSY: "#ffcf7d",
    PetState.DRAG: "#e8c37a",
    PetState.SPEAKING: "#ffd28a",
}


@dataclass
class Bubble:
    text: str
    expire: float


class Renderer:
    def __init__(self, canvas: tk.Canvas, cfg: PetConfig, sheet: Spritesheet | None) -> None:
        self.canvas = canvas
        self.cfg = cfg
        self.sheet = sheet
        self._image_item: int | None = None
        self._last_state: PetState | None = None

    # ---- 对外接口 ----

    def draw(self, state: PetState, frame: int, bubble: Bubble | None = None) -> None:
        self.canvas.delete("pet")
        self.canvas.delete("bubble")
        self._image_item = None  # ?????????????????
        if self.sheet is not None:
            self._draw_image(state, frame)
        else:
            self._draw_vector(state, frame)
        if bubble:
            self._draw_bubble(bubble.text)

    def is_over_body(self, x: int, y: int) -> bool:
        w, h = self.cfg.window_w, self.cfg.window_h
        cx, cy = w * BODY_CX, h * BODY_CY
        rx, ry = w * BODY_RX, h * BODY_RY
        return ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0

    # ---- 图集模式 ----

    def _draw_image(self, state: PetState, frame: int) -> None:
        img = self.sheet.frame(state, frame)
        if img is None:
            self._draw_vector(state, frame)
            return
        w, h = self.cfg.window_w, self.cfg.window_h
        x = w // 2
        y = h - 26 - img.height() // 2
        if self._image_item is None:
            self._image_item = self.canvas.create_image(x, y, image=img, tags="pet")
        else:
            self.canvas.itemconfig(self._image_item, image=img)
            self.canvas.coords(self._image_item, x, y)

    # ---- 矢量占位模式 ----

    def _draw_vector(self, state: PetState, frame: int) -> None:
        w, h = self.cfg.window_w, self.cfg.window_h
        cx, cy = w * BODY_CX, h * BODY_CY
        rx, ry = w * BODY_RX, h * BODY_RY
        color = BODY_COLORS.get(state, BODY_COLORS[PetState.IDLE])

        bounce = 0
        if state == PetState.HAPPY:
            bounce = [0, -8, -4, -10, -2][frame % 5]
        elif state == PetState.SLEEPING:
            bounce = [-3, -1][frame % 2]

        cy += bounce
        if state == PetState.DRAG:
            ry *= 0.78  # 被拖扁一点

        # 身体
        self.canvas.create_oval(
            cx - rx, cy - ry, cx + rx, cy + ry,
            fill=color, outline="#c98a3d", width=3, tags="pet",
        )
        # 肚皮
        self.canvas.create_oval(
            cx - rx * 0.5, cy + ry * 0.1, cx + rx * 0.5, cy + ry * 0.85,
            fill="#fff3e0", outline="", tags="pet",
        )

        eye_y = cy - ry * 0.25
        eye_dx = rx * 0.28
        blink = state == PetState.IDLE and frame in (1, 2)

        if state == PetState.SLEEPING:
            self._closed_eyes(cx - eye_dx, cx + eye_dx, eye_y + 4, rx * 0.16)
            self._zzz(cx + rx * 0.55, cy - ry * 0.9)
        else:
            if state in (PetState.HAPPY, PetState.WAVING, PetState.BUSY):
                self._arc_eyes(cx - eye_dx, cx + eye_dx, eye_y, rx * 0.17)
            elif blink:
                self._closed_eyes(cx - eye_dx, cx + eye_dx, eye_y, rx * 0.16)
            else:
                r = max(5, rx * 0.075)
                self.canvas.create_oval(cx - eye_dx - r, eye_y - r, cx - eye_dx + r, eye_y + r, fill="#3b2b20", outline="", tags="pet")
                self.canvas.create_oval(cx + eye_dx - r, eye_y - r, cx + eye_dx + r, eye_y + r, fill="#3b2b20", outline="", tags="pet")

        mouth_y = cy + ry * 0.28
        if state == PetState.SLEEPING:
            pass
        elif state == PetState.EATING or state == PetState.SPEAKING:
            mw = rx * (0.42 if state == PetState.EATING else 0.30)
            mh = ry * (0.34 if state == PetState.EATING else 0.22)
            self.canvas.create_oval(cx - mw, mouth_y - mh * 0.5, cx + mw, mouth_y + mh * 0.8, fill="#5b2b1a", outline="", tags="pet")
            if state == PetState.EATING:
                self._draw_food(cx + rx * 0.05, mouth_y - mh - 6, rx * 0.16)
        elif state == PetState.SAD:
            self.canvas.create_arc(cx - rx * 0.30, mouth_y - ry * 0.18, cx + rx * 0.30, mouth_y + ry * 0.30, start=20, extent=140, style="arc", outline="#3b2b20", width=3, tags="pet")
            self.canvas.create_oval(cx - eye_dx + rx * 0.1, eye_y + ry * 0.15, cx - eye_dx + rx * 0.22, eye_y + ry * 0.4, fill="#7fb8e8", outline="", tags="pet")
        else:
            self.canvas.create_arc(cx - rx * 0.26, mouth_y - ry * 0.2, cx + rx * 0.26, mouth_y + ry * 0.28, start=0, extent=180, style="arc", outline="#3b2b20", width=3, tags="pet")

        if state == PetState.HAPPY or state == PetState.WAVING:
            blush = rx * 0.13
            self.canvas.create_oval(cx - rx * 0.62, mouth_y - ry * 0.12, cx - rx * 0.62 + blush, mouth_y + blush - ry * 0.12, fill="#ffb3b3", outline="", tags="pet")
            self.canvas.create_oval(cx + rx * 0.62 - blush, mouth_y - ry * 0.12, cx + rx * 0.62, mouth_y + blush - ry * 0.12, fill="#ffb3b3", outline="", tags="pet")

        if state == PetState.WAVING:
            self._arm(cx + rx * 0.85, cy - ry * 0.1, rx * 0.18, 0)
        if state == PetState.BUSY:
            self._arm(cx - rx * 0.85, cy - ry * 0.05, rx * 0.16, -40)
            self._arm(cx + rx * 0.85, cy - ry * 0.05, rx * 0.16, -40)
            self._sweat(cx + rx * 0.45, cy - ry * 0.75)
        if state == PetState.DRAG:
            self._motion_lines(cx - rx, cy + ry * 0.4)

    # ---- 矢量小部件 ----

    def _closed_eyes(self, x1: float, x2: float, y: float, half: float) -> None:
        self.canvas.create_arc(x1 - half, y - half, x1 + half, y + half, start=200, extent=140, style="arc", outline="#3b2b20", width=2, tags="pet")
        self.canvas.create_arc(x2 - half, y - half, x2 + half, y + half, start=200, extent=140, style="arc", outline="#3b2b20", width=2, tags="pet")

    def _arc_eyes(self, x1: float, x2: float, y: float, half: float) -> None:
        self.canvas.create_arc(x1 - half, y - half, x1 + half, y + half, start=20, extent=140, style="arc", outline="#3b2b20", width=3, tags="pet")
        self.canvas.create_arc(x2 - half, y - half, x2 + half, y + half, start=20, extent=140, style="arc", outline="#3b2b20", width=3, tags="pet")

    def _arm(self, x: float, y: float, r: float, angle: float) -> None:
        self.canvas.create_oval(x - r, y - r, x + r, y + r, fill=BODY_COLORS[PetState.IDLE], outline="#c98a3d", width=2, tags="pet")

    def _sweat(self, x: float, y: float) -> None:
        self.canvas.create_oval(x - 4, y - 4, x + 4, y + 4, fill="#9fd4f5", outline="", tags="pet")

    def _zzz(self, x: float, y: float) -> None:
        sizes = [(9, 0), (6, -12), (4, -22)]
        for r, dy in sizes:
            self.canvas.create_oval(x - r, y + dy - r, x + r, y + dy + r, fill="", outline="#7a6bb0", width=2, tags="pet")

    def _draw_food(self, x: float, y: float, r: float) -> None:
        self.canvas.create_oval(x - r, y - r, x + r, y + r, fill="#e05555", outline="#a03a3a", width=2, tags="pet")
        self.canvas.create_arc(x - r * 0.5, y - r * 1.15, x + r * 0.5, y + r * 0.1, start=0, extent=180, style="arc", outline="#7a9b3d", width=3, tags="pet")

    def _motion_lines(self, x: float, y: float) -> None:
        for i, dy in enumerate((-6, 0, 6)):
            self.canvas.create_line(x - 6 - i * 4, y + dy, x + 2 - i * 4, y + dy, fill="#c9a86a", width=2, tags="pet")

    # ---- 气泡 ----

    def _draw_bubble(self, text: str) -> None:
        w, h = self.cfg.window_w, self.cfg.window_h
        margin = 10
        max_w = w - 2 * margin
        lines = self._wrap(text, max_w - 22)
        line_h = 16
        bw = min(max_w, max(60, max(len(ln) * 13 + 20 for ln in lines)))
        bh = len(lines) * line_h + 14
        bx = (w - bw) / 2
        by = 8
        self.canvas.create_polygon(
            bx, by, bx + bw, by, bx + bw, by + bh, bx, by + bh,
            smooth=True, fill="#ffffff", outline="#d0d0d0", width=1, tags="bubble",
        )
        self.canvas.create_polygon(
            bx + bw * 0.42, by + bh - 2, bx + bw * 0.58, by + bh - 2, bx + bw * 0.5, by + bh + 10,
            fill="#ffffff", outline="", tags="bubble",
        )
        for i, ln in enumerate(lines):
            self.canvas.create_text(w / 2, by + 12 + i * line_h, text=ln, fill="#333333", font=("Microsoft YaHei UI", 9), tags="bubble")

    @staticmethod
    def _wrap(text: str, max_px: int) -> list[str]:
        lines: list[str] = []
        for raw in text.splitlines():
            cur = ""
            for ch in raw:
                wch = 13 if ord(ch) > 0x2E80 else 7
                if cur and len(cur) * 13 + wch > max_px:
                    lines.append(cur)
                    cur = ch
                else:
                    cur += ch
            lines.append(cur)
        return lines or [""]