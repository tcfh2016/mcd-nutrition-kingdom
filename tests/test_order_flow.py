"""下单链路（core/order_flow.py）单元测试。"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.order_flow import map_food_to_product, match_coupons, normalize_name


class TestNormalizeName(unittest.TestCase):
    def test_bracket(self):
        self.assertEqual(normalize_name("纯牛奶（盒装）"), normalize_name("纯牛奶(盒装)"))

    def test_space(self):
        self.assertEqual(normalize_name("100%苹果汁"), normalize_name("100% 苹果汁"))

    def test_case(self):
        self.assertEqual(normalize_name("Pro"), normalize_name("pro"))


class TestMapFoodToProduct(unittest.TestCase):
    def setUp(self):
        self.meals = {
            "5022": {"name": "猪柳蛋麦满分"},
            "4437": {"name": "玉米杯"},
            "520689": {"name": "鲜萃咖啡"},
            "3755": {"name": "纯牛奶(盒装)"},
            "6362": {"name": "100% 苹果汁(盒装)"},
            "515520": {"name": "怡泉+C"},
            "3010": {"name": "雪碧"},
        }

    def test_exact(self):
        self.assertEqual(map_food_to_product("猪柳蛋麦满分", self.meals), "5022")

    def test_size_prefix(self):
        # 营养库的"小杯玉米杯"应映射到菜单"玉米杯"
        self.assertEqual(map_food_to_product("小杯玉米杯", self.meals), "4437")
        self.assertEqual(map_food_to_product("小杯鲜萃咖啡", self.meals), "520689")

    def test_bracket_diff(self):
        self.assertEqual(map_food_to_product("纯牛奶（盒装）", self.meals), "3755")

    def test_space_and_box(self):
        self.assertEqual(map_food_to_product("100%苹果汁", self.meals), "6362")

    def test_symbol(self):
        self.assertEqual(map_food_to_product("中杯怡泉+C", self.meals), "515520")

    def test_not_found(self):
        self.assertIsNone(map_food_to_product("巨无霸", self.meals))


class TestMatchCoupons(unittest.TestCase):
    def setUp(self):
        # 西湖银泰店真实返回的券结构（券主数据 code 与门店 SKU code 不同）
        self.coupons = [
            {"title": "新人专享-中杯美式7折", "couponId": "AAA", "couponCode": "MCD001",
             "products": [{"productCode": "9900000119", "productName": "美式中杯"}]},
            {"title": "新人专享-中杯奶铁7折", "couponId": "BBB", "couponCode": "MCD002",
             "products": [{"productCode": "9900000117", "productName": "奶铁中杯"}]},
        ]

    def test_match_by_name(self):
        # 门店 SKU code 与券主数据 code 不同，靠名称模糊匹配
        mapped = [{"productCode": "507368", "meal_name": "麦咖啡™热美式中杯"}]
        matched = match_coupons(self.coupons, mapped)
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0]["title"], "新人专享-中杯美式7折")
        self.assertIn("507368", matched[0]["matched_meal_codes"])

    def test_match_by_code(self):
        mapped = [{"productCode": "9900000119", "meal_name": "美式中杯"}]
        matched = match_coupons(self.coupons, mapped)
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0]["couponId"], "AAA")

    def test_match_both(self):
        mapped = [
            {"productCode": "507368", "meal_name": "麦咖啡™热美式中杯"},
            {"productCode": "507328", "meal_name": "麦咖啡™热奶铁中杯"},
        ]
        matched = match_coupons(self.coupons, mapped)
        self.assertEqual(len(matched), 2)

    def test_match_none(self):
        mapped = [{"productCode": "5022", "meal_name": "猪柳蛋麦满分"}]
        self.assertEqual(match_coupons(self.coupons, mapped), [])

    def test_match_empty_coupons(self):
        self.assertEqual(match_coupons([], [{"productCode": "5022", "meal_name": "猪柳蛋麦满分"}]), [])


if __name__ == "__main__":
    unittest.main()
