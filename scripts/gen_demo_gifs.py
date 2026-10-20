#!/usr/bin/env python3
"""自动录制「四大宫殿」演示 GIF 动图。

原理：用 Playwright（headless Chromium）加载 web/index.html，
      对四宫分别执行真实交互（点击 / 输入 / 切 Tab），
      逐帧截图后用 Pillow 合成 GIF，输出到 docs/。

用法：
    python scripts/gen_demo_gifs.py            # 生成全部四张
    python scripts/gen_demo_gifs.py --only meal # 只生成点餐宫

依赖：
    pip install playwright pillow
    python -m playwright install chromium
"""
import argparse
import os
import time

from playwright.sync_api import sync_playwright
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
INDEX = os.path.join(ROOT, "web", "index.html")
DOCS = os.path.join(ROOT, "docs")

# 录屏视口（宽度固定，高度可容纳完整内容）
W, H = 900, 1100
# GIF 缩放比例（GIF 体积控制：原始 900 宽 → 输出 720 宽）
SCALE = 0.8
OUT_W = int(W * SCALE)
OUT_H = int(H * SCALE)


def _shot(page, out_dir, idx):
    """截取整页视口并缩放保存，返回保存的 PNG 路径。"""
    png = os.path.join(out_dir, f"f{idx:03d}.png")
    page.screenshot(path=png)
    img = Image.open(png).resize((OUT_W, OUT_H), Image.LANCZOS)
    img.save(png)
    return png


def _scroll_to(page, selector):
    """滚动到指定元素（让关键结果进入视口）。"""
    try:
        page.eval_on_selector(selector, "el => el.scrollIntoView({block:'start'})")
    except Exception:
        pass


def _frames_to_gif(frames, out_gif, fps=3, dwell=1):
    """把 PNG 帧序列合成为 GIF。

    fps 控制播放速度：3fps ≈ 每帧停留 333ms，动作舒缓不花眼。
    dwell 控制每个关键状态额外停留的帧数（dwell=1 时每个状态停留 2 帧），
    让读者有充分时间看清结果。
    """
    # 每个关键帧重复 dwell+1 次，拉长停留时间
    expanded = []
    for f in frames:
        for _ in range(dwell + 1):
            expanded.append(f)
    imgs = [Image.open(f).convert("RGB") for f in expanded]
    # 首帧作为基准，其余帧用 optimize + duration 控制
    imgs[0].save(
        out_gif,
        save_all=True,
        append_images=imgs[1:],
        duration=int(1000 / fps),
        loop=0,
        optimize=False,
        disposal=2,
    )
    size = os.path.getsize(out_gif)
    print(f"[GIF] {out_gif}  {len(frames)} 状态 ×{dwell+1}  {fps}fps  {size/1024:.0f} KB")


def record_meal(page, out_dir):
    """点餐宫：改热量 → 生成 → 切模式 → 勾忌口 → 生成。"""
    frames = []
    # 初始：页面默认已渲染点餐宫结果，滚动到结果卡
    _scroll_to(page, "#resultCard")
    time.sleep(0.4)
    frames.append(_shot(page, out_dir, len(frames)))
    # 改热量预算为 800（控卡）
    page.fill("#kcal", "800")
    page.click("#go")
    _scroll_to(page, "#resultCard")
    time.sleep(0.5)
    frames.append(_shot(page, out_dir, len(frames)))
    # 切到「增肌高蛋白」
    page.click('.mode-btn[data-mode="protein"]')
    page.click("#go")
    _scroll_to(page, "#resultCard")
    time.sleep(0.5)
    frames.append(_shot(page, out_dir, len(frames)))
    # 切到「控糖低GI」+ 勾选忌口「辣」
    page.click('.mode-btn[data-mode="lowcarb"]')
    page.click('.exclude-chip[data-exclude="辣"]')
    page.click("#go")
    _scroll_to(page, "#resultCard")
    time.sleep(0.5)
    frames.append(_shot(page, out_dir, len(frames)))
    return frames


