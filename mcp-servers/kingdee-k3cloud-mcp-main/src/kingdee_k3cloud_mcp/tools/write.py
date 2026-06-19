"""写入类工具：save_bill, submit_bill, audit_bill, unaudit_bill, delete_bill, execute_operation, push_bill。"""

import json

from kingdee_k3cloud_mcp.utils import WRITE_TOOL, DESTRUCTIVE_TOOL, _ids_data
from kingdee_k3cloud_mcp.tools import ToolContext

_ctx: ToolContext | None = None


def register_write_tools(mcp, ctx: ToolContext):
    """注册写入类工具。"""
    global _ctx
    _ctx = ctx
    mcp.tool(annotations=WRITE_TOOL)(save_bill)
    mcp.tool(annotations=WRITE_TOOL)(submit_bill)
    mcp.tool(annotations=WRITE_TOOL)(audit_bill)
    mcp.tool(annotations=WRITE_TOOL)(unaudit_bill)
    mcp.tool(annotations=DESTRUCTIVE_TOOL)(delete_bill)
    mcp.tool(annotations=WRITE_TOOL)(execute_operation)
    mcp.tool(annotations=WRITE_TOOL)(push_bill)


def save_bill(form_id: str, model_data: str) -> str:
    """保存金蝶云星空单据（新增或更新）。写入工具，只读模式下不可用。

    执行前建议先调用 preview_write 预览变更。

    Args:
        form_id: 表单ID。如 BD_MATERIAL、SAL_SaleOrder 等
        model_data: JSON格式的单据数据。示例（保存物料）：
            {"Model": {"FCreateOrgId": {"FNumber": "100"}, "FNumber": "MAT001", "FName": "物料名称"}}
            如果传入的JSON中没有"Model"键，会自动包装。
    """
    if _ctx.is_readonly():
        return _ctx.err("只读模式：写入操作已禁用")
    try:
        data = json.loads(model_data)
    except json.JSONDecodeError as e:
        return _ctx.err(f"model_data JSON 格式错误: {e}")
    if "Model" not in data:
        data = {"Model": data}
    try:
        return _ctx.ok(_ctx.get_sdk().Save(form_id, data))
    except Exception as e:
        return _ctx.err(str(e))


def submit_bill(
    form_id: str,
    numbers: str = "",
    ids: str = "",
) -> str:
    """提交金蝶云星空单据。写入工具，只读模式下不可用。

    Args:
        form_id: 表单ID。如 BD_MATERIAL、SAL_SaleOrder 等
        numbers: 单据编号，多个用逗号分隔。如 "MAT001,MAT002"
        ids: 单据内码ID，多个用逗号分隔（numbers 和 ids 二选一）
    """
    if _ctx.is_readonly():
        return _ctx.err("只读模式：写入操作已禁用")
    try:
        return _ctx.ok(_ctx.get_sdk().Submit(form_id, _ids_data(numbers, ids)))
    except Exception as e:
        return _ctx.err(str(e))


def audit_bill(
    form_id: str,
    numbers: str = "",
    ids: str = "",
) -> str:
    """审核金蝶云星空单据。写入工具，只读模式下不可用。

    Args:
        form_id: 表单ID。如 BD_MATERIAL、SAL_SaleOrder 等
        numbers: 单据编号，多个用逗号分隔。如 "MAT001,MAT002"
        ids: 单据内码ID，多个用逗号分隔（numbers 和 ids 二选一）
    """
    if _ctx.is_readonly():
        return _ctx.err("只读模式：写入操作已禁用")
    try:
        return _ctx.ok(_ctx.get_sdk().Audit(form_id, _ids_data(numbers, ids)))
    except Exception as e:
        return _ctx.err(str(e))


