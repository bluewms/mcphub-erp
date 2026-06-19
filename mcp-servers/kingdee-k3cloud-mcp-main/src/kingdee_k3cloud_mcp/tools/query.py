"""查询类工具：query_bill, query_bill_json, count_bill, query_bill_all, query_bill_to_file, query_bill_range。"""

import json
import os

from kingdee_k3cloud_mcp.utils import (
    READ_ONLY_TOOL,
    _wrap_query_result,
    _is_session_expired,
    _iter_date_chunks,
)
from kingdee_k3cloud_mcp.tools import ToolContext

_ctx: ToolContext | None = None


def register_query_tools(mcp, ctx: ToolContext):
    """注册查询类工具。"""
    global _ctx
    _ctx = ctx
    mcp.tool(annotations=READ_ONLY_TOOL)(query_bill)
    mcp.tool(annotations=READ_ONLY_TOOL)(query_bill_json)
    mcp.tool(annotations=READ_ONLY_TOOL)(count_bill)
    mcp.tool(annotations=READ_ONLY_TOOL)(query_bill_all)
    mcp.tool(annotations=READ_ONLY_TOOL)(query_bill_to_file)
    mcp.tool(annotations=READ_ONLY_TOOL)(query_bill_range)


def query_bill(
    form_id: str,
    field_keys: str,
    filter_string: str = "",
    order_string: str = "",
    top_count: int = 100,
    start_row: int = 0,
    limit: int = 2000,
) -> str:
    """查询金蝶云星空单据数据（返回二维数组）。只读工具。

    Args:
        form_id: 表单ID。常用值：
            BD_MATERIAL(物料)、BD_Customer(客户)、BD_Supplier(供应商)、
            SAL_SaleOrder(销售订单)、PUR_PurchaseOrder(采购订单)、
            STK_InStock(入库单)、STK_OutStock(出库单)、GL_VOUCHER(凭证)
        field_keys: 查询字段，逗号分隔。如 "FName,FNumber"
        filter_string: 过滤条件。如 "FNumber like 'MAT%'"
        order_string: 排序字段。如 "FNumber ASC"
        top_count: 本次最多返回行数，默认100。映射到金蝶 TopRowCount（绝对终止行号 = start_row + top_count），
            同时作为金蝶 Limit（单次页大小）。设为 0 表示不限制行数（仅靠 limit 控制）。
        start_row: 起始行号，默认0。翻页时传入上一次返回的 next_start_row。
        limit: 仅在 top_count=0 时生效，作为金蝶 Limit 页大小上限，默认2000。
            top_count>0 时此参数被忽略（页大小由 top_count 决定）。
    """
    raw = _ctx.get_sdk().ExecuteBillQuery(
        {
            "FormId": form_id,
            "FieldKeys": field_keys,
            "FilterString": filter_string,
            "OrderString": order_string,
            "TopRowCount": (start_row + top_count) if top_count > 0 else 0,
            "StartRow": start_row,
            "Limit": top_count if top_count > 0 else limit,
        }
    )
    return _wrap_query_result(raw, top_count, limit, start_row)


def query_bill_json(
    form_id: str,
    field_keys: str,
    filter_string: str = "",
    order_string: str = "",
    top_count: int = 100,
    start_row: int = 0,
    limit: int = 2000,
) -> str:
    """查询金蝶云星空单据数据（返回JSON格式，字段名作为key）。只读工具。

    与 query_bill 的区别：返回结果是JSON对象数组，每条记录的字段名作为key，更易读。

    Args:
        form_id: 表单ID。常用值：
            BD_MATERIAL(物料)、BD_Customer(客户)、BD_Supplier(供应商)、
            SAL_SaleOrder(销售订单)、PUR_PurchaseOrder(采购订单)、
            STK_InStock(入库单)、STK_OutStock(出库单)、GL_VOUCHER(凭证)
        field_keys: 查询字段，逗号分隔。如 "FName,FNumber,FCreateOrgId,FUseOrgId"
        filter_string: 过滤条件。如 "FNumber like 'MAT%'"
        order_string: 排序字段。如 "FNumber ASC"
        top_count: 本次最多返回行数，默认100。映射到金蝶 TopRowCount（绝对终止行号 = start_row + top_count），
            同时作为金蝶 Limit（单次页大小）。设为 0 表示不限制行数（仅靠 limit 控制）。
        start_row: 起始行号，默认0。翻页时传入上一次返回的 next_start_row。
        limit: 仅在 top_count=0 时生效，作为金蝶 Limit 页大小上限，默认2000。
            top_count>0 时此参数被忽略（页大小由 top_count 决定）。
    """
    raw = _ctx.get_sdk().BillQuery(
        {
            "FormId": form_id,
            "FieldKeys": field_keys,
            "FilterString": filter_string,
            "OrderString": order_string,
            "TopRowCount": (start_row + top_count) if top_count > 0 else 0,
            "StartRow": start_row,
            "Limit": top_count if top_count > 0 else limit,
        }
    )
    return _wrap_query_result(raw, top_count, limit, start_row)


