# 麦当劳营养点餐 Agent（McD Nutrition Agent）

> 一个基于麦当劳 MCP 能力的营养点餐智能体：说出你的热量/营养目标，自动帮你拼出一份「吃得饱、营养对」的麦当劳套餐。

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)

---

## 这是什么？

身材管控期也想吃麦当劳？**麦当劳营养点餐 Agent** 会根据你的每日热量预算与营养目标，基于麦当劳 MCP 提供的 **160+ 种餐品真实营养数据**，自动拼配出满足约束的套餐，并给出完整的三大营养素（蛋白质 / 脂肪 / 碳水）与钠、钙明细。

支持三种营养模式：

| 模式 | 定位 | 约束目标 |
|------|------|----------|
| `calorie` | 控卡减脂 | 总热量 ≤ 预算，脂肪供能占比压低 |
| `protein` | 增肌高蛋白 | 保证蛋白质摄入下限，高蛋白密度优先 |
| `lowcarb` | 控糖低GI | 限制碳水化合物总量 |

## 目标用户

- **健身 / 减脂人群**：想精准控制每一餐的热量与宏量营养；
- **控糖 / 低碳饮食者**：需要限制碳水摄入；
- **普通上班族**：没时间算热量，想一键得到一个"相对健康"的麦当劳搭配。

## 特性

- ✅ 真实调用麦当劳 MCP 获取餐品营养数据（`list-nutrition-foods`）
- ✅ 多模式约束求解引擎（贪心 + 局部搜索，自动去重与多样性控制）
- ✅ 双形态交付：**WorkBuddy Skill** + **独立 CLI**，共用同一核心引擎
- ✅ **v2 全链路**：营养套餐 → 门店 → 可下单商品映射 → 算价 → 下单
- ✅ 离线快照兜底，无 MCP 环境也能演示
- ✅ 输出完整营养标签（热量 / 蛋白 / 脂肪 / 碳水 / 钠 / 钙）

## 快速开始

### 依赖

- Python 3.9+

### 方式一：独立 CLI

```bash
# 控卡减脂，预算 500 千卡
python cli/main.py --mode calorie --kcal 500

# 增肌高蛋白，预算 700 千卡
python cli/main.py --mode protein --kcal 700

# 控糖低GI，预算 450 千卡
python cli/main.py --mode lowcarb --kcal 450

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

### 方式三：Web 界面（无需安装）

直接用浏览器打开 `web/index.html`，即可在可视化界面中选择营养模式、调整热量预算，实时生成套餐建议（含营养素图表）。

> 该页面为自包含单文件（内联营养数据 + Chart.js CDN），无需任何后端即可运行。

### 方式二：WorkBuddy Skill

1. 将本仓库安装为 WorkBuddy 技能（参考 `skill/` 目录）；
2. 在 WorkBuddy 对话中自然表达需求，例如：
   > "我今晚只吃 500 千卡，帮我搭配一份麦当劳"
3. Agent 会实时调用麦当劳 MCP 获取营养数据并给出套餐建议。

## 架构

```
mcd-nutrition-agent/
├── core/
│   ├── nutrition.py            # 核心引擎：数据模型 + 多模式约束求解
│   ├── mcp_client.py           # 麦当劳 MCP 客户端封装
│   ├── order_flow.py           # v2 全链路：名称映射 + 下单编排
│   ├── nutrition_snapshot.json # 离线营养快照（兜底）
│   └── __init__.py
├── cli/
│   └── main.py                 # 独立 CLI（壳 B，含 --order 全链路）
├── web/
│   └── index.html              # Web 界面（单文件、自包含）
├── skill/                       # WorkBuddy Skill（壳 A）
├── generate_web.py             # Web 界面生成脚本
├── README.md                    # 本文件
├── CONTEST_DECLARATION.md       # 参赛声明
├── MCP_INTEGRATION.md           # MCP 集成说明
├── mcp-config.example.json      # 脱敏 MCP 配置示例
└── workbuddy.md                 # WorkBuddy 专项奖励：对话上下文
```

**核心设计原则**：营养计算与套餐拼配逻辑只写一次（`core/`），WorkBuddy Skill 与独立 CLI 均复用该核心，避免重复实现。

## 使用示例

输入：`--mode calorie --kcal 500`（控卡减脂，预算 500 千卡）

输出：

```
【控卡减脂】套餐建议（预算 500 千卡）
----------------------------------------------
餐品                            热量    蛋白    脂肪    碳水
苹果片                           32     0     0     7
汉堡包                          248    13     8    29
皮蛋鸡肉粥                        133     6     3    20
小杯玉米杯                         53     2     1     7
----------------------------------------------
合计                           466    21    12    63

钠含量：1104 mg   钙含量：105 mg
热量利用率：93%
```

## 目标用户与价值

麦当劳常被贴上"高热量"标签，但实际菜单中存在大量可搭配的低热量、高蛋白选项。本项目通过 MCP 提供的结构化营养数据，把"健康点餐"从口号变成可执行、可量化的动作，让每一个想管住嘴的人都能在麦当劳找到适合自己的那一份。

## License

MIT
