# tray.py

"""系统托盘管理器。"""
from __future__ import annotations
import time
import threading
from PIL import Image, ImageDraw
from typing import TYPE_CHECKING

try:
    import pystray
    from pystray import MenuItem as item
except ImportError:
    pystray = None

if TYPE_CHECKING:
    from .app import PetApp

class TrayManager:
    def __init__(self, app: PetApp) -> None:
        self.app = app
        self.icon: pystray.Icon | None = None
        self._is_visible = True

    def start(self) -> None:
        if pystray is None:
            print("[tray] 未安装 pystray，系统托盘不可用。请运行 pip install pystray pillow")
            return

        # 1. 加载或生成图标
        try:
            # 如果你有图标素材，放在 pet/assets/icon.png
            from .config import ASSETS_DIR
            icon_path = ASSETS_DIR / "icon.png"
            image = Image.open(icon_path)
        except Exception:
            # 兜底：动态画一个黄色圆脸
            image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            dc = ImageDraw.Draw(image)
            dc.ellipse((8, 8, 56, 56), fill="#ffd28a", outline="#c98a3d", width=3)
            dc.ellipse((20, 24, 28, 32), fill="#3b2b20") # 左眼
            dc.ellipse((36, 24, 44, 32), fill="#3b2b20") # 右眼

        # 2. 定义菜单动作（都在 pystray 子线程触发，必须用 after 调度到主线程）
        def on_show_hide(icon, item):
            self.app.window.root.after(0, self._toggle_visibility)

        def on_interact(icon, item):
            self.app.window.root.after(0, self.app._interact)

        def on_panel(icon, item):
            self.app.window.root.after(0, self.app.open_control_panel)

        def on_quit(icon, item):
            self.app.window.root.after(0, self.app.quit)

        def on_lift(icon, item):
            self.app.window.root.after(0, self._lift_window)

        # 3. 构建菜单
        menu = pystray.Menu(
            item('显示/隐藏宠物', on_show_hide, default=True),
            item('提至最前', on_lift),
            pystray.Menu.SEPARATOR,
            item('👋 互动', on_interact),
            item('⚙️ 控制面板', on_panel),
            pystray.Menu.SEPARATOR,
            item('🚪 退出', on_quit)
        )

        # 4. 创建并启动托盘（必须在子线程）
        self.icon = pystray.Icon("DesktopPet", image, "桌面宠物", menu)
        threading.Thread(target=self.icon.run, daemon=True).start()

    def _toggle_visibility(self) -> None:
        root = self.app.window.root
        if self._is_visible:
            root.withdraw() # 隐藏窗口
            self._is_visible = False
        else:
            root.deiconify() # 显示窗口
            self._is_visible = True
            self._lift_window()    # 提到最前

    def _lift_window(self):
        root = self.app.window.root
        if not self._is_visible:
            self._toggle_visibility()
            return
        root.lift()
        root.focus_force()

    def stop(self) -> None:
        if self.icon:
            self.icon.visible = False    # 先发送一次隐藏请求
            self.icon.stop()
            self.icon = None
            time.sleep(0.15)    # 给 Windows 消息队列留 150 毫秒去处理清理消息