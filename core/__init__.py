"""core 包初始化。

对外暴露核心引擎与 MCP 客户端，供 CLI / Skill / Web 复用。
"""
from .nutrition import (
    FoodItem,
    NutritionTarget,
    MealPlan,
    build_target,
    plan_meal,
    parse_foods_from_mcp,
    load_snapshot,
    infer_category,
)
from .mcp_client import McDonaldsMCPClient

__all__ = [
    "FoodItem",
    "NutritionTarget",
    "MealPlan",
    "build_target",
    "plan_meal",
    "parse_foods_from_mcp",
    "load_snapshot",
    "infer_category",
    "McDonaldsMCPClient",
]
