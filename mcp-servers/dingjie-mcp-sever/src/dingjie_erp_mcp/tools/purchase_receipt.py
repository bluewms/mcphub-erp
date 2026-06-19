"""采购入库工具 (PURCHASE_RECEIPT)

提供 7 个工具：
- query_purchase_receipts: 查询采购入库单列表
- read_purchase_receipt: 查看采购入库单详情
- create_purchase_receipt: 创建采购入库单
- approve_purchase_receipt: 审核采购入库单
- disapprove_purchase_receipt: 撤销审核采购入库单
- delete_purchase_receipt: 删除采购入库单
- invalid_purchase_receipt: 作废采购入库单
"""

import json
import logging

logger = logging.getLogger(__name__)


def register_purchase_receipt_tools(mcp, get_client, is_readonly):
    """注册采购入库相关工具"""

    @mcp.tool()
    def query_purchase_receipts(
        doc_no: str = "",
        supplier_no: str = "",
        start_date: str = "",
        end_date: str = "",
        limit: int = 100,
        offset: int = 0,
    ) -> str:
        """查询鼎捷 ERP 采购入库单列表

        支持按单号、供应商、日期范围筛选，返回采购入库单列表。

        Args:
            doc_no: 单号（模糊匹配）
            supplier_no: 供应商编号
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            limit: 返回行数上限，默认100
            offset: 跳过行数，用于翻页
        """
        client = get_client()
        filters: dict = {"limit": limit, "offset": offset}
        if doc_no:
            filters["doc_no"] = doc_no
        if supplier_no:
            filters["supplier_no"] = supplier_no
        if start_date:
            filters["start_date"] = start_date
        if end_date:
            filters["end_date"] = end_date

        try:
            result = client.query_purchase_receipts(filters)
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    @mcp.tool()
    def read_purchase_receipt(doc_no: str) -> str:
        """查看鼎捷 ERP 采购入库单详情

        通过单号查看采购入库单的所有字段信息，包括单身明细。

        Args:
            doc_no: 单号
        """
        client = get_client()
        try:
            result = client.read_purchase_receipt(doc_no)
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    @mcp.tool()
    def create_purchase_receipt(
        om_site_id: str,
        supplier_no: str,
        doc_type_no: str = "",
        doc_date: str = "",
        responsibility_employee_no: str = "",
        department_no: str = "",
        remark: str = "",
        details: str = "",
    ) -> str:
        """创建鼎捷 ERP 采购入库单

        Args:
            om_site_id: 营运据点编号
            supplier_no: 供应商编号
            doc_type_no: 单据类型编号
            doc_date: 单据日期 (YYYY-MM-DD)
            responsibility_employee_no: 负责人员编号
            department_no: 部门编号
            remark: 备注
            details: 明细 JSON 数组，如:
                [{"business_qty": 100, "warehouse_no": "WH01", "item_no": "MAT001"}]
        """
        if is_readonly():
            return json.dumps({"error": "只读模式：写入操作已禁用"}, ensure_ascii=False)

        client = get_client()
        data: dict = {
            "om_site_id": om_site_id,
            "supplier_no": supplier_no,
        }
        if doc_type_no:
            data["doc_type_no"] = doc_type_no
        if doc_date:
            data["doc_date"] = doc_date
        if responsibility_employee_no:
            data["responsibility_employee_no"] = responsibility_employee_no
        if department_no:
            data["department_no"] = department_no
        if remark:
            data["remark"] = remark
        if details:
            try:
                data["details"] = json.loads(details)
            except json.JSONDecodeError as e:
                return json.dumps({"error": f"details JSON 格式错误: {e}"}, ensure_ascii=False)

        try:
            result = client.create_purchase_receipt(data)
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    @mcp.tool()
    def approve_purchase_receipt(doc_no: str) -> str:
        """审核鼎捷 ERP 采购入库单

        Args:
            doc_no: 单号
        """
        if is_readonly():
            return json.dumps({"error": "只读模式：写入操作已禁用"}, ensure_ascii=False)

        client = get_client()
        try:
            result = client.approve_purchase_receipt(doc_no)
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    @mcp.tool()
    def disapprove_purchase_receipt(doc_no: str) -> str:
        """撤销审核鼎捷 ERP 采购入库单

        Args:
            doc_no: 单号
        """
        if is_readonly():
            return json.dumps({"error": "只读模式：写入操作已禁用"}, ensure_ascii=False)

        client = get_client()
        try:
            result = client.disapprove_purchase_receipt(doc_no)
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    @mcp.tool()
    def delete_purchase_receipt(doc_no: str) -> str:
        """删除鼎捷 ERP 采购入库单

        注意：删除操作不可撤销，请谨慎使用。

        Args:
            doc_no: 单号
        """
        if is_readonly():
            return json.dumps({"error": "只读模式：写入操作已禁用"}, ensure_ascii=False)

        client = get_client()
        try:
            result = client.delete_purchase_receipt(doc_no)
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    @mcp.tool()
    def invalid_purchase_receipt(doc_no: str) -> str:
        """作废鼎捷 ERP 采购入库单

        Args:
            doc_no: 单号
        """
        if is_readonly():
            return json.dumps({"error": "只读模式：写入操作已禁用"}, ensure_ascii=False)

        client = get_client()
        try:
            result = client.invalid_purchase_receipt(doc_no)
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
