"""物料工具 (ITEM)

提供 2 个工具：
- query_materials: 查询物料列表
- read_material: 查看物料详情
"""

import json
import logging

logger = logging.getLogger(__name__)


def register_material_tools(mcp, get_client, is_readonly):
    """注册物料相关工具"""

    @mcp.tool()
    def query_materials(
        code: str = "",
        name: str = "",
        item_type: str = "",
        limit: int = 100,
        offset: int = 0,
    ) -> str:
        """查询鼎捷 ERP 物料列表

        支持按编码、名称、属性筛选，返回物料列表。

        Args:
            code: 产品编码（模糊匹配）
            name: 产品名称（模糊匹配）
            item_type: 品号属性
            limit: 返回行数上限，默认100
            offset: 跳过行数，用于翻页
        """
        client = get_client()
        filters: dict = {"limit": limit, "offset": offset}
        if code:
            filters["code"] = code
        if name:
            filters["name"] = name
        if item_type:
            filters["item_type"] = item_type

        try:
            result = client.query_materials(filters)
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    @mcp.tool()
    def read_material(code: str) -> str:
        """查看鼎捷 ERP 物料详情

        通过产品编码查看物料的所有字段信息。

        Args:
            code: 产品编码
        """
        client = get_client()
        try:
            result = client.read_material(code)
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
