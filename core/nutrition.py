"""麦当劳营养点餐 Agent —— 核心引擎。

本模块是项目唯一的核心业务逻辑，被 WorkBuddy Skill 与独立 CLI/Web 共同复用。
它负责：
1. 定义餐品营养数据模型；
2. 实现多模式（控卡 / 增肌 / 控糖）套餐拼配算法；
3. 输出带营养标签的套餐建议。

营养数据来源于麦当劳 MCP 的 list-nutrition-foods 工具（运行时获取），
本模块同时内置一份静态快照作为离线兜底，确保无 MCP 环境也能演示。
"""
from __future__ import annotations

import dataclasses
import json
from typing import Iterable, Optional

# ============================================================================
# 数据模型
# ============================================================================


@dataclasses.dataclass(frozen=True)
class FoodItem:
    """单个餐品的营养数据。"""

    product_name: str
    energy_kcal: float          # 千卡
    protein: float              # 克
    fat: float                  # 克
    carbohydrate: float         # 克
    sodium: float               # 毫克
    calcium: float              # 毫克
    category: str = "unknown"   # burger / side / drink / dessert / breakfast / coffee

    @property
    def energy_kj(self) -> float:
        return round(self.energy_kcal * 4.184, 1)

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class NutritionTarget:
    """一套营养约束目标（多模式之一）。"""

    mode: str                     # "calorie" | "protein" | "lowcarb"
    label: str                    # 展示名
    max_kcal: float               # 热量上限（千卡）
    min_protein: float = 0.0      # 最低蛋白质（克）
    max_fat: float = float("inf")  # 最高脂肪（克）
    max_carb: float = float("inf")  # 最高碳水（克）
    max_sodium: float = float("inf")  # 最高钠（毫克）


@dataclasses.dataclass(frozen=True)
class MealPlan:
    """一份拼配好的套餐。"""

    target: NutritionTarget
    items: tuple[FoodItem, ...]
    total_kcal: float
    total_protein: float
    total_fat: float
    total_carb: float
    total_sodium: float
    total_calcium: float

    def to_dict(self) -> dict:
        return {
            "mode": self.target.mode,
            "label": self.target.label,
            "items": [i.to_dict() for i in self.items],
            "totals": {
                "kcal": round(self.total_kcal, 1),
                "protein": round(self.total_protein, 1),
                "fat": round(self.total_fat, 1),
                "carbohydrate": round(self.total_carb, 1),
                "sodium": round(self.total_sodium, 1),
                "calcium": round(self.total_calcium, 1),
            },
        }


# ============================================================================
# 多模式目标工厂
# ============================================================================


def build_target(mode: str, kcal: float, extra: Optional[dict] = None) -> NutritionTarget:
    """根据模式与热量预算构建营养目标。

    Args:
        mode: "calorie" 控卡减脂 / "protein" 增肌高蛋白 / "lowcarb" 控糖低GI
        kcal: 用户提供的热量预算（千卡）
        extra: 可选，覆盖默认约束字段
    """
    extra = extra or {}
    if mode == "calorie":
        t = NutritionTarget(
            mode=mode,
            label="控卡减脂",
            max_kcal=kcal,
            max_fat=max(15.0, kcal * 0.35 / 9),  # 脂肪供能占比 ≤ 35%
        )
    elif mode == "protein":
        t = NutritionTarget(
            mode=mode,
            label="增肌高蛋白",
            max_kcal=kcal,
            min_protein=max(20.0, kcal * 0.20 / 4),  # 蛋白质供能占比 ≥ 20%
        )
    elif mode == "lowcarb":
        t = NutritionTarget(
            mode=mode,
            label="控糖低GI",
            max_kcal=kcal,
            max_carb=max(30.0, kcal * 0.30 / 4),  # 碳水供能占比 ≤ 30%
        )
    else:
        raise ValueError(f"未知模式: {mode}（支持 calorie/protein/lowcarb）")

    for k, v in extra.items():
        object.__setattr__(t, k, v)
    return t


# ============================================================================
# 套餐拼配引擎
# ============================================================================


