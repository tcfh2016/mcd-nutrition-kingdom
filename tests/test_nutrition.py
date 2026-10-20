"""核心引擎（core/nutrition.py）单元测试。

运行：在项目根目录执行 `python -m unittest discover -s tests -v`
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.nutrition import (
    FoodItem,
    build_target,
    filter_foods,
    infer_category,
    load_snapshot,
    parse_foods_from_mcp,
    plan_daily,
    plan_meal,
)


def _food(name, kcal, protein, fat, carb, sodium=0, calcium=0, category="unknown"):
    return FoodItem(name, kcal, protein, fat, carb, sodium, calcium, category)


class TestBuildTarget(unittest.TestCase):
    def test_calorie_mode(self):
        t = build_target("calorie", 500)
        self.assertEqual(t.label, "控卡减脂")
        self.assertEqual(t.max_kcal, 500)
        self.assertAlmostEqual(t.max_fat, max(15.0, 500 * 0.35 / 9), places=4)

    def test_protein_mode(self):
        t = build_target("protein", 700)
        self.assertEqual(t.label, "增肌高蛋白")
        self.assertAlmostEqual(t.min_protein, max(20.0, 700 * 0.20 / 4), places=4)

    def test_lowcarb_mode(self):
        t = build_target("lowcarb", 450)
        self.assertEqual(t.label, "控糖低GI")
        self.assertAlmostEqual(t.max_carb, max(30.0, 450 * 0.30 / 4), places=4)

    def test_unknown_mode_raises(self):
        with self.assertRaises(ValueError):
            build_target("nonsense", 500)


class TestPlanMeal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.foods = load_snapshot()
        assert len(cls.foods) > 100, "快照数据不足，请先运行 scripts/refresh_snapshot.py"

    def _plan(self, mode, kcal, **kw):
        target = build_target(mode, kcal)
        return plan_meal(self.foods, target, **kw)

    def test_within_budget(self):
        for mode, kcal in [("calorie", 500), ("protein", 700), ("lowcarb", 450)]:
            plan = self._plan(mode, kcal)
            self.assertIsNotNone(plan, f"{mode} 模式应能拼出套餐")
            self.assertLessEqual(plan.total_kcal, kcal + 1e-6)

    def test_no_duplicate_food(self):
        for mode, kcal in [("calorie", 500), ("protein", 700), ("lowcarb", 450)]:
            plan = self._plan(mode, kcal)
            names = [i.product_name for i in plan.items]
            self.assertEqual(len(names), len(set(names)), f"{mode} 模式不应有同名重复")

    def test_no_duplicate_drink_base(self):
        from core.nutrition import _drink_base
        plan = self._plan("calorie", 500, max_items=6)
        bases = [b for b in (_drink_base(i.product_name) for i in plan.items) if b]
        self.assertEqual(len(bases), len(set(bases)), "同基础饮品不应重复")

    def test_category_balance(self):
        plan = self._plan("calorie", 500, max_per_category=2)
        from collections import Counter
        cats = Counter(i.category for i in plan.items)
        self.assertTrue(all(v <= 2 for v in cats.values()), f"每类不应超过 2 个，实际 {dict(cats)}")

    def test_protein_min(self):
        plan = self._plan("protein", 700)
        self.assertGreaterEqual(plan.total_protein, build_target("protein", 700).min_protein - 1e-6)

    def test_lowcarb_limit(self):
        plan = self._plan("lowcarb", 450)
        self.assertLessEqual(plan.total_carb, build_target("lowcarb", 450).max_carb + 1e-6)

    def test_max_items(self):
        plan = self._plan("calorie", 800, max_items=3)
        self.assertLessEqual(len(plan.items), 3)


class TestInferCategory(unittest.TestCase):
    def test_burger(self):
        for name in ("巨无霸", "板烧鸡腿堡", "猪柳蛋麦满分", "脆汁鸡-琵琶腿", "蜜汁快乐"):
            self.assertEqual(infer_category(name), "burger", name)

    def test_side(self):
        for name in ("中薯条", "小杯玉米杯", "苹果片", "香芋派", "皮蛋鸡肉粥"):
            self.assertEqual(infer_category(name), "side", name)

    def test_drink(self):
        for name in ("可乐中杯", "小杯鲜萃咖啡", "热美式中杯", "优品豆浆大杯", "纯悦"):
            self.assertEqual(infer_category(name), "drink", name)


class TestParseFoodsFromMcp(unittest.TestCase):
    def test_parse_lines(self):
        raw = (
            "{productName,nutritionDescription,energyKj,energyKcal,protein,fat,carbohydrate,sodium,calcium}:\n"
            "  猪柳蛋麦满分,null,1618,387,23,21,25,846,243\n"
            "  无糖可口可乐中杯,null,0,0,0,0,1,35,0\n"
        )
        foods = parse_foods_from_mcp(raw)
        self.assertEqual(len(foods), 2)
        self.assertEqual(foods[0].product_name, "猪柳蛋麦满分")
        self.assertEqual(foods[0].energy_kcal, 387)
        self.assertEqual(foods[0].protein, 23)
        self.assertEqual(foods[1].product_name, "无糖可口可乐中杯")
        self.assertEqual(foods[1].energy_kcal, 0)


class TestFilterFoods(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.foods = load_snapshot()

    def test_no_restriction(self):
        self.assertEqual(len(filter_foods(self.foods, [])), len(self.foods))

    def test_exclude_spicy(self):
        result = filter_foods(self.foods, ["辣"])
        self.assertTrue(all("辣" not in f.product_name for f in result))
        self.assertLess(len(result), len(self.foods))

    def test_exclude_fish(self):
        result = filter_foods(self.foods, ["鱼"])
        self.assertTrue(all("鱼" not in f.product_name and "鳕鱼" not in f.product_name for f in result))

    def test_unknown_falls_back_to_literal(self):
        result = filter_foods(self.foods, ["巨无霸"])
        self.assertTrue(all("巨无霸" not in f.product_name for f in result))


class TestPlanMealExclude(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.foods = load_snapshot()

    def test_exclude_applied(self):
        plan = plan_meal(self.foods, build_target("calorie", 500), exclude=["辣", "鱼"])
        self.assertIsNotNone(plan)
        for it in plan.items:
            self.assertNotIn("辣", it.product_name)
            self.assertNotIn("鱼", it.product_name)


class TestPlanDaily(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.foods = load_snapshot()

    def test_three_meals(self):
        plans = plan_daily(self.foods, "calorie", 1800)
        self.assertEqual(list(plans.keys()), ["早餐", "午餐", "晚餐"])

    def test_no_cross_meal_duplicate(self):
        plans = plan_daily(self.foods, "calorie", 1800)
        all_names = [it.product_name for p in plans.values() if p for it in p.items]
        self.assertEqual(len(all_names), len(set(all_names)), "三餐不应重复同一餐品")

    def test_total_within_budget(self):
        plans = plan_daily(self.foods, "calorie", 1800)
        total = sum(p.total_kcal for p in plans.values() if p)
        self.assertLessEqual(total, 1800 + 1e-6)


if __name__ == "__main__":
    unittest.main()
