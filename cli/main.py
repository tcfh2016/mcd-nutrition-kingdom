#!/usr/bin/env python3
"""麦当劳营养点餐 Agent —— 独立 CLI。

用法示例：
    # 控卡减脂：预算 500 千卡
    python cli/main.py --mode calorie --kcal 500

    # 增肌高蛋白：预算 700 千卡
    python cli/main.py --mode protein --kcal 700

    # 控糖低GI：预算 450 千卡
    python cli/main.py --mode lowcarb --kcal 450

    # 实时调用麦当劳 MCP 获取餐品数据（需配置环境变量）
    MCD_MCP_BASE_URL=... MCD_MCP_AUTH_TOKEN=... python cli/main.py --mode calorie --kcal 500 --live

    # 输出 JSON
    python cli/main.py --mode calorie --kcal 500 --json

    # v2 全链路：营养拼配 → 门店 → 映射可下单商品 → 算价（需 --live）
    MCD_MCP_BASE_URL=... MCD_MCP_AUTH_TOKEN=... python cli/main.py --mode calorie --kcal 500 --live --order --city 杭州 --keyword 西湖
"""
from __future__ import annotations

import argparse
import json
import os
import sys

# 允许直接运行 core 包（无需安装）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import build_target, plan_meal, load_snapshot, McDonaldsMCPClient, OrderOrchestrator  # noqa: E402

MODE_HELP = {
    "calorie": "控卡减脂：控制总热量，压低脂肪供能占比",
    "protein": "增肌高蛋白：保证蛋白质摄入下限",
    "lowcarb": "控糖低GI：限制碳水总量",
}


def render_plan(plan) -> str:
    lines = []
    lines.append(f"【{plan.target.label}】套餐建议（预算 {plan.target.max_kcal:.0f} 千卡）")
    lines.append("-" * 46)
    lines.append(f"{'餐品':<24}{'热量':>8}{'蛋白':>6}{'脂肪':>6}{'碳水':>6}")
    for item in plan.items:
        lines.append(
            f"{item.product_name:<24}{item.energy_kcal:>8.0f}"
            f"{item.protein:>6.0f}{item.fat:>6.0f}{item.carbohydrate:>6.0f}"
        )
    lines.append("-" * 46)
    t = plan.to_dict()["totals"]
    lines.append(
        f"{'合计':<24}{t['kcal']:>8.0f}{t['protein']:>6.0f}"
        f"{t['fat']:>6.0f}{t['carbohydrate']:>6.0f}"
    )
    lines.append(f"\n钠含量：{t['sodium']:.0f} mg   钙含量：{t['calcium']:.0f} mg")
    lines.append(f"热量利用率：{t['kcal'] / plan.target.max_kcal * 100:.0f}%")
    return "\n".join(lines)


def render_order_flow(result: dict) -> str:
    lines = []
    lines.append("【全链路点餐流程】")
    for step in result.get("steps", []):
        lines.append(f"  ✓ {step}")
    if result.get("error"):
        lines.append(f"  ✗ 错误：{result['error']}")
        return "\n".join(lines)

    if result.get("store"):
        s = result["store"]
        lines.append(f"\n门店：{s['storeName']}（{s['storeCode']}，距 {s.get('distance','?')} 米）")

    if result.get("plan"):
        p = result["plan"]
        lines.append(f"\n营养套餐（{p['label']}，预算 {p['target']['max_kcal']:.0f} 千卡）：")
        for it in p["items"]:
            lines.append(f"  - {it['product_name']}")

    if result.get("mapped_items"):
        lines.append("\n可下单商品映射：")
        for it in result["mapped_items"]:
            lines.append(f"  - {it['food_name']} → [{it['productCode']}] {it['meal_name']} ¥{it['price']}")

    if result.get("unmapped"):
        lines.append(f"\n未能映射的商品：{', '.join(result['unmapped'])}")

    if result.get("price"):
        lines.append(f"\n价格计算：{json.dumps(result['price'], ensure_ascii=False)}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="麦当劳营养点餐 Agent")
    parser.add_argument("--mode", choices=["calorie", "protein", "lowcarb"],
                        default="calorie", help="营养模式")
    parser.add_argument("--kcal", type=float, required=True, help="热量预算（千卡）")
    parser.add_argument("--max-items", type=int, default=4, help="套餐最多餐品数")
    parser.add_argument("--live", action="store_true", help="实时调用麦当劳 MCP 获取餐品")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出")
    parser.add_argument("--order", action="store_true", help="v2 全链路（营养→门店→映射→算价）")
    parser.add_argument("--city", default="杭州", help="门店城市（--order 时使用）")
    parser.add_argument("--keyword", default="", help="门店位置关键词（--order 时使用）")
    args = parser.parse_args()

    # v2 全链路模式
    if args.order:
        if not args.live:
            print("错误：全链路模式需要 --live（实时调用 MCP）", file=sys.stderr)
            return 1
        client = McDonaldsMCPClient()
        orch = OrderOrchestrator(client)
        result = orch.full_flow(args.mode, args.kcal, args.city, args.keyword)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(render_order_flow(result))
        return 0 if not result.get("error") else 1

    if args.live:
        client = McDonaldsMCPClient()
        foods = client.list_nutrition_foods()
        source = "MCP（实时）"
        if not foods:
            print("错误：MCP 未返回餐品数据，请检查 MCD_MCP_BASE_URL / 认证配置。", file=sys.stderr)
            return 1
    else:
        foods = load_snapshot()
        source = "离线快照（未配置 MCP）"

    target = build_target(args.mode, args.kcal)
    plan = plan_meal(foods, target, max_items=args.max_items)

    if plan is None:
        print(f"无法在预算 {args.kcal:.0f} 千卡内拼出满足约束的套餐，请放宽预算或减少约束。", file=sys.stderr)
        return 1

    print(f"数据来源：{source}\n")
    if args.json:
        print(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(render_plan(plan))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
