#!/usr/bin/env python3
"""麦当劳营养王国 —— Web 后端服务（纯标准库实现，无第三方依赖）。

启动后：
- 访问 http://127.0.0.1:8765/ 打开 Web 界面
- /api/foods 返回营养数据（实时 MCP 优先，离线快照兜底）

实时 MCP：配置环境变量 MCD_MCP_BASE_URL / MCD_MCP_AUTH_TOKEN 后，
后端会直连麦当劳 MCP 拉取最新营养数据；未配置或失败时自动降级为离线快照。
"""
from __future__ import annotations

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from http.server import BaseHTTPRequestHandler, HTTPServer  # noqa: E402

from core import load_snapshot, McDonaldsMCPClient  # noqa: E402

INDEX_HTML = os.path.join(HERE, "index.html")
PORT = int(os.environ.get("PORT", "8765"))


def get_foods():
    """获取营养数据：实时 MCP 优先，MCP 快照兜底。返回 (foods, source, snapshot_updated)。"""
    client = McDonaldsMCPClient()  # 从环境变量读 base_url / auth_token
    if client.base_url:
        try:
            foods = client.list_nutrition_foods()
            if foods:
                return [f.to_dict() for f in foods], "mcp", ""
        except Exception:
            pass
    snapshot_path = os.path.join(ROOT, "core", "nutrition_snapshot.json")
    try:
        updated = time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(snapshot_path)))
    except OSError:
        updated = ""
    return [f.to_dict() for f in load_snapshot()], "snapshot", updated


def load_kingdom_snapshot():
    """读取「营养王国 · 潮玩宫」离线快照。"""
    path = os.path.join(ROOT, "core", "kingdom_snapshot.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _collect_kingdom_live(client):
    """实时聚合潮玩宫数据（mall/lottery/account/campaign）。

    需配置 MCD_MCP_BASE_URL / MCD_MCP_AUTH_TOKEN；任一工具失败则返回 None，
    由 get_kingdom 降级为离线快照。
    """
    def _list(x):
        d = x.get("data") if isinstance(x, dict) else None
        return d if isinstance(d, list) else []

    def _obj(x):
        d = x.get("data") if isinstance(x, dict) else None
        return d if isinstance(d, dict) else {}

    mall_coupons = _list(client.mall_points_products("1>4"))
    mall_physical = _list(client.mall_points_products("2,2>8"))
    mall_party = _list(client.mall_points_products("1>6>20,1>6>21,1>6>22,1>6>25,1>6>34"))
    lottery = _obj(client.query_lottery_info())
    account = _obj(client.query_my_account())
    campaign = _list(client.campaign_calendar())
    coupons = _list(client.available_coupons())

    if not (mall_coupons or mall_physical or mall_party):
        return None  # 无商城数据，视为实时不可用，降级快照

    return {
        "account": account,
        "mall": {
            "coupons": mall_coupons,
            "physical": mall_physical,
            "party": mall_party,
        },
        "lottery": lottery,
        "coupons": coupons,
        "campaign": campaign,
    }


def get_kingdom():
    """获取潮玩宫数据：实时 MCP 优先，离线快照兜底。返回 (data, source)。"""
    client = McDonaldsMCPClient()
    if client.base_url:
        try:
            data = _collect_kingdom_live(client)
            if data:
                return data, "mcp"
        except Exception:
            pass
    return load_kingdom_snapshot(), "snapshot"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/foods":
            foods, source, snapshot_updated = get_foods()
            body = json.dumps({"source": source, "foods": foods,
                               "snapshot_updated": snapshot_updated},
                              ensure_ascii=False).encode("utf-8")
            self._respond(200, "application/json; charset=utf-8", body)
        elif self.path == "/api/kingdom":
            kingdom, source = get_kingdom()
            body = json.dumps({"source": source, "kingdom": kingdom},
                              ensure_ascii=False).encode("utf-8")
            self._respond(200, "application/json; charset=utf-8", body)
        elif self.path in ("/", "/index.html"):
            try:
                with open(INDEX_HTML, "r", encoding="utf-8") as f:
                    body = f.read().encode("utf-8")
                self._respond(200, "text/html; charset=utf-8", body)
            except OSError:
                self._respond(404, "text/plain; charset=utf-8", b"index.html not found")
        else:
            self._respond(404, "text/plain; charset=utf-8", b"Not Found")

    def _respond(self, status: int, ctype: str, body: bytes):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def main():
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    print("麦当劳营养王国 后端已启动")
    print(f"  Web 界面: http://127.0.0.1:{PORT}/")
    print(f"  营养数据: http://127.0.0.1:{PORT}/api/foods")
    print(f"  潮玩宫:   http://127.0.0.1:{PORT}/api/kingdom")
    print("  （配置 MCD_MCP_BASE_URL / MCD_MCP_AUTH_TOKEN 后自动切换实时 MCP）")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == "__main__":
    main()