def count_bill(form_id: str, filter_string: str = "") -> str:
    """估算某查询条件下的数据行数（不返回数据内容）。只读工具。

    用于大数据量查询前的探测。

    返回 JSON 格式：
        {"estimated_rows": N, "is_exact": true/false, "hint": "..."}
    当 is_exact=false 时，实际行数 ≥ estimated_rows，建议按月/周分片查询。

    Args:
        form_id: 表单ID。如 SAL_SaleOrder、PUR_PurchaseOrder、BD_MATERIAL 等
        filter_string: 过滤条件。如 "FDate >= '2025-01-01' AND FDate < '2026-01-01'"
    """
    _PROBE_LIMIT = 5000
    raw = _ctx.get_sdk().BillQuery(
        {
            "FormId": form_id,
            "FieldKeys": "FID",
            "FilterString": filter_string,
            "TopRowCount": _PROBE_LIMIT,
            "StartRow": 0,
            "Limit": _PROBE_LIMIT,
        }
    )

    if _is_session_expired(raw):
        return raw

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw

    if not isinstance(data, list):
        return raw

    count = len(data)
    is_exact = count < _PROBE_LIMIT
    result: dict = {"estimated_rows": count, "is_exact": is_exact}
    if not is_exact:
        result["hint"] = (
            f"实际行数 ≥ {_PROBE_LIMIT}，建议按自然月分片查询（每月单独调用 query_bill_json）。"
        )
    return json.dumps(result, ensure_ascii=False)


def query_bill_all(
    form_id: str,
    field_keys: str,
    filter_string: str = "",
    order_string: str = "",
    max_rows: int = 20000,
    page_size: int = 2000,
) -> str:
    """自动翻页查询直到拉完或达到 max_rows 安全上限。只读工具。

    适合估算 ≤ 数千行的场景。大数据量（> 5000 行）请用 query_bill_to_file（落盘）
    或 query_bill_range（日期分片），避免超过 MCP 1 MB 返回限制。

    返回格式：
        {"rows": [...], "row_count": N, "exhausted": true/false,
         "next_start_row": N,   # 仅 exhausted=false 时
         "hint": "..."}         # 仅 exhausted=false 时

    Args:
        form_id: 表单ID。如 SAL_SaleOrder、PUR_PurchaseOrder、BD_MATERIAL 等
        field_keys: 查询字段，逗号分隔。如 "FBillNo,FDate,FAmount"
        filter_string: 过滤条件。如 "FDate >= '2025-01-01'"
        order_string: 排序字段。如 "FDate ASC"
        max_rows: 安全上限，默认 20000；超过则提前终止并返回 exhausted=false
        page_size: 每页行数，默认 2000，建议不超过 2000
    """
    params = {
        "FormId": form_id,
        "FieldKeys": field_keys,
        "FilterString": filter_string,
        "OrderString": order_string,
    }
    rows, exhausted, next_start, err = _ctx.paginate_bill(params, page_size, max_rows)
    if err is not None:
        return err
    result: dict = {"rows": rows, "row_count": len(rows), "exhausted": exhausted}
    if not exhausted:
        result["next_start_row"] = next_start
        result["hint"] = (
            "已达 max_rows 安全上限，如需继续请调用 query_bill_range 或缩小 filter_string 后手动分片"
        )
    return json.dumps(result, ensure_ascii=False)


def query_bill_to_file(
    form_id: str,
    field_keys: str,
    filter_string: str = "",
    output_path: str = "",
    format: str = "ndjson",
    page_size: int = 2000,
    max_rows: int = 500000,
) -> str:
    """自动翻页并流式写入本地文件，适合大数据量导出（万行以上）。只读工具。

    不在内存中累积数据，写入完成后返回文件路径和统计信息。
    文件可用 Read 工具抽检，或交由 pandas/polars 处理。

    返回格式：
        {"path": "...", "row_count": N, "bytes": M, "format": "ndjson"}
        若中途出错：{"error": "...", "path": "...", "row_count": <已写入>, "bytes": M}

    Args:
        form_id: 表单ID。如 SAL_SaleOrder、PUR_PurchaseOrder、BD_MATERIAL 等
        field_keys: 查询字段，逗号分隔。如 "FBillNo,FDate,FAmount"
        filter_string: 过滤条件。如 "FDate >= '2025-01-01'"
        output_path: 输出文件绝对路径。如 "/tmp/orders.ndjson"
        format: 输出格式，ndjson（每行一个 JSON 对象）或 csv，默认 ndjson
        page_size: 每页行数，默认 2000
        max_rows: 最大写入行数，默认 500000；超过则截断并正常返回
    """
    if not output_path or not os.path.isabs(output_path):
        return json.dumps({"error": "output_path 必须为非空绝对路径"}, ensure_ascii=False)
    if format not in {"ndjson", "csv"}:
        return json.dumps(
            {"error": f"format 必须是 ndjson 或 csv，收到: {format!r}"}, ensure_ascii=False
        )
    parent = os.path.dirname(output_path)
    if not os.path.isdir(parent):
        return json.dumps({"error": f"目录不存在: {parent}"}, ensure_ascii=False)

    fields = [f.strip() for f in field_keys.split(",") if f.strip()]
    params = {
        "FormId": form_id,
        "FieldKeys": field_keys,
        "FilterString": filter_string,
        "OrderString": "",
        "StartRow": 0,
    }

    try:
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            rows_written, _, error_raw = _ctx.stream_to_file(
                f, params, page_size, max_rows, fields, format, False
            )
    except OSError as e:
        return json.dumps({"error": f"文件写入失败: {e}"}, ensure_ascii=False)

    file_bytes = os.path.getsize(output_path)

    if error_raw is not None:
        return json.dumps(
            {
                "error": "查询中途遇到错误，已写入部分数据",
                "path": output_path,
                "row_count": rows_written,
                "bytes": file_bytes,
            },
            ensure_ascii=False,
        )

    return json.dumps(
        {
            "path": output_path,
            "row_count": rows_written,
            "bytes": file_bytes,
            "format": format,
        },
        ensure_ascii=False,
    )


