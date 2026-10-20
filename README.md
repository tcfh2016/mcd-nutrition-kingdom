<p align="center">
  <img src="docs/banner.png" width="100%" alt="McDonald's Nutrition Agent" />
</p>

<h1 align="center">麦当劳营养点餐 Agent</h1>
<p align="center"><strong>说出你的热量 / 营养目标，自动拼一份「吃得饱、营养对」的麦当劳套餐。</strong></p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License"></a>
  <a href="#"><img src="https://img.shields.io/badge/Python-3.9%2B-blue.svg" alt="Python"></a>
  <a href="MCP_INTEGRATION.md"><img src="https://img.shields.io/badge/Data-McDonald's%20MCP-da291c.svg" alt="McDonald's MCP"></a>
  <a href="workbuddy.md"><img src="https://img.shields.io/badge/WorkBuddy-Skill-5865F2.svg" alt="WorkBuddy Skill"></a>
</p>

---

## ✨ 这是什么？

身材管控期也想吃麦当劳？**麦当劳营养点餐 Agent** 会根据你的每日热量预算与营养目标，基于麦当劳 MCP 提供的 **156 种餐品真实营养数据**，自动拼配出满足约束的套餐，并给出完整的三大营养素（蛋白质 / 脂肪 / 碳水）与钠、钙明细。

支持三种营养模式：

| 模式 | 定位 | 约束目标 |
|------|------|----------|
| 🔥 `calorie` | 控卡减脂 | 总热量 ≤ 预算，压低脂肪供能占比 |
| 💪 `protein` | 增肌高蛋白 | 保证蛋白质摄入下限，高蛋白密度优先 |
| 🍬 `lowcarb` | 控糖低 GI | 限制碳水化合物总量 |

---

## 🎬 实际演练效果

> 以下是**现场实测输出**（营养数据来自麦当劳官方 MCP，非 mock）。

### ① 控卡减脂 —— "我今晚只想吃 500 千卡"

```bash
python cli/main.py --mode calorie --kcal 500
```

```text
【控卡减脂】套餐建议（预算 500 千卡）
----------------------------------------------
餐品                            热量    蛋白    脂肪    碳水
蜜汁快乐                         258    22     9    20
蜜汁BBQ风味薄皮脆汁鸡-琵琶腿             173    18     9     5
小杯玉米杯                         53     2     1     7
小杯鲜萃咖啡                        15     1     0     3
----------------------------------------------
合计                           499    43    19    35

钠含量：1271 mg   钙含量：61 mg
热量利用率：100%   ← 精准卡在预算线内
```

### ② 增肌高蛋白 —— "练后要补蛋白，700 千卡左右"

```bash
python cli/main.py --mode protein --kcal 700
```

```text
【增肌高蛋白】套餐建议（预算 700 千卡）
果然多肉                         478    36    17    44
蜜汁BBQ风味薄皮脆汁鸡-带骨里脊            152    20     5     6
小杯玉米杯                         53     2     1     7
大杯鲜萃咖啡                        13     1     0     0
合计                           696    59    23    57

蛋白质 59g  ← 一顿顶半日蛋白需求
```

### ③ 控糖低 GI —— "控糖期想吃麦当劳"

```bash
python cli/main.py --mode lowcarb --kcal 450
```

```text
【控糖低GI】套餐建议（预算 450 千卡）
蜜汁快乐                         258    22     9    20
蒜了吧黄油风味薄皮脆汁鸡-琵琶腿             164    19     6     6
冰美式大杯                         14     1     0     2
大杯鲜萃咖啡                        13     1     0     0
合计                           449    43    15    28

碳水仅 28g  ← 饮料全是黑咖啡/美式，零含糖
```

### ④ 忌口过滤 —— "我对海鲜过敏"

```bash
python cli/main.py --mode calorie --kcal 550 --exclude "鱼"
```

```text
未过滤 ：蜜汁快乐 + 儿童鱼排堡   + 冰美式小杯 + 大杯鲜萃咖啡
忌「鱼」：蜜汁快乐 + 火腿扒麦满分 + 冰美式大杯 + 小杯鲜萃咖啡
                          ↑ 含"鱼"的餐品被自动替换
```

> 支持的忌口 / 过敏原：`辣`、`鱼`、`牛肉`、`猪肉`、`鸡肉`、`蛋`、`乳糖`、`海鲜`、`麸质`。

### ⑤ 全链路下单 —— "帮我直接下单"

从营养建议到真实下单，一条链走完：

| 步骤 | MCP 工具 | 现场结果 |
|------|----------|----------|
| ① 营养拼配 | `list-nutrition-foods` | 猪柳蛋麦满分 + 小杯玉米杯 + 小杯鲜萃咖啡 = 455 kcal |
| ② 定位门店 | `query-nearby-stores` | 麦当劳杭州西湖银泰餐厅（`3330052`） |
| ③ 查询菜单 | `query-meals` | 早餐时段菜单 |
| ④ 名称映射 | `map_food_to_product` | 猪柳蛋麦满分→`5022`、玉米杯→`4437`、鲜萃咖啡→`520689` |
| ⑤ 算价 | `calculate-price` | **¥40.5**，取餐方式：堂食 / 外带 |
| ⑥ 下单 | `create-order` | 真实下单（**需用户确认**） |

