"""必备工具（规范要求）：health_check, query_metadata, preview_write。"""

import json
import os

from kingdee_k3cloud_mcp.utils import READ_ONLY_TOOL, PREVIEW_TOOL
from kingdee_k3cloud_mcp.tools import ToolContext

_ctx: ToolContext | None = None


def register_essential_tools(mcp, ctx: ToolContext):
    """注册必备工具。"""
    global _ctx
    _ctx = ctx
    mcp.tool(annotations=READ_ONLY_TOOL)(health_check)
    mcp.tool(annotations=READ_ONLY_TOOL)(query_metadata)
    mcp.tool(annotations=PREVIEW_TOOL)(preview_write)


def health_check() -> str:
    """检查金蝶 K3Cloud 连接状态和 Server 运行模式。只读工具。

    返回服务器地址、连接状态、当前模式等信息。
    """
    mode = "readonly" if _ctx.is_readonly() else "readwrite"
    try:
        sdk = _ctx.get_sdk()
        reachable = sdk is not None
        return _ctx.ok({
            "server": {
                "name": _ctx.server_name,
                "mode": mode,
            },
            "erp": {
                "reachable": reachable,
                "server_url": os.getenv("KD_SERVER_URL", ""),
                "acct_id": os.getenv("KD_ACCT_ID", ""),
            },
        })
    except Exception as e:
        return _ctx.err(f"健康检查失败: {e}")


def query_metadata(form_id: str) -> str:
    """查询金蝶云星空表单的元数据（字段结构信息）。只读工具。

    用于获取某个表单有哪些字段、字段类型等信息，便于构造查询和保存参数。

    Args:
        form_id: 表单ID。如 SAL_SaleOrder、PUR_PurchaseOrder、BD_MATERIAL 等
    """
    try:
        raw = _ctx.get_sdk().QueryBusinessInfo({"FormId": form_id})
        return _ctx.ok({"form_id": form_id, "raw": raw})
    except Exception as e:
        return _ctx.err(str(e))


def preview_write(
    form_id: str,
    operation: str,
    model_data: str = "",
    numbers: str = "",
) -> str:
    """预览写入操作，不实际修改 ERP 数据。只读工具。

    用于在执行写入（保存/提交/审核/删除等）前确认将要发生的变更。
    在只读模式下也可调用，因为它不修改数据。

    Args:
        form_id: 表单ID。如 BD_MATERIAL、SAL_SaleOrder 等
        operation: 操作类型，如 save、submit、audit、unaudit、delete、push
        model_data: 操作数据的 JSON 字符串（save 操作时传入）
        numbers: 单据编号（submit/audit/delete 等操作时传入）
    """
    valid_ops = {"save", "submit", "audit", "unaudit", "delete", "push"}
    if operation not in valid_ops:
        return _ctx.err(f"不支持的操作类型: {operation}，可选值: {', '.join(sorted(valid_ops))}")

    risk_map = {
        "save": "write",
        "submit": "write",
        "audit": "write",
        "unaudit": "write",
        "delete": "danger",
        "push": "write",
    }
    risk = risk_map.get(operation, "write")

    summary_parts = [f"将对 {form_id} 执行 {operation} 操作"]
    if numbers:
        summary_parts.append(f"目标单号: {numbers}")
    if model_data:
        try:
            parsed = json.loads(model_data)
            summary_parts.append(f"数据字段: {', '.join(parsed.keys()) if isinstance(parsed, dict) else '明细数据'}")
        except json.JSONDecodeError:
            summary_parts.append("数据字段: （JSON 格式无效）")

    warnings = []
    if risk == "danger":
        warnings.append("此操作可能不可恢复，请谨慎执行")
    if _ctx.is_readonly():
        warnings.append("当前为只读模式，实际写入操作将被拒绝")

    return _ctx.ok({
        "operation": operation,
        "object": form_id,
        "risk": risk,
        "summary": "，".join(summary_parts),
        "warnings": warnings,
    })
