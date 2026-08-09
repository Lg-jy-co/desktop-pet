# 桌面宠物 精灵图规范（供 AI 绘图 & 手工替换参考）

> 目标：生成两张 **可被程序直接读取** 的精灵图集，放入 `pet/assets/sprites/` 后，程序即可自动识别并播放对应动画。  
> 主图集兼容 **Codex hatch-pet 标准**：1536×1872、8 列 × 9 行、每格 192×208、PNG 透明背景。  
> 移动图集为独立文件，规格：768×832、4 列 × 4 行，每格同样 192×208。

---

## 1. 主图集 `spritesheet.png`（情绪状态）

### 1.1 硬性规格

| 项目 | 数值 | 说明 |
|------|------|------|
| 文件名 | `spritesheet.png` | 固定，不可改 |
| 画布尺寸 | **1536 × 1872 px** | 8 列 × 192 = 1536；9 行 × 208 = 1872 |
| 网格 | **8 列 × 9 行** | 列 = 帧，行 = 状态 |
| 单格尺寸 | **192 × 208 px** | `cell_w × cell_h` |
| 色彩模式 | **RGBA (32-bit)** | 必须含 Alpha 通道 |
| 背景 | **完全透明 (Alpha=0)** | 无灰底、无网格线、无水印 |
| 未用格 | **完全透明** | 超过该状态帧数的格子留空 |

> ⚠️ 程序在 `spritesheet.py` 中按 `cfg.cell_w=192, cell_h=208, cols=8, rows=9` 硬切图；**任何尺寸偏差都会导致错位或读取失败**。

### 1.2 行号 ↔ 状态映射

程序在 `config.py -> AtlasConfig.row_map` 中定义，`states.py -> PetState` 枚举对应。  
**移动状态不在本图集中，它们由移动图集负责。**

| 行号 (row) | 状态名 | 枚举值 | 默认帧数 | 说明 |
|-----------|--------|--------|----------|------|
| 0 | `idle` | `IDLE` | 6 | 待机：眨眼、环顾 |
| 1 | `happy` | `HAPPY` | 5 | 开心：原地跳跃、眯眼笑 |
| 2 | `eating` | `EATING` | 5 | 进食：张嘴咀嚼、有食物图标 |
| 3 | `sleeping` | `SLEEPING` | 4 | 睡眠：闭眼、Zzz、微微起伏 |
| 4 | `sad` | `SAD` | 4 | 难过：垂头、流泪 |
| 5 | `busy` | `BUSY` | 5 | 忙碌：敲键盘/看屏幕、冒汗 |
| 6 | `waving` | `WAVING` | 4 | 挥手：抬手打招呼 |
| 7 | `drag` | `DRAG` | 3 | 被拖拽：被拽着衣服提起（身体轻微拉伸） |
| 8 | `speaking` | `SPEAKING` | 4 | 说话/气泡：张嘴 |

> **如需改行号**，必须同步修改 `config.json` 的 `atlas.row_map` 与 `states.py` 的枚举顺序，**强烈建议保持默认**。

### 1.3 每行帧数与播放时长（来自 `states.py -> STATE_TIMING`）

| 状态 | 帧数 | 每帧时长 | 循环？ |
|------|------|----------|--------|
| idle | 6 | 280, 110, 110, 140, 140, 320 ms | ✅ 是 |
| happy | 5 | 140, 140, 140, 140, 280 ms | ❌ 否（播完回 idle） |
| eating | 5 | 150, 150, 150, 150, 260 ms | ❌ 否 |
| sleeping | 4 | 520, 520, 520, 520 ms | ✅ 是 |
| sad | 4 | 180, 180, 180, 300 ms | ❌ 否 |
| busy | 5 | 120, 120, 120, 120, 220 ms | ❌ 否 |
| drag | 3 | 100, 100, 200 ms | ❌ 否（拖拽期间持续） |
| waving | 4 | 140, 140, 140, 280 ms | ❌ 否 |
| speaking | 4 | 150, 150, 150, 280 ms | ❌ 否 |

**关键点**：
- 每行**前 N 格**对应 N 个帧，**多余格子必须留透明**
- `idle` 和 `sleeping` 是循环动画（`loop=True`），其余播放一次后自动回 `idle`
- 最后一帧通常是“定格/收尾帧”，不要画成中间过渡帧

---

## 2. 移动图集 `move_spritesheet.png`（移动方向）

### 2.1 硬性规格

| 项目 | 数值 | 说明 |
|------|------|------|
| 文件名 | `move_spritesheet.png` | 固定，不可改 |
| 画布尺寸 | **768 × 832 px** | 4 列 × 192 = 768；4 行 × 208 = 832 |
| 网格 | **4 列 × 4 行** | 列 = 帧，行 = 方向 |
| 单格尺寸 | **192 × 208 px** | 与主图集完全一致 |
| 色彩模式 | **RGBA (32-bit)** | 含 Alpha 通道 |
| 背景 | **完全透明** | 同主图集要求 |
| 未用格 | **完全透明** | 超过帧数的格子留空 |

