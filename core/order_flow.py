"""营养餐品 → 可下单商品 的映射与下单编排（v2 全链路）。

解决核心问题：营养数据（list-nutrition-foods）的餐品名，需要映射到
可下单商品（query-meals）的 productCode，才能走 create-order 下单。

提供：
1. 名称归一化 + 模糊匹配（处理"纯牛奶（盒装）"vs"纯牛奶(盒装)"等差异）
2. 全链路编排：门店 → 营养套餐 → 映射 code → 算价 → 下单
"""
from __future__ import annotations

import re
from typing import Any, Optional

from .nutrition import MealPlan


def normalize_name(name: str) -> str:
    """归一化餐品名，去除括号差异、空格、大小写差异，便于匹配。"""
    s = name.strip().lower()
    # 统一全角/半角括号
    s = s.replace("（", "(").replace("）", ")")
    # 去掉括号内容（保留主名），同时保留一份含括号的用于精确匹配
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"\s+", "", s)
    return s


def _clean_for_key(name: str) -> str:
    """生成匹配键：去掉修饰词，提取核心名称。"""
    s = normalize_name(name)
    # 去掉常见修饰前缀/后缀
    for w in ("套餐", "三件套", "四件套", "单人", "双人", "随心选", "精选",
              "单点", "单品", "盒装", "大杯", "中杯", "小杯", "大", "中", "小"):
        s = s.replace(w, "")
    return s


def map_food_to_product(food_name: str, meals_map: dict) -> Optional[str]:
    """将营养餐品名映射到可下单商品的 productCode。

    Args:
        food_name: 营养库中的餐品名（如"巨无霸"）
        meals_map: query-meals 返回的 data.meals 映射表 {code: {name, ...}}

    Returns:
        匹配到的 productCode，找不到则返回 None
    """
    target = normalize_name(food_name)
    target_key = _clean_for_key(food_name)

    best_code = None
    best_score = -1

    for code, info in meals_map.items():
        name = info.get("name", "")
        norm = normalize_name(name)
        key = _clean_for_key(name)

        score = 0
        if norm == target:
            score = 100  # 完全一致
        elif key == target_key:
            score = 90
        elif target_key and (target_key in key or key in target_key):
            # 子串匹配：主名互含
            shorter = min(len(target_key), len(key))
            longer = max(len(target_key), len(key))
            if shorter > 0 and longer > 0:
                score = 70 + (shorter / longer) * 20
        # 核心词包含
        if score <= 0 and target_key and len(target_key) >= 2:
            if target_key in norm or norm in target:
                score = 60

        if score > best_score:
            best_score = score
            best_code = code

    # 阈值：分数过低视为不匹配
    return best_code if best_score >= 60 else None


class OrderOrchestrator:
    """全链路下单编排器。

    流程：营养拼配 → 门店餐品 → code 映射 → 算价 → 下单
    """

    def __init__(self, client):
        self.client = client

    def full_flow(self, mode: str, kcal: float, city: str, keyword: str,
                  be_type: int = 1) -> dict:
        """执行完整链路（不实际下单，到"算价确认"为止）。

        实际下单需用户明确确认，避免误下单。
        """
        result = {"steps": []}

        # 1. 营养拼配
        foods = self.client.list_nutrition_foods()
        from .nutrition import build_target, plan_meal
        target = build_target(mode, kcal)
        plan = plan_meal(foods, target)
        if plan is None:
            result["error"] = "无法拼出满足约束的套餐"
            return result
        result["plan"] = plan.to_dict()
        result["steps"].append("营养拼配完成")

        # 2. 查询门店
        stores = self.client.query_nearby_stores(city, keyword, be_type)
        store_list = stores.get("data", []) if isinstance(stores, dict) else []
        if not store_list:
            result["error"] = "未找到附近门店"
            return result
        store = store_list[0]
        store_code = store.get("storeCode")
        result["store"] = {
            "storeName": store.get("storeName"),
            "storeCode": store_code,
            "distance": store.get("distance"),
        }
        result["steps"].append(f"定位门店：{store.get('storeName')}")

        # 3. 查询门店可下单餐品
        meals = self.client.query_meals(store_code, order_type=1, be_type=be_type)
        meals_map = self._extract_meals_map(meals)
        result["steps"].append(f"获取门店菜单（{len(meals_map)} 个可下单商品）")

        # 4. 映射 productCode
        mapped_items = []
        unmapped = []
        for item in plan.items:
            code = map_food_to_product(item.product_name, meals_map)
            if code:
                mapped_items.append({
                    "food_name": item.product_name,
                    "productCode": code,
                    "meal_name": meals_map[code]["name"],
                    "price": meals_map[code].get("currentPrice"),
                    "quantity": 1,
                })
            else:
                unmapped.append(item.product_name)
        result["mapped_items"] = mapped_items
        result["unmapped"] = unmapped
        result["steps"].append(f"映射可下单商品 {len(mapped_items)}/{len(plan.items)} 项")

        # 5. 算价（如有映射结果）
        if mapped_items:
            price_result = self.client.calculate_price(
                store_code, order_type=1, be_type=be_type,
                items=[{"productCode": i["productCode"], "quantity": 1}
                       for i in mapped_items],
            )
            result["price"] = self._extract_price(price_result)
            result["steps"].append("算价完成")

        return result

    # ------------------------------------------------------------------
    # 解析辅助
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_meals_map(meals: Any) -> dict:
        if isinstance(meals, dict):
            return meals.get("data", {}).get("meals", {})
        return {}

    @staticmethod
    def _extract_price(price: Any) -> Any:
        if isinstance(price, dict):
            return price.get("data", price)
        return price

    # ------------------------------------------------------------------
    # 下单（需用户明确确认后调用）
    # ------------------------------------------------------------------
    def create_order(self, store_code: str, be_type: int, order_type: int,
                     items: list, take_way_code: Optional[str] = None,
                     address_id: Optional[str] = None,
                     be_code: Optional[str] = None) -> Any:
        """创建订单（到店 order_type=1 需 take_way_code；外送 order_type=2 需 address_id）。"""
        params = {
            "storeCode": store_code,
            "orderType": order_type,
            "beType": be_type,
            "items": items,
        }
        if take_way_code:
            params["takeWayCode"] = take_way_code
        if address_id:
            params["addressId"] = address_id
        if be_code:
            params["beCode"] = be_code
        return self.client._call("mcp__mcd-mcp__create-order", params)