def unaudit_bill(
    form_id: str,
    numbers: str = "",
    ids: str = "",
) -> str:
    """反审核金蝶云星空单据。写入工具，只读模式下不可用。

    Args:
        form_id: 表单ID。如 BD_MATERIAL、SAL_SaleOrder 等
        numbers: 单据编号，多个用逗号分隔。如 "MAT001,MAT002"
        ids: 单据内码ID，多个用逗号分隔（numbers 和 ids 二选一）
    """
    if _ctx.is_readonly():
        return _ctx.err("只读模式：写入操作已禁用")
    try:
        return _ctx.ok(_ctx.get_sdk().UnAudit(form_id, _ids_data(numbers, ids)))
    except Exception as e:
        return _ctx.err(str(e))


def delete_bill(
    form_id: str,
    numbers: str = "",
    ids: str = "",
) -> str:
    """删除金蝶云星空单据。危险工具，只读模式下不可用。

    删除操作可能不可恢复，请谨慎使用。执行前建议先调用 preview_write 预览。

    Args:
        form_id: 表单ID。如 BD_MATERIAL、SAL_SaleOrder 等
        numbers: 单据编号，多个用逗号分隔。如 "MAT001,MAT002"
        ids: 单据内码ID，多个用逗号分隔（numbers 和 ids 二选一）
    """
    if _ctx.is_readonly():
        return _ctx.err("只读模式：写入操作已禁用")
    try:
        return _ctx.ok(_ctx.get_sdk().Delete(form_id, _ids_data(numbers, ids)))
    except Exception as e:
        return _ctx.err(str(e))


def execute_operation(
    form_id: str,
    op_number: str,
    numbers: str = "",
    ids: str = "",
) -> str:
    """执行金蝶云星空单据操作（禁用、反禁用等）。写入工具，只读模式下不可用。

    Args:
        form_id: 表单ID。如 BD_MATERIAL、SAL_SaleOrder 等
        op_number: 操作类型。常用值：Forbid(禁用)、Enable(反禁用)
        numbers: 单据编号，多个用逗号分隔
        ids: 单据内码ID，多个用逗号分隔（numbers 和 ids 二选一）
    """
    if _ctx.is_readonly():
        return _ctx.err("只读模式：写入操作已禁用")
    try:
        return _ctx.ok(_ctx.get_sdk().ExcuteOperation(form_id, op_number, _ids_data(numbers, ids)))
    except Exception as e:
        return _ctx.err(str(e))


def push_bill(
    form_id: str,
    numbers: str = "",
    ids: str = "",
    rule_id: str = "",
    target_form_id: str = "",
    target_org_id: str = "0",
    target_bill_type_id: str = "",
    is_enable_default_rule: str = "true",
    custom_params: str = "",
) -> str:
    """下推金蝶云星空单据（如销售订单下推发货通知单）。写入工具，只读模式下不可用。

    Args:
        form_id: 源单表单ID。如 SAL_SaleOrder、PUR_PurchaseOrder 等
        numbers: 源单编号，多个用逗号分隔
        ids: 源单内码ID，多个用逗号分隔（numbers 和 ids 二选一）
        rule_id: 转换规则ID（不填则用默认规则）
        target_form_id: 目标单据表单ID（不填则由规则决定）
        target_org_id: 目标组织ID，默认"0"
        target_bill_type_id: 目标单据类型ID（不填则用默认）
        is_enable_default_rule: 是否启用默认转换规则，默认"true"
        custom_params: 自定义参数JSON字符串。如 '{"FDATE":"2024-01-01"}'（不填则不传）
    """
    if _ctx.is_readonly():
        return _ctx.err("只读模式：写入操作已禁用")
    data = {
        "Numbers": [n.strip() for n in numbers.split(",") if n.strip()] if numbers else [],
        "Ids": ids,
        "RuleId": rule_id,
        "TargetFormId": target_form_id,
        "TargetOrgId": target_org_id,
        "TargetBillTypeId": target_bill_type_id,
        "IsEnableDefaultRule": is_enable_default_rule,
    }
    if custom_params:
        try:
            data["CustomParams"] = json.loads(custom_params)
        except json.JSONDecodeError as e:
            return _ctx.err(f"custom_params JSON 格式错误: {e}")
    try:
        return _ctx.ok(_ctx.get_sdk().Push(form_id, data))
    except Exception as e:
        return _ctx.err(str(e))
