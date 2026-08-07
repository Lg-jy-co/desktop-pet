"""精灵图集加载。

读取 assets/sprites/spritesheet.png，按 config.AtlasConfig 的
行列布局把每个状态的一行切成若干帧（PhotoImage）。
布局规格与 hatch-pet 一致：8 列 x 9 行，每格 192x208。
"""
from __future__ import annotations

import tkinter as tk
from pathlib import Path

from .config import AtlasConfig
from .states import STATE_TIMING, PetState


class Spritesheet:
    def __init__(self, root: tk.Misc, path: Path, cfg: AtlasConfig) -> None:
        self.cfg = cfg
        self.sheet = tk.PhotoImage(file=str(path))
        self.frames: dict[PetState, list[tk.PhotoImage]] = {}
        state_to_row = {v: k for k, v in cfg.row_map.items()}
        cw, ch = cfg.cell_w, cfg.cell_h
        for state in PetState:
            row = state_to_row.get(state.value)
            if row is None:
                continue
            count = min(len(STATE_TIMING[state]), cfg.cols)
            frames: list[tk.PhotoImage] = []
            for col in range(count):
                x, y = col * cw, row * ch
                cell = tk.PhotoImage(width=cw, height=ch)
                # ???? tkinter API????? copy_replace(from_coords=...)
                try:
                    cell.copy_replace(
                        self.sheet,
                        from_coords=(x, y, x + cw, y + ch),
                        to=(0, 0),
                    )
                except AttributeError:
                    cell.copy(self.sheet, from_=(x, y, x + cw, y + ch), to=(0, 0))
                frames.append(cell)
            if frames:
                self.frames[state] = frames
        self._root = root

    def frame(self, state: PetState, index: int) -> tk.PhotoImage | None:
        frames = self.frames.get(state)
        if not frames:
            return None
        return frames[index % len(frames)]