def _fits(item: FoodItem, target: NutritionTarget,
          acc: dict, max_items: int, cur_count: int,
          max_per_category: Optional[int] = None) -> bool:
    """判断把 item 加入当前累计后是否仍满足约束。"""
    if cur_count >= max_items:
        return False
    # 避免重复餐品（同名去重）
    if item.product_name in acc.get("_names", set()):
        return False
    # 类别均衡：限制同一类别餐品数量，避免套餐过度集中于某一类
    if max_per_category is not None:
        if acc.get("_cat_count", {}).get(item.category, 0) >= max_per_category:
            return False
    # 饮品去重：避免同一基础饮品点两个冷热款（如热美式+冰美式）
    base = _drink_base(item.product_name)
    if base and base in acc.get("_drinks", set()):
        return False
    kcal = acc["kcal"] + item.energy_kcal
    if kcal > target.max_kcal + 1e-6:
        return False
    if acc["fat"] + item.fat > target.max_fat + 1e-6:
        return False
    if acc["carb"] + item.carbohydrate > target.max_carb + 1e-6:
        return False
    if acc["sodium"] + item.sodium > target.max_sodium + 1e-6:
        return False
    return True


def _add(item: FoodItem, acc: dict) -> None:
    acc["kcal"] += item.energy_kcal
    acc["protein"] += item.protein
    acc["fat"] += item.fat
    acc["carb"] += item.carbohydrate
    acc["sodium"] += item.sodium
    acc["calcium"] += item.calcium
    acc.setdefault("_names", set()).add(item.product_name)
    acc.setdefault("_cats", set()).add(item.category)
    acc.setdefault("_cat_count", {})[item.category] = acc["_cat_count"].get(item.category, 0) + 1
    base = _drink_base(item.product_name)
    if base:
        acc.setdefault("_drinks", set()).add(base)


def _new_acc() -> dict:
    return {"kcal": 0.0, "protein": 0.0, "fat": 0.0, "carb": 0.0,
            "sodium": 0.0, "calcium": 0.0, "_names": set(), "_cats": set(),
            "_cat_count": {}, "_drinks": set()}


def plan_meal(
    foods: Iterable[FoodItem],
    target: NutritionTarget,
    max_items: int = 4,
    categories: Optional[set[str]] = None,
    max_per_category: Optional[int] = None,
    exclude: Optional[list[str]] = None,
) -> Optional[MealPlan]:
    """在给定餐品集合上拼配一份满足约束的套餐。

    采用贪心 + 局部搜索：优先按模式打分排序，再迭代填充。
    返回最优候选套餐，无法满足约束时返回 None。

    Args:
        foods: 候选餐品（通常来自 MCP list-nutrition-foods）
        target: 营养目标
        max_items: 套餐最多包含的餐品数量
        categories: 可选，限制候选餐品类别（如 {"burger","side","drink"}）
        max_per_category: 可选，每类餐品数量上限（如 2，保证套餐结构均衡）
        exclude: 可选，忌口/过敏原名列表（如 ["辣", "鱼", "牛肉"]），过滤匹配餐品
    """
    if exclude:
        foods = filter_foods(foods, exclude)
    pool = [f for f in foods if categories is None or f.category in categories]

    # 打分：蛋白质密度（增肌）或低热量密度（控卡/控糖）优先
    if target.mode == "protein":
        def score(f: FoodItem) -> float:
            return f.protein / max(f.energy_kcal, 1.0)
    else:
        def score(f: FoodItem) -> float:
            # 优先蛋白高、脂肪低的餐品
            return (f.protein / max(f.energy_kcal, 1.0)) - (f.fat / max(f.energy_kcal, 1.0) * 0.5)

    pool = sorted(pool, key=score, reverse=True)

    best: Optional[MealPlan] = None

    # 贪心：从高分餐品开始逐次加入，尽量填充到接近预算
    acc = _new_acc()
    chosen: list[FoodItem] = []
    for item in pool:
        if _fits(item, target, acc, max_items, len(chosen), max_per_category):
            _add(item, acc)
            chosen.append(item)
        # 控卡/控糖：达到预算的 90% 或已加满即停，避免过度贪心
        if acc["kcal"] >= target.max_kcal * 0.9:
            break

    # 第二遍：用低热量小食/饮品补足剩余热量（提升饱腹感与利用率）
    if acc["kcal"] < target.max_kcal * 0.85 and len(chosen) < max_items:
        remaining = [f for f in pool if f.product_name not in acc["_names"]]
        remaining.sort(key=lambda f: f.energy_kcal)  # 优先小份量
        for item in remaining:
            if len(chosen) >= max_items:
                break
            if _fits(item, target, acc, max_items, len(chosen), max_per_category):
                _add(item, acc)
                chosen.append(item)
                if acc["kcal"] >= target.max_kcal * 0.9:
                    break

    if chosen:
        best = _make_plan(target, chosen, acc)

    # 局部搜索：替换，改善目标指标
    # protein 模式：提升总蛋白；calorie/lowcarb：提升热量利用率（更贴近预算）
    for _ in range(len(pool) * 2):
        improved = False
        for i, kept in enumerate(chosen):
            for cand in pool:
                if cand.product_name in acc["_names"]:
                    continue
                trial_acc = dict(acc)
                trial_acc["_names"] = set(acc["_names"])
                trial_acc["_cats"] = set(acc["_cats"])
                trial_acc["_drinks"] = set(acc.get("_drinks", set()))
                trial_acc["_cat_count"] = dict(acc.get("_cat_count", {}))
                trial_acc["_names"].discard(kept.product_name)
                base = _drink_base(kept.product_name)
                if base:
                    trial_acc["_drinks"].discard(base)
                # 移除 kept 的类别计数
                _cat = kept.category
                if trial_acc["_cat_count"].get(_cat, 0) <= 1:
                    trial_acc["_cat_count"].pop(_cat, None)
                else:
                    trial_acc["_cat_count"][_cat] -= 1
                trial_acc["kcal"] -= kept.energy_kcal
                trial_acc["protein"] -= kept.protein
                trial_acc["fat"] -= kept.fat
                trial_acc["carb"] -= kept.carbohydrate
                trial_acc["sodium"] -= kept.sodium
                trial_acc["calcium"] -= kept.calcium
                if not _fits(cand, target, trial_acc, max_items, len(chosen) - 1, max_per_category):
                    continue
                if target.mode == "protein":
                    better = cand.protein > kept.protein
                else:
                    # 更贴近预算（但不超），且不牺牲过多蛋白
                    better = (cand.energy_kcal > kept.energy_kcal
                              and cand.protein >= kept.protein - 2)
                if better:
                    chosen[i] = cand
                    acc = trial_acc
                    _add(cand, acc)
                    improved = True
                    break
            if improved:
                break
        if not improved:
            break
    if chosen:
        best = _make_plan(target, chosen, acc)

    return best


