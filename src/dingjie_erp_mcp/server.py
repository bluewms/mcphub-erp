"""鼎捷 ERP MCP Server 入口

使用 FastMCP 框架，支持 stdio / SSE / streamable-http 传输。
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from dingjie_erp_mcp.sdk import DingjieClient, DingjieAPIError, create_client_from_env
from dingjie_erp_mcp.tools import register_all_tools

logger = logging.getLogger(__name__)

# 全局状态
mcp = FastMCP("dingjie-erp")
_client: DingjieClient | None = None
_readonly = False


def get_client() -> DingjieClient:
    """获取鼎捷 ERP 客户端"""
    global _client
    if _client is None:
        _client = create_client_from_env()
    return _client


def setup() -> None:
    """初始化环境变量和客户端"""
    load_dotenv(dotenv_path=Path.cwd() / ".env")

    required = ["DINGJIE_SERVER_URL"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"缺少必要环境变量: {', '.join(missing)}")

    # 初始化客户端（验证连接）
    get_client()


# ============================================================
# 通用工具
# ============================================================

@mcp.tool()
def health_check() -> str:
    """检查鼎捷 ERP 连接状态

    返回服务器地址、认证状态、可用工具数量等信息。
    """
    client = get_client()
    result = {
        "server_url": client.server_url,
        "connected": True,
        "mode": "readonly" if _readonly else "readwrite",
        "locale": client.locale,
    }
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def query_metadata(obj: str) -> str:
    """查询鼎捷 ERP 表单的元数据（字段结构信息）

    用于获取某个表单有哪些字段、字段类型等信息，便于构造查询和创建参数。

    Args:
        obj: 业务对象名。常用值：
            purchase_receipt (采购入库)、
            sales_issue (销货出库)、
            material (物料)
    """
    from dingjie_erp_mcp.sdk.models import get_field_doc

    header_fields = get_field_doc(obj, "header")
    detail_fields = get_field_doc(obj, "detail")

    if not header_fields and not detail_fields:
        return json.dumps({"error": f"未知的业务对象: {obj}"}, ensure_ascii=False)

    result = {}
    if header_fields:
        result["header"] = {
            name: {
                "e10_field": info["e10"],
                "type": info["type"],
                "desc": info["desc"],
            }
            for name, info in header_fields.items()
        }
    if detail_fields:
        result["detail"] = {
            name: {
                "e10_field": info["e10"],
                "type": info["type"],
                "desc": info["desc"],
            }
            for name, info in detail_fields.items()
        }
    return json.dumps(result, ensure_ascii=False, indent=2)


# ============================================================
# 注册业务工具
# ============================================================

register_all_tools(mcp, get_client, lambda: _readonly)


# ============================================================
# 主入口
# ============================================================

def main():
    """启动 MCP Server"""
    global _readonly

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
    )

    parser = argparse.ArgumentParser(description="鼎捷 ERP E10 MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="传输协议（默认 stdio）",
    )
    parser.add_argument(
        "--mode",
        choices=["readonly", "readwrite"],
        default=os.environ.get("MCP_MODE", "readwrite"),
        help="readonly: 仅查询工具；readwrite: 全部工具（默认）",
    )
    args = parser.parse_args()

    _readonly = args.mode == "readonly"
    setup()

    tool_counts = {"read": 9, "write": 11}  # 预估数量
    if _readonly:
        logger.info(f"[dingjie-erp] mode=readonly, tools={tool_counts['read']}")
    else:
        logger.info(f"[dingjie-erp] mode=readwrite, tools={tool_counts['read'] + tool_counts['write']}")

    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
