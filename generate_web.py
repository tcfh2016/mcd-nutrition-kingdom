#!/usr/bin/env python3
"""生成麦当劳营养点餐 Agent 的 Web 界面（单文件、自包含）。

将 core/nutrition_snapshot.json 的营养数据内联到 HTML 中，
前端用 JS 复刻拼配算法，实现无需后端即可交互的演示界面。
"""
from __future__ import annotations

import json
import os

from core.nutrition import infer_category

HERE = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT = os.path.join(HERE, "core", "nutrition_snapshot.json")
OUT = os.path.join(HERE, "web", "index.html")


def load_foods():
    with open(SNAPSHOT, "r", encoding="utf-8") as f:
        foods = json.load(f)
    # 前端做类别均衡需要 category 字段，这里补上
    for f in foods:
        f["category"] = infer_category(f["product_name"])
    return foods


def build_html(foods: list) -> str:
    data_js = json.dumps(foods, ensure_ascii=False)
    return TEMPLATE.replace("/*__FOOD_DATA__*/", data_js)


TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>麦当劳营养点餐 Agent</title>
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
  .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 20px; }
  .metric {
    background: #fff; border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px;
  }
  .metric .label { font-size: 12px; color: var(--muted); }
  .metric .num { font-size: 24px; font-weight: 700; margin-top: 2px; }
  .metric .unit { font-size: 12px; color: var(--muted); font-weight: 400; }
  table { width: 100%; border-collapse: collapse; font-size: 14px; }
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
  @media (max-width: 640px) { .chart-row { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>麦当劳营养点餐 Agent<span class="badge">McD MCP</span></h1>
    <div class="sub">说出你的热量/营养目标，自动拼出一份「吃得饱、营养对」的麦当劳套餐。基于麦当劳 MCP 真实营养数据。</div>
  </header>

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
        <input type="number" id="kcal" value="500" min="100" max="2000" step="50">
      </div>
      <button class="primary" id="go">生成套餐</button>
    </div>
  </div>

  <div class="metrics" id="metrics" style="display:none;"></div>

  <div class="card" id="resultCard" style="display:none;">
    <h2 style="font-size:16px; font-weight:700; margin:0 0 12px;" id="resultTitle"></h2>
    <table id="resultTable"></table>
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
    数据来源：麦当劳 MCP <code>list-nutrition-foods</code> 返回的真实营养数据（离线快照兜底）。
    启动 <code>web/server.py</code> 后端后，本页面将自动切换为实时 MCP 数据。
  </div>
</div>

<script>
const FOODS = /*__FOOD_DATA__*/;

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

function render(target) {
  const { chosen, acc } = plan(FOODS, target);
  if (chosen.length === 0) {
    el("metrics").style.display = "none";
    el("resultCard").style.display = "block";
    el("resultTitle").textContent = "无法拼出满足约束的套餐";
    el("resultTable").innerHTML = '<tr><td class="empty">请放宽热量预算或调整模式</td></tr>';
    return;
  }
  el("metrics").style.display = "grid";
  el("resultCard").style.display = "block";
  el("resultTitle").textContent = `【${target.label}】套餐建议（预算 ${target.maxKcal} 千卡）`;

  const util = Math.round(acc.kcal / target.maxKcal * 100);
  el("metrics").innerHTML = `
    <div class="metric"><div class="label">总热量</div><div class="num">${Math.round(acc.kcal)}<span class="unit"> 千卡</span></div></div>
    <div class="metric"><div class="label">蛋白质</div><div class="num">${Math.round(acc.protein)}<span class="unit"> g</span></div></div>
    <div class="metric"><div class="label">脂肪</div><div class="num">${Math.round(acc.fat)}<span class="unit"> g</span></div></div>
    <div class="metric"><div class="label">碳水</div><div class="num">${Math.round(acc.carb)}<span class="unit"> g</span></div></div>
    <div class="metric"><div class="label">热量利用率</div><div class="num">${util}<span class="unit"> %</span></div></div>
  `;

  let rows = `<tr><th>餐品</th><th>热量(kcal)</th><th>蛋白(g)</th><th>脂肪(g)</th><th>碳水(g)</th><th>钠(mg)</th></tr>`;
  for (const f of chosen) {
    rows += `<tr><td>${f.product_name}</td><td>${Math.round(f.energy_kcal)}</td><td>${Math.round(f.protein)}</td><td>${Math.round(f.fat)}</td><td>${Math.round(f.carbohydrate)}</td><td>${Math.round(f.sodium)}</td></tr>`;
  }
  rows += `<tr class="total"><td>合计</td><td>${Math.round(acc.kcal)}</td><td>${Math.round(acc.protein)}</td><td>${Math.round(acc.fat)}</td><td>${Math.round(acc.carb)}</td><td>${Math.round(acc.sodium)}</td></tr>`;
  el("resultTable").innerHTML = rows;

  drawCharts(chosen, acc);
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

el("go").addEventListener("click", generate);

function generate() {
  const kcal = parseFloat(el("kcal").value) || 500;
  const target = buildTarget(currentMode, kcal);
  render(target);
}

el("modeHint").textContent = MODE_HINT[currentMode];

function updateSourceHint() {
  const hint = el("sourceHint");
  if (!hint) return;
  const src = window.__foodSource;
  if (src === "麦当劳 MCP 实时数据") {
    hint.innerHTML = '数据来源：<strong style="color:#639922;">麦当劳 MCP 实时数据</strong>（通过 web/server.py 后端）';
  } else if (src === "离线快照") {
    hint.innerHTML = '数据来源：<strong>离线快照</strong>（未检测到后端，运行 <code>python web/server.py</code> 可切换实时 MCP）';
  } else {
    hint.innerHTML = '数据来源：麦当劳 MCP <code>list-nutrition-foods</code> 返回的真实营养数据（离线快照兜底）。启动 <code>web/server.py</code> 后端后自动切换实时 MCP。';
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
      window.__foodSource = data.source === "mcp" ? "麦当劳 MCP 实时数据" : "离线快照";
      updateSourceHint();
      generate();
    }
  } catch (e) {
    // 后端不可用，保持内联快照
    window.__foodSource = "离线快照";
    updateSourceHint();
  }
}

updateSourceHint();
generate();
loadRemoteFoods();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    foods = load_foods()
    html = build_html(foods)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"生成完成：{OUT}（{len(html)} 字符，{len(foods)} 种餐品）")
