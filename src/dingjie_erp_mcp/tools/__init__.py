"""MCP 工具注册

借鉴 muk_mcp 的模块化设计：
- 每个业务对象一个文件
- 统一的输入输出格式
- 只读模式检查
"""

from dingjie_erp_mcp.tools.purchase_receipt import register_purchase_receipt_tools
from dingjie_erp_mcp.tools.sales_issue import register_sales_issue_tools
from dingjie_erp_mcp.tools.material import register_material_tools


def register_all_tools(mcp, get_client, is_readonly):
    """注册所有 MCP 工具

    Args:
        mcp: FastMCP 实例
        get_client: 获取 DingjieClient 的函数
        is_readonly: 检查是否只读模式的函数
    """
    register_purchase_receipt_tools(mcp, get_client, is_readonly)
    register_sales_issue_tools(mcp, get_client, is_readonly)
    register_material_tools(mcp, get_client, is_readonly)
