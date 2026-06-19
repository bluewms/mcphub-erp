"""MCP 工具注册汇总。"""

from dataclasses import dataclass

from .essential import register_essential_tools
from .profile import register_profile_tools
from .query import register_query_tools
from .read import register_read_tools
from .write import register_write_tools


@dataclass
class ToolContext:
    """工具注册上下文，传递给每个 register 函数。

    Attributes:
        get_sdk: 获取 SDK 实例的函数
        is_readonly: 检查是否只读模式的函数
        ok: 构造成功返回的函数
        err: 构造错误返回的函数
        server_name: 服务器名称
        paginate_bill: 内部翻页原语（_paginate_bill）
        stream_to_file: 流式写入原语（_stream_to_file_handle）
    """

    get_sdk: callable
    is_readonly: callable
    ok: callable
    err: callable
    server_name: str
    paginate_bill: callable = None
    stream_to_file: callable = None


def register_all_tools(mcp, ctx: ToolContext):
    """注册所有 MCP 工具。"""
    register_essential_tools(mcp, ctx)
    register_profile_tools(mcp, ctx)
    register_query_tools(mcp, ctx)
    register_read_tools(mcp, ctx)
    register_write_tools(mcp, ctx)