> ⚠️ 移动图集单独加载，不影响主图集；缺失时方向键移动将回退到矢量占位绘制。

### 2.2 行号 ↔ 方向映射

配置位于 `config.py -> MoveAtlasConfig.row_map`，默认如下：

| 行号 (row) | 状态名 | 枚举值 | 默认帧数 | 说明 |
|-----------|--------|--------|----------|------|
| 0 | `move_up` | `MOVE_UP` | 4 | 向上移动（腿部/身体向上动态） |
| 1 | `move_down` | `MOVE_DOWN` | 4 | 向下移动 |
| 2 | `move_left` | `MOVE_LEFT` | 4 | 向左移动（侧面行走） |
| 3 | `move_right` | `MOVE_RIGHT` | 4 | 向右移动（镜像或不同帧） |

> **如需调整行序**，修改 `config.json` 中 `move_atlas.row_map`，但需保证与 `states.py` 中新增的 `MOVE_*` 枚举一致。

### 2.3 帧时长与循环

移动状态在 `states.py` 中的 `STATE_TIMING` 默认如下（可根据动画自行调整）：

```python
PetState.MOVE_UP: [120, 120, 120, 120]
PetState.MOVE_DOWN: [120, 120, 120, 120]
PetState.MOVE_LEFT: [120, 120, 120, 120]
PetState.MOVE_RIGHT: [120, 120, 120, 120]
```
- 移动动画均为循环播放，方向键按住时连续播放，松开后回到 idle。
- 每帧时长保持均匀（120ms）即可，也可调整为更自然的节奏。

### 2.4 视觉设计建议
- 统一风格：角色造型、线条、颜色应与主图集一致。
- 方向感：
  - `move_up` / `move_down`：正面朝前，腿部或身体有明显的上下运动趋势。
  - `move_left` / `move_right`：侧面行走姿态，注意左右方向不要搞反（左行时角色面向左，右行时面向右）。
- 帧数扩展：如想增加帧数（如 6 帧），需同步修改图片宽度（6 × 192 = 1152）和 `MoveAtlasConfig.cols`，并在 `STATE_TIMING` 中补足对应数量的毫秒值。

---

## 3. 程序如何读取与渲染（两图集通用）
### 3.1 切图逻辑 (`spritesheet.py`)
主图集和移动图集使用完全相同的切图逻辑，只是行映射和帧数来源不同。
伪代码：
```python
# 主图集
for state in [IDLE, HAPPY, ...]:
    row = atlas.row_map_reverse[state]
    count = min(len(STATE_TIMING[state]), atlas.cols)
    # 切出 count 帧

# 移动图集
if pet_cfg.use_move_spritesheet and move_path.exists():
    for state in [MOVE_UP, MOVE_DOWN, MOVE_LEFT, MOVE_RIGHT]:
        row = move_atlas.row_map_reverse[state]
        count = min(len(STATE_TIMING[state]), move_atlas.cols)
        # 切出 count 帧
```

### 3.2 绘制位置 (`renderer.py -> _draw_image`)

```python
# 底部对齐窗口底部，留 26px 边距，水平居中
x = window_w // 2
y = window_h - 26 - img.height() // 2
```

> **设计建议**：把角色脚部/身体底部放在单格**下方 10~20px** 处；不要画满整格，否则会贴边。

### 3.3 点击判定 (`renderer.py -> is_over_body`)

- 以窗口中心 (w*0.5, h*0.55) 为椭圆中心
- 半径：rx = w*0.34 ≈ 82px, ry = h*0.27 ≈ 73px
- **角色主体像素应落在该椭圆内**，否则点击、右键菜单可能无法触发。

### 3.4 兜底渲染 (`renderer.py -> _draw_vector`)
无图时程序用代码画椭圆、眼睛、嘴巴等。有图时完全不走这套逻辑，所以图里必须包含所有表现细节。

## 4. 视觉设计规范（通用）
### 4.1 整体风格
- 统一色调、统一线条粗细（2~4px 描边）、统一光源方向。
- 同一行所有帧必须是同一角色、同一比例、同一视角。
- 角色在格子内垂直居中偏下，水平居中。

### 4.2 透明度与边缘
- **格子边缘 8~12px 必须全透明**，防止切图时边缘溢出。
- 不要在格子外画阴影、光晕——**全部内容在 192×208 内**。
- 当角色描边出现异常颜色（如紫色等），可尝试用以下程序进行修复：
```python
# image_fix.py
# 依赖Pillow库完成，可通过 pip install Pillow 安装

from PIL import Image
img = Image.open("image_origin.png")    # 此处填欲修复的图片文件名
# 将 alpha 通道二值化，阈值 128
alpha = img.getchannel('A').point(lambda x: 255 if x > 128 else 0)
img.putalpha(alpha)
img.save("image_fixed.png")
```

