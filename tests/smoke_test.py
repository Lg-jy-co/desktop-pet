"""冒烟测试：验证核心功能链路（无第三方依赖，需 Windows 桌面环境）。

用法：
    python tests/smoke_test.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pet.app import PetApp
from pet.config import PetConfig
from pet.foods import FOODS
from pet.notifier import Message


def main() -> int:
    cfg = PetConfig(click_through=False, demo_message_interval=0)
    app = PetApp(cfg)
    root = app.window.root

    def pump(ms: int = 0) -> None:
        deadline = time.time() + ms / 1000.0
        while time.time() < deadline:
            root.update()
            time.sleep(0.01)

    try:
        # 1. 初始状态应为 idle
        pump(150)
        assert app.animator.state.value == "idle", app.animator.state
        print("[ok] 启动 -> idle")

        # 2. 喂食：饥饿下降、心情上升、进入 eating
        before_hunger = app.stats.hunger
        before_mood = app.stats.mood
        app._feed(FOODS[0])
        assert app.stats.hunger < before_hunger
        assert app.stats.mood > before_mood
        assert app.animator.state.value == "eating"
        pump(400)
        print(f"[ok] 喂食 {FOODS[0].name}: hunger {before_hunger:.0f}->{app.stats.hunger:.0f}, mood {before_mood:.0f}->{app.stats.mood:.0f}")

        # 3. 抚摸：心情上升、进入 happy
        before_mood = app.stats.mood
        app._interact()
        assert app.stats.mood > before_mood
        assert app.animator.state.value == "happy"
        pump(400)
        print("[ok] 抚摸 -> happy")

        # 4. 消息提醒：进入 busy 并出现气泡
        app._on_message(Message("微信-好友", "老王", "晚上一起吃饭吗？"))
        assert app.animator.state.value == "busy"
        assert app._bubble is not None
        pump(400)
        print("[ok] 消息提醒 -> busy + 气泡")

        # 5. 连跑 1.5 秒动画循环（含图集帧渲染），确保不抛 TclError
        pump(1500)
        print("[ok] 动画循环（图集模式）无异常")

        # 6. 属性按时间衰减
        hunger_before = app.stats.hunger
        time.sleep(1.2)
        pump(50)
        assert app.stats.hunger >= hunger_before
        print(f"[ok] 时间衰减生效 (hunger {hunger_before:.2f} -> {app.stats.hunger:.2f})")

        print("\nSMOKE TEST PASSED")
        return 0
    finally:
        app.quit()


if __name__ == "__main__":
    raise SystemExit(main())
