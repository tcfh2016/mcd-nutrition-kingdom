#!/usr/bin/env python3
"""麦当劳营养点餐 Agent —— Web 后端服务（纯标准库实现，无第三方依赖）。

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


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/foods":
            foods, source, snapshot_updated = get_foods()
            body = json.dumps({"source": source, "foods": foods,
                               "snapshot_updated": snapshot_updated},
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
    print("麦当劳营养点餐 Agent 后端已启动")
    print(f"  Web 界面: http://127.0.0.1:{PORT}/")
    print(f"  营养数据: http://127.0.0.1:{PORT}/api/foods")
    print("  （配置 MCD_MCP_BASE_URL / MCD_MCP_AUTH_TOKEN 后自动切换实时 MCP）")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == "__main__":
    main()
