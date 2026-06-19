"""Kingdee K3Cloud MCP Server 入口。

使用 FastMCP 框架，支持 stdio / SSE / streamable-http 传输。
符合《企业管理软件 MCP 标准服务规范》。

工具按功能领域分文件组织（tools/essential.py, tools/query.py 等），
server.py 只做入口、SDK 实例管理和分页原语。
"""

import argparse
import csv
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP

# ============================================================
# SDK 和工具注解（re-export 供测试导入）
# ============================================================

from kingdee_k3cloud_mcp.sdk import RetryableK3CloudApiSdk
from kingdee_k3cloud_mcp.utils import (
    _ok,
    _err,
    _check_expired,
    _is_session_expired,
    _wrap_query_result,
    _iter_date_chunks,
    _ids_data,
    SESSION_LOST_MSG,
    READ_ONLY_TOOL,
    PREVIEW_TOOL,
    WRITE_TOOL,
    DESTRUCTIVE_TOOL,
)

# ============================================================
# 工具函数（re-export 供测试导入）
# ============================================================

from kingdee_k3cloud_mcp.tools import register_all_tools, ToolContext
from kingdee_k3cloud_mcp.tools.essential import health_check, query_metadata, preview_write
from kingdee_k3cloud_mcp.tools.profile import get_profile
from kingdee_k3cloud_mcp.tools.query import (
    query_bill,
    query_bill_json,
    count_bill,
    query_bill_all,
    query_bill_to_file,
    query_bill_range,
)
from kingdee_k3cloud_mcp.tools.read import view_bill
from kingdee_k3cloud_mcp.tools.write import (
    save_bill,
    submit_bill,
    audit_bill,
    unaudit_bill,
    delete_bill,
    execute_operation,
    push_bill,
)

logger = logging.getLogger(__name__)

# ============================================================
# 全局状态
# ============================================================

# SDK instance: initialized in setup() after environment is validated.
api_sdk: "RetryableK3CloudApiSdk | None" = None

# Write-tool guard: default True (readonly per spec). Set to False in main() when --mode readwrite.
_readonly = True

mcp = FastMCP("kingdee-k3cloud")


class ApiKeyVerifier:
    """验证静态 API Key（Bearer Token）。

    仅在 SSE/streamable-http 传输时生效；MCP_API_KEY 未设置时禁用鉴权。
    """

    def __init__(self, api_key: str):
        self._key = api_key

    async def verify_token(self, token: str) -> AccessToken | None:
        if token == self._key:
            return AccessToken(token=token, client_id="api-key-client", scopes=[])
        return None


def _sdk() -> "RetryableK3CloudApiSdk":
    """Return the initialized SDK, asserting it is not None."""
    assert api_sdk is not None, "api_sdk not initialized — call setup() first"
    return api_sdk


# ============================================================
# 分页原语（依赖 _sdk()，供 query 工具通过 ToolContext 使用）
# ============================================================


def _paginate_bill(
    params: dict, page_size: int, max_rows: int
) -> "tuple[list, bool, int, str | None]":
    """内部翻页原语。返回 (rows, exhausted, next_start_row, error_raw)。

    - rows: 已拉取的数据列表
    - exhausted=True 表示已拉完所有数据；False 表示因 max_rows 提前截断
    - next_start_row: 下次应从此行继续（exhausted=False 时有意义）
    - error_raw: 非 None 表示遇到 session expired / 格式错误，调用方应直接 return
    """
    rows: list = []
    initial_start = params.get("StartRow", 0)
    current_start = initial_start

    while True:
        page_params = {
            **params,
            "StartRow": current_start,
            # TopRowCount 是绝对终止行号而非页大小，必须随偏移增长才能覆盖当前页窗口
            "TopRowCount": current_start + page_size,
            "Limit": page_size,
        }
        raw = _sdk().BillQuery(page_params)

        if _is_session_expired(raw):
            return rows, False, current_start, raw

        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return rows, False, current_start, raw

        if not isinstance(data, list):
            return rows, False, current_start, raw

        rows.extend(data)
        page_count = len(data)

        if len(rows) >= max_rows:
            rows = rows[:max_rows]
            return rows, False, initial_start + max_rows, None

        if page_count < page_size:
            return rows, True, initial_start + len(rows), None

        current_start += page_size