def record_wish(page, out_dir):
    """许愿宫：点愿望 chip → 语义解析 → 展示结果。"""
    frames = []
    page.click('.tab-btn[data-tab="wish"]')
    time.sleep(0.5)
    frames.append(_shot(page, out_dir, len(frames)))
    # 点「小孩不辣有玩具」
    page.click('.wish-chip[data-wish="我想吃一顿不辣、甜甜的儿童套餐，最好有玩具，500千卡左右"]')
    page.click("#wishGo")
    _scroll_to(page, "#wishResult")
    time.sleep(0.6)
    frames.append(_shot(page, out_dir, len(frames)))
    # 点「爱美不长胖」
    page.click('.wish-chip[data-wish="我想吃一顿不长胖、高蛋白、还不会长痘的晚餐"]')
    page.click("#wishGo")
    _scroll_to(page, "#wishResult")
    time.sleep(0.6)
    frames.append(_shot(page, out_dir, len(frames)))
    # 点「素食者」（无法实现的愿望 → 愿望池）
    page.click('.wish-chip[data-wish="我是素食者，想吃一顿麦当劳"]')
    page.click("#wishGo")
    _scroll_to(page, "#wishResult")
    time.sleep(0.6)
    frames.append(_shot(page, out_dir, len(frames)))
    return frames


def record_kingdom(page, out_dir):
    """潮玩宫：积分账户 → 切商城分类 → 抽奖。"""
    frames = []
    page.click('.tab-btn[data-tab="kingdom"]')
    time.sleep(0.6)
    frames.append(_shot(page, out_dir, len(frames)))
    # 切「实物周边」
    page.click('.sub-tab[data-cat="physical"]')
    time.sleep(0.5)
    frames.append(_shot(page, out_dir, len(frames)))
    # 切「派对体验」
    page.click('.sub-tab[data-cat="party"]')
    time.sleep(0.5)
    frames.append(_shot(page, out_dir, len(frames)))
    # 切回「餐品券」并抽一次
    page.click('.sub-tab[data-cat="coupons"]')
    time.sleep(0.4)
    page.click("#lotteryDraw")
    time.sleep(0.5)
    frames.append(_shot(page, out_dir, len(frames)))
    return frames


def record_activity(page, out_dir):
    """活动宫：活动日历 → 领券 → 派对入口。"""
    frames = []
    page.click('.tab-btn[data-tab="activity"]')
    time.sleep(0.6)
    frames.append(_shot(page, out_dir, len(frames)))
    # 点第一张券「一键领取」
    page.click(".coupon-claim")
    time.sleep(0.5)
    frames.append(_shot(page, out_dir, len(frames)))
    return frames


SCENES = {
    "meal": ("点餐宫", record_meal),
    "wish": ("许愿宫", record_wish),
    "kingdom": ("潮玩宫", record_kingdom),
    "activity": ("活动宫", record_activity),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=list(SCENES.keys()), help="只生成某一宫")
    ap.add_argument("--fps", type=int, default=3, help="GIF 帧率（默认 3，越小越慢）")
    ap.add_argument("--dwell", type=int, default=1, help="每个关键状态额外停留的帧数（默认 1）")
    args = ap.parse_args()

    os.makedirs(DOCS, exist_ok=True)

    names = [args.only] if args.only else list(SCENES.keys())

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        # 每个场景独立 context + 页面，避免状态串扰
        for key in names:
            title, fn = SCENES[key]
            ctx = browser.new_context(
                viewport={"width": W, "height": H},
                device_scale_factor=1,
            )
            page = ctx.new_page()
            # 用 domcontentloaded 避免 file:// 下 fetch 外部资源导致 goto 等待 load 超时
            page.goto("file:///" + INDEX.replace("\\", "/"), wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(1200)

            out_dir = os.path.join(DOCS, f"_gif_{key}")
            os.makedirs(out_dir, exist_ok=True)
            # 清空旧帧
            for f in os.listdir(out_dir):
                if f.endswith(".png"):
                    os.remove(os.path.join(out_dir, f))

            print(f"\n=== 录制「{title}」===")
            try:
                frames = fn(page, out_dir)
            except Exception as e:
                print(f"[ERR] {title} 录制失败: {e}")
                ctx.close()
                continue

            gif_path = os.path.join(DOCS, f"demo-{key}.gif")
            _frames_to_gif(frames, gif_path, fps=args.fps, dwell=args.dwell)
            ctx.close()

        browser.close()

    print("\n全部完成。")


if __name__ == "__main__":
    main()
