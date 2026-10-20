#!/usr/bin/env python3
"""生成麦当劳营养王国 的 Web 界面（单文件、自包含）。

将 core/nutrition_snapshot.json 的营养数据内联到 HTML 中，
前端用 JS 复刻拼配算法，实现无需后端即可交互的演示界面。
"""
from __future__ import annotations

import json
import os

from core.nutrition import infer_category

HERE = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT = os.path.join(HERE, "core", "nutrition_snapshot.json")
KINGDOM_SNAPSHOT = os.path.join(HERE, "core", "kingdom_snapshot.json")
OUT = os.path.join(HERE, "web", "index.html")


def load_foods():
    with open(SNAPSHOT, "r", encoding="utf-8") as f:
        foods = json.load(f)
    # 前端做类别均衡需要 category 字段，这里补上
    for f in foods:
        f["category"] = infer_category(f["product_name"])
    return foods


def load_kingdom():
    with open(KINGDOM_SNAPSHOT, "r", encoding="utf-8") as f:
        return json.load(f)


def build_html(foods: list, kingdom: dict) -> str:
    food_js = json.dumps(foods, ensure_ascii=False)
    kingdom_js = json.dumps(kingdom, ensure_ascii=False)
    html = TEMPLATE.replace("/*__FOOD_DATA__*/", food_js)
    html = html.replace("/*__KINGDOM_DATA__*/", kingdom_js)
    return html


TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>麦当劳营养王国</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
  :root {
    --bg: #faf9f6;
    --card: #ffffff;
    --border: #e8e6df;
    --text: #1f1f1d;
    --muted: #8a887f;
    --accent: #da291c;
    --accent-2: #ffbc0d;
    --protein: #378add;
    --fat: #ef9f27;
    --carb: #1d9e75;
    --ok: #639922;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    background: var(--bg); color: var(--text); line-height: 1.6;
  }
  .wrap { max-width: 960px; margin: 0 auto; padding: 32px 20px 64px; }
  header { margin-bottom: 24px; }
  header h1 { font-size: 26px; font-weight: 700; margin: 0 0 6px; }
  header .sub { color: var(--muted); font-size: 14px; }
  .badge {
    display: inline-block; background: var(--accent); color: #fff; font-size: 12px;
    padding: 2px 10px; border-radius: 20px; margin-left: 8px; vertical-align: middle;
  }
  .card {
    background: var(--card); border: 1px solid var(--border); border-radius: 14px;
    padding: 20px 24px; margin-bottom: 20px;
  }
  .controls { display: flex; flex-wrap: wrap; gap: 16px; align-items: flex-end; }
  .field { display: flex; flex-direction: column; gap: 6px; }
  .field label { font-size: 13px; color: var(--muted); }
  select, input[type=number] {
    font-size: 15px; padding: 8px 12px; border: 1px solid var(--border); border-radius: 8px;
    background: #fff; color: var(--text); min-width: 120px;
  }
  button.primary {
    font-size: 15px; font-weight: 600; padding: 9px 22px; border: none; border-radius: 8px;
    background: var(--accent); color: #fff; cursor: pointer;
  }
  button.primary:hover { opacity: 0.9; }
  .modes { display: flex; gap: 10px; flex-wrap: wrap; margin: 16px 0 4px; }
  .mode-btn {
    font-size: 13px; padding: 6px 14px; border: 1px solid var(--border); border-radius: 20px;
    background: #fff; cursor: pointer; color: var(--text);
  }
  .mode-btn.active { background: var(--accent); color: #fff; border-color: var(--accent); }
  .mode-hint { font-size: 12px; color: var(--muted); min-height: 18px; }
  .exclude-row { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin-top: 14px; }
  .exclude-label { font-size: 13px; color: var(--muted); }
  .exclude-chip {
    font-size: 12px; padding: 4px 12px; border: 1px solid var(--border); border-radius: 16px;
    background: #fff; cursor: pointer; color: var(--text);
  }
  .exclude-chip.active { background: #fdecec; color: var(--accent); border-color: var(--accent); font-weight: 600; }
  .daily-row { margin-top: 14px; }
  .daily-toggle { display: inline-flex; align-items: center; gap: 8px; font-size: 14px; cursor: pointer; color: var(--text); }
  .daily-toggle input { width: 16px; height: 16px; cursor: pointer; }
  .meal-block { border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; margin-bottom: 14px; background: #fff; }
  .meal-block .meal-head { font-size: 15px; font-weight: 700; margin-bottom: 8px; }
  .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 20px; }
  .metric {
    background: #fff; border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px;
  }
  .metric .label { font-size: 12px; color: var(--muted); }
  .metric .num { font-size: 24px; font-weight: 700; margin-top: 2px; }
  .metric .unit { font-size: 12px; color: var(--muted); font-weight: 400; }
  .table-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; }
  table { width: 100%; min-width: 620px; border-collapse: collapse; font-size: 14px; }
  td:first-child { word-break: break-word; }
  th, td { text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--border); }
  th { color: var(--muted); font-weight: 500; font-size: 13px; }
  tr.total td { font-weight: 700; border-top: 2px solid var(--border); }
  .chart-row { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 8px; }
  .chart-box { position: relative; height: 260px; }
  .legend { display: flex; gap: 16px; flex-wrap: wrap; font-size: 12px; color: var(--muted); margin-bottom: 8px; }
  .legend span { display: flex; align-items: center; gap: 4px; }
  .dot { width: 10px; height: 10px; border-radius: 2px; display: inline-block; }
  .empty { color: var(--muted); padding: 24px 0; text-align: center; }
  .foot { font-size: 12px; color: var(--muted); margin-top: 12px; }
  .tabs { display: flex; gap: 8px; margin-bottom: 20px; }
  .tab-btn {
    font-size: 15px; font-weight: 600; padding: 10px 22px; border: 1px solid var(--border);
    border-radius: 24px; background: #fff; cursor: pointer; color: var(--muted);
  }
  .tab-btn.active { background: var(--accent); color: #fff; border-color: var(--accent); }
  .points-hero {
    display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 16px;
    background: linear-gradient(135deg, #da291c 0%, #b31f14 100%); color: #fff;
    border-radius: 14px; padding: 24px 28px; margin-bottom: 20px;
  }
  .points-big { font-size: 44px; font-weight: 700; line-height: 1; }
  .points-big .unit { font-size: 14px; font-weight: 400; opacity: 0.9; margin-left: 6px; }
  .points-side { text-align: right; font-size: 13px; opacity: 0.92; }
  .sub-tabs { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; }
  .sub-tab {
    font-size: 13px; padding: 6px 16px; border: 1px solid var(--border); border-radius: 18px;
    background: #fff; cursor: pointer; color: var(--text);
  }
  .sub-tab.active { background: #1f1f1d; color: #fff; border-color: #1f1f1d; }
  .goods-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 14px; }
  .goods-card {
    background: #fff; border: 1px solid var(--border); border-radius: 12px; overflow: hidden;
    display: flex; flex-direction: column; transition: transform .12s ease, box-shadow .12s ease;
  }
  .goods-card:hover { transform: translateY(-2px); box-shadow: 0 6px 16px rgba(0,0,0,.08); }
  .goods-img { width: 100%; height: 130px; object-fit: cover; background: #f3f2ee; display: block; }
  .goods-body { padding: 12px 14px; display: flex; flex-direction: column; gap: 6px; flex: 1; }
  .goods-name { font-size: 14px; font-weight: 600; line-height: 1.4; }
  .goods-selling { font-size: 12px; color: var(--muted); line-height: 1.5; flex: 1; }
  .goods-meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
  .tag-point { font-size: 13px; font-weight: 700; color: var(--accent); }
  .tag-price { font-size: 13px; font-weight: 700; color: #1f1f1d; }
  .tag-cat {
    font-size: 11px; color: #8a6d1a; background: #fdf3d7; border-radius: 4px; padding: 1px 6px;
  }
  .lottery-head { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; margin-bottom: 4px; }
  .lottery-tag { font-size: 12px; color: #fff; background: var(--accent); border-radius: 4px; padding: 1px 8px; }
  .prize-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 12px; margin-top: 14px; }
  .prize-item {
    display: flex; align-items: center; gap: 10px; border: 1px solid var(--border);
    border-radius: 10px; padding: 10px 12px; background: #fff;
  }
  .prize-item img { width: 40px; height: 40px; object-fit: cover; border-radius: 6px; background: #f3f2ee; }
  .prize-item .pname { font-size: 13px; line-height: 1.3; }
  .prize-item .ptype { font-size: 11px; color: var(--muted); }
  .campaign-item {
    display: flex; gap: 14px; align-items: center; border: 1px solid var(--border);
    border-radius: 12px; padding: 12px 14px; margin-bottom: 12px; background: #fff;
  }
  .campaign-item img { width: 90px; height: 66px; object-fit: cover; border-radius: 8px; background: #f3f2ee; flex-shrink: 0; }
  .campaign-item .ctitle { font-size: 14px; font-weight: 600; }
  .campaign-item .cdesc { font-size: 12px; color: var(--muted); margin-top: 2px; }
  .campaign-item .cdate { font-size: 11px; color: var(--accent); margin-top: 4px; }
  .kingdom-note { font-size: 12px; color: var(--muted); margin-top: 12px; }
  textarea {
    width: 100%; margin-top: 14px; padding: 12px 14px; font-size: 15px; line-height: 1.6;
    border: 1px solid var(--border); border-radius: 10px; background: #fff; color: var(--text);
    font-family: inherit; resize: vertical;
  }
  textarea:focus { outline: none; border-color: var(--accent); }
  .wish-actions { display: flex; gap: 10px; align-items: center; margin-top: 14px; flex-wrap: wrap; }
  button.ghost {
    font-size: 14px; padding: 9px 18px; border: 1px solid var(--border); border-radius: 8px;
    background: #fff; color: var(--text); cursor: pointer;
  }
  button.ghost:hover { border-color: var(--accent); color: var(--accent); }
  .wish-examples { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin-top: 14px; }
  .wish-ex-label { font-size: 12px; color: var(--muted); }
  .wish-chip {
    font-size: 13px; padding: 5px 12px; border: 1px dashed var(--border); border-radius: 16px;
    background: #fdf9f1; cursor: pointer; color: var(--text);
  }
  .wish-chip:hover { border-color: var(--accent-2); background: #fff6e0; }
  .wish-parse { display: flex; gap: 8px; flex-wrap: wrap; margin: 10px 0 14px; }
  .wish-tag {
    font-size: 12px; padding: 3px 10px; border-radius: 14px; background: #f1efe8; color: #5f5e5a;
  }
  .wish-tag.accent { background: #fdecec; color: var(--accent); }
  .wish-tag.gold { background: #fdf3d7; color: #8a6d1a; }
  .wish-party {
    display: flex; gap: 14px; align-items: center; border: 1px solid #f5d98b; background: #fffaf0;
    border-radius: 12px; padding: 14px 16px; margin-bottom: 12px;
  }
  .wish-party img { width: 80px; height: 60px; object-fit: cover; border-radius: 8px; background: #f3f2ee; flex-shrink: 0; }
  .wish-party .ptitle { font-size: 14px; font-weight: 600; }
  .wish-party .pselling { font-size: 12px; color: var(--muted); margin-top: 2px; }
  .wish-party .pprice { font-size: 13px; font-weight: 700; color: var(--accent); margin-top: 4px; }
  .wish-pool-item {
    display: flex; gap: 12px; align-items: flex-start; border: 1px solid var(--border);
    border-radius: 10px; padding: 12px 14px; margin-bottom: 10px; background: #fff;
  }
  .wish-pool-item .wtext { font-size: 14px; flex: 1; }
  .wish-pool-item .wmeta { font-size: 11px; color: var(--muted); margin-top: 4px; }
  .wish-pool-item .wstatus { font-size: 11px; padding: 2px 8px; border-radius: 10px; flex-shrink: 0; white-space: nowrap; }
  .wish-pool-item .wstatus.done { background: #eaf3de; color: #3b6d11; }
  .wish-pool-item .wstatus.pending { background: #fdf3d7; color: #854f0b; }
  .wish-pool-empty { color: var(--muted); font-size: 13px; padding: 8px 0; }
  .coupon-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 14px; }
  .coupon-card { display: flex; border: 1px solid var(--border); border-radius: 12px; overflow: hidden; background: #fff; }
  .coupon-amount {
    width: 92px; flex-shrink: 0; display: flex; flex-direction: column; align-items: center; justify-content: center;
    background: linear-gradient(135deg, #da291c, #b31f14); color: #fff; padding: 16px 8px;
  }
  .coupon-amount .num { font-size: 22px; font-weight: 700; line-height: 1; }
  .coupon-amount .suffix { font-size: 12px; margin-top: 2px; opacity: .9; }
  .coupon-amount .label { font-size: 10px; opacity: .85; margin-top: 6px; }
  .coupon-body { flex: 1; padding: 12px 14px; display: flex; flex-direction: column; justify-content: space-between; gap: 8px; }
  .coupon-title { font-size: 14px; font-weight: 600; }
  .coupon-desc { font-size: 12px; color: var(--muted); }
  .coupon-claim {
    align-self: flex-start; font-size: 12px; padding: 4px 12px; border: 1px solid var(--accent);
    border-radius: 14px; background: #fff; color: var(--accent); cursor: pointer;
  }
  .coupon-claim:hover { background: var(--accent); color: #fff; }
  .act-section-title { font-size: 16px; font-weight: 700; margin: 0 0 4px; }
  .scene-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 14px; margin-top: 12px; }
  .scene-card { border: 1px solid var(--border); border-radius: 12px; padding: 16px 18px; background: #fff; }
  .scene-title { font-size: 15px; font-weight: 700; }
  .scene-desc { font-size: 13px; color: var(--muted); margin-top: 6px; line-height: 1.5; }
  .scene-tags { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 10px; }
  .scene-tags span { font-size: 11px; color: #8a6d1a; background: #fdf3d7; border-radius: 4px; padding: 1px 8px; }
  .goods-claim { margin-top: 10px; font-size: 13px; padding: 6px 0; border: 1px solid var(--accent); border-radius: 8px; background: #fff; color: var(--accent); cursor: pointer; }
  .goods-claim:hover { background: var(--accent); color: #fff; }
  .goods-claim.done { border-color: #639922; color: #639922; cursor: default; }
  .lottery-cta { font-size: 14px; font-weight: 600; padding: 9px 22px; border: none; border-radius: 8px; background: var(--accent); color: #fff; cursor: pointer; }
  .lottery-cta:hover { opacity: .9; }
  .modal-mask { position: fixed; inset: 0; background: rgba(0,0,0,.4); display: flex; align-items: center; justify-content: center; z-index: 100; padding: 20px; }
  .modal { background: #fff; border-radius: 14px; padding: 24px; max-width: 420px; width: 100%; box-shadow: 0 10px 40px rgba(0,0,0,.2); }
  .modal-title { font-size: 16px; font-weight: 700; margin-bottom: 10px; }
  .modal-body { font-size: 14px; color: var(--text); line-height: 1.6; margin-bottom: 18px; }
  .modal-actions { display: flex; gap: 10px; justify-content: flex-end; }
  @media (max-width: 640px) { .chart-row { grid-template-columns: 1fr; } .points-hero { flex-direction: column; align-items: flex-start; } .points-side { text-align: left; } .wish-party { flex-direction: column; align-items: flex-start; } }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>麦当劳营养王国<span class="badge">McDonald's MCP</span></h1>
    <div class="sub">说出你的热量/营养目标，自动拼出一份「吃得饱、营养对」的麦当劳套餐。基于麦当劳 MCP 真实营养数据。</div>
  </header>

  <nav class="tabs">
    <button class="tab-btn active" data-tab="meal">点餐宫 · 营养点餐</button>
    <button class="tab-btn" data-tab="kingdom">潮玩宫 · 积分乐园</button>
    <button class="tab-btn" data-tab="wish">许愿宫 · 心愿即达</button>
    <button class="tab-btn" data-tab="activity">活动宫 · 联名速递</button>
  </nav>

  <div id="mealPanel">
  <div class="card">
    <div class="modes">
      <button class="mode-btn active" data-mode="calorie">控卡减脂</button>
      <button class="mode-btn" data-mode="protein">增肌高蛋白</button>
      <button class="mode-btn" data-mode="lowcarb">控糖低GI</button>
    </div>
    <div class="mode-hint" id="modeHint"></div>
    <div class="controls">
      <div class="field">
        <label for="kcal">热量预算（千卡）</label>
        <input type="number" id="kcal" value="500" min="100" max="3000" step="50">
      </div>
      <button class="primary" id="go">生成套餐</button>
    </div>
    <div class="exclude-row">
      <span class="exclude-label">忌口 / 过敏原：</span>
      <button class="exclude-chip" data-exclude="辣">辣</button>
      <button class="exclude-chip" data-exclude="鱼">鱼</button>
      <button class="exclude-chip" data-exclude="牛肉">牛肉</button>
      <button class="exclude-chip" data-exclude="猪肉">猪肉</button>
      <button class="exclude-chip" data-exclude="鸡肉">鸡肉</button>
      <button class="exclude-chip" data-exclude="蛋">蛋</button>
      <button class="exclude-chip" data-exclude="乳糖">乳糖</button>
      <button class="exclude-chip" data-exclude="海鲜">海鲜</button>
      <button class="exclude-chip" data-exclude="麸质">麸质</button>
    </div>
    <div class="daily-row">
      <label class="daily-toggle"><input type="checkbox" id="daily"> 全天三餐规划（早餐 / 午餐 / 晚餐，按 30% / 40% / 30% 拆分预算）</label>
    </div>
  </div>

  <div class="metrics" id="metrics" style="display:none;"></div>

  <div class="card" id="resultCard" style="display:none;">
    <h2 style="font-size:16px; font-weight:700; margin:0 0 12px;" id="resultTitle"></h2>
    <div class="table-wrap"><div id="resultTable"></div></div>
    <div class="chart-row">
      <div>
        <div class="legend">
          <span><span class="dot" style="background:#378add;"></span>蛋白质</span>
          <span><span class="dot" style="background:#ef9f27;"></span>脂肪</span>
          <span><span class="dot" style="background:#1d9e75;"></span>碳水</span>
        </div>
        <div class="chart-box"><canvas id="macroChart" role="img" aria-label="三大营养素占比图"></canvas></div>
      </div>
      <div>
        <div class="legend"><span><span class="dot" style="background:#da291c;"></span>热量（千卡）</span></div>
        <div class="chart-box"><canvas id="kcalChart" role="img" aria-label="各餐品热量条形图"></canvas></div>
      </div>
    </div>
  </div>

  <div class="card foot" id="sourceHint">
    数据来源：麦当劳 MCP <code>list-nutrition-foods</code> 真实营养数据（内联快照）。
    启动 <code>web/server.py</code> 后端后，本页面通过 <code>/api/foods</code> 自动加载数据。
  </div>
  </div>

  <div id="kingdomPanel" style="display:none;">
    <div id="kingdomBody"></div>
    <div class="card foot" id="kingdomHint">数据来源：麦当劳 MCP 积分商城 / 抽奖真实数据（内联快照）。启动 <code>web/server.py</code> 后端后，通过 <code>/api/kingdom</code> 自动加载。</div>
  </div>

  <div id="wishPanel" style="display:none;">
    <div class="card">
      <h2 style="font-size:16px; font-weight:700; margin:0 0 6px;">许下你的营养心愿</h2>
      <div class="sub">小孩想吃不辣又好玩、爱美的你想吃「不长胖、高蛋白、还好看」……把想象说出来，Agent 帮你实现；实现不了的，收进愿望池帮你转达麦当劳。</div>
      <textarea id="wishInput" rows="3" placeholder="例如：我想吃一顿不辣、甜甜的儿童套餐，最好有玩具，500 千卡左右"></textarea>
      <div class="wish-actions">
        <button class="primary" id="wishGo">实现愿望</button>
        <button class="ghost" id="wishClear">清空</button>
      </div>
      <div class="wish-examples">
        <span class="wish-ex-label">试试：</span>
        <button class="wish-chip" data-wish="我想吃一顿不辣、甜甜的儿童套餐，最好有玩具，500千卡左右">👶 小孩不辣有玩具</button>
        <button class="wish-chip" data-wish="我想吃一顿不长胖、高蛋白、还不会长痘的晚餐">💅 爱美不长胖</button>
        <button class="wish-chip" data-wish="控糖期想吃麦当劳，低GI，450千卡">🍬 控糖低GI</button>
        <button class="wish-chip" data-wish="我是素食者，想吃一顿麦当劳">🥗 素食者</button>
        <button class="wish-chip" data-wish="想给女儿办一个生日派对">🎂 生日派对</button>
      </div>
    </div>

    <div id="wishResult"></div>

    <div class="card">
      <h2 style="font-size:16px; font-weight:700; margin:0 0 6px;">愿望池 · 转达麦当劳</h2>
      <div class="sub">实现不了的愿望会被收进这里，一键导出转交麦当劳产品团队。</div>
      <div id="wishPool"></div>
      <div class="wish-actions" style="margin-top:12px;">
        <button class="ghost" id="wishCopy">复制愿望清单</button>
        <button class="ghost" id="wishMail">邮件转达麦当劳</button>
        <button class="ghost" id="wishExport">下载 JSON</button>
        <button class="ghost" id="wishPoolClear">清空愿望池</button>
      </div>
    </div>
  </div>

  <div id="activityPanel" style="display:none;">
    <div id="activityBody"></div>
    <div class="card foot" id="activityHint">数据来源：麦当劳 MCP 活动日历 / 优惠券真实数据（内联快照）。启动 <code>web/server.py</code> 后端后，通过 <code>/api/kingdom</code> 自动加载。</div>
  </div>
</div>

<div class="modal-mask" id="modalMask" style="display:none;">
  <div class="modal">
    <div class="modal-title" id="modalTitle"></div>
    <div class="modal-body" id="modalBody"></div>
    <div class="modal-actions">
      <button class="ghost" id="modalCancel">取消</button>
      <button class="primary" id="modalConfirm">确认</button>
    </div>
  </div>
</div>

<script>
const FOODS = /*__FOOD_DATA__*/;
const KINGDOM = /*__KINGDOM_DATA__*/;

const MODE_HINT = {
  calorie: "目标：总热量 ≤ 预算，压低脂肪供能占比",
  protein: "目标：保证蛋白质摄入下限，优先高蛋白密度",
  lowcarb: "目标：限制碳水化合物总量，适合控糖/低碳"
};

let currentMode = "calorie";
let macroChart = null, kcalChart = null;

const el = id => document.getElementById(id);

const DRINK_BASE_ORDER = [
  ["鲜萃咖啡", "鲜萃咖啡"], ["焦糖玛奇朵", "玛奇朵"], ["燕麦奶铁", "燕麦奶铁"],
  ["燕麦奶", "燕麦奶"], ["伯爵红茶", "红茶"], ["阿芙佳朵", "阿芙佳朵"],
  ["卡布奇诺", "卡布奇诺"], ["玛奇朵", "玛奇朵"], ["美式", "美式咖啡"],
  ["拿铁", "拿铁"], ["奶铁", "奶铁"], ["可乐", "可乐"], ["雪碧", "雪碧"],
  ["红茶", "红茶"], ["黑巧", "黑巧"], ["抹茶", "抹茶"], ["牛奶", "牛奶"],
  ["豆浆", "豆浆"], ["苹果汁", "苹果汁"], ["怡泉", "怡泉"], ["朱古力", "朱古力"], ["雪冰", "雪冰"]
];

function drinkBase(name) {
  if (name.includes("盒装")) return "";
  for (const [k, v] of DRINK_BASE_ORDER) if (name.includes(k)) return v;
  return "";
}

function buildTarget(mode, kcal) {
  if (mode === "calorie") return { mode, label: "控卡减脂", maxKcal: kcal, minProtein: 0, maxFat: Math.max(15, kcal * 0.35 / 9), maxCarb: Infinity, maxSodium: Infinity };
  if (mode === "protein") return { mode, label: "增肌高蛋白", maxKcal: kcal, minProtein: Math.max(20, kcal * 0.20 / 4), maxFat: Infinity, maxCarb: Infinity, maxSodium: Infinity };
  return { mode, label: "控糖低GI", maxKcal: kcal, minProtein: 0, maxFat: Infinity, maxCarb: Math.max(30, kcal * 0.30 / 4), maxSodium: Infinity };
}

function score(f, target) {
  if (target.mode === "protein") return f.protein / Math.max(f.energy_kcal, 1);
  return (f.protein / Math.max(f.energy_kcal, 1)) - (f.fat / Math.max(f.energy_kcal, 1) * 0.5);
}

function plan(foods, target, maxItems = 4, maxPerCategory = 2) {
  const pool = [...foods].sort((a, b) => score(b, target) - score(a, target));
  const acc = { kcal: 0, protein: 0, fat: 0, carb: 0, sodium: 0, calcium: 0, names: new Set(), drinks: new Set(), catCount: {} };
  const chosen = [];

  function fits(f) {
    if (chosen.length >= maxItems) return false;
    if (acc.names.has(f.product_name)) return false;
    const cat = f.category || "unknown";
    if ((acc.catCount[cat] || 0) >= maxPerCategory) return false;
    const b = drinkBase(f.product_name);
    if (b && acc.drinks.has(b)) return false;
    if (acc.kcal + f.energy_kcal > target.maxKcal + 1e-6) return false;
    if (acc.fat + f.fat > target.maxFat + 1e-6) return false;
    if (acc.carb + f.carbohydrate > target.maxCarb + 1e-6) return false;
    return true;
  }
  function add(f) {
    acc.kcal += f.energy_kcal; acc.protein += f.protein; acc.fat += f.fat;
    acc.carb += f.carbohydrate; acc.sodium += f.sodium; acc.calcium += f.calcium;
    acc.names.add(f.product_name);
    const cat = f.category || "unknown";
    acc.catCount[cat] = (acc.catCount[cat] || 0) + 1;
    const b = drinkBase(f.product_name); if (b) acc.drinks.add(b);
    chosen.push(f);
  }

  for (const f of pool) {
    if (fits(f)) { add(f); if (acc.kcal >= target.maxKcal * 0.9) break; }
  }
  if (acc.kcal < target.maxKcal * 0.85 && chosen.length < maxItems) {
    const rest = pool.filter(f => !acc.names.has(f.product_name)).sort((a, b) => a.energy_kcal - b.energy_kcal);
    for (const f of rest) {
      if (chosen.length >= maxItems) break;
      if (fits(f)) { add(f); if (acc.kcal >= target.maxKcal * 0.9) break; }
    }
  }
  return { chosen, acc };
}

const ALLERGEN_KEYWORDS = {
  "辣": ["辣"],
  "鱼": ["鱼", "鳕鱼"],
  "牛肉": ["牛堡", "安格斯"],
  "猪肉": ["猪", "培根", "火腿", "烟肉", "香肠"],
  "鸡肉": ["鸡"],
  "蛋": ["蛋"],
  "乳糖": ["奶", "牛奶", "奶铁", "朱古力", "新地", "麦旋风", "冰淇淋", "雪冰", "拉明顿"],
  "海鲜": ["鱼", "鳕鱼", "虾"],
  "麸质": ["堡", "满分", "卷", "油条"]
};

function filterFoods(foods, restrictions) {
  if (!restrictions || restrictions.length === 0) return foods;
  const words = new Set();
  restrictions.forEach(r => (ALLERGEN_KEYWORDS[r] || [r]).forEach(w => words.add(w)));
  const arr = [...words];
  return foods.filter(f => !arr.some(w => f.product_name.includes(w)));
}

function planDaily(foods, mode, totalKcal, exclude) {
  const names = ["早餐", "午餐", "晚餐"];
  const ratios = [0.3, 0.4, 0.3];
  const pool = filterFoods(foods, exclude);
  const used = new Set();
  const plans = [];
  for (let i = 0; i < 3; i++) {
    const target = buildTarget(mode, totalKcal * ratios[i]);
    const candidates = pool.filter(f => !used.has(f.product_name));
    const res = plan(candidates, target, 4, 2);
    const p = res.chosen.length ? res : null;
    plans.push({ name: names[i], target: target, plan: p });
    if (p) p.chosen.forEach(it => used.add(it.product_name));
  }
  return plans;
}

function renderSingle(mode, kcal, exclude) {
  const target = buildTarget(mode, kcal);
  const pool = filterFoods(FOODS, exclude);
  const { chosen, acc } = plan(pool, target);
  const excludeNote = exclude && exclude.length ? `（忌口：${exclude.join("、")}）` : "";
  if (chosen.length === 0) {
    el("metrics").style.display = "none";
    el("resultCard").style.display = "block";
    el("resultTitle").textContent = `无法拼出满足约束的套餐${excludeNote}`;
    el("resultTable").innerHTML = '<div class="empty">请放宽热量预算、调整模式或减少忌口</div>';
    return;
  }
  el("metrics").style.display = "grid";
  el("resultCard").style.display = "block";
  el("resultTitle").textContent = `【${target.label}】套餐建议（预算 ${target.maxKcal} 千卡）${excludeNote}`;

  const util = Math.round(acc.kcal / target.maxKcal * 100);
  el("metrics").innerHTML = `
    <div class="metric"><div class="label">总热量</div><div class="num">${Math.round(acc.kcal)}<span class="unit"> 千卡</span></div></div>
    <div class="metric"><div class="label">蛋白质</div><div class="num">${Math.round(acc.protein)}<span class="unit"> g</span></div></div>
    <div class="metric"><div class="label">脂肪</div><div class="num">${Math.round(acc.fat)}<span class="unit"> g</span></div></div>
    <div class="metric"><div class="label">碳水</div><div class="num">${Math.round(acc.carb)}<span class="unit"> g</span></div></div>
    <div class="metric"><div class="label">热量利用率</div><div class="num">${util}<span class="unit"> %</span></div></div>
  `;

  let rows = `<table><tr><th>餐品</th><th>热量(kcal)</th><th>蛋白(g)</th><th>脂肪(g)</th><th>碳水(g)</th><th>钠(mg)</th></tr>`;
  for (const f of chosen) {
    rows += `<tr><td>${f.product_name}</td><td>${Math.round(f.energy_kcal)}</td><td>${Math.round(f.protein)}</td><td>${Math.round(f.fat)}</td><td>${Math.round(f.carbohydrate)}</td><td>${Math.round(f.sodium)}</td></tr>`;
  }
  rows += `<tr class="total"><td>合计</td><td>${Math.round(acc.kcal)}</td><td>${Math.round(acc.protein)}</td><td>${Math.round(acc.fat)}</td><td>${Math.round(acc.carb)}</td><td>${Math.round(acc.sodium)}</td></tr></table>`;
  el("resultTable").innerHTML = rows;

  drawCharts(chosen, acc);
}

function renderDaily(mode, totalKcal, exclude) {
  const plans = planDaily(FOODS, mode, totalKcal, exclude);
  el("metrics").style.display = "none";
  el("resultCard").style.display = "block";
  const excludeNote = exclude && exclude.length ? `（忌口：${exclude.join("、")}）` : "";
  const label = plans.length ? plans[0].target.label : "";
  el("resultTitle").textContent = `【${label}】全天三餐规划（总预算 ${totalKcal} 千卡）${excludeNote}`;

  let html = "";
  let allChosen = [];
  let totalAcc = { kcal: 0, protein: 0, fat: 0, carb: 0, sodium: 0 };
  plans.forEach(({ name, target, plan: p }) => {
    const budget = Math.round(target.maxKcal);
    if (!p) {
      html += `<div class="meal-block"><div class="meal-head">${name}（预算 ${budget} 千卡）</div><div class="empty">无法拼出满足约束的套餐</div></div>`;
      return;
    }
    const { chosen, acc } = p;
    allChosen = allChosen.concat(chosen);
    totalAcc.kcal += acc.kcal; totalAcc.protein += acc.protein;
    totalAcc.fat += acc.fat; totalAcc.carb += acc.carb; totalAcc.sodium += acc.sodium;
    let rows = `<table><tr><th>餐品</th><th>热量(kcal)</th><th>蛋白(g)</th><th>脂肪(g)</th><th>碳水(g)</th></tr>`;
    for (const f of chosen) {
      rows += `<tr><td>${f.product_name}</td><td>${Math.round(f.energy_kcal)}</td><td>${Math.round(f.protein)}</td><td>${Math.round(f.fat)}</td><td>${Math.round(f.carbohydrate)}</td></tr>`;
    }
    rows += `<tr class="total"><td>小计</td><td>${Math.round(acc.kcal)}</td><td>${Math.round(acc.protein)}</td><td>${Math.round(acc.fat)}</td><td>${Math.round(acc.carb)}</td></tr></table>`;
    html += `<div class="meal-block"><div class="meal-head">${name}（预算 ${budget} 千卡）</div><div class="table-wrap">${rows}</div></div>`;
  });
  html += `<div class="meal-block" style="background:#fdf9f1;"><div class="meal-head">全天合计</div>
    <div class="metrics" style="display:grid; margin:0;">
      <div class="metric"><div class="label">总热量</div><div class="num">${Math.round(totalAcc.kcal)}<span class="unit"> 千卡</span></div></div>
      <div class="metric"><div class="label">蛋白质</div><div class="num">${Math.round(totalAcc.protein)}<span class="unit"> g</span></div></div>
      <div class="metric"><div class="label">脂肪</div><div class="num">${Math.round(totalAcc.fat)}<span class="unit"> g</span></div></div>
      <div class="metric"><div class="label">碳水</div><div class="num">${Math.round(totalAcc.carb)}<span class="unit"> g</span></div></div>
    </div></div>`;
  el("resultTable").innerHTML = html;
  drawCharts(allChosen, totalAcc);
}

function drawCharts(chosen, acc) {
  const macroCtx = el("macroChart");
  if (macroChart) macroChart.destroy();
  macroChart = new Chart(macroCtx, {
    type: "doughnut",
    data: {
      labels: ["蛋白质", "脂肪", "碳水"],
      datasets: [{
        data: [Math.round(acc.protein), Math.round(acc.fat), Math.round(acc.carb)],
        backgroundColor: ["#378add", "#ef9f27", "#1d9e75"],
        borderWidth: 2, borderColor: "#fff"
      }]
    },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
  });

  const kcalCtx = el("kcalChart");
  if (kcalChart) kcalChart.destroy();
  kcalChart = new Chart(kcalCtx, {
    type: "bar",
    data: {
      labels: chosen.map(f => f.product_name),
      datasets: [{
        label: "热量", data: chosen.map(f => Math.round(f.energy_kcal)),
        backgroundColor: "#da291c", borderRadius: 4
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { x: { ticks: { autoSkip: false, maxRotation: 45, font: { size: 11 } } }, y: { beginAtZero: true } }
    }
  });
}

document.querySelectorAll(".mode-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".mode-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    currentMode = btn.dataset.mode;
    el("modeHint").textContent = MODE_HINT[currentMode];
    generate();
  });
});

let selectedExclude = new Set();

el("go").addEventListener("click", generate);

document.querySelectorAll(".exclude-chip").forEach(chip => {
  chip.addEventListener("click", () => {
    const v = chip.dataset.exclude;
    if (selectedExclude.has(v)) { selectedExclude.delete(v); chip.classList.remove("active"); }
    else { selectedExclude.add(v); chip.classList.add("active"); }
    generate();
  });
});

el("daily").addEventListener("change", () => {
  if (el("daily").checked && (parseFloat(el("kcal").value) || 0) < 1500) {
    el("kcal").value = 1800;
  }
  generate();
});

function generate() {
  const kcal = parseFloat(el("kcal").value) || 500;
  const exclude = [...selectedExclude];
  if (el("daily").checked) {
    renderDaily(currentMode, kcal, exclude);
  } else {
    renderSingle(currentMode, kcal, exclude);
  }
}

el("modeHint").textContent = MODE_HINT[currentMode];

function updateSourceHint() {
  const hint = el("sourceHint");
  if (!hint) return;
  const src = window.__foodSource;
  if (src === "麦当劳 MCP 实时数据") {
    hint.innerHTML = '数据来源：<strong style="color:#639922;">麦当劳 MCP 实时数据</strong>（通过 web/server.py 后端实时调用）';
  } else if (src === "麦当劳 MCP 快照") {
    const t = window.__snapshotUpdated ? '，快照更新于 ' + window.__snapshotUpdated : '';
    hint.innerHTML = '数据来源：<strong style="color:#639922;">麦当劳 MCP 真实数据</strong>' + t +
      '（通过 web/server.py 后端加载；配置 <code>MCD_MCP_BASE_URL</code> 可切换实时直连）';
  } else {
    hint.innerHTML = '数据来源：麦当劳 MCP <code>list-nutrition-foods</code> 真实营养数据（内联快照）。启动 <code>web/server.py</code> 后端后，通过 <code>/api/foods</code> 自动加载。';
  }
}

async function loadRemoteFoods() {
  try {
    const resp = await fetch("/api/foods", { cache: "no-store" });
    if (!resp.ok) return;
    const data = await resp.json();
    if (data.foods && data.foods.length > 0) {
      FOODS.length = 0;
      FOODS.push(...data.foods);
      window.__foodSource = data.source === "mcp" ? "麦当劳 MCP 实时数据" : "麦当劳 MCP 快照";
      window.__snapshotUpdated = data.snapshot_updated || "";
      updateSourceHint();
      generate();
    }
  } catch (e) {
    // 后端不可用，保持内联快照
    window.__foodSource = "离线快照";
    updateSourceHint();
  }
}

// ===== 潮玩宫 · 积分乐园 =====
let kingdomCategory = "coupons";

function escapeHtml(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
}

function goodsCard(g) {
  const point = String(g.point == null ? "0" : g.point);
  const price = String(g.price == null ? "0" : g.price);
  const hasPoint = point !== "0" && point !== "0.00" && point !== "";
  const priceLabel = hasPoint
    ? `<span class="tag-point">${escapeHtml(point)} 积分</span>`
    : `<span class="tag-price">¥${escapeHtml(price)}</span>`;
  const cat = escapeHtml(g.catName || "");
  const btn = hasPoint
    ? `<button class="goods-claim" data-action="redeem" data-point="${escapeHtml(point)}" data-name="${escapeHtml(g.spuName)}">立即兑换</button>`
    : `<button class="goods-claim" data-action="party">去预订</button>`;
  return `<div class="goods-card">
    <img class="goods-img" src="${escapeHtml(g.spuImage)}" alt="${escapeHtml(g.spuName)}" loading="lazy" onerror="this.style.visibility='hidden'">
    <div class="goods-body">
      <div class="goods-name">${escapeHtml(g.spuName)}</div>
      <div class="goods-selling">${escapeHtml(g.selling)}</div>
      <div class="goods-meta">${priceLabel}${cat ? `<span class="tag-cat">${cat}</span>` : ""}</div>
      ${btn}
    </div>
  </div>`;
}

function renderKingdom() {
  const mall = KINGDOM.mall || {};
  const account = KINGDOM.account || {};
  const lottery = KINGDOM.lottery || {};
  const campaigns = KINGDOM.campaign || [];
  const avail = account.availablePoint == null ? "0" : account.availablePoint;

  const goods = mall[kingdomCategory] || [];

  const prizes = (lottery.prizes || []).map(p => `<div class="prize-item">
    <img src="${escapeHtml(p.imageUrl)}" alt="" loading="lazy" onerror="this.style.visibility='hidden'">
    <div><div class="pname">${escapeHtml(p.name)}</div><div class="ptype">${escapeHtml(p.typeText || "")}</div></div>
  </div>`).join("");

  const camps = campaigns.map(c => `<div class="campaign-item">
    <img src="${escapeHtml(c.image)}" alt="" loading="lazy" onerror="this.style.visibility='hidden'">
    <div><div class="ctitle">${escapeHtml(c.title)}</div><div class="cdesc">${escapeHtml(c.desc)}</div><div class="cdate">${escapeHtml(c.date || "")}</div></div>
  </div>`).join("");

  el("kingdomBody").innerHTML = `
    <div class="points-hero">
      <div>
        <div class="points-big">${escapeHtml(avail)}<span class="unit">${escapeHtml(account.currency || "积分")}</span></div>
        <div style="margin-top:8px; font-size:13px; opacity:.92;">${account.demo ? "演示账户：点餐下单即可攒积分，积分换好礼" : "点餐攒积分，积分换好礼"}</div>
      </div>
      <div class="points-side">
        累计 ${escapeHtml(account.accumulativePoint == null ? "0" : account.accumulativePoint)}<br>
        本月将过期 ${escapeHtml(account.currentMouthExpirePoint == null ? "0" : account.currentMouthExpirePoint)}
      </div>
    </div>

    <div class="card">
      <h2 style="font-size:16px; font-weight:700; margin:0 0 12px;">积分商城 · 潮玩橱窗</h2>
      <div class="sub-tabs">
        <button class="sub-tab ${kingdomCategory === "coupons" ? "active" : ""}" data-cat="coupons">餐品券 · 积分兑</button>
        <button class="sub-tab ${kingdomCategory === "physical" ? "active" : ""}" data-cat="physical">实物周边 · 限量</button>
        <button class="sub-tab ${kingdomCategory === "party" ? "active" : ""}" data-cat="party">派对体验</button>
      </div>
      <div class="goods-grid">${goods.length ? goods.map(goodsCard).join("") : '<div class="empty">暂无在售商品</div>'}</div>
    </div>

    <div class="card">
      <div class="lottery-head">
        <h2 style="font-size:16px; font-weight:700; margin:0;">${escapeHtml(lottery.activityName || "积分抽奖")}</h2>
        <span class="lottery-tag">${escapeHtml(lottery.activityStatusText || "")}</span>
        <span style="font-size:13px; color:var(--muted);">${escapeHtml(lottery.drawPoint == null ? "0" : lottery.drawPoint)} 积分/次 · ${escapeHtml(lottery.drawTypeText || "")}</span>
        <button class="lottery-cta" id="lotteryDraw" style="margin-left:auto;">抽一次</button>
      </div>
      <div class="prize-grid">${prizes || '<div class="empty">暂无奖品</div>'}</div>
    </div>

    <div class="card">
      <h2 style="font-size:16px; font-weight:700; margin:0 0 4px;">当季联名 · 活动速递</h2>
      <div style="margin-top:12px;">${camps || '<div class="empty">暂无活动</div>'}</div>
    </div>
  `;

  el("kingdomBody").querySelectorAll(".sub-tab").forEach(btn => {
    btn.addEventListener("click", () => {
      kingdomCategory = btn.dataset.cat;
      renderKingdom();
    });
  });
  el("kingdomBody").querySelectorAll(".goods-claim").forEach(btn => {
    btn.addEventListener("click", () => {
      const action = btn.dataset.action;
      if (action === "party") {
        showModal("预订派对体验", "派对 / 体验需到店参加，可前往「活动宫 · 派对体验」查看详情并预订。", null);
      } else if (action === "redeem") {
        redeemGoods(btn, btn.dataset.name, btn.dataset.point);
      }
    });
  });
  const drawBtn = el("lotteryDraw");
  if (drawBtn) drawBtn.addEventListener("click", () => drawLottery(lottery));
}

function showModal(title, bodyHtml, onConfirm) {
  el("modalTitle").textContent = title;
  el("modalBody").innerHTML = bodyHtml;
  el("modalMask").style.display = "flex";
  el("modalConfirm").onclick = () => {
    el("modalMask").style.display = "none";
    if (onConfirm) onConfirm();
  };
  el("modalCancel").onclick = () => { el("modalMask").style.display = "none"; };
}

function redeemGoods(btn, name, point) {
  showModal("确认兑换", `将使用 <strong style="color:#da291c;">${escapeHtml(point)} 积分</strong> 兑换「<strong>${escapeHtml(name)}</strong>」。<br><span style="color:#8a887f; font-size:12px;">真实兑换需登录会员，此处为演示流程。</span>`, () => {
    btn.textContent = "已兑换";
    btn.classList.add("done");
    btn.disabled = true;
  });
}

function drawLottery(lottery) {
  const point = lottery.drawPoint == null ? "0" : lottery.drawPoint;
  const prizes = lottery.prizes || [];
  showModal("确认抽奖", `本次将消耗 <strong style="color:#da291c;">${escapeHtml(point)} 积分</strong> 抽一次。<br><span style="color:#8a887f; font-size:12px;">真实抽奖需登录会员，此处为演示流程。</span>`, () => {
    if (prizes.length === 0) {
      showModal("抽奖结果", "暂无奖品可抽", null);
      return;
    }
    const win = prizes[Math.floor(Math.random() * prizes.length)];
    showModal("抽奖结果", `🎉 恭喜抽中「<strong>${escapeHtml(win.name)}</strong>」（${escapeHtml(win.typeText || "奖品")}）！<br><span style="color:#8a887f; font-size:12px;">奖品已放入你的卡包，可在「我的奖品」查看。</span>`, null);
  });
}

document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    const tab = btn.dataset.tab;
    el("mealPanel").style.display = tab === "meal" ? "" : "none";
    el("kingdomPanel").style.display = tab === "kingdom" ? "" : "none";
    el("wishPanel").style.display = tab === "wish" ? "" : "none";
    el("activityPanel").style.display = tab === "activity" ? "" : "none";
    if (tab === "kingdom") renderKingdom();
    if (tab === "wish") renderWishPool();
    if (tab === "activity") renderActivity();
  });
});

async function loadRemoteKingdom() {
  try {
    const resp = await fetch("/api/kingdom", { cache: "no-store" });
    if (!resp.ok) return;
    const data = await resp.json();
    if (data.kingdom) {
      Object.keys(KINGDOM).forEach(k => delete KINGDOM[k]);
      Object.assign(KINGDOM, data.kingdom);
      const hint = el("kingdomHint");
      if (hint) {
        hint.innerHTML = data.source === "mcp"
          ? '数据来源：<strong style="color:#639922;">麦当劳 MCP 实时数据</strong>（通过 web/server.py 实时调用）'
          : '数据来源：<strong style="color:#639922;">麦当劳 MCP 真实数据</strong>（积分商城/抽奖快照；配置 <code>MCD_MCP_BASE_URL</code> 可切换实时）';
      }
      renderKingdom();
    }
  } catch (e) {
    // 后端不可用，保持内联快照
  }
}

updateSourceHint();
generate();
loadRemoteFoods();
loadRemoteKingdom();
renderKingdom();

// ===== 许愿宫 · 心愿即达 =====
const WISH_POOL_KEY = "mcd_wish_pool";

const MODE_LABEL = { calorie: "控卡减脂", protein: "增肌高蛋白", lowcarb: "控糖低GI" };

function parseWish(text) {
  const t = (text || "").trim();
  let mode = "calorie", kcal = 500, exclude = [], tags = [], party = null;

  if (/增肌|蛋白|健身|撸铁|练后|补蛋白/.test(t)) mode = "protein";
  else if (/控糖|低糖|低gi|低碳|戒糖|不吃糖|生酮/.test(t)) mode = "lowcarb";
  else if (/减|瘦|控卡|低卡|不胖|热量|轻食/.test(t)) mode = "calorie";

  const m = t.match(/(\d{3,4})\s*(千卡|大卡|kcal|卡路里)?/i);
  if (m) kcal = parseInt(m[1], 10);
  else if (/一天|三餐|全天/.test(t)) kcal = 1800;
  else if (/早餐|早饭/.test(t)) kcal = 400;
  else if (/晚餐|晚饭|晚上/.test(t)) kcal = 550;
  else if (/午餐|午饭|中午/.test(t)) kcal = 650;
  kcal = Math.min(Math.max(kcal, 200), 2000);

  if (/不.?辣|别辣|不要辣|微辣都不要|忌辣/.test(t)) exclude.push("辣");
  if (/不.?鱼|鱼过敏|海鲜过敏|忌海鲜|不要海鲜|不吃海鲜/.test(t)) exclude.push("海鲜");
  if (/不.?牛|牛肉过敏|不要牛肉|不吃牛肉/.test(t)) exclude.push("牛肉");
  if (/不.?猪|猪肉过敏|不要猪肉|不吃猪肉/.test(t)) exclude.push("猪肉");
  if (/不.?鸡|鸡肉过敏|不要鸡肉|不吃鸡肉/.test(t)) exclude.push("鸡肉");
  if (/不.?蛋|蛋过敏|不要蛋|不吃蛋/.test(t)) exclude.push("蛋");
  if (/乳糖|不耐受|不喝.?奶|不要奶/.test(t)) exclude.push("乳糖");
  if (/素食|吃素|不吃肉|不要肉/.test(t)) exclude.push("牛肉", "猪肉", "鸡肉", "海鲜", "鱼");

  if (/甜|冰淇淋|麦旋风|甜品|巧克力/.test(t)) tags.push("偏好甜点");
  if (/小孩|宝宝|儿童|儿子|女儿|小朋友|娃/.test(t)) tags.push("儿童");
  if (/爱美|护肤|皮肤|痘|精致/.test(t)) tags.push("爱美");
  if (/玩具|开心乐园|潮玩/.test(t)) tags.push("想要玩具");

  if (/生日/.test(t)) party = "生日派对";
  else if (/读书|绘本|亲子阅读|阅读/.test(t)) party = "趣读派对";
  else if (/体验营|职业|cosplay|牙医|消防/.test(t)) party = "体验营";
  else if (/派对|聚会|轰趴/.test(t)) party = "主题派对";

  return { mode, kcal, exclude, tags, party, raw: t };
}

function matchExclude(name, exclude) {
  return exclude.some(k => {
    if (k === "牛肉") return name.includes("牛");
    if (k === "猪肉") return name.includes("猪");
    if (k === "鸡肉") return name.includes("鸡");
    if (k === "海鲜") return /鱼|虾|蟹/.test(name);
    if (k === "鱼") return name.includes("鱼");
    if (k === "蛋") return name.includes("蛋");
    if (k === "乳糖") return /奶|乳/.test(name);
    if (k === "辣") return name.includes("辣");
    return name.includes(k);
  });
}

function matchParty(partyType) {
  const party = (KINGDOM.mall && KINGDOM.mall.party) || [];
  const cat = p => (p.catName || "") + (p.spuName || "");
  return party.filter(p => {
    const c = cat(p);
    if (partyType === "生日派对") return c.includes("生日");
    if (partyType === "趣读派对") return c.includes("趣读") || c.includes("读书");
    if (partyType === "体验营") return c.includes("体验营") || c.includes("品鉴") || c.includes("牙医") || c.includes("消防");
    if (partyType === "主题派对") return c.includes("主题") || c.includes("派对");
    return c.includes("派对");
  });
}

function wishPool() {
  try { return JSON.parse(localStorage.getItem(WISH_POOL_KEY) || "[]"); }
  catch (e) { return []; }
}
function saveWishPool(arr) {
  localStorage.setItem(WISH_POOL_KEY, JSON.stringify(arr));
}
function addToPool(wish, status) {
  const arr = wishPool();
  arr.unshift({ id: Date.now(), text: wish.raw, mode: wish.mode, kcal: wish.kcal,
                exclude: wish.exclude, party: wish.party, status: status,
                time: new Date().toLocaleString("zh-CN") });
  saveWishPool(arr);
  renderWishPool();
}

function renderWishPool() {
  const box = el("wishPool");
  if (!box) return;
  const arr = wishPool();
  if (arr.length === 0) {
    box.innerHTML = '<div class="wish-pool-empty">愿望池空空的，快许个愿吧～</div>';
    return;
  }
  box.innerHTML = arr.map(w => {
    const statusTag = w.status === "done"
      ? '<span class="wstatus done">已实现</span>'
      : '<span class="wstatus pending">待转达麦当劳</span>';
    const meta = `${MODE_LABEL[w.mode] || w.mode} · ${w.kcal} 千卡` +
      (w.exclude && w.exclude.length ? ` · 忌口 ${w.exclude.join("/")}` : "") +
      (w.party ? ` · ${w.party}` : "");
    return `<div class="wish-pool-item">
      <div class="wtext">${escapeHtml(w.text)}<div class="wmeta">${escapeHtml(meta)} · ${escapeHtml(w.time)}</div></div>
      ${statusTag}
    </div>`;
  }).join("");
}

function formatWishesText() {
  const arr = wishPool();
  const lines = ["【麦当劳营养王国 · 用户愿望清单】",
    "导出时间：" + new Date().toLocaleString("zh-CN"),
    "共 " + arr.length + " 条愿望", ""];
  arr.forEach((w, i) => {
    const status = w.status === "done" ? "已实现" : "待转达";
    const meta = (MODE_LABEL[w.mode] || w.mode) + " · " + w.kcal + "千卡"
      + (w.exclude && w.exclude.length ? " · 忌口 " + w.exclude.join("/") : "")
      + (w.party ? " · " + w.party : "");
    lines.push((i + 1) + ". [" + status + "] " + w.text);
    lines.push("   （" + meta + "）");
  });
  lines.push("");
  lines.push("—— 由麦当劳营养王国 Agent 收集，希望麦当劳能推出这些餐品 / 体验。");
  return lines.join("\n");
}

function fallbackCopy(text, done) {
  const ta = document.createElement("textarea");
  ta.value = text; document.body.appendChild(ta); ta.select();
  try { document.execCommand("copy"); done(); } catch (e) { alert("复制失败，请手动复制"); }
  document.body.removeChild(ta);
}

function copyWishes() {
  const arr = wishPool();
  if (arr.length === 0) { alert("愿望池为空"); return; }
  const text = formatWishesText();
  const done = () => alert("愿望清单已复制，可粘贴到邮件 / 飞书 / 问卷提交");
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(done).catch(() => fallbackCopy(text, done));
  } else {
    fallbackCopy(text, done);
  }
}

function mailWishes() {
  const arr = wishPool();
  if (arr.length === 0) { alert("愿望池为空"); return; }
  const subject = encodeURIComponent("麦当劳营养王国 · 用户愿望清单");
  const body = encodeURIComponent(formatWishesText());
  window.location.href = "mailto:?subject=" + subject + "&body=" + body;
}

function exportWishes() {
  const arr = wishPool();
  if (arr.length === 0) { alert("愿望池为空"); return; }
  const payload = JSON.stringify({
    title: "麦当劳营养王国 · 用户愿望清单",
    exported_at: new Date().toLocaleString("zh-CN"),
    count: arr.length,
    wishes: arr.map(w => ({ 愿望: w.text, 状态: w.status === "done" ? "已实现" : "待转达",
                            模式: MODE_LABEL[w.mode] || w.mode, 热量: w.kcal + "千卡",
                            忌口: w.exclude, 派对: w.party || "" }))
  }, null, 2);
  const blob = new Blob([payload], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "麦当劳愿望清单.json";
  a.click();
  URL.revokeObjectURL(a.href);
  if (navigator.clipboard) navigator.clipboard.writeText(payload).catch(() => {});
}

function renderWish() {
  const input = el("wishInput");
  const box = el("wishResult");
  const text = input.value.trim();
  if (!text) { box.innerHTML = '<div class="card"><div class="empty">请先输入你的愿望</div></div>'; return; }

  const w = parseWish(text);
  const tags = [
    `<span class="wish-tag accent">${MODE_LABEL[w.mode]}</span>`,
    `<span class="wish-tag">${w.kcal} 千卡</span>`
  ];
  if (w.exclude.length) tags.push(`<span class="wish-tag gold">忌口 ${w.exclude.join("、")}</span>`);
  w.tags.forEach(t => tags.push(`<span class="wish-tag">${t}</span>`));
  if (w.party) tags.push(`<span class="wish-tag accent">${w.party}</span>`);

  let body = "";
  if (w.party) {
    const matches = matchParty(w.party);
    if (matches.length) {
      body = `<div style="font-size:13px; color:var(--muted); margin-bottom:10px;">你的愿望更像一场「体验」，麦当劳有现成方案：</div>` +
        matches.slice(0, 3).map(p => `<div class="wish-party">
          <img src="${escapeHtml(p.spuImage)}" alt="" loading="lazy" onerror="this.style.visibility='hidden'">
          <div><div class="ptitle">${escapeHtml(p.spuName)}</div>
          <div class="pselling">${escapeHtml(p.selling)}</div>
          <div class="pprice">${p.price && p.price !== "0" ? "¥" + escapeHtml(p.price) : "免费"}</div></div>
        </div>`).join("");
      body += `<div style="font-size:12px; color:var(--muted);">可到「潮玩宫 → 派对体验」预订；该愿望已收进愿望池。</div>`;
      addToPool(w, "pending");
    } else {
      body = '<div class="empty">这个体验愿望已收进愿望池，待转达麦当劳。</div>';
      addToPool(w, "pending");
    }
  } else {
    const pool = w.exclude.length
      ? FOODS.filter(f => !matchExclude(f.product_name, w.exclude))
      : FOODS;
    const target = buildTarget(w.mode, w.kcal);
    const { chosen, acc } = plan(pool, target);
    if (chosen.length === 0) {
      body = `<div style="font-size:14px; margin-bottom:8px;">麦当劳现有餐品暂时很难完美满足这个愿望（${w.exclude.length ? "忌口 " + w.exclude.join("、") + " 过滤后可选太少" : "约束过严"}）。</div>
        <div style="font-size:12px; color:var(--muted);">已收进愿望池，帮你转达麦当劳产品团队。</div>`;
      addToPool(w, "pending");
    } else {
      let rows = `<tr><th>餐品</th><th>热量(kcal)</th><th>蛋白(g)</th><th>脂肪(g)</th><th>碳水(g)</th></tr>`;
      for (const f of chosen) {
        rows += `<tr><td>${escapeHtml(f.product_name)}</td><td>${Math.round(f.energy_kcal)}</td><td>${Math.round(f.protein)}</td><td>${Math.round(f.fat)}</td><td>${Math.round(f.carbohydrate)}</td></tr>`;
      }
      rows += `<tr class="total"><td>合计</td><td>${Math.round(acc.kcal)}</td><td>${Math.round(acc.protein)}</td><td>${Math.round(acc.fat)}</td><td>${Math.round(acc.carb)}</td></tr>`;
      body = `<div style="font-size:14px; margin-bottom:8px;">愿望已实现 🎉 为你拼出这份套餐：</div>
        <div class="table-wrap"><table>${rows}</table></div>
        <div style="font-size:12px; color:var(--muted); margin-top:10px;">${w.tags.length ? "已结合你的偏好（" + w.tags.join("、") + "）。" : ""}该愿望已记入愿望池。</div>`;
      addToPool(w, "done");
    }
  }

  box.innerHTML = `<div class="card">
    <h2 style="font-size:16px; font-weight:700; margin:0 0 4px;">愿望解析</h2>
    <div class="wish-parse">${tags.join("")}</div>
    ${body}
  </div>`;
}

el("wishGo").addEventListener("click", renderWish);
el("wishClear").addEventListener("click", () => { el("wishInput").value = ""; el("wishResult").innerHTML = ""; });
el("wishInput").addEventListener("keydown", e => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) renderWish(); });
document.querySelectorAll(".wish-chip").forEach(chip => {
  chip.addEventListener("click", () => {
    el("wishInput").value = chip.dataset.wish;
    renderWish();
  });
});
el("wishCopy").addEventListener("click", copyWishes);
el("wishMail").addEventListener("click", mailWishes);
el("wishExport").addEventListener("click", exportWishes);
el("wishPoolClear").addEventListener("click", () => { saveWishPool([]); renderWishPool(); });

renderWishPool();

// ===== 活动宫 · 联名速递 =====
function renderActivity() {
  const campaign = KINGDOM.campaign || [];
  const coupons = KINGDOM.coupons || [];
  const party = (KINGDOM.mall && KINGDOM.mall.party) || [];

  const camps = campaign.map(c => `<div class="campaign-item">
    <img src="${escapeHtml(c.image)}" alt="" loading="lazy" onerror="this.style.visibility='hidden'">
    <div><div class="ctitle">${escapeHtml(c.title)}</div><div class="cdesc">${escapeHtml(c.desc)}</div><div class="cdate">${escapeHtml(c.date || "")}</div></div>
  </div>`).join("");

  const cp = coupons.map(c => `<div class="coupon-card">
    <div class="coupon-amount"><div class="num">${escapeHtml(c.amount)}</div>${c.suffix ? `<div class="suffix">${escapeHtml(c.suffix)}</div>` : ""}<div class="label">麦麦省券</div></div>
    <div class="coupon-body">
      <div><div class="coupon-title">${escapeHtml(c.title)}</div><div class="coupon-desc">${escapeHtml(c.desc)}</div></div>
      <button class="coupon-claim" data-coupon="${escapeHtml(c.title)}">一键领取</button>
    </div>
  </div>`).join("");

  const partyCards = party.slice(0, 3).map(p => `<div class="wish-party">
    <img src="${escapeHtml(p.spuImage)}" alt="" loading="lazy" onerror="this.style.visibility='hidden'">
    <div><div class="ptitle">${escapeHtml(p.spuName)}</div>
    <div class="pselling">${escapeHtml(p.selling)}</div>
    <div class="pprice">${p.price && p.price !== "0" ? "¥" + escapeHtml(p.price) : "免费"}</div></div>
  </div>`).join("");

  el("activityBody").innerHTML = `
    <div class="card">
      <h2 class="act-section-title">当季联名 · 活动速递</h2>
      <div style="margin-top:12px;">${camps || '<div class="empty">暂无活动</div>'}</div>
    </div>
    <div class="card">
      <h2 class="act-section-title">麦麦省 · 优惠券</h2>
      <div class="sub">领取后点餐自动可用；真实领取需登录会员，演示点击可体验流程。</div>
      <div class="coupon-grid" style="margin-top:14px;">${cp || '<div class="empty">暂无可领券</div>'}</div>
    </div>
    <div class="card">
      <h2 class="act-section-title">派对 / 体验 · 到店参加</h2>
      <div style="margin-top:12px;">${partyCards || '<div class="empty">暂无活动</div>'}</div>
    </div>
    <div class="card">
      <h2 class="act-section-title">更多场景 · 企业团餐 & 外送</h2>
      <div class="scene-grid">
        <div class="scene-card">
          <div class="scene-title">企业团餐</div>
          <div class="scene-desc">满减 / 满折促销规则 + 助餐服务，适合企业批量订餐</div>
          <div class="scene-tags"><span>满减满折</span><span>助餐服务</span><span>query-promotions</span></div>
        </div>
        <div class="scene-card">
          <div class="scene-title">麦乐送 · 外送</div>
          <div class="scene-desc">地址管理 + 附近门店查询，外送全链路下单</div>
          <div class="scene-tags"><span>地址管理</span><span>门店查询</span><span>delivery-*</span></div>
        </div>
      </div>
      <div class="sub" style="margin-top:12px;">以上能力由麦当劳 MCP 提供，在 WorkBuddy Skill 对话中可实时调用完成团餐 / 外送下单（需门店与地址上下文）。</div>
    </div>
  `;

  el("activityBody").querySelectorAll(".coupon-claim").forEach(btn => {
    btn.addEventListener("click", () => {
      btn.textContent = "已领取";
      btn.disabled = true;
      btn.style.borderColor = "#639922";
      btn.style.color = "#639922";
    });
  });
}
</script>
</body>
</html>
"""


if __name__ == "__main__":
    foods = load_foods()
    kingdom = load_kingdom()
    html = build_html(foods, kingdom)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"生成完成：{OUT}（{len(html)} 字符，{len(foods)} 种餐品）")
    print(f"  潮玩宫：餐品券 {len(kingdom['mall']['coupons'])} / 实物周边 "
          f"{len(kingdom['mall']['physical'])} / 派对体验 {len(kingdom['mall']['party'])}")
