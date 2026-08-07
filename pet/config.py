"""全局配置。

优先级：内置默认值 < data/config.json（可选覆盖）。
所有路径均相对项目根目录，因此整个文件夹可以随意移动。
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent          # pet/
PROJECT_DIR = BASE_DIR.parent                       # 项目根


def _app_root() -> Path:
    """打包成 exe 后，把数据和资源都放在 exe 同级目录，方便迁移。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return PROJECT_DIR


APP_ROOT = _app_root()
ASSETS_DIR = APP_ROOT / "pet" / "assets"
SPRITES_DIR = ASSETS_DIR / "sprites"
SOUNDS_DIR = ASSETS_DIR / "sounds"
DATA_DIR = APP_ROOT / "data"

CONFIG_FILE = DATA_DIR / "config.json"
STATE_FILE = DATA_DIR / "pet_state.json"
INBOX_FILE = DATA_DIR / "inbox.json"

# 透明键色：窗口里这个颜色的像素会完全透明（Windows Tk 特性）
MAGENTA = "#ff00ff"


@dataclass
class AtlasConfig:
    """精灵图集布局，默认对齐 hatch-pet 的 8x9 规格（可改）。"""

    cols: int = 8
    rows: int = 9
    cell_w: int = 192
    cell_h: int = 208
    # 行号 -> 状态名。真实图片需要按这个行序排列。
    row_map: dict = field(
        default_factory=lambda: {
            0: "idle",
            1: "happy",
            2: "eating",
            3: "sleeping",
            4: "sad",
            5: "busy",
            6: "waving",
            7: "drag",
            8: "speaking",
        }
    )

    def __post_init__(self) -> None:
        # JSON 配置里的键会是字符串，统一转成 int，避免行号拼接出错
        self.row_map = {int(k): v for k, v in self.row_map.items()}


@dataclass
class PetConfig:
    window_w: int = 240
    window_h: int = 270
    start_x: int | None = None
    start_y: int | None = None
    topmost: bool = True
    # True：光标不在宠物身上时窗口点击穿透（Windows）
    click_through: bool = True
    # 有 spritesheet.png 就用图集，否则使用内置矢量占位画
    use_spritesheet: bool = True

    # ---- 属性变化速率（按真实时间） ----
    hunger_per_hour: float = 1.6          # 每小时增加的饿饿值
    mood_per_hour: float = 0.7            # 每小时降低的心情
    energy_per_hour: float = 1.1          # 每小时降低的精力
    energy_recover_per_hour: float = 35.0  # 睡眠时每小时恢复的精力
    hungry_threshold: float = 75.0    # 高于此值显示“饿”状态
    sleepy_threshold: float = 22.0    # 低于此值显示“困”状态

    # ---- 行为 ----
    auto_save_interval: float = 60.0  # 秒
    idle_after_action: float = 6.0    # 互动/投喂后回到 idle 的秒数
    random_action_interval: float = 16.0  # 随机卖萌间隔
    random_action_chance: float = 0.5     # 每次随机判定概率

    # ---- 消息提醒 ----
    demo_message_interval: float = 45.0   # 模拟消息间隔（0=关闭）
    inbox_poll_interval: float = 2.0      # 监听 data/inbox.json 的轮询间隔
    bubble_seconds: float = 6.0           # 气泡显示时长
    beep_on_message: bool = True

    atlas: AtlasConfig = field(default_factory=AtlasConfig)


def _deep_merge(base: dict, override: dict) -> dict:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def _from_raw(cfg: PetConfig, raw: dict) -> PetConfig:
    """把用户 JSON 覆盖到默认配置上，返回新配置。"""
    merged = asdict(cfg)
    _deep_merge(merged, raw)
    atlas = merged.get("atlas")
    if isinstance(atlas, dict):
        merged["atlas"] = AtlasConfig(**atlas)
    elif "atlas" in merged:
        merged.pop("atlas")  # atlas 不是对象时回退默认
    return PetConfig(**merged)


def load_config() -> PetConfig:
    cfg = PetConfig()
    if CONFIG_FILE.exists():
        try:
            raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            cfg = _from_raw(cfg, raw)
        except Exception as exc:  # ??????????
            print(f"[config] ?? {CONFIG_FILE} ??????????{exc}")
    else:
        # 首次运行：生成一份默认配置，方便用户按需修改
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            CONFIG_FILE.write_text(
                json.dumps(asdict(cfg), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass
    return cfg