def _make_plan(target: NutritionTarget, items: list[FoodItem], acc: dict) -> MealPlan:
    return MealPlan(
        target=target,
        items=tuple(items),
        total_kcal=acc["kcal"],
        total_protein=acc["protein"],
        total_fat=acc["fat"],
        total_carb=acc["carb"],
        total_sodium=acc["sodium"],
        total_calcium=acc["calcium"],
    )


# ============================================================================
# 餐品分类推断（基于名称，用于可选类别过滤）
# ============================================================================

_BURGER_KEYS = ("堡", "满分", "卷", "鸡排", "鸡球", "鱼", "鸡翅", "鸡腿", "里脊", "香肠", "叠叠",
                "脆汁鸡", "V翅", "双翅", "鸡块", "牛堡", "安格斯", "香鸡", "巨无霸",
                # 限定套餐名（程序员节谐音款）归主菜类
                "蜜汁", "多肉", "满满", "支撑")
_SIDE_KEYS = ("薯条", "玉米杯", "脆薯饼", "油条", "派", "冰淇淋", "新地", "麦旋风", "拉明顿", "苹果片",
              "麦乐鸡", "粥")
_DRINK_KEYS = ("可乐", "雪碧", "咖啡", "茶", "奶", "豆浆", "果汁", "朱古力", "雪冰", "美式", "玛奇朵",
               "卡布奇诺", "怡泉", "纯悦", "浓缩", "燕麦", "黑巧", "鲜萃", "阿芙佳朵",
               "阳光橙", "爆珠", "美汁源", "橙橙")

# 用于饮品去重的基础名（去掉冷热/大小前缀后的核心名）。
# 顺序有意义：更具体的词排前面，避免"燕麦奶铁"被"奶铁"截获。
_DRINK_BASE_ORDER = [
    ("鲜萃咖啡", "鲜萃咖啡"),
    ("焦糖玛奇朵", "玛奇朵"),
    ("燕麦奶铁", "燕麦奶铁"),
    ("燕麦奶", "燕麦奶"),
    ("伯爵红茶", "红茶"),
    ("阿芙佳朵", "阿芙佳朵"),
    ("卡布奇诺", "卡布奇诺"),
    ("玛奇朵", "玛奇朵"),
    ("美式", "美式咖啡"),
    ("拿铁", "拿铁"),
    ("奶铁", "奶铁"),
    ("可乐", "可乐"),
    ("雪碧", "雪碧"),
    ("红茶", "红茶"),
    ("黑巧", "黑巧"),
    ("抹茶", "抹茶"),
    ("牛奶", "牛奶"),
    ("豆浆", "豆浆"),
    ("苹果汁", "苹果汁"),
    ("怡泉", "怡泉"),
    ("朱古力", "朱古力"),
    ("雪冰", "雪冰"),
]


