"""宠物状态机。

状态名与精灵图集的行一一对应（见 config.AtlasConfig.row_map）。
每个状态是一串帧，帧时长单位为毫秒；最后一帧播完回到 idle
（sleeping 除外，它保持循环直到被唤醒）。
"""
from __future__ import annotations

from enum import Enum


class PetState(str, Enum):
    IDLE = "idle"
    HAPPY = "happy"
    WAVING = "waving"
    EATING = "eating"
    SLEEPING = "sleeping"
    SAD = "sad"
    BUSY = "busy"
    DRAG = "drag"
    SPEAKING = "speaking"


# 每个状态的一帧时长（毫秒）。最后一帧通常是“停留帧”。
STATE_TIMING: dict[PetState, list[int]] = {
    PetState.IDLE: [280, 110, 110, 140, 140, 320],
    PetState.HAPPY: [140, 140, 140, 140, 280],
    PetState.WAVING: [140, 140, 140, 280],
    PetState.EATING: [150, 150, 150, 150, 260],
    PetState.SLEEPING: [520, 520, 520, 520],
    PetState.SAD: [180, 180, 180, 300],
    PetState.BUSY: [120, 120, 120, 120, 220],
    PetState.DRAG: [100, 100, 200],
    PetState.SPEAKING: [150, 150, 150, 280],
}

# 有“情绪”的状态播完一遍后回到 idle；睡眠/拖动由外部控制退出
LOOP_BACK_TO_IDLE = {
    PetState.HAPPY,
    PetState.WAVING,
    PetState.EATING,
    PetState.SAD,
    PetState.SPEAKING,
}


class Animator:
    """简单的帧动画推进器。"""

    def __init__(self) -> None:
        self.state: PetState = PetState.IDLE
        self.frame = 0
        self.frame_start = 0.0
        self.loop = False

    def play(self, state: PetState, loop: bool = False, now: float = 0.0) -> None:
        if state == self.state and self.loop == loop:
            return
        self.state = state
        self.loop = loop
        self.frame = 0
        self.frame_start = now

    def tick(self, now: float) -> None:
        """按时间推进帧；返回 True 表示切换到了新帧。"""
        timings = STATE_TIMING[self.state]
        elapsed = (now - self.frame_start) * 1000.0
        new_frame = 0
        acc = 0.0
        for idx, ms in enumerate(timings):
            acc += ms
            if elapsed < acc:
                new_frame = idx
                break
        else:
            if self.loop:
                new_frame = 0
                self.frame_start = now
            else:
                new_frame = len(timings) - 1
        if new_frame != self.frame:
            self.frame = new_frame
            return True
        return False

    @property
    def finished(self) -> bool:
        """非循环状态是否已播完（停在最后一帧）。"""
        if self.loop:
            return False
        return self.frame == len(STATE_TIMING[self.state]) - 1