"""读取类工具：view_bill。"""

from kingdee_k3cloud_mcp.utils import READ_ONLY_TOOL
from kingdee_k3cloud_mcp.tools import ToolContext

_ctx: ToolContext | None = None


def register_read_tools(mcp, ctx: ToolContext):
    """注册读取单条详情类工具。"""
    global _ctx
    _ctx = ctx
    mcp.tool(annotations=READ_ONLY_TOOL)(view_bill)


def view_bill(
    form_id: str,
    number: str = "",
    bill_id: str = "",
) -> str:
    """查看金蝶云星空单条记录的完整详情。只读工具。

    通过编号或内码查看单条记录的所有字段信息。

    Args:
        form_id: 表单ID。如 BD_MATERIAL、SAL_SaleOrder 等
        number: 单据编号。如 "MATERIAL001"（number 和 bill_id 二选一）
        bill_id: 单据内码ID（number 和 bill_id 二选一）
    """
    data = {"CreateOrgId": 0, "Number": number, "Id": bill_id, "IsSortBySeq": "false"}
    return _ctx.get_sdk().View(form_id, data)
