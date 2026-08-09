# app.py

import os
import random
import time
import tkinter as tk
from tkinter import filedialog
import winsound
from pathlib import Path

from .config import SPRITES_DIR, PetConfig, load_config
from .foods import FOODS, Food, calculate_file_feed_value, create_food_from_file
from .notifier import Message, Notifier
from .renderer import Bubble, Renderer
from .spritesheet import Spritesheet
from .states import LOOP_BACK_TO_IDLE, Animator, PetState
from .stats import DecayRates, PetStats
from .window import PetWindow

PET_SAYINGS = [
    "喵呜喵呜~",
    "好摸，好舒服",
    "再摸摸我嘛~",
    "嘻嘻~",
    "最喜欢主人了",
]
RANDOM_SPEECH = [
    "我在发呆~",
    "要不要一起玩呀？",
    "明天也要早起哦",
    "注意休息哦",
]


class PetApp:
    def __init__(self, cfg=None) -> None:
        self.cfg = cfg or load_config()
        self.rates = DecayRates(
            hunger_per_hour=self.cfg.hunger_per_hour,
            mood_per_hour=self.cfg.mood_per_hour,
            energy_per_hour=self.cfg.energy_per_hour,
            energy_recover_per_hour=self.cfg.energy_recover_per_hour,
        )
        self.window = PetWindow(self.cfg, hit_test=self._hit_test)
        root = self.window.root

        self.stats = PetStats.load()
        self._apply_offline_elapsed()

        self.animator = Animator()
        sheet = None
        if self.cfg.use_spritesheet:
            path = SPRITES_DIR / "spritesheet.png"
            if path.exists():
                try:
                    sheet = Spritesheet(root, self.cfg)
                    print(f"[app] 已加载图集：{path.name}")
                except Exception as exc:
                    print(f"[app] 图集加载失败，改用矩形占位绘制：{exc}")
        self.renderer = Renderer(self.window.canvas, self.cfg, sheet)
        self.notifier = Notifier(self.cfg, root, self._on_message)

        self._sleeping = False
        self._bubble = None
        self._dragged = False
        self._last_decay = time.time()
        self._last_random = time.time()
        self._last_save = time.time()
        self._last_random_move = time.time()
        self._move_speed = 10
        self._selected = False
        self._move_direction = (0, 0)
        self._random_move_interval = 8.0
        self._random_move_duration = 2.0
        self._is_random_moving = False
        self._random_move_end = 0.0

        self._setup_menu()
        self.window.bind_drag(on_start=self._drag_start, on_move=self._drag_move, on_end=self._drag_end)
        # self.window.canvas.bind("<Button-1>", self._click_press)
        # self.window.canvas.bind("<ButtonRelease-1>", self._click_release)
        self.window.canvas.bind("<Double-Button-1>", self._double_click)
        self.window.canvas.bind("<Button-3>", self._menu_popup)
        root.bind("<Escape>", lambda _e: self.quit())
        root.bind("<KeyPress>", self._on_key_press)
        root.bind("<KeyRelease>", self._on_key_release)
        root.focus_set()
        self._setup_drop_target()

        self.notifier.start()
        self.animator.play(PetState.IDLE, loop=True, now=time.time())
        self._tick()

        self._drag_start_pos = (0, 0)

    def run(self) -> None:
        self.window.root.mainloop()

    def _tick(self) -> None:
        try:
            now = time.time()
            self._decay(now)
            self._update_state(now)
            self._handle_movement(now)
            self.animator.tick(now)
            if self._bubble and now > self._bubble.expire:
                self._bubble = None
            self.renderer.draw(self.animator.state, self.animator.frame, bubble=self._bubble)
            self._maybe_random_action(now)
            if now - self._last_save > self.cfg.auto_save_interval:
                self._last_save = now
                self.stats.save()
        finally:
            self.window.root.after(100, self._tick)

    def _decay(self, now: float) -> None:
        dt = now - self._last_decay
        self._last_decay = now
        if dt <= 0:
            return
        self.stats.apply_idle_seconds(dt, sleeping=self._sleeping, rates=self.rates)

    def _apply_offline_elapsed(self) -> None:
        hours = (time.time() - self.stats.last_seen) / 3600.0
        if hours > 0.01:
            self.stats.apply_elapsed(hours, sleeping=False, rates=self.rates)
            print(f"[app] 离线 {hours:.1f} 小时，属性已按时间流逝更新")

    def _update_state(self, now: float) -> None:
        state = self.animator.state
        if self._sleeping:
            self.animator.play(PetState.SLEEPING, loop=True, now=now)
            return
        if state in LOOP_BACK_TO_IDLE and self.animator.finished:
            self.animator.play(PetState.IDLE, loop=True, now=now)
            state = PetState.IDLE
        if state == PetState.IDLE:
            if self.stats.is_hungry:
                self.animator.play(PetState.SAD, now=now)
            elif self.stats.energy <= 3:
                self._auto_sleep(now)

    def _maybe_random_action(self, now: float) -> None:
        if now - self._last_random < self.cfg.random_action_interval:
            return
        self._last_random = now
        if self._sleeping or self.animator.state != PetState.IDLE:
            return
        if random.random() > self.cfg.random_action_chance:
            return
        action = random.choice(("wave", "happy", "speak"))
        if action == "wave":
            self._say("(挥手)")
            self.animator.play(PetState.WAVING, now=now)
        elif action == "happy":
            self.animator.play(PetState.HAPPY, now=now)
        else:
            self._say(random.choice(RANDOM_SPEECH))
            self.animator.play(PetState.SPEAKING, now=now)

    def _handle_movement(self, now: float) -> None:
        # 键盘移动
        if self._selected and (self._move_direction[0] != 0 or self._move_direction[1] != 0):
            dx, dy = self._move_direction
            self._move_pet(dx * self._move_speed, dy * self._move_speed)
            self._update_move_animation(dx, dy)
            return  # 有键盘移动时不处理随机移动，也不重置状态

        # 随机移动
        if not self._selected and not self._sleeping and not self._dragged:
            if not self._is_random_moving:
                if now - self._last_random_move > self._random_move_interval:
                    if random.random() < 0.3:
                        self._start_random_move(now)
            else:
                if now >= self._random_move_end:
                    self._stop_random_move()
                else:
                    dx, dy = self._move_direction
                    self._move_pet(dx * self._move_speed, dy * self._move_speed)
                    self._update_move_animation(dx, dy)
                    return  # 正在随机移动，不重置

        # 如果当前状态是移动状态，且不在移动中（键盘/随机），回到 IDLE
        if self.animator.state in (PetState.MOVE_UP, PetState.MOVE_DOWN,
                                   PetState.MOVE_LEFT, PetState.MOVE_RIGHT):
            self.animator.play(PetState.IDLE, loop=True, now=time.time())

    def _start_random_move(self, now: float) -> None:
        self._is_random_moving = True
        self._random_move_end = now + self._random_move_duration
        self._move_direction = (random.choice([-1, 0, 1]), random.choice([-1, 0, 1]))
        while self._move_direction == (0, 0):
            self._move_direction = (random.choice([-1, 0, 1]), random.choice([-1, 0, 1]))
        self._update_move_animation(self._move_direction[0], self._move_direction[1])
        self._last_random_move = now

    def _stop_random_move(self) -> None:
        self._is_random_moving = False
        self._move_direction = (0, 0)
        if self.animator.state != PetState.SLEEPING and self.animator.state != PetState.DRAG:
            self.animator.play(PetState.IDLE, loop=True, now=time.time())

    def _move_pet(self, dx: int, dy: int) -> None:
        root = self.window.root
        x = root.winfo_x() + dx
        y = root.winfo_y() + dy
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        w = self.cfg.window_w
        h = self.cfg.window_h
        x = max(0, min(sw - w, x))
        y = max(0, min(sh - h, y))
        root.geometry(f"+{x}+{y}")

    def _update_move_animation(self, dx: int, dy: int) -> None:
        if self._sleeping or self._dragged:
            return
        if dx > 0 and dy == 0:
            self.animator.play(PetState.MOVE_RIGHT, loop=True, now=time.time())
        elif dx < 0 and dy == 0:
            self.animator.play(PetState.MOVE_LEFT, loop=True, now=time.time())
        elif dy < 0 and dx == 0:
            self.animator.play(PetState.MOVE_UP, loop=True, now=time.time())
        elif dy > 0 and dx == 0:
            self.animator.play(PetState.MOVE_DOWN, loop=True, now=time.time())
        elif dx != 0 and dy != 0:
            if self.animator.state != PetState.BUSY:
                self.animator.play(PetState.BUSY, loop=True, now=time.time())

    def _on_key_press(self, event: tk.Event) -> None:
        if not self._selected:
            return
        key = event.keysym
        if key == "KP_Up" or key == "Up":
            self._move_direction = (0, -1)
        elif key == "KP_Down" or key == "Down":
            self._move_direction = (0, 1)
        elif key == "KP_Left" or key == "Left":
            self._move_direction = (-1, 0)
        elif key == "KP_Right" or key == "Right":
            self._move_direction = (1, 0)
        elif key == "KP_Home":
            self._move_direction = (-1, -1)
        elif key == "KP_Prior":
            self._move_direction = (1, -1)
        elif key == "KP_End":
            self._move_direction = (-1, 1)
        elif key == "KP_Next":
            self._move_direction = (1, 1)
        elif key == "KP_Begin":
            self._move_direction = (0, 0)

    def _on_key_release(self, event: tk.Event) -> None:
        key = event.keysym
        if key in ("KP_Up", "Up", "KP_Down", "Down", "KP_Left", "Left", "KP_Right", "Right",
                   "KP_Home", "KP_Prior", "KP_End", "KP_Next", "KP_Begin"):
            self._move_direction = (0, 0)
            if not self._is_random_moving and not self._sleeping and not self._dragged:
                self.animator.play(PetState.IDLE, loop=True, now=time.time())
            if self.animator.state in (PetState.MOVE_UP, PetState.MOVE_DOWN,
                                       PetState.MOVE_LEFT, PetState.MOVE_RIGHT):
                self.animator.play(PetState.IDLE, loop=True, now=time.time())

    def _setup_drop_target(self) -> None:
        try:
            from tkinterdnd2 import TkinterDnD, DND_FILES
            TkinterDnD.require(self.window.root)
            self.window.canvas.drop_target_register(DND_FILES)
            self.window.canvas.dnd_bind('<<Drop>>', self._on_file_drop)
            print("[app] 文件拖拽投喂已启用")
        except ImportError:
            print("[app] tkinterdnd2 未安装，文件拖拽投喂不可用 (pip install tkinterdnd2)")
        except Exception as e:
            print(f"[app] 文件拖拽设置失败: {e}")

    def _on_file_drop(self, event) -> None:
        files = event.data
        if isinstance(files, str):
            import re
            files = re.findall(r'\{([^}]+)\}|(\S+)', files)
            files = [f[0] or f[1] for f in files]
        for file_path in files:
            if os.path.isfile(file_path):
                self._feed_file(file_path)

    def _feed_file(self, file_path: str) -> None:
        try:
            satiety, mood, detail = calculate_file_feed_value(file_path)
            food = create_food_from_file(file_path)
            now = time.time()
            self._sleeping = False
            self.stats.feed(satiety, mood)
            self.stats.save()
            self._say(f"文件投喂成功！{food.emoji} 饱食度+{int(satiety)} 心情+{int(mood)}")
            self.animator.play(PetState.EATING, now=now)
            try:
                os.remove(file_path)
                print(f"[app] 已删除投喂文件: {file_path}")
            except Exception as e:
                print(f"[app] 删除文件失败: {e}")
        except Exception as e:
            print(f"[app] 文件投喂失败: {e}")
            self._say("文件投喂失败~")

    def _click_press(self, event: tk.Event) -> None:
        self._dragged = False

    def _click_release(self, event: tk.Event) -> None:
        # 如果发生过拖拽，drag_end 已经由 bind_drag 调用，这里只处理纯点击
        if self._dragged:
            self._dragged = False
            return
        self._selected = not self._selected
        if self._selected:
            self._say("选中啦~ (小键盘方向键移动)")
        else:
            self._say("取消选中")
        self._interact()

    def _double_click(self, _event: tk.Event) -> None:
        now = time.time()
        if self._sleeping:
            self._wake(now)
            return
        self._say("你好呀~")
        self.animator.play(PetState.WAVING, now=now)

    def _interact(self) -> None:
        now = time.time()
        if self._sleeping:
            self._wake(now)
            return
        self.stats.pet()
        self.stats.save()
        self._say(random.choice(PET_SAYINGS))
        self.animator.play(PetState.HAPPY, now=now)

    def _feed(self, food: Food) -> None:
        now = time.time()
        self._sleeping = False
        self.stats.feed(food.satiety, food.mood)
        self.stats.save()
        self._say(f"好好吃！{food.emoji}")
        self.animator.play(PetState.EATING, now=now)

    def _feed_local_file_dialog(self) -> None:
        file_path = filedialog.askopenfilename(
            title="选择要投喂的文件",
            filetypes=[
                ("所有文件", "*.*"),
                ("文本文件", "*.txt *.md"),
                ("代码文件", "*.py *.js *.ts *.json *.html *.css"),
                ("文档", "*.pdf *.doc *.docx *.xls *.xlsx"),
                ("图片", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"),
                ("压缩包", "*.zip *.rar *.7z"),
            ]
        )
        if file_path:
            self._feed_file(file_path)

    def _wave(self) -> None:
        now = time.time()
        if self._sleeping:
            self._wake(now)
            return
        self._say("你好呀~")
        self.animator.play(PetState.WAVING, now=now)

    def _toggle_sleep(self) -> None:
        now = time.time()
        if self._sleeping:
            self._wake(now)
        else:
            self._sleeping = True
            self._say("晚安~ Zzz")
            self.animator.play(PetState.SLEEPING, loop=True, now=now)
            self.stats.save()

    def _auto_sleep(self, now: float) -> None:
        self._sleeping = True
        self._say("好困啊……先睡了 Zzz")
        self.animator.play(PetState.SLEEPING, loop=True, now=now)

    def _wake(self, now: float) -> None:
        if not self._sleeping:
            return
        self._sleeping = False
        self.stats.wake_up()
        self.stats.save()
        self._say("醒啦！")
        self.animator.play(PetState.HAPPY, now=now)

    def _drag_start(self, event: tk.Event) -> None:  # 加上 event 参数
        self._dragged = False
        self._drag_start_pos = (event.x_root, event.y_root)
        self._selected = False
        if self._is_random_moving:
            self._stop_random_move()
        self.window.set_click_through(False)

    def _drag_move(self, event: tk.Event = None) -> None:
        # 只有移动超过 3 像素，才认为是拖拽
        if not self._dragged:
            dx = event.x_root - self._drag_start_pos[0]
            dy = event.y_root - self._drag_start_pos[1]
            if abs(dx) > 3 or abs(dy) > self.cfg.drag_threshold:
                self._dragged = True

        if self._dragged:
            if not self._sleeping and self.animator.state != PetState.DRAG:
                self.animator.play(PetState.DRAG, loop=True, now=time.time())

    def _drag_end(self, event: tk.Event) -> None:
        self.window.set_click_through(self.cfg.click_through)  # 恢复穿透设置

        if self._dragged:
            # 发生过移动 → 拖拽结束
            if self.animator.state == PetState.DRAG:
                self.animator.play(PetState.IDLE, loop=True, now=time.time())
            self._dragged = False
        else:
            # 没有移动 → 纯点击（原来的 _click_release 逻辑）
            self._selected = not self._selected
            if self._selected:
                self._say("选中啦~ (小键盘方向键移动)")
            else:
                self._say("取消选中")
            self._interact()

    def _on_message(self, msg: Message) -> None:
        self._say(f"{msg.source}·{msg.sender}：{msg.content}"[:80])
        if not self._sleeping:
            self.animator.play(PetState.BUSY, now=time.time())
        if self.cfg.beep_on_message:
            try:
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except Exception:
                pass

    def _test_message(self) -> None:
        self._on_message(Message("手动测试", "系统", "这是一条测试消息"))

    def _say(self, text: str) -> None:
        self._bubble = Bubble(text=text, expire=time.time() + self.cfg.bubble_seconds)

    def _show_status(self) -> None:
        self._say(self.stats.summary())

    def _hit_test(self, x: int, y: int) -> bool:
        return self.renderer.is_over_body(x, y)

    def _setup_menu(self) -> None:
        menu = tk.Menu(self.window.root, tearoff=0)
        feed_menu = tk.Menu(menu, tearoff=0)
        for food in FOODS:
            feed_menu.add_command(
                label=f"{food.emoji} {food.name}（饱+{int(food.satiety)}）",
                command=lambda f=food: self._feed(f),
            )
        feed_menu.add_separator()
        feed_menu.add_command(
            label="📁 本地文件投喂...",
            command=self._feed_local_file_dialog,
        )
        menu.add_cascade(label="🍕 投喂", menu=feed_menu)
        menu.add_command(label="👋 互动", command=self._interact)
        menu.add_command(label="😊 挥手", command=self._wave)
        menu.add_command(label="😴 睡眠/唤醒", command=self._toggle_sleep)
        menu.add_command(label="📊 查看状态", command=self._show_status)
        menu.add_command(label="🔔 测试消息", command=self._test_message)
        menu.add_separator()
        menu.add_command(label="🚪 退出", command=self.quit)
        self._menu = menu

    def _menu_popup(self, event: tk.Event) -> None:
        try:
            self._menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._menu.grab_release()

    def quit(self) -> None:
        self.stats.save()
        self.notifier.stop()
        self.window.root.destroy()