---

## 🎯 目标用户

| 客户画像 | 痛点 | 对应能力 |
|----------|------|----------|
| 🏃 **健身 / 减脂人群** | 想精准控每餐热量与宏量营养 | `calorie` 控卡减脂 |
| 💪 **增肌人群** | 练后要保证蛋白质摄入 | `protein` 增肌高蛋白 |
| 🍬 **控糖 / 低碳饮食者** | 需要限制碳水、低 GI | `lowcarb` 控糖低 GI |
| 🧑‍💻 **普通上班族** | 没空算热量，想一键健康点餐 | `--daily` 全天三餐规划 |

---

## 🚀 特性

- ✅ **真实调用麦当劳 MCP** 获取餐品营养数据（`list-nutrition-foods`，156 种餐品）
- ✅ **多模式约束求解引擎**（贪心 + 局部搜索，自动去重与类别多样性控制，每类餐品 ≤ 2）
- ✅ **忌口 / 过敏原过滤**（辣、鱼、牛肉、猪肉、鸡肉、蛋、乳糖、海鲜、麸质）
- ✅ **全天多餐规划**（早 / 午 / 晚三餐按 30/40/30 比例拆配，跨餐不重复）
- ✅ **双形态交付**：WorkBuddy Skill + 独立 CLI，共用同一核心引擎
- ✅ **v2 全链路**：营养套餐 → 门店 → 可下单商品映射 → 算价 → 下单
- ✅ **离线快照兜底**，无 MCP 环境也能演示
- ✅ **完整营养标签**（热量 / 蛋白 / 脂肪 / 碳水 / 钠 / 钙）

---

## ⚡ 快速开始

### 依赖

- Python 3.9+（无第三方依赖）

### 方式一：独立 CLI

```bash
# 控卡减脂，预算 500 千卡
python cli/main.py --mode calorie --kcal 500

# 增肌高蛋白，预算 700 千卡
python cli/main.py --mode protein --kcal 700

# 控糖低GI，预算 450 千卡
python cli/main.py --mode lowcarb --kcal 450

# 忌口过滤：不吃辣、不吃鱼
python cli/main.py --mode calorie --kcal 500 --exclude "辣,鱼"

# 全天三餐规划：总预算 1800 千卡
python cli/main.py --mode calorie --kcal 1800 --daily

# 输出 JSON
python cli/main.py --mode calorie --kcal 500 --json
```

> 默认使用离线营养快照；如需实时调用麦当劳 MCP，配置环境变量后加 `--live`：
>
> ```bash
> export MCD_MCP_BASE_URL="https://your-mcp-endpoint"
> export MCD_MCP_AUTH_TOKEN="your-token"
> python cli/main.py --mode calorie --kcal 500 --live
> ```

### 方式二：Web 界面

**离线模式（零依赖）**：直接用浏览器打开 `web/index.html`，可视化选择营养模式、拖热量滑块，实时生成套餐建议（含营养素图表）。自包含单文件，无需后端。

**实时 MCP 模式**：启动后端，页面自动切换为麦当劳 MCP 实时数据：

```bash
export MCD_MCP_BASE_URL="https://your-mcp-endpoint"
export MCD_MCP_AUTH_TOKEN="your-token"
python web/server.py
# 浏览器访问 http://127.0.0.1:8765/
```

### 方式三：WorkBuddy Skill

在 WorkBuddy 对话中自然表达需求，Agent 会实时调用麦当劳 MCP 出方案：

> "我今晚只吃 500 千卡，帮我搭配一份麦当劳"

---

## 🏗️ 架构

```
mcd-nutrition-agent/
├── core/
│   ├── nutrition.py            # 核心引擎：数据模型 + 多模式约束求解
│   ├── mcp_client.py           # 麦当劳 MCP 客户端封装（双环境）
│   ├── order_flow.py           # v2 全链路：名称映射 + 下单编排
│   ├── nutrition_snapshot.json # 离线营养快照（156 餐品，兜底）
│   └── __init__.py
├── cli/
│   └── main.py                 # 独立 CLI（含 --order 全链路）
├── web/
│   ├── index.html              # Web 界面（单文件、自包含，可离线打开）
│   └── server.py               # Web 后端（实时 MCP 优先，快照兜底）
├── scripts/
│   └── refresh_snapshot.py     # 从 MCP 数据重新生成营养快照
├── demo/                       # 客户演示材料（脚本 + 说明页 + 结果卡）
├── tests/                      # 单元测试（unittest，零依赖，37 个用例）
├── skill/                      # WorkBuddy Skill（SKILL.md）
└── docs/                       # README 等文档素材
```

**核心设计原则**：营养计算与套餐拼配逻辑只写一次（`core/`），WorkBuddy Skill 与独立 CLI 均复用该核心，避免重复实现。

---

## 📄 License

[MIT](LICENSE)