## 5. 生成与替换流程
### 5.1 主图集
1. 按主图集规格生成/绘制 **1536×1872** 大图。
2. 检查尺寸、透明、每行帧数。
3. 覆盖 `pet/assets/sprites/spritesheet.png`。

### 5.2 移动图集
1. 按移动图集规格生成/绘制 **768×832** 大图。
2. 检查四行四个方向，每行帧数符合预期。
3. 覆盖 `pet/assets/sprites/move_spritesheet.png`。

### 5.3 验证方法
```bash
python main.py
```

- 情绪状态：右键菜单 → 投喂、互动、睡眠、挥手、测试消息，观察所有 9 种动画。
- 移动动画：点击宠物选中，使用方向键移动，检查四个方向的行走动画。
- 拖拽：拖拽窗口时应显示 drag 状态。
- 如果移动图集缺失，移动时自动回退矢量绘制（不会报错）。

## 6. 常见坑 & Checklist
### 6.1 主图集常见问题
|问题	|原因	|解决 |
|------|------|----|
|动画错位/撕裂	|画布非 1536×1872 或单格非 192×208	|严格按规格导出|
|某状态不播放	|该行帧数 < `STATE_TIMING` 定义	|补足帧数，或改 `STATE_TIMING`|
|角色偏上/偏下	|脚部未靠近格子底部	|角色脚部靠近格子底部 10~20px|
|点击无反应	|主体像素超出椭圆判定区	|缩小角色或调整判定参数|
|背景有灰边	|导出时未勾选透明/Alpha	|导出 PNG 时确保背景 Alpha=0|
|拖拽状态变形异常	|drag 行画的不是拖拽姿态	|画出被拉扯的效果，不要依赖程序变形|

### 6.2 移动图集常见问题
|问题	|原因	|解决 |
|----|----|----|
|移动无动画，只显示椭圆	|文件缺失或命名错误	|确认文件名为 `move_spritesheet.png`，放在正确目录|
|移动动画方向错误	|行映射混乱	|检查 `move_atlas.row_map` 与图片行序是否一致|
|某方向只动几帧就卡住	|帧数不足	|确保图片该行帧数 ≥ `STATE_TIMING` 中对应方向的帧数|
|移动与情绪状态混淆	|移动状态使用了情绪行的索引	|移动状态不在主图集中，不要在主图集里画移动帧|

✅ 上线前自检清单
-[ ] 主图集 `spritesheet.png` **1536×1872，透明，9 行完整**
-[ ] 移动图集 `move_spritesheet.png` **768×832，透明，4 行完整**
-[ ] 每行帧数 ≥ `STATE_TIMING` 定义值
-[ ] 角色主体在椭圆判定区内
-[ ] 无外溢阴影/光晕
-[ ] 主图集和移动图集风格统一
-[ ] python main.py 可完整测试情绪动画和方向键移动动画

## 7. 进阶：自定义行映射 / 增加状态
如需在主图集中新增状态（如 `running`、`jumping`）：
1. `states.py` 增加 `PetState` 枚举值
2. `STATE_TIMING` 增加帧时长列表
3. `config.py` `AtlasConfig.row_map` 增加行号映射
4. `renderer.py` `BODY_COLORS` 增加颜色（矢量模式用）
5. 精灵图增加对应行（需扩展 `rows` 或复用空行）
6. `spritesheet.py` 会自动读取新映射
> 当前主图集 `rows=9` 已满，**新增状态需修改 `AtlasConfig.rows` 并重新生成更大图集**，建议评估后再做。

如需增加新的移动方向（如斜向）：
- 在 `states.py` 添加新 `MOVE_*` 状态
- 在 `MoveAtlasConfig.row_map` 中分配新行
- 扩展移动图集高度（`rows` 增加），图片尺寸相应改变

## 8. 相关文件速查
| 文件                                 | 作用                                      |
|------------------------------------|-----------------------------------------|
| `pet/config.py`                    | 	`AtlasConfig`（主图集）、`MoveAtlasConfig`（移动图集） |
| `pet/states.py`                    | 	`PetState` 枚举（含移动状态）、`STATE_TIMING` 帧时长    |
| `pet/spritesheet.py`	              | 加载主图集和移动图集，按行/列切出帧                      |
| `pet/renderer.py`	                 | 绘制入口，自动根据状态选择图集或矢量模式                    |
| `tools/make_placeholder_sheet.py`	 | 生成主图集占位图（不含移动图集）                        |
| `docs/image-spec.md`	              | 本文档                                     |
