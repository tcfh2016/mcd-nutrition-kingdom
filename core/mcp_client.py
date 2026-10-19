"""麦当劳 MCP 客户端封装。

负责与麦当劳 MCP（mcp__mcd-mcp__* 工具）交互，屏蔽底层调用细节。
运行于 WorkBuddy 时通过 DeferExecuteTool 调用 MCP 工具；
运行于独立 CLI 时，通过 HTTP/SSE 直连 MCP Server（配置见 mcp-config.example.json）。
"""
from __future__ import annotations

import json
import os
from typing import Any, Optional

from .nutrition import FoodItem, parse_foods_from_mcp


class McDonaldsMCPClient:
    """麦当劳 MCP 的轻量客户端。

    设计原则：
    - 真实调用 MCP 工具获取营养/门店/下单数据，不硬编码业务结果；
    - 支持两种运行环境：WorkBuddy（deferred tool）与独立 CLI（HTTP 直连）。
    """

    def __init__(self, base_url: Optional[str] = None, auth_token: Optional[str] = None):
        # 独立 CLI 环境：从环境变量读取，避免泄露凭证
        self.base_url = base_url or os.environ.get("MCD_MCP_BASE_URL", "")
        self.auth_token = auth_token or os.environ.get("MCD_MCP_AUTH_TOKEN", "")
        # WorkBuddy 环境：注入 DeferExecuteTool 调用器（由 skill 层传入）
        self._defer_caller = None

    def set_defer_caller(self, caller) -> None:
        """注入 WorkBuddy 的 DeferExecuteTool 调用函数。"""
        self._defer_caller = caller

    # ------------------------------------------------------------------
    # 营养数据
    # ------------------------------------------------------------------
    def list_nutrition_foods(self) -> list[FoodItem]:
        """获取麦当劳常见餐品营养数据（真实调用 MCP）。"""
        raw = self._call("mcp__mcd-mcp__list-nutrition-foods", {})
        if isinstance(raw, dict):
            # WorkBuddy 返回已解析的结构；尝试提取 data 字段文本
            data = raw.get("data", "")
            if isinstance(data, list):
                return [FoodItem(**f) for f in data]
            raw = data
        return parse_foods_from_mcp(str(raw))

    # ------------------------------------------------------------------
    # 门店
    # ------------------------------------------------------------------
    def query_nearby_stores(self, city: str, keyword: str, be_type: int = 1) -> Any:
        return self._call("mcp__mcd-mcp__query-nearby-stores", {
            "searchType": 2, "city": city, "keyword": keyword, "beType": be_type,
        })

    # ------------------------------------------------------------------
    # 下单链路（v2）
    # ------------------------------------------------------------------
    def query_meals(self, store_code: str, order_type: int, be_type: int,
                    be_code: str = "", reservation_date: str = "") -> Any:
        params = {
            "storeCode": store_code,
            "orderType": order_type,
            "beType": be_type,
        }
        if be_code:
            params["beCode"] = be_code
        if reservation_date:
            params["reservationDate"] = reservation_date
        return self._call("mcp__mcd-mcp__query-meals", params)

    def calculate_price(self, store_code: str, order_type: int, be_type: int,
                        items: list, be_code: str = "",
                        reservation_date: str = "") -> Any:
        params = {
            "storeCode": store_code,
            "orderType": order_type,
            "beType": be_type,
            "items": items,
        }
        if be_code:
            params["beCode"] = be_code
        if reservation_date:
            params["reservationDate"] = reservation_date
        return self._call("mcp__mcd-mcp__calculate-price", params)

    # ------------------------------------------------------------------
    # 积分 / 营销
    # ------------------------------------------------------------------
    def query_my_account(self) -> Any:
        return self._call("mcp__mcd-mcp__query-my-account", {})

    def query_lottery_info(self) -> Any:
        return self._call("mcp__mcd-mcp__query-lottery-info", {})

    # ------------------------------------------------------------------
    # 底层调用分发
    # ------------------------------------------------------------------
    def _call(self, tool_name: str, params: dict) -> Any:
        if self._defer_caller is not None:
            return self._defer_caller(tool_name, params)
        if self.base_url:
            return self._call_http(tool_name, params)
        raise RuntimeError(
            "未配置 MCP 调用方式：请注入 defer_caller（WorkBuddy）"
            "或设置 MCD_MCP_BASE_URL / MCD_MCP_AUTH_TOKEN（独立 CLI）。"
        )

    def _call_http(self, tool_name: str, params: dict) -> Any:
        """通过 MCP 的 HTTP/SSE 端点直连（独立 CLI 场景）。"""
        import urllib.request

        # 精简的 JSON-RPC over HTTP 调用（适配标准 MCP streamable HTTP）
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": params},
        }
        req = urllib.request.Request(
            self.base_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.auth_token}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        # 提取 MCP 返回的 content[0].text
        result = body.get("result", {})
        content = result.get("content", [])
        if content and isinstance(content, list):
            text = content[0].get("text", "")
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text
        return result