def _drink_base(name: str) -> str:
    # 盒装包装饮品（如纯牛奶（盒装））与现制饮品视为不同商品，不参与冷热/规格去重
    if "盒装" in name:
        return ""
    for k, v in _DRINK_BASE_ORDER:
        if k in name:
            return v
    return ""


def infer_category(name: str) -> str:
    if any(k in name for k in _DRINK_KEYS):
        return "drink"
    if any(k in name for k in _BURGER_KEYS):
        return "burger"
    if any(k in name for k in _SIDE_KEYS):
        return "side"
    return "unknown"


# ============================================================================
# 忌口 / 过敏原过滤
# ============================================================================

# 忌口/过敏原名 → 餐品名关键词（含任一关键词即排除）。
# MCP 营养数据不含过敏原字段，故基于餐品名做启发式匹配。
ALLERGEN_KEYWORDS = {
    "辣": ["辣"],
    "鱼": ["鱼", "鳕鱼"],
    "牛肉": ["牛堡", "安格斯"],
    "猪肉": ["猪", "培根", "火腿", "烟肉", "香肠"],
    "鸡肉": ["鸡"],
    "蛋": ["蛋"],
    "乳糖": ["奶", "牛奶", "奶铁", "朱古力", "新地", "麦旋风", "冰淇淋", "雪冰", "拉明顿"],
    "海鲜": ["鱼", "鳕鱼", "虾"],
    "麸质": ["堡", "满分", "卷", "油条"],
}


def filter_foods(foods: Iterable[FoodItem], restrictions: list[str]) -> list[FoodItem]:
    """按忌口/过敏原名列表过滤餐品。

    Args:
        foods: 候选餐品
        restrictions: 忌口名列表（如 ["辣", "鱼", "牛肉"]）；未识别的名字按字面作关键词
    """
    if not restrictions:
        return list(foods)
    words: set[str] = set()
    for r in restrictions:
        words.update(ALLERGEN_KEYWORDS.get(r, [r]))
    return [f for f in foods if not any(w in f.product_name for w in words)]


# ============================================================================
# 全天多餐规划
# ============================================================================


def plan_daily(
    foods: Iterable[FoodItem],
    mode: str,
    total_kcal: float,
    exclude: Optional[list[str]] = None,
    meal_names: tuple[str, ...] = ("早餐", "午餐", "晚餐"),
    ratios: tuple[float, ...] = (0.3, 0.4, 0.3),
    max_items: int = 4,
    max_per_category: Optional[int] = 2,
) -> dict:
    """全天多餐规划：按比例拆分总预算，逐餐拼配（跨餐不重复同一餐品）。

    Returns:
        {餐名: MealPlan}，某餐无法拼出时为 None
    """
    plans: dict = {}
    used: set[str] = set()
    for name, ratio in zip(meal_names, ratios):
        target = build_target(mode, total_kcal * ratio)
        candidates = [f for f in foods if f.product_name not in used]
        plan = plan_meal(candidates, target, max_items=max_items,
                         max_per_category=max_per_category, exclude=exclude)
        plans[name] = plan
        if plan:
            for it in plan.items:
                used.add(it.product_name)
    return plans


# ============================================================================
# MCP 餐品数据解析
# ============================================================================


def parse_foods_from_mcp(raw: str) -> list[FoodItem]:
    """解析 list-nutrition-foods 返回的文本数据（形如 "name,desc,kj,kcal,protein,..."）。

    该工具返回格式为 "{productName,nutritionDescription,energyKj,energyKcal,protein,...}"
    每行一个餐品，字段以逗号分隔。
    """
    foods: list[FoodItem] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 9:
            continue
        name = parts[0]
        try:
            vals = [float(p) if p and p != "null" else 0.0 for p in parts[2:9]]
        except ValueError:
            continue
        # parts[2:9] = energyKj, energyKcal, protein, fat, carbohydrate, sodium, calcium
        kcal = vals[1]
        protein = vals[2]
        fat = vals[3]
        carb = vals[4]
        sodium = vals[5]
        calcium = vals[6]
        if kcal <= 0 and protein <= 0 and fat <= 0 and carb <= 0:
            continue
        foods.append(
            FoodItem(
                product_name=name,
                energy_kcal=kcal,
                protein=protein,
                fat=fat,
                carbohydrate=carb,
                sodium=sodium,
                calcium=calcium,
                category=infer_category(name),
            )
        )
    return foods


def load_snapshot(path: Optional[str] = None) -> list[FoodItem]:
    """加载离线营养快照（JSON），作为无 MCP 环境的兜底。"""
    import os
    if path is None:
        path = os.path.join(os.path.dirname(__file__), "nutrition_snapshot.json")
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [FoodItem(**{**d, "category": infer_category(d["product_name"])})
            for d in raw]
