# MCP 集成说明（MCP_INTEGRATION）

本文档说明「麦当劳营养王国」实际使用的麦当劳 MCP Server、Tool、调用流程与业务价值。

## 1. 使用的 MCP Server

- **Server 名称**：麦当劳 MCP（`mcd-mcp`）
- **用途**：提供麦当劳餐品营养、门店、下单、积分、营销等能力的结构化数据接口。

## 2. 实际使用的 Tool

| Tool | 用途 | 在本项目中的角色 |
|------|------|------------------|
| `list-nutrition-foods` | 获取常见餐品营养成分（能量/蛋白/脂肪/碳水/钠/钙） | **核心数据源**，为套餐拼配提供全部候选餐品 |
| `query-nearby-stores` | 查询附近可点餐门店 | 全链路：定位门店，获取 storeCode |
| `query-meals` | 查询门店可下单餐品列表（含 code + 价格） | 全链路：将营养餐品映射到可下单商品 |
| `calculate-price` | 计算商品价格（含优惠，返回 takeWayList） | 全链路：算价并获取下单所需的 takeWayCode |
| `create-order` | 创建订单 | 全链路：最终下单（需用户确认） |
| `query-order` | 查询订单状态 | 全链路：下单后跟踪支付/配送状态 |
| `query-my-account` | 查询积分账户 | **潮玩宫**：积分账户卡片（可用/累计/过期积分） |
| `mall-points-products` | 查询积分商城可兑换商品（餐品券/实物/周边/派对） | **潮玩宫**：商城橱窗三分类（积分兑餐品券、实物周边、派对体验） |
| `query-lottery-info` | 查看积分抽奖活动与奖品 | **潮玩宫**：积分抽奖区（单次积分 + 奖品列表） |
| `query-my-prizes` | 查询抽奖获得的奖品 | **潮玩宫**：（规划）我的奖品 |
| `campaign-calendar` | 查询营销活动日历 | **潮玩宫/活动宫**：当季联名/活动速递横幅 |
| `available-coupons` | 查询可领取的优惠券（麦麦省） | **活动宫**：优惠券一键领取 |
| `query-store-coupons` | 查询门店可用优惠券 | 全链路：点餐省钱优化 |
| `query-promotions` | 查询团餐促销规则（满减/满折） | **活动宫**：企业团餐场景（beType=6） |
| `query-meal-assistance` | 查询助餐服务 | **活动宫**：企业团餐场景 |
| `delivery-query-stores` | 查询外送门店 | **活动宫**：外送场景 |
| `delivery-query-addresses` | 查询收货地址 | **活动宫**：外送地址管理 |

> v1 已真实调用 `list-nutrition-foods` 完成营养拼配；v2 已打通「营养 → 门店 → 餐品映射 → 算价 → 下单」全链路（下单为副作用操作，需用户确认）；v3「潮玩宫」已基于积分商城 / 抽奖 / 活动日历工具构建积分乐园（读链路落地，兑换/抽奖为副作用操作需确认）；v3「许愿宫」为前端语义层——将自然语言愿望解析为营养约束（复用 `list-nutrition-foods` 拼配实现），无法实现的愿望本地收集（愿望池）导出转达，派对类愿望复用 `mall-points-products` 派对数据引导预订；v3「活动宫」基于 `campaign-calendar` + `available-coupons` + `mall-points-products` 构建联名速递（活动日历 + 优惠券领取 + 派对入口）。

## 3. 调用流程

### 3.1 营养拼配（v1 核心）

```
用户输入（模式 + 热量预算）
        │
        ▼
┌─────────────────────────────┐
│  McDonaldsMCPClient         │
│  .list_nutrition_foods()    │  ──► 调用 mcp__mcd-mcp__list-nutrition-foods
└─────────────────────────────┘
        │  返回 156 种餐品营养数据
        ▼
┌─────────────────────────────┐
│  core.nutrition             │
│  parse_foods_from_mcp()     │  ──► 解析为 FoodItem 数据模型
│  build_target(mode, kcal)   │  ──► 构建多模式营养约束
│  plan_meal(...)             │  ──► 贪心+局部搜索 拼配套餐
└─────────────────────────────┘
        │
        ▼
   套餐建议（含完整营养标签）
```

### 3.2 全链路下单（v2）

```
营养套餐（3.1 输出）
        │
        ▼
① query-nearby-stores ──► 定位门店 storeCode
        │
        ▼
② query-meals ──► 门店可下单商品（code + 价格）
        │
        ▼
③ map_food_to_product ──► 营养餐品名 → productCode（模糊匹配）
        │
        ▼
④ calculate-price ──► 总价 + takeWayCode
        │
        ▼
⑤ create-order ──► 下单（需用户确认，副作用操作）
        │
        ▼
⑥ query-order ──► 跟踪订单状态
```

### 3.3 双运行环境适配

`core/mcp_client.py` 中的 `McDonaldsMCPClient` 支持两种 MCP 调用方式，共用同一核心逻辑：

1. **WorkBuddy 环境**：通过 `set_defer_caller()` 注入 WorkBuddy 的 MCP 工具调用器，实际调用 `mcp__mcd-mcp__*`；
2. **独立 CLI 环境**：通过环境变量 `MCD_MCP_BASE_URL` / `MCD_MCP_AUTH_TOKEN` 直连 MCP Server（JSON-RPC over HTTP）。

## 4. 业务价值

- **把"健康点餐"变成可量化动作**：利用 MCP 提供的结构化营养数据，将用户模糊的"想吃得健康"转化为可执行的热量/宏量营养约束；
- **降低决策门槛**：用户无需手动查询每种餐品的热量，Agent 自动完成"候选筛选 → 约束求解 → 营养汇总"全流程；
- **真实数据驱动**：所有营养结论均来自麦当劳官方 MCP，而非人工臆测或第三方数据，结果可信、可复现。

## 5. 合规说明

- 本项目仅**读取**麦当劳 MCP 的公开查询类接口（营养、门店、积分查询），不涉及用户敏感数据的越权访问；
- MCP 凭证通过环境变量注入，仓库中不含任何真实凭证（见 `mcp-config.example.json`）；
- 离线营养快照（`core/nutrition_snapshot.json`）为 `list-nutrition-foods` 返回数据的全量静态快照（156 种餐品），仅用于无 MCP 环境的演示，不影响"真实使用 MCP"这一核心事实。
