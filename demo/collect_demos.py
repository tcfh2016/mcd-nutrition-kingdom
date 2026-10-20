#!/usr/bin/env python3
"""收集 5 个 demo 的最终结构化结果，输出 JSON 供生成演示脚本与结果卡使用。

- demo 1-3：控卡 / 增肌 / 控糖（离线快照）
- demo 4：忌口过滤（忌"鱼"，含 before/after 对比）
- demo 5：v2 全链路下单（真实 MCP 数据，硬编码自现场实测）
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import build_target, plan_meal, load_snapshot

foods = load_snapshot()


def to_items(plan):
    out = []
    for it in plan.items:
        out.append({
            "name": it.product_name,
            "kcal": round(it.energy_kcal, 1),
            "protein": round(it.protein, 1),
            "fat": round(it.fat, 1),
            "carb": round(it.carbohydrate, 1),
            "sodium": round(it.sodium, 1),
            "calcium": round(it.calcium, 1),
        })
    return out


def to_totals(plan, budget):
    t = plan.to_dict()["totals"]
    return {
        "kcal": round(t["kcal"], 1),
        "protein": round(t["protein"], 1),
        "fat": round(t["fat"], 1),
        "carb": round(t["carbohydrate"], 1),
        "sodium": round(t["sodium"], 1),
        "calcium": round(t["calcium"], 1),
        "utilization": round(t["kcal"] / budget * 100),
    }


results = []

# ---- demo 1-3 ----
for spec in [
    {"id": 1, "title": "控卡减脂", "customer": "健身 / 减脂人群",
     "story": "我今晚只想吃 500 千卡，少油一点", "mode": "calorie", "kcal": 500},
    {"id": 2, "title": "增肌高蛋白", "customer": "增肌人群",
     "story": "我最近在增肌，蛋白质要够，700 千卡左右", "mode": "protein", "kcal": 700},
    {"id": 3, "title": "控糖低 GI", "customer": "控糖 / 低碳饮食者",
     "story": "控糖期想吃麦当劳，碳水别太高", "mode": "lowcarb", "kcal": 450},
]:
    t = build_target(spec["mode"], spec["kcal"])
    p = plan_meal(foods, t, max_items=4, max_per_category=2)
    results.append({
        "id": spec["id"], "title": spec["title"], "customer": spec["customer"],
        "story": spec["story"], "mode": spec["mode"],
        "budget_kcal": spec["kcal"], "label": p.target.label,
        "items": to_items(p), "totals": to_totals(p, spec["kcal"]),
    })

# ---- demo 4：忌口过滤（忌"鱼"，海鲜过敏） ----
t4 = build_target("calorie", 550)
before = plan_meal(foods, t4, max_items=4, max_per_category=2)
after = plan_meal(foods, t4, max_items=4, max_per_category=2, exclude=["鱼"])
results.append({
    "id": 4, "title": "忌口过滤", "customer": "忌口 / 过敏人群",
    "story": "我对海鲜过敏，别给我配鱼排堡之类的东西",
    "mode": "calorie", "budget_kcal": 550, "label": "控卡减脂",
    "exclude": ["鱼"],
    "before": {"items": to_items(before), "totals": to_totals(before, 550)},
    "after": {"items": to_items(after), "totals": to_totals(after, 550)},
})

# ---- demo 5：v2 全链路下单（真实 MCP 现场实测） ----
results.append({
    "id": 5, "title": "全链路下单", "customer": "想直接吃到的顾客 / 技术评审",
    "story": "早上想吃顿低卡早餐，帮我直接下单",
    "mode": "calorie", "budget_kcal": 500, "label": "控卡减脂",
    "store": {
        "name": "麦当劳杭州西湖银泰餐厅", "storeCode": "3330052",
        "address": "延安路 98 号", "distance": "4917",
    },
    "items": [
        {"name": "猪柳蛋麦满分", "kcal": 387, "protein": 23, "fat": 21, "carb": 25, "sodium": 846, "calcium": 243},
        {"name": "小杯玉米杯", "kcal": 53, "protein": 2, "fat": 1, "carb": 7, "sodium": 1, "calcium": 6},
        {"name": "小杯鲜萃咖啡", "kcal": 15, "protein": 1, "fat": 0, "carb": 3, "sodium": 2, "calcium": 6},
    ],
    "totals": {"kcal": 455, "protein": 26, "fat": 22, "carb": 35, "sodium": 849, "calcium": 255, "utilization": 91},
    "mapped": [
        {"food": "猪柳蛋麦满分", "code": "5022", "meal": "猪柳蛋麦满分", "price": 18.0},
        {"food": "小杯玉米杯", "code": "4437", "meal": "小杯玉米杯", "price": 13.0},
        {"food": "小杯鲜萃咖啡", "code": "520689", "meal": "小杯鲜萃咖啡", "price": 9.5},
    ],
    "price": {"total": 40.5, "currency": "¥", "discount": 0},
    "takeway": ["堂食（eat-in）", "外带（take-in-store）"],
})

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_results.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(json.dumps(results, ensure_ascii=False, indent=2))
print(f"\n[SAVED] {out_path}")
