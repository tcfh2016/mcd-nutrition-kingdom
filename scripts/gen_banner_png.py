#!/usr/bin/env python3
"""生成麦当劳配色 banner PNG（本地 IDE / GitHub 都能显示的 README 头图）。"""
from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 280

# ---- 对角渐变背景 #DA291C -> #A61408 ----
top = (0xDA, 0x29, 0x1C)
bot = (0xA6, 0x14, 0x08)
img = Image.new("RGB", (W, H))
px = img.load()
for y in range(H):
    for x in range(0, W, 4):  # 4px 步长提速，视觉无差
        t = (x + y) / (W + H)
        r = int(top[0] + (bot[0] - top[0]) * t)
        g = int(top[1] + (bot[1] - top[1]) * t)
        b = int(top[2] + (bot[2] - top[2]) * t)
        for dx in range(4):
            if x + dx < W:
                px[x + dx, y] = (r, g, b)

draw = ImageDraw.Draw(img)

YELLOW = (0xFF, 0xC7, 0x2C)
WHITE = (0xFF, 0xFF, 0xFF)
LIGHT = (0xFF, 0xD9, 0xD4)

# ---- 底部黄色细带 ----
draw.rectangle([0, H - 12, W, H], fill=YELLOW)

# ---- 金色拱门 M（两个倒 U）----
def arch(cx, top_y, bottom_y, r, width):
    """倒 U 拱：两条竖线 + 顶部半圆，圆心 cx。"""
    left = cx - r
    right = cx + r
    # 左竖线
    draw.line([(left, bottom_y), (left, top_y)], fill=YELLOW, width=width)
    # 右竖线
    draw.line([(right, bottom_y), (right, top_y)], fill=YELLOW, width=width)
    # 顶部半圆（180° -> 360° = 上半圆）
    box = [cx - r, top_y - r, cx + r, top_y + r]
    draw.arc(box, start=180, end=360, fill=YELLOW, width=width)
    # 圆角端点（竖线底部 + 半圆两端小圆帽）
    for (ex, ey) in [(left, bottom_y), (right, bottom_y), (left, top_y), (right, top_y)]:
        rr = width // 2
        draw.ellipse([ex - rr, ey - rr, ex + rr, ey + rr], fill=YELLOW)

# 拱门整体平移，对齐 SVG 的 translate(66,44)
off_x, off_y = 66, 44
# 拱1：圆心 156, 竖线 top 152 bottom 234, r=50
arch(off_x + 90, off_y + 108, off_y + 190, 50, 34)
# 拱2：圆心 256
arch(off_x + 190, off_y + 108, off_y + 190, 50, 34)

# ---- 文字 ----
def font(path, size):
    return ImageFont.truetype(path, size)

bold = font("C:/Windows/Fonts/arialbd.ttf", 56)
reg = font("C:/Windows/Fonts/arial.ttf", 28)
small = font("C:/Windows/Fonts/arial.ttf", 18)

title = "McDonald's Nutrition Agent"
sub = "Eat well. Live well."
foot = "Powered by McDonald's MCP \u00b7 156 real menu nutrition data"

# 若标题超宽则降字号
w_title = draw.textlength(title, font=bold)
if w_title > 790:
    bold = font("C:/Windows/Fonts/arialbd.ttf", 48)
    w_title = draw.textlength(title, font=bold)

draw.text((384, 84), title, font=bold, fill=WHITE)
draw.text((386, 152), sub, font=reg, fill=YELLOW)
draw.text((386, 202), foot, font=small, fill=LIGHT)

out = "D:/AI/Workbuddy/mcd-dev/mcd-nutrition-agent/docs/banner.png"
img.save(out)
print(f"[SAVED] {out}  title_width={w_title:.0f}px")
