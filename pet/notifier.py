"""消息提醒框架。

设计：任何 IM 都可以写一个 hook 类（实现 BaseHook），Notifier 负责把
消息安全地送到 UI 线程（气泡 + 状态 + 可选提示音）。

内置两个可直接用的 hook：
- SimulatorHook  定时生成模拟消息，方便测试
- JsonFileHook   轮询 data/inbox.json，方便其他程序/脚本对接

微信 / QQ 的正式 hook 后续在本文件（或同目录新文件）里按 BaseHook
接口实现即可，接口已经留好。
"""
from __future__ import annotations

import json
import threading
import time
import tkinter as tk
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from .config import INBOX_FILE, PetConfig


@dataclass
class Message:
    source: str   # 来源，如 微信 / QQ / 模拟器
    sender: str
    content: str
    ts: float = field(default_factory=time.time)

    def to_text(self) -> str:
        return f"{self.source}·{self.sender}：{self.content}"


class BaseHook(ABC):
    """消息源接口。实现类必须在独立线程运行，不能直接操作 Tk。"""

    name: str = "base"

    @abstractmethod
    def start(self, on_message) -> None:
        """启动监听。on_message(Message) 会被回调（任意线程）。"""

    @abstractmethod
    def stop(self) -> None:
        """停止监听。"""


class SimulatorHook(BaseHook):
    """模拟消息源，用于演示和测试提醒效果。"""

    name = "模拟器"

    def __init__(self, interval: float) -> None:
        self.interval = interval
        self._stop = threading.Event()
        self._on_message = None
        self._index = 0

    def start(self, on_message) -> None:
        self._on_message = on_message
        threading.Thread(target=self._run, daemon=True).start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        samples = [
            ("微信-群聊", "老王", "晚上一起吃饭吗？"),
            ("QQ-好友", "小美", "在吗？发你一个文件"),
            ("微信-工作群", "张主管", "明早 10 点开会，记得上线"),
            ("QQ-群", "吃瓜群众", "哈哈哈哈这张图笑死我了"),
            ("微信-好友", "妈妈", "记得按时吃饭，早点睡"),
        ]
        while not self._stop.wait(self.interval):
            source, sender, content = samples[self._index % len(samples)]
            self._index += 1
            self._on_message(Message(source, sender, content))


class JsonFileHook(BaseHook):
    """轮询 data/inbox.json 的消息源。

    文件格式：JSON 数组，程序只处理新增条目：
    [{"source": "微信", "sender": "老王", "content": "晚上一起吃饭吗？"}]
    微信 / QQ 的正式 hook 后续可以把收到的消息直接追加到这个文件，
    或者参考本类实现自己的 hook。
    """

    name = "inbox.json"

    def __init__(self, path: Path, poll_interval: float) -> None:
        self.path = path
        self.poll_interval = poll_interval
        self._stop = threading.Event()
        self._on_message = None
        self._seen = 0

    def start(self, on_message) -> None:
        self._on_message = on_message
        self._seen = self._count()
        threading.Thread(target=self._run, daemon=True).start()

    def stop(self) -> None:
        self._stop.set()

    def _count(self) -> int:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return len(data) if isinstance(data, list) else 0
        except Exception:
            return 0

    def _run(self) -> None:
        while not self._stop.wait(self.poll_interval):
            if not self.path.exists():
                continue
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(data, list):
                continue
            for item in data[self._seen:]:
                msg = Message(
                    source=str(item.get("source", "外部")),
                    sender=str(item.get("sender", "未知")),
                    content=str(item.get("content", "")),
                )
                self._on_message(msg)
            self._seen = len(data)


class Notifier:
    """统一管理所有消息 hook，并把消息调度到 Tk 主线程。"""

    def __init__(self, cfg: PetConfig, root: tk.Misc, on_message) -> None:
        self.cfg = cfg
        self.root = root
        self.on_message = on_message
        self._running = False
        self.hooks: list[BaseHook] = []
        if cfg.demo_message_interval > 0:
            self.hooks.append(SimulatorHook(cfg.demo_message_interval))
        self.hooks.append(JsonFileHook(INBOX_FILE, cfg.inbox_poll_interval))

    def start(self) -> None:
        self._running = True
        for hook in self.hooks:
            try:
                hook.start(self._dispatch)
            except Exception as exc:
                print(f"[notifier] hook「{hook.name}」启动失败：{exc}")

    def stop(self) -> None:
        self._running = False
        for hook in self.hooks:
            try:
                hook.stop()
            except Exception:
                pass

    def _dispatch(self, msg: Message) -> None:
        if not self._running:
            return
        try:
            self.root.after(0, lambda: self.on_message(msg))
        except tk.TclError:
            pass