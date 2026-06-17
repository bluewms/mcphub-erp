"""销货出库工具 (SALES_ISSUE)

提供 7 个工具：
- query_sales_issues: 查询销货出库单列表
- read_sales_issue: 查看销货出库单详情
- create_sales_issue: 创建销货出库单
- approve_sales_issue: 审核销货出库单
- disapprove_sales_issue: 撤销审核销货出库单
- delete_sales_issue: 删除销货出库单
- invalid_sales_issue: 作废销货出库单
"""

import json
import logging

logger = logging.getLogger(__name__)


def register_sales_issue_tools(mcp, get_client, is_readonly):
    """注册销货出库相关工具"""

    @mcp.tool()
    def query_sales_issues(
        doc_no: str = "",
        customer_no: str = "",
        start_date: str = "",
        end_date: str = "",
        limit: int = 100,
        offset: int = 0,
    ) -> str:
        """查询鼎捷 ERP 销货出库单列表

        支持按单号、客户、日期范围筛选，返回销货出库单列表。

        Args:
            doc_no: 单号（模糊匹配）
            customer_no: 客户编号
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            limit: 返回行数上限，默认100
            offset: 跳过行数，用于翻页
        """
        client = get_client()
        filters: dict = {"limit": limit, "offset": offset}
        if doc_no:
            filters["doc_no"] = doc_no
        if customer_no:
            filters["customer_no"] = customer_no
        if start_date:
            filters["start_date"] = start_date
        if end_date:
            filters["end_date"] = end_date

        try:
            result = client.query_sales_issues(filters)
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    @mcp.tool()
    def read_sales_issue(doc_no: str) -> str:
        """查看鼎捷 ERP 销货出库单详情

        通过单号查看销货出库单的所有字段信息，包括单身明细。

        Args:
            doc_no: 单号
        """
        client = get_client()
        try:
            result = client.read_sales_issue(doc_no)
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    @mcp.tool()
    def create_sales_issue(
        om_site_id: str,
        customer_no: str,
        doc_type_no: str = "",
        doc_date: str = "",
        employee_no: str = "",
        administration_unit_no: str = "",
        remark: str = "",
        details: str = "",
    ) -> str:
        """创建鼎捷 ERP 销货出库单

        Args:
            om_site_id: 营运据点编号
            customer_no: 客户编号
            doc_type_no: 单据类型编号
            doc_date: 单据日期 (YYYY-MM-DD)
            employee_no: 仓管员编号
            administration_unit_no: 仓管部门编号
            remark: 备注
            details: 明细 JSON 数组，如:
                [{"business_qty": 50, "warehouse_no": "WH01"}]
        """
        if is_readonly():
            return json.dumps({"error": "只读模式：写入操作已禁用"}, ensure_ascii=False)

        client = get_client()
        data: dict = {
            "om_site_id": om_site_id,
            "customer_no": customer_no,
        }
        if doc_type_no:
            data["doc_type_no"] = doc_type_no
        if doc_date:
            data["doc_date"] = doc_date
        if employee_no:
            data["employee_no"] = employee_no
        if administration_unit_no:
            data["administration_unit_no"] = administration_unit_no
        if remark:
            data["remark"] = remark
        if details:
            try:
                data["details"] = json.loads(details)
            except json.JSONDecodeError as e:
                return json.dumps({"error": f"details JSON 格式错误: {e}"}, ensure_ascii=False)

        try:
            result = client.create_sales_issue(data)
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    @mcp.tool()
    def approve_sales_issue(doc_no: str) -> str:
        """审核鼎捷 ERP 销货出库单

        Args:
            doc_no: 单号
        """
        if is_readonly():
            return json.dumps({"error": "只读模式：写入操作已禁用"}, ensure_ascii=False)

        client = get_client()
        try:
            result = client.approve_sales_issue(doc_no)
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    @mcp.tool()
    def disapprove_sales_issue(doc_no: str) -> str:
        """撤销审核鼎捷 ERP 销货出库单

        Args:
            doc_no: 单号
        """
        if is_readonly():
            return json.dumps({"error": "只读模式：写入操作已禁用"}, ensure_ascii=False)

        client = get_client()
        try:
            result = client.disapprove_sales_issue(doc_no)
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    @mcp.tool()
    def delete_sales_issue(doc_no: str) -> str:
        """删除鼎捷 ERP 销货出库单

        注意：删除操作不可撤销，请谨慎使用。

        Args:
            doc_no: 单号
        """
        if is_readonly():
            return json.dumps({"error": "只读模式：写入操作已禁用"}, ensure_ascii=False)

        client = get_client()
        try:
            result = client.delete_sales_issue(doc_no)
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    @mcp.tool()
    def invalid_sales_issue(doc_no: str) -> str:
        """作废鼎捷 ERP 销货出库单

        Args:
            doc_no: 单号
        """
        if is_readonly():
            return json.dumps({"error": "只读模式：写入操作已禁用"}, ensure_ascii=False)

        client = get_client()
        try:
            result = client.invalid_sales_issue(doc_no)
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
