"""鼎捷 ERP MCP Server 入口

使用 FastMCP 框架，支持 stdio / SSE / streamable-http 传输。
符合《企业管理软件 MCP 标准服务规范》。
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
_readonly = True  # 默认只读（规范要求）


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


def _ok(data: dict) -> str:
    """构造成功返回"""
    return json.dumps({"success": True, "data": data}, ensure_ascii=False, default=str)


def _err(msg: str) -> str:
    """构造错误返回"""
    return json.dumps({"success": False, "error": msg}, ensure_ascii=False)


# ============================================================
# 必备工具（规范要求）
# ============================================================

@mcp.tool()
def health_check() -> str:
    """检查鼎捷 ERP 连接状态和 Server 运行模式。

    只读工具。返回服务器地址、连接状态、当前模式等信息。
    """
    mode = "readonly" if _readonly else "readwrite"
    try:
        client = get_client()
        # 尝试调用一个轻量接口验证连接
        try:
            client.get_enterprise_sites()
            reachable = True
        except Exception:
            reachable = False

        return _ok({
            "server": {
                "name": "dingjie-erp",
                "mode": mode,
                "target_prod": client.target_prod,
            },
            "erp": {
                "reachable": reachable,
                "server_url": client.server_url,
                "ent_id": client.ent_id,
                "company_id": client.company_id,
            },
        })
    except Exception as e:
        return _err(f"健康检查失败: {e}")


@mcp.tool()
def query_metadata(obj: str) -> str:
    """查询鼎捷 ERP 表单的元数据（字段结构信息）。

    只读工具。用于获取某个表单有哪些字段、字段类型等信息，便于构造查询和创建参数。

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
        return _err(f"未知的业务对象: {obj}")

    result = {"object": obj}
    if header_fields:
        result["header"] = [
            {"name": name, "type": info["type"], "desc": info["desc"]}
            for name, info in header_fields.items()
        ]
    if detail_fields:
        result["detail"] = [
            {"name": name, "type": info["type"], "desc": info["desc"]}
            for name, info in detail_fields.items()
        ]
    return _ok(result)


@mcp.tool()
def preview_write(
    obj: str,
    operation: str,
    values: str = "",
    doc_no: str = "",
) -> str:
    """预览写入操作，不实际修改 ERP 数据。

    只读工具。用于在执行写入（创建/审核/删除等）前确认将要发生的变更。
    在只读模式下也可调用，因为它不修改数据。

    Args:
        obj: 业务对象名，如 purchase_receipt、sales_issue
        operation: 操作类型，如 create、approve、disapprove、delete、invalid
        values: 操作数据的 JSON 字符串（create 操作时传入）
        doc_no: 单号（approve/delete/invalid 等操作时传入）
    """
    valid_objects = {"purchase_receipt", "sales_issue", "material"}
    if obj not in valid_objects:
        return _err(f"不支持的业务对象: {obj}，可选值: {', '.join(sorted(valid_objects))}")

    valid_ops = {"create", "approve", "disapprove", "delete", "invalid"}
    if operation not in valid_ops:
        return _err(f"不支持的操作类型: {operation}，可选值: {', '.join(sorted(valid_ops))}")

    risk_map = {
        "create": "write",
        "approve": "write",
        "disapprove": "write",
        "delete": "danger",
        "invalid": "danger",
    }
    risk = risk_map.get(operation, "write")

    summary_parts = [f"将对 {obj} 执行 {operation} 操作"]
    if doc_no:
        summary_parts.append(f"目标单号: {doc_no}")
    if values:
        try:
            parsed = json.loads(values)
            summary_parts.append(f"数据字段: {', '.join(parsed.keys()) if isinstance(parsed, dict) else '明细数据'}")
        except json.JSONDecodeError:
            summary_parts.append("数据字段: （JSON 格式无效）")

    warnings = []
    if risk == "danger":
        warnings.append("此操作可能不可恢复，请谨慎执行")
    if _readonly:
        warnings.append("当前为只读模式，实际写入操作将被拒绝")

    result = {
        "operation": operation,
        "object": obj,
        "risk": risk,
        "summary": "，".join(summary_parts),
        "warnings": warnings,
    }
    return _ok(result)


# ============================================================
# 推荐工具
# ============================================================

@mcp.tool()
def get_profile() -> str:
    """获取鼎捷 MCP Server 的身份和连接配置信息。

    只读工具。返回服务器名称、连接地址、企业编号、据点、模式等。
    """
    try:
        client = get_client()
        return _ok({
            "server_name": "dingjie-erp",
            "system": "dingjie",
            "target_prod": client.target_prod,
            "server_url": client.server_url,
            "ent_id": client.ent_id,
            "company_id": client.company_id,
            "lang": client.lang,
            "mode": "readonly" if _readonly else "readwrite",
        })
    except Exception as e:
        return _err(f"获取配置信息失败: {e}")


# ============================================================
# 注册业务工具
# ============================================================

register_all_tools(mcp, get_client, lambda: _readonly, _ok, _err)


# ============================================================
# 主入口
# ============================================================

def main():
    """启动 MCP Server"""
    global _readonly

    logging.basicConfig(
        level=os.environ.get("MCP_LOG_LEVEL", "INFO"),
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
        default=os.environ.get("MCP_MODE", "readonly"),
        help="readonly: 仅查询工具；readwrite: 全部工具（默认 readonly）",
    )
    args = parser.parse_args()

    _readonly = args.mode == "readonly"
    setup()

    if _readonly:
        logger.info("[dingjie-erp] mode=readonly, tools=查询+元数据+预览")
    else:
        logger.info("[dingjie-erp] mode=readwrite, tools=全部")

    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
