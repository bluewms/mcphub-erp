"""推荐工具：get_profile。"""

import os

from kingdee_k3cloud_mcp.utils import READ_ONLY_TOOL
from kingdee_k3cloud_mcp.tools import ToolContext

_ctx: ToolContext | None = None


def register_profile_tools(mcp, ctx: ToolContext):
    """注册配置信息工具。"""
    global _ctx
    _ctx = ctx
    mcp.tool(annotations=READ_ONLY_TOOL)(get_profile)


def get_profile() -> str:
    """获取金蝶 MCP Server 的身份和连接配置信息。只读工具。

    返回服务器名称、连接地址、账套、模式等。
    """
    return _ctx.ok({
        "server_name": _ctx.server_name,
        "system": "kingdee",
        "server_url": os.getenv("KD_SERVER_URL", ""),
        "acct_id": os.getenv("KD_ACCT_ID", ""),
        "username": os.getenv("KD_USERNAME", ""),
        "lcid": os.getenv("KD_LCID", "2052"),
        "mode": "readonly" if _ctx.is_readonly() else "readwrite",
    })