def query_bill_range(
    form_id: str,
    field_keys: str,
    date_field: str,
    date_from: str,
    date_to: str,
    extra_filter: str = "",
    chunk: str = "month",
    output_path: str = "",
    page_size: int = 2000,
) -> str:
    """按日期自动切片 + 翻页，适合跨月/跨年查询。只读工具。

    将 [date_from, date_to) 按 chunk 切成 N 段，每段独立翻页拉取。
    output_path 为空时内联返回（受 MCP 1 MB 限制，适合小跨度）；
    非空时流式落盘，适合大跨度（年级）查询。

    返回格式（内联）：
        {"rows": [...], "row_count": N, "chunks": K, "exhausted": true}
    返回格式（落盘）：
        {"path": "...", "row_count": N, "bytes": M, "chunks": K, "format": "ndjson"}
        若中途出错：{"error": "...", "path": "...", "row_count": <已写入>, "bytes": M}

    Args:
        form_id: 表单ID。如 SAL_SaleOrder、PUR_PurchaseOrder 等
        field_keys: 查询字段，逗号分隔
        date_field: 日期字段名。通常是 FDate 或 FCreateDate
        date_from: 起始日期（含），YYYY-MM-DD
        date_to: 结束日期（不含），YYYY-MM-DD
        extra_filter: 额外过滤条件（与日期条件 AND 拼接）
        chunk: 切片粒度，month（默认）/ week / day
        output_path: 落盘路径（绝对路径）。空=内联返回
        page_size: 每页行数，默认 2000
    """
    try:
        chunks = list(_iter_date_chunks(date_from, date_to, chunk))
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    inline_mode = not output_path

    if not inline_mode:
        if not os.path.isabs(output_path):
            return json.dumps({"error": "output_path 必须为绝对路径"}, ensure_ascii=False)
        parent = os.path.dirname(output_path)
        if not os.path.isdir(parent):
            return json.dumps({"error": f"目录不存在: {parent}"}, ensure_ascii=False)

    fields = [f.strip() for f in field_keys.split(",") if f.strip()]

    def _build_filter(chunk_from: str, chunk_to: str) -> str:
        date_filter = f"{date_field} >= '{chunk_from}' AND {date_field} < '{chunk_to}'"
        return f"({extra_filter}) AND {date_filter}" if extra_filter else date_filter

    if inline_mode:
        all_rows: list = []
        for chunk_from, chunk_to in chunks:
            params: dict = {
                "FormId": form_id,
                "FieldKeys": field_keys,
                "FilterString": _build_filter(chunk_from, chunk_to),
                "OrderString": "",
            }
            rows, _exhausted, _next, err = _ctx.paginate_bill(params, page_size, 20000)
            if err is not None:
                return err
            all_rows.extend(rows)
        return json.dumps(
            {
                "rows": all_rows,
                "row_count": len(all_rows),
                "chunks": len(chunks),
                "exhausted": True,
            },
            ensure_ascii=False,
        )

    # Streaming / file mode
    total_count = 0
    error_raw = None
    try:
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            header_written = False
            for chunk_from, chunk_to in chunks:
                params = {
                    "FormId": form_id,
                    "FieldKeys": field_keys,
                    "FilterString": _build_filter(chunk_from, chunk_to),
                    "OrderString": "",
                    "StartRow": 0,
                }
                rows_written, header_written, error_raw = _ctx.stream_to_file(
                    f, params, page_size, 500000, fields, "ndjson", header_written
                )
                total_count += rows_written
                if error_raw is not None:
                    break
    except OSError as e:
        return json.dumps({"error": f"文件写入失败: {e}"}, ensure_ascii=False)

    file_bytes = os.path.getsize(output_path)

    if error_raw is not None:
        return json.dumps(
            {
                "error": "查询中途遇到错误，已写入部分数据",
                "path": output_path,
                "row_count": total_count,
                "bytes": file_bytes,
            },
            ensure_ascii=False,
        )

    return json.dumps(
        {
            "path": output_path,
            "row_count": total_count,
            "bytes": file_bytes,
            "chunks": len(chunks),
            "format": "ndjson",
        },
        ensure_ascii=False,
    )