def _stream_to_file_handle(
    f,
    params: dict,
    page_size: int,
    max_rows: int,
    fields: list,
    fmt: str,
    header_written: bool,
) -> "tuple[int, bool, str | None]":
    """将分页查询结果流式追加写入已打开的文件句柄。

    Returns:
        (rows_written, header_written, error_raw)
    """
    writer = csv.writer(f) if fmt == "csv" else None
    rows_written = 0
    current_start = params.get("StartRow", 0)

    while True:
        page_params = {
            **params,
            "StartRow": current_start,
            "TopRowCount": current_start + page_size,
            "Limit": page_size,
        }
        raw = _sdk().BillQuery(page_params)

        if _is_session_expired(raw):
            return rows_written, header_written, raw

        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return rows_written, header_written, raw

        if not isinstance(data, list):
            return rows_written, header_written, raw

        for row in data:
            if fmt == "ndjson":
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            elif writer is not None:  # fmt == "csv"
                if not header_written:
                    writer.writerow(fields)
                    header_written = True
                writer.writerow([row.get(field, "") for field in fields])
            rows_written += 1
            if rows_written >= max_rows:
                return rows_written, header_written, None

        if len(data) < page_size:
            break

        current_start += page_size

    return rows_written, header_written, None


# ============================================================
# 注册所有工具（模块级，导入即注册）
# ============================================================

_ctx = ToolContext(
    get_sdk=_sdk,
    is_readonly=lambda: _readonly,
    ok=_ok,
    err=_err,
    server_name="kingdee-k3cloud",
    paginate_bill=_paginate_bill,
    stream_to_file=_stream_to_file_handle,
)
register_all_tools(mcp, _ctx)


# ============================================================
# 初始化和启动
# ============================================================


def setup() -> None:
    """Initialize environment, validate required vars, and create the SDK instance."""
    global api_sdk
    load_dotenv(dotenv_path=Path.cwd() / ".env")
    _required_env = ["KD_SERVER_URL", "KD_ACCT_ID", "KD_USERNAME", "KD_APP_ID", "KD_APP_SEC"]
    _missing_env = [k for k in _required_env if not os.getenv(k)]
    if _missing_env:
        raise RuntimeError(f"Missing required env vars: {', '.join(_missing_env)}")

    api_key = os.getenv("MCP_API_KEY", "")
    if api_key:
        issuer_url = os.getenv("MCP_ISSUER_URL", "http://localhost:8000")
        mcp._token_verifier = ApiKeyVerifier(api_key)
        mcp.settings.auth = AuthSettings(issuer_url=issuer_url, resource_server_url=issuer_url)  # type: ignore[arg-type]

    server_url = os.getenv("KD_SERVER_URL", "")
    api_sdk = RetryableK3CloudApiSdk(server_url)
    api_sdk.InitConfig(
        acct_id=os.getenv("KD_ACCT_ID", ""),
        user_name=os.getenv("KD_USERNAME", ""),
        app_id=os.getenv("KD_APP_ID", ""),
        app_secret=os.getenv("KD_APP_SEC", ""),
        server_url=server_url,
        lcid=int(os.getenv("KD_LCID", "2052")),
        org_num=int(os.getenv("KD_ORG_NUM", "0") or "0"),
    )


def main():
    global _readonly

    logging.basicConfig(
        level=os.environ.get("MCP_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
    )

    parser = argparse.ArgumentParser(description="Kingdee K3Cloud MCP Server")
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

    _read_count = 11  # health_check, preview_write, query_metadata, get_profile, query_bill, query_bill_json, count_bill, query_bill_all, query_bill_to_file, query_bill_range, view_bill
    _write_count = 7  # save_bill, submit_bill, audit_bill, unaudit_bill, delete_bill, execute_operation, push_bill
    tool_count = _read_count if _readonly else _read_count + _write_count
    logger.info(f"[k3cloud] mode={args.mode}, tools={tool_count}")
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
