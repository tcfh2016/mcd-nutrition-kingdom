"""core 包初始化。

对外暴露核心引擎与 MCP 客户端，供 CLI / Skill / Web 复用。
"""
from .nutrition import (
    FoodItem,
    NutritionTarget,
    MealPlan,
    build_target,
    plan_meal,
    plan_daily,
    parse_foods_from_mcp,
    load_snapshot,
    infer_category,
    filter_foods,
    ALLERGEN_KEYWORDS,
)
from .mcp_client import McDonaldsMCPClient
from .order_flow import OrderOrchestrator, map_food_to_product, normalize_name, match_coupons

__all__ = [
    "FoodItem",
    "NutritionTarget",
    "MealPlan",
    "build_target",
    "plan_meal",
    "plan_daily",
    "parse_foods_from_mcp",
    "load_snapshot",
    "infer_category",
    "filter_foods",
    "ALLERGEN_KEYWORDS",
    "McDonaldsMCPClient",
    "OrderOrchestrator",
    "map_food_to_product",
    "normalize_name",
    "match_coupons",
]
