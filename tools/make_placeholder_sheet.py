# make_placeholder_sheet.py

"""生成占位精灵图集：pet/assets/sprites/spritesheet.png

规格与 hatch-pet 一致：8 列 x 9 行，每格 192x208，PNG 透明背景。
每个状态占一行，行序见 pet/config.py 的 row_map。

占位图用纯 Python 绘制（零依赖），仅供开发调试；
正式美术图请按 docs/image-spec.md 的规格让 AI 生成后直接替换本文件。

用法：python tools/make_placeholder_sheet.py
"""
from __future__ import annotations

import math
import struct
import sys
import zlib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

OUT = PROJECT_ROOT / "pet" / "assets" / "sprites" / "spritesheet.png"

COLS, ROWS = 8, 9
CW, CH = 96, 104          # 半分辨率绘制，最后 2x 放大
SCALE = 2

# ---------------- 极简 PNG 写入 ----------------

def write_png(path: Path, w: int, h: int, rgba: bytes) -> None:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    raw = bytearray()
    stride = w * 4
    for y in range(h):
        raw.append(0)
        raw.extend(rgba[y * stride : (y + 1) * stride])
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 6))
    png += chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)


# ---------------- 形状绘制（SDF + 抗锯齿） ----------------

def blend_px(buf: bytearray, w: int, x: int, y: int, rgba, alpha: float) -> None:
    if alpha <= 0:
        return
    i = (y * w + x) * 4
    inv = 1.0 - alpha
    buf[i] = int(buf[i] * inv + rgba[0] * alpha)
    buf[i + 1] = int(buf[i + 1] * inv + rgba[1] * alpha)
    buf[i + 2] = int(buf[i + 2] * inv + rgba[2] * alpha)
    buf[i + 3] = int(buf[i + 3] * inv + rgba[3] * alpha)


def fill(buf: bytearray, w: int, h: int, box, rgba, sdf) -> None:
    x0, y0, x1, y1 = (int(v) for v in box)
    for py in range(max(0, y0), min(h, y1)):
        for px in range(max(0, x0), min(w, x1)):
            d = sdf(px + 0.5, py + 0.5)
            cov = 0.5 - d
            if cov <= 0:
                continue
            blend_px(buf, w, px, py, rgba, min(1.0, cov))


def ellipse(cx, cy, rx, ry):
    def sdf(x, y):
        dx, dy = (x - cx) / rx, (y - cy) / ry
        return (math.sqrt(dx * dx + dy * dy) - 1.0) * min(rx, ry)

    return sdf


def circle(cx, cy, r):
    return ellipse(cx, cy, r, r)


def ring_arc(cx, cy, r, thick, a0, a1):
    """圆环的一段圆弧；a0/a1 为弧度，0 指向右，顺时针（y 向下）。"""

    def norm_angle(a):
        return a % (2 * math.pi)

    span = norm_angle(a1 - a0)

    def sdf(x, y):
        dx, dy = x - cx, y - cy
        dist = math.hypot(dx, dy)
        angle = math.atan2(dy, dx)
        rel = norm_angle(angle - a0)
        if rel > span:
            return 1.0
        return abs(dist - r) - thick / 2.0

    return sdf


def rounded_rect(cx, cy, hw, hh, r):
    def sdf(x, y):
        qx = abs(x - cx) - (hw - r)
        qy = abs(y - cy) - (hh - r)
        ox, oy = max(qx, 0.0), max(qy, 0.0)
        return math.hypot(ox, oy) + min(max(qx, qy), 0.0) - r

    return sdf


# ---------------- 每个状态的画法 ----------------

