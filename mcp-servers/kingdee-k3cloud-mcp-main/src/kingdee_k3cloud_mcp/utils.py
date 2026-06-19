"""公共辅助函数和工具注解常量。"""

import json
from collections.abc import Iterator
from datetime import date, timedelta

from mcp.types import ToolAnnotations

# ============================================================
# 工具注解常量（规范要求：所有工具必须标注风险等级）
# ============================================================

READ_ONLY_TOOL = ToolAnnotations(readOnlyHint=True, destructiveHint=False)
PREVIEW_TOOL = ToolAnnotations(readOnlyHint=True, destructiveHint=False)
WRITE_TOOL = ToolAnnotations(readOnlyHint=False, destructiveHint=False)
DESTRUCTIVE_TOOL = ToolAnnotations(readOnlyHint=False, destructiveHint=True)

# ============================================================
# 统一返回格式
# ============================================================


def _ok(data) -> str:
    """构造成功返回"""
    return json.dumps({"success": True, "data": data}, ensure_ascii=False, default=str)


def _err(msg: str) -> str:
    """构造错误返回"""
    return json.dumps({"success": False, "error": msg}, ensure_ascii=False)


# ============================================================
# 会话过期检测
# ============================================================

SESSION_LOST_MSG = "会话信息已丢失"


def _check_expired(data) -> bool:
    if isinstance(data, list):
        return any(_check_expired(item) for item in data)
    if isinstance(data, dict):
        errors = (data.get("Result") or {}).get("ResponseStatus", {}).get("Errors", [])
        return any(SESSION_LOST_MSG in (e.get("Message") or "") for e in errors)
    return False


def _is_session_expired(result: str) -> bool:
    try:
        return _check_expired(json.loads(result))
    except (json.JSONDecodeError, TypeError, ValueError):
        return False


# ============================================================
# 数据构造辅助
# ============================================================


def _ids_data(numbers: str, ids: str) -> dict:
    return {
        "CreateOrgId": 0,
        "Numbers": [n.strip() for n in numbers.split(",") if n.strip()] if numbers else [],
        "Ids": [i.strip() for i in ids.split(",") if i.strip()] if ids else [],
    }


# ============================================================
# 查询结果包装
# ============================================================


def _wrap_query_result(raw: str, top_count: int, limit: int, start_row: int) -> str:
    """将 SDK 查询结果包装为带分页元数据的 envelope。

    仅对成功列表响应生效；错误响应原样透传。
    """
    if _is_session_expired(raw):
        return raw

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw

    if not isinstance(data, list):
        return raw

    row_count = len(data)
    cap = top_count if top_count > 0 else limit
    truncated = row_count > 0 and row_count >= cap

    result: dict = {
        "rows": data,
        "row_count": row_count,
        "truncated": truncated,
    }
    if truncated:
        result["next_start_row"] = start_row + row_count
        result["hint"] = (
            f"返回行数已达上限（{cap} 行），数据可能被截断。"
            f"请用 start_row={start_row + row_count} 继续翻页获取下一页数据。"
        )

    return json.dumps(result, ensure_ascii=False)


# ============================================================
# 日期切片
# ============================================================


def _iter_date_chunks(
    date_from: str, date_to: str, chunk: str
) -> "Iterator[tuple[str, str]]":
    """将 [date_from, date_to) 切成 N 个半开区间。chunk ∈ {'month','week','day'}。"""
    if chunk not in {"month", "week", "day"}:
        raise ValueError(f"chunk 必须是 month/week/day，收到: {chunk!r}")
    try:
        current = date.fromisoformat(date_from)
        end = date.fromisoformat(date_to)
    except ValueError as e:
        raise ValueError(f"日期格式错误（需要 YYYY-MM-DD）: {e}") from e
    if end <= current:
        raise ValueError("date_to 必须晚于 date_from")

    while current < end:
        if chunk == "month":
            if current.month == 12:
                next_dt = date(current.year + 1, 1, 1)
            else:
                next_dt = date(current.year, current.month + 1, 1)
        elif chunk == "week":
            next_dt = current + timedelta(weeks=1)
        else:
            next_dt = current + timedelta(days=1)
        chunk_end = min(next_dt, end)
        yield current.isoformat(), chunk_end.isoformat()
        current = chunk_end
