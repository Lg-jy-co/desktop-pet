# 桌面宠物

一个基于 Python + Tkinter 实现的桌面宠物程序，兼容 Codex hatch-pet 的精灵图规范。

## 功能特性

- **投喂系统** - 6 种食物（苹果、蛋糕、鱼干、鸡腿、可乐、零食），每种饱食度和心情加成不同
- **互动系统** - 点击抚摸、双击挥手、拖拽移动
- **状态机** - 13 种状态：待机、开心、进食、睡眠、难过、忙碌、挥手、拖拽、说话，以及上/下/左/右四个移动方向
- **消息通知** - 内置模拟器 + JSON 文件监听，为微信/QQ 接入预留接口
- **属性系统** - 饥饿/心情/能量三维属性，支持离线时间增量计算
- **数据持久化** - 自动保存/加载宠物状态到 data/pet_state.json
- **精灵图渲染** - 有图用图，无图用内置程序化绘制兜底

## 新增功能

### 本地文件投喂
- 在投喂菜单中新增“本地文件投喂”选项
- 投喂值规则：基础值 1，扩展名倍率（.txt*5、.py*10、.md*3、.json*2），文件名关键词倍率（含“水果”*2、gift*5、零食*3）
- 投喂后源文件会被删除（请投喂副本或可丢弃文件）
- 拖拽投喂需要 tkinterdnd2（pip install tkinterdnd2）

### 键盘移动
- 点击宠物选中后，使用方向键（或小键盘方向键）移动
- 四个方向拥有独立的移动动画（通过 `move_spritesheet.png` 提供）
- 松开按键后自动恢复待机状态

### 随机移动
- 宠物每约 8 秒有 30% 几率随机移动（持续 2 秒）
- 选中状态时禁用随机移动

### 拖拽动画
- 拖拽时播放 DRAG 占位状态（身体扁平）
- 拖拽会清除选中状态

### 通知修复
- 修复 _on_message 正确使用 now=time.time()

## 快速开始

```bash
cd desktop-pet
python main.py
```

```bash
python main.py --no-click-through
python main.py --config data/config.json
```

## 运行测试

```bash
python tests/smoke_test.py
```

## 打包为 exe（可选）

```bash
pip install pyinstaller
pyinstaller -F -w -n DesktopPet main.py
```

## 操作说明

| 操作 | 效果 |
|-----|------|
| 左键点击（未拖拽） | 选中 / 取消选中宠物，并抚摸互动 |
| 拖拽鼠标 | 移动宠物窗口 |
| 右键菜单 | 投喂、互动、挥手、睡眠/唤醒…… |
| 方向键 | 选中时移动宠物 |
| ESC | 退出程序 |

## 配置文件

配置文件位于 data/config.json（首次运行自动生成），主要参数：

```json
{
  "window_w": 240,
  "window_h": 270,
  "topmost": true,
  "click_through": true,
  "use_spritesheet": true,
  "hunger_per_hour": 1.6,
  "mood_per_hour": 0.7,
  "energy_per_hour": 1.1,
  "energy_recover_per_hour": 35.0,
  "hungry_threshold": 75.0,
  "sleepy_threshold": 22.0,
  "auto_save_interval": 60.0,
  "demo_message_interval": 45.0,
  "bubble_seconds": 6.0,
  "beep_on_message": true,
  "use_move_spritesheet": true,
  "drag_threshold": 3
}
```

## 精灵图规范

如需替换自定义贴图，请按以下规范制作：

pet/assets/sprites/spritesheet.png：
- 仅包含 9 个情绪状态（idle ~ speaking）
- 移动状态使用独立的 `move_spritesheet.png`
- **画布尺寸**：1536 × 1872 像素（8 列 × 9 行，每格 192 × 208）
- **背景**：透明
- **行号对应状态**（可在 config.json 中修改 atlas.row_map）：

| 行号 | 状态名 | 说明 |
|------|--------|-----|
| 0 | idle | 待机/眨眼/环顾 |
| 1 | happy | 开心/跳跃 |
| 2 | eating | 进食/张嘴 |
| 3 | sleeping | 睡觉/闭眼/Zzz |
| 4 | sad | 难过/流泪 |
| 5 | busy | 忙碌/敲键盘/电脑屏幕 |
| 6 | waving | 挥手/打招呼 |
| 7 | drag | 被拖拽 |
| 8 | speaking | 说话/张嘴 |

每行帧数建议参考 pet/states.py 中的 STATE_TIMING（每状态每帧时长表）。



**生成占位精灵图：**
```bash
python tools/make_placeholder_sheet.py
```

pet/assets/sprites/move_spritesheet.png：

- **画布尺寸**：768 × 832 像素（4 列 × 4 行，每格 192 × 208）
- **背景**：透明
- **行号对应状态**（可在 config.json 中修改 move_atlas.row_map）：

| 行号 | 状态名 | 说明   |
|------|--------|------|
| 0 | move_up | 向上移动 |
| 1 | move_down | 向下移动 |
| 2 | move_left | 向左移动 |
| 3 | move_right | 向右移动 |


每行帧数建议参考 pet/states.py 中的 STATE_TIMING（每状态每帧时长表）。

## 消息通知接入

框架预留了微信/QQ 接入接口，两种方式：

### 方式一：JSON 文件监听（推荐）
其他程序向 data/inbox.json 追加消息：
```json
[
  {"source": "微信", "sender": "张三", "content": "中午一起吃饭吗？"},
  {"source": "QQ", "sender": "小李", "content": "在吗？发你一个文件"}
]
```

### 方式二：自定义 Hook
继承 pet.notifier.BaseHook 实现自己的消息源：
```python
from pet.notifier import BaseHook, Message

class WeChatHook(BaseHook):
    name = "微信"
    def start(self, on_message):
        pass
    def stop(self):
        pass
```

## 目录结构

```
desktop-pet/
├── main.py
├── requirements.txt
├── pet/
│   ├── __init__.py
│   ├── app.py
│   ├── window.py
│   ├── renderer.py
│   ├── spritesheet.py
│   ├── states.py
│   ├── stats.py
│   ├── foods.py
│   ├── notifier.py
│   ├── config.py
│   └── assets/
│       ├── sprites/
│       └── sounds/
├── tools/
│   └── make_placeholder_sheet.py
├── data/
│   ├── config.json
│   ├── pet_state.json
│   └── inbox.json
└── docs/
    └── image-spec.md
```

## 开发路线图

- [x] 核心框架（窗口、渲染、状态机、属性、投喂、持久化）
- [x] 消息通知框架（模拟器 + JSON 文件监听）
- [x] 占位精灵图生成器
- [ ] 微信 Hook 实现（需第三方库或 adb）
- [ ] QQ Hook 实现
- [ ] 系统托盘图标
- [ ] 更多食物/动作/语音
- [ ] 设置界面（GUI）

## 许可证

MIT License