def draw_frame(buf: int, w: int, h: int, cx: int, cy: int, state: str, frame: int) -> None:
    """state 对应一行，frame 对应列。cx/cy 是格子中心。"""
    r = 27  # 身体半径（半分辨率单位）
    bounce = 0
    body = (255, 210, 138, 255)

    if state == "happy":
        bounce = [0, -6, -3, -9, -1][frame % 5]
    elif state == "eating":
        body = (255, 217, 160, 255)
    elif state == "sleeping":
        body = (201, 182, 232, 255)
        bounce = [-3, -1][frame % 2]
    elif state == "sad":
        body = (168, 191, 224, 255)
    elif state == "busy":
        body = (255, 207, 125, 255)
    elif state == "drag":
        body = (232, 195, 122, 255)

    cy += bounce
    ry = 27 if state != "drag" else 22

    # 身体
    fill(buf, w, h, (cx - r - 2, cy - ry - 2, cx + r + 2, cy + ry + 2), body, ellipse(cx, cy, r, ry))
    # 肚皮
    fill(buf, w, h, (cx - 14, cy + 3, cx + 14, cy + 24), (255, 243, 224, 255), ellipse(cx, cy + 12, 13, 11))

    eye_y = cy - 7
    dx = 8
    mouth_y = cy + 9

    if state == "sleeping":
        # 闭眼（∩ 弧）+ Zzz
        for ex in (cx - dx, cx + dx):
            fill(buf, w, h, (ex - 5, eye_y - 5, ex + 5, eye_y + 5), (59, 43, 32, 255), ring_arc(ex, eye_y, 3.5, 1.6, math.radians(200), math.radians(340)))
        for i, (rr, ox, oy) in enumerate([(5, 16, -22), (3.6, 22, -30), (2.6, 26, -36)]):
            fill(buf, w, h, (cx + ox - rr - 1, cy + oy - rr - 1, cx + ox + rr + 1, cy + oy + rr + 1), (122, 107, 176, 255), circle(cx + ox, cy + oy, rr))
    else:
        if state in ("happy", "waving", "busy"):
            # 开心眼（^ ^）
            for ex in (cx - dx, cx + dx):
                fill(buf, w, h, (ex - 5, eye_y - 5, ex + 5, eye_y + 5), (59, 43, 32, 255), ring_arc(ex, eye_y, 4, 2.2, math.radians(200), math.radians(340)))
        elif state == "idle" and frame in (1, 2):
            # 眨眼
            for ex in (cx - dx, cx + dx):
                fill(buf, w, h, (ex - 5, eye_y - 5, ex + 5, eye_y + 5), (59, 43, 32, 255), ring_arc(ex, eye_y, 3.5, 1.6, math.radians(200), math.radians(340)))
        else:
            # 圆眼睛
            for ex in (cx - dx, cx + dx):
                fill(buf, w, h, (ex - 4, eye_y - 4, ex + 4, eye_y + 4), (59, 43, 32, 255), circle(ex, eye_y, 3.2))

    if state == "eating" or state == "speaking":
        mw = 12 if state == "eating" else 8
        mh = 10 if state == "eating" else 7
        fill(buf, w, h, (cx - mw, mouth_y - 4, cx + mw, mouth_y + mh), (91, 43, 26, 255), ellipse(cx, mouth_y + 2, mw, mh))
        if state == "eating":
            fill(buf, w, h, (cx + 2 - 6, mouth_y - 16, cx + 2 + 6, mouth_y - 4), (224, 85, 85, 255), circle(cx + 2, mouth_y - 10, 5.5))
            fill(buf, w, h, (cx - 6, mouth_y - 19, cx + 6, mouth_y - 12), (122, 155, 61, 255), ring_arc(cx, mouth_y - 15, 4.5, 2.5, math.radians(20), math.radians(160)))
    elif state == "sad":
        fill(buf, w, h, (cx - 9, mouth_y - 4, cx + 9, mouth_y + 6), (59, 43, 32, 255), ring_arc(cx, mouth_y, 7, 2.2, math.radians(200), math.radians(340)))
        fill(buf, w, h, (cx - dx + 1, eye_y + 2, cx - dx + 6, eye_y + 9), (127, 184, 232, 255), circle(cx - dx + 3, eye_y + 5, 2.6))
    elif state == "sleeping":
        pass
    else:
        fill(buf, w, h, (cx - 8, mouth_y - 4, cx + 8, mouth_y + 6), (59, 43, 32, 255), ring_arc(cx, mouth_y + 2, 6, 2.2, math.radians(20), math.radians(160)))

    # 腮红（开心/挥手）
    if state in ("happy", "waving"):
        for sx in (cx - 17, cx + 17):
            fill(buf, w, h, (sx - 4, mouth_y - 3, sx + 4, mouth_y + 5), (255, 179, 179, 255), circle(sx, mouth_y + 1, 3.2))

    if state == "waving":
        # 举起的手
        fill(buf, w, h, (cx + r - 4, cy - ry - 8, cx + r + 10, cy - ry + 6), body, circle(cx + r + 3, cy - ry - 1, 7))
        for i in range(3):
            fill(buf, w, h, (cx + r + 12 + i * 2, cy - ry - 5, cx + r + 15 + i * 2, cy - ry + 3), (201, 138, 61, 200), rounded_rect(cx + r + 13.5 + i * 2, cy - ry - 1, 1.2, 4, 1))
    if state == "busy":
        # 耳机 + 汗滴
        for sx in (cx - r, cx + r):
            fill(buf, w, h, (sx - 5, cy - ry - 5, sx + 5, cy + ry - 12), (70, 70, 90, 255), rounded_rect(sx, cy - ry + 5, 3.5, ry - 8, 3))
        fill(buf, w, h, (cx + 12, cy - 22, cx + 19, cy - 14), (159, 212, 245, 255), circle(cx + 15, cy - 18, 3.2))
    if state == "drag":
        # 拖拽线
        for i, dy in enumerate((-6, 0, 6)):
            x = cx - r - 8 - i * 3
            fill(buf, w, h, (x - 8, cy + dy - 1, x + 8, cy + dy + 2), (201, 168, 106, 200), rounded_rect(x, cy + dy, 8, 1.5, 1))


def main() -> None:
    w, h = CW * COLS, CH * ROWS
    buf = bytearray(w * h * 4)  # 全透明

    row_states = ["idle", "happy", "eating", "sleeping", "sad", "busy", "waving", "drag", "speaking"]
    from pet.states import STATE_TIMING, PetState

    for row, state in enumerate(row_states):
        frames = len(STATE_TIMING[PetState(state)])
        for col in range(frames):
            cx = col * CW + CW // 2
            cy = row * CH + CH // 2
            draw_frame(buf, w, h, cx, cy, state, col)

    # 2x 最近邻放大
    out_w, out_h = w * SCALE, h * SCALE
    out = bytearray(out_w * out_h * 4)
    for y in range(h):
        for x in range(w):
            i = (y * w + x) * 4
            px = bytes(buf[i : i + 4])
            oy, ox = y * SCALE, x * SCALE
            o = (oy * out_w + ox) * 4
            out[o : o + 4] = px
            out[o + 4 : o + 8] = px
            out[o + out_w * 4 : o + out_w * 4 + 4] = px
            out[o + out_w * 4 + 4 : o + out_w * 4 + 8] = px

    write_png(OUT, out_w, out_h, bytes(out))
    print(f"已生成占位图集：{OUT}（{out_w}x{out_h}）")


if __name__ == "__main__":
    main()