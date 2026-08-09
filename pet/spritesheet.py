# spriteshht.py

"""精灵图集加载。

读取 assets/sprites/spritesheet.png，按 config.AtlasConfig 的
行列布局把每个状态的一行切成若干帧（PhotoImage）。
布局规格与 hatch-pet 一致：8 列 x 9 行，每格 192x208。
"""
from __future__ import annotations

import tkinter as tk
from pathlib import Path

from .config import PetConfig, MoveAtlasConfig, SPRITES_DIR
from .states import STATE_TIMING, PetState


class Spritesheet:
    def __init__(self, root: tk.Misc, pet_cfg: PetConfig) -> None:
        self.pet_cfg = pet_cfg
        path = SPRITES_DIR / "spritesheet.png"
        self.sheet = tk.PhotoImage(file=str(path))
        self.frames: dict[PetState, list[tk.PhotoImage]] = {}
        state_to_row = {v: k for k, v in pet_cfg.atlas.row_map.items()}
        cw, ch = pet_cfg.atlas.cell_w, pet_cfg.atlas.cell_h
        for state in PetState:
            row = state_to_row.get(state.value)
            if row is None:
                continue
            count = min(len(STATE_TIMING[state]), pet_cfg.atlas.cols)
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

        self.move_frames: dict[PetState, list[tk.PhotoImage]] = {}
        if pet_cfg.use_move_spritesheet:
            move_path = SPRITES_DIR / pet_cfg.move_atlas.file
            if move_path.exists():
                self._load_move_sheet(move_path, pet_cfg.move_atlas)

    def frame(self, state: PetState, index: int) -> tk.PhotoImage | None:
        frames = self.frames.get(state)
        if not frames:
            return None
        return frames[index % len(frames)]

    def _load_move_sheet(self, path: Path, move_cfg: MoveAtlasConfig) -> None:
        sheet = tk.PhotoImage(file=str(path))
        state_to_row = {v: k for k, v in move_cfg.row_map.items()}
        cw, ch = move_cfg.cell_w, move_cfg.cell_h
        for state in PetState:
            if state.value not in state_to_row:
                continue
            row = state_to_row[state.value]
            count = min(len(STATE_TIMING.get(state, [])), move_cfg.cols)
            frames = []
            for col in range(count):
                x, y = col * cw, row * ch
                cell = tk.PhotoImage(width=cw, height=ch)
                try:
                    cell.copy_replace(sheet, from_coords=(x, y, x + cw, y + ch), to=(0, 0))
                except AttributeError:
                    cell.copy(sheet, from_=(x, y, x + cw, y + ch), to=(0, 0))
                frames.append(cell)
            if frames:
                self.move_frames[state] = frames

    def move_frame(self, state: PetState, index: int) -> tk.PhotoImage | None:
        frames = self.move_frames.get(state)
        if not frames:
            return None
        return frames[index % len(frames)]