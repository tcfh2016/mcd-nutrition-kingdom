# WorkBuddy 对话上下文（workbuddy.md）

> 本文件用于「麦当劳程序员创意开发大赛」的 WorkBuddy 专项奖励，记录本项目在腾讯 WorkBuddy 智能体中的使用方式与对话上下文。

## 项目与 WorkBuddy 的联动方式

「麦当劳营养王国」以 **WorkBuddy Skill** 形态集成到腾讯 WorkBuddy 智能体中，使 WorkBuddy 用户能够在自然语言对话中直接获得基于麦当劳 MCP 的营养点餐建议。

## 典型对话场景

**用户**：我今晚只想吃 500 千卡，帮我搭配一份麦当劳，少油一点。

**WorkBuddy（调用本 Skill）**：
1. 调用麦当劳 MCP `list-nutrition-foods` 获取 156 种餐品真实营养数据；
2. 解析为结构化 `FoodItem` 数据模型；
3. 按「控卡减脂」模式构建营养约束（总热量 ≤ 500 kcal、压低脂肪供能占比）；
4. 运行贪心 + 局部搜索引擎，拼配出满足约束的套餐；
5. 输出带完整营养标签的套餐建议。

**用户**：我最近在增肌，蛋白质要够，700 千卡左右。

**WorkBuddy**：切换到「增肌高蛋白」模式，保证蛋白质下限，优先高蛋白密度餐品……

## Skill 能力说明

- **能力名**：`mcd-nutrition-kingdom`（麦当劳营养王国）
- **触发词**：麦当劳、点餐、热量、控卡、减脂、增肌、控糖、营养搭配、麦麦套餐
- **输入**：营养模式（控卡/增肌/控糖）+ 热量预算（千卡）
- **输出**：满足约束的套餐 + 完整营养标签（热量/蛋白/脂肪/碳水/钠/钙）

## 真实使用 WorkBuddy 的说明

本项目通过以下方式**真实使用腾讯 WorkBuddy 智能体**：

1. 核心功能以 WorkBuddy Skill 形式交付，可直接在 WorkBuddy 对话中被调用；
2. Skill 通过 WorkBuddy 的 MCP 工具调用机制，真实调用麦当劳 MCP（`mcp__mcd-mcp__list-nutrition-foods`）；
3. 营养点餐引擎（`core/nutrition.py`）作为 Skill 的后端逻辑，被 WorkBuddy 智能体在对话流程中驱动执行。

## 对话上下文快照

- **开发环境**：腾讯 WorkBuddy（Windows，Python 3.13）
- **麦当劳 MCP 连通性验证**：`now-time-info` / `query-nearby-stores` / `query-my-account` / `list-nutrition-foods` / `query-lottery-info` 均已实测调用成功
- **营养数据规模**：`list-nutrition-foods` 返回 156 种餐品，含完整能量/蛋白/脂肪/碳水/钠/钙字段
