"""宠物属性：饥饿 / 心情 / 精力，带真实时间衰减与 JSON 持久化。"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field

from .config import STATE_FILE

MIN_VAL = 0.0
MAX_VAL = 100.0


def _clamp(value: float) -> float:
    return max(MIN_VAL, min(MAX_VAL, value))


@dataclass(frozen=True)
class DecayRates:
    """属性随时间变化的速率（每小时）。"""

    hunger_per_hour: float = 1.6
    mood_per_hour: float = 0.7
    energy_per_hour: float = 1.1
    energy_recover_per_hour: float = 35.0


DEFAULT_RATES = DecayRates()


@dataclass
class PetStats:
    hunger: float = 20.0     # 0-100，越高越饿
    mood: float = 70.0
    energy: float = 85.0
    last_seen: float = field(default_factory=time.time)
    fed_count: int = 0
    petted_count: int = 0

    # ---- 读取与保存 ----

    @classmethod
    def load(cls) -> "PetStats":
        if STATE_FILE.exists():
            try:
                raw = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                valid = {k: raw[k] for k in asdict(cls()).keys() if k in raw}
                return cls(**valid)
            except Exception as exc:
                print(f"[stats] 读取存档失败，使用初始值：{exc}")
        return cls()

    def save(self) -> None:
        self.last_seen = time.time()
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # ---- 时间流逝 ----

    def apply_elapsed(
        self, hours: float, sleeping: bool = False, rates: DecayRates = DEFAULT_RATES
    ) -> None:
        """按经过的小时数更新属性。sleeping=True 表示这段时间在睡觉。"""
        self.hunger = _clamp(self.hunger + hours * rates.hunger_per_hour)
        if sleeping:
            self.energy = _clamp(self.energy + hours * rates.energy_recover_per_hour)
        else:
            self.mood = _clamp(self.mood - hours * rates.mood_per_hour)
            self.energy = _clamp(self.energy - hours * rates.energy_per_hour)
            if self.energy <= 0:
                self.mood = _clamp(self.mood - hours * 0.5)

    def apply_idle_seconds(
        self, seconds: float, sleeping: bool = False, rates: DecayRates = DEFAULT_RATES
    ) -> None:
        """运行期间按秒衰减。"""
        self.apply_elapsed(seconds / 3600.0, sleeping=sleeping, rates=rates)

    # ---- 交互 ----

    def feed(self, satiety: float, mood: float) -> None:
        self.hunger = _clamp(self.hunger - satiety)
        self.mood = _clamp(self.mood + mood)
        self.fed_count += 1

    def pet(self) -> None:
        self.mood = _clamp(self.mood + 8.0)
        self.energy = _clamp(self.energy - 0.5)
        self.petted_count += 1

    def wake_up(self) -> None:
        self.energy = _clamp(self.energy + 10.0)
        self.mood = _clamp(self.mood + 2.0)

    # ---- 状态判定 ----

    @property
    def is_hungry(self) -> bool:
        return self.hunger >= 75.0

    @property
    def is_sleepy(self) -> bool:
        return self.energy <= 22.0

    @property
    def is_happy(self) -> bool:
        return self.mood >= 85.0

    def summary(self) -> str:
        return (
            f"饥饿 {self.hunger:.0f}/100  心情 {self.mood:.0f}/100  "
            f"精力 {self.energy:.0f}/100\n"
            f"投喂 {self.fed_count} 次 · 抚摸 {self.petted_count} 次"
        )