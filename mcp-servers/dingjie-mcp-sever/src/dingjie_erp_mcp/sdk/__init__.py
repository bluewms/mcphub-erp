"""鼎捷 ERP 互联中台 API 客户端

鼎捷 ERP 有两种接口体系：
1. E10 OAPI（新版 RESTful API）: e10.oapi.purchase.receipt.data.create
2. 互联中台（Web Service JSON 协议）: app.purchase.stockin.create

本 SDK 优先使用互联中台接口，因为：
- 接口数量更多（170+ 个），覆盖几乎所有业务场景
- 支持分包机制（page_size/key_condition），天然支持大数据量查询
- 统一信封格式，所有接口调用方式一致
- 多产品兼容（T100/E10/TIPTOP/易飞/WF）

互联中台 JSON 请求信封格式：
{
    "key": "f5458f5c0f9022db743a7c0710145903",
    "type": "sync",
    "host": {
        "prod": "APP",       // 发送方产品
        "ip": "10.40.71.91",  // 发送方 IP
        "lang": "zh_TW",      // 语言
        "acct": "Machine ID1", // 机器码
        "timestamp": "20151211123204361" // 时间戳
    },
    "service": {
        "prod": "T100",       // 接收方产品（T100/E10/TIPTOP/易飞）
        "name": "app.purchase.stockin.create", // 服务名称
        "ip": "10.40.40.18",  // 接收方 IP
        "id": "topprd"        // 接收方数据库
    },
    "datakey": {
        "EntId": "99",        // 企业编号
        "CompanyId": "DSCTC"  // 营运据点
    },
    "payload": {
        "std_data": {
            "parameter": { ... }  // 业务数据
        }
    }
}

互联中台 JSON 响应信封格式：
{
    "srvver": "1.0",
    "srvcode": "000",  // 000:成功, 100:失败
    "payload": {
        "std_data": {
            "execution": {
                "code": "0",       // 0:成功, 非0:错误
                "sql_code": "",
                "description": ""
            },
            "parameter": { ... }   // 返回的业务数据
        }
    }
}
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class DingjieAPIError(Exception):
    """鼎捷 ERP API 错误"""

    def __init__(self, message: str, *, srvcode: str | None = None, code: str | None = None, description: str | None = None):
        super().__init__(message)
        self.srvcode = srvcode
        self.code = code
        self.description = description


class DingjieClient:
    """鼎捷 ERP 互联中台 API 客户端

    通过互联中台 JSON 协议与鼎捷 ERP 通信。
    支持两种接口模式：
    1. 互联中台（推荐）：统一信封格式，170+ 个接口
    2. E10 OAPI（备用）：RESTful API，接口较少

    功能：
    - 自动构造中台信封（host/service/datakey/payload）
    - 请求重试（指数退避）
    - 统一错误处理（解析 srvcode/execution.code）
    - 分包查询支持（page_size/key_condition）
    """

    def __init__(
        self,
        server_url: str,
        key: str = "",
        ent_id: str = "",
        company_id: str = "",
        target_prod: str = "E10",
        target_id: str = "",
        host_prod: str = "APP",
        host_ip: str = "",
        lang: str = "zh_TW",
        timeout: int = 30,
        verify_ssl: bool = True,
    ) -> None:
        self.server_url = server_url.rstrip("/")
        self.key = key
        self.ent_id = ent_id
        self.company_id = company_id
        self.target_prod = target_prod  # 接收方产品（T100/E10/TIPTOP/易飞）
        self.target_id = target_id      # 接收方数据库 ID
        self.host_prod = host_prod       # 发送方产品
        self.host_ip = host_ip           # 发送方 IP
        self.lang = lang                 # 语言（zh_TW/zh_CN）
        self.timeout = timeout
        self.verify_ssl = verify_ssl

        # 配置 requests Session
        self.session = requests.Session()
        self.session.verify = verify_ssl

        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    # ----------------------------------------------------------
    # 中台信封构造
    # ----------------------------------------------------------

    def _build_envelope(self, service_name: str, parameter: dict[str, Any], call_type: str = "sync") -> dict[str, Any]:
        """构造互联中台 JSON 请求信封

        Args:
            service_name: 服务名称，如 "app.purchase.stockin.create"
            parameter: 业务数据（放入 payload.std_data.parameter）
            call_type: 调用类型（sync/async）
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")[:17]

        envelope = {
            "key": self.key,
            "type": call_type,
            "host": {
                "prod": self.host_prod,
                "ip": self.host_ip,
                "lang": self.lang,
                "acct": "",
                "timestamp": timestamp,
            },
            "service": {
                "prod": self.target_prod,
                "name": service_name,
            },
            "datakey": {
                "EntId": self.ent_id,
                "CompanyId": self.company_id,
            },
            "payload": {
                "std_data": {
                    "parameter": parameter,
                }
            },
        }

        # 如果有 target_id，加入 service
        if self.target_id:
            envelope["service"]["id"] = self.target_id

        return envelope

    def _parse_response(self, resp_json: dict[str, Any]) -> dict[str, Any]:
        """解析互联中台 JSON 响应信封

        Returns:
            解包后的业务数据（payload.std_data.parameter）

        Raises:
            DingjieAPIError: 如果 srvcode != "000" 或 execution.code != "0"
        """
        srvcode = resp_json.get("srvcode", "")
        srvver = resp_json.get("srvver", "")

        # 检查服务级别错误
        if srvcode != "000":
            description = resp_json.get("description", "")
            raise DingjieAPIError(
                f"中台服务错误 (srvcode={srvcode}): {description}",
                srvcode=srvcode,
            )

        # 解包 payload
        payload = resp_json.get("payload", {})
        std_data = payload.get("std_data", {})
        execution = std_data.get("execution", {})
        parameter = std_data.get("parameter", {})

        # 检查执行级别错误
        code = execution.get("code", "")
        if code != "0":
            sql_code = execution.get("sql_code", "")
            description = execution.get("description", "")
            raise DingjieAPIError(
                f"执行错误 (code={code}, sql_code={sql_code}): {description}",
                code=code,
                description=description,
            )

        # 返回业务数据
        return {
            "execution": execution,
            "parameter": parameter,
        }

    # ----------------------------------------------------------
    # 核心 API 调用
    # ----------------------------------------------------------

    def call_service(self, service_name: str, parameter: dict[str, Any], call_type: str = "sync") -> dict[str, Any]:
        """调用互联中台服务

        Args:
            service_name: 服务名称，如 "app.purchase.stockin.create"
            parameter: 业务数据
            call_type: sync（同步）或 async（异步）

        Returns:
            解包后的业务数据
        """
        envelope = self._build_envelope(service_name, parameter, call_type)
        url = f"{self.server_url}/api/v1/call"

        logger.debug(f">>> 中台调用: {service_name}")

        try:
            resp = self.session.post(
                url,
                json=envelope,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout,
            )
        except requests.ConnectionError as e:
            raise DingjieAPIError(f"网络连接失败: {e}")
        except requests.Timeout:
            raise DingjieAPIError(f"请求超时 ({self.timeout}s): {service_name}")

        if resp.status_code >= 400:
            raise DingjieAPIError(f"HTTP 错误 ({resp.status_code}): {resp.text}")

        try:
            resp_json = resp.json()
        except json.JSONDecodeError:
            raise DingjieAPIError(f"响应 JSON 解析失败: {resp.text}")

        return self._parse_response(resp_json)

    # ----------------------------------------------------------
    # 采购入库 (purchase_stock_in)
    # ----------------------------------------------------------

    def create_purchase_stockin(self, data: dict[str, Any]) -> dict[str, Any]:
        """创建采购入库单

        服务名: app.purchase.stockin.create
        """
        return self.call_service("app.purchase.stockin.create", data)

    def query_purchase_stockins(self, filters: dict[str, Any]) -> dict[str, Any]:
        """查询采购入库单列表

        服务名: purchase.stock.in.list.query.get
        """
        return self.call_service("purchase.stock.in.list.query.get", filters)

    def read_purchase_stockin(self, data: dict[str, Any]) -> dict[str, Any]:
        """查看采购入库单详情

        服务名: purchase.stock.in.details.read.get
        """
        return self.call_service("purchase.stock.in.details.read.get", data)

    def approve_purchase_stockin(self, data: dict[str, Any]) -> dict[str, Any]:
        """审核采购入库单

        服务名: purchase.stock.in.data.approve
        """
        return self.call_service("purchase.stock.in.data.approve", data)

    def disapprove_purchase_stockin(self, data: dict[str, Any]) -> dict[str, Any]:
        """撤销审核采购入库单

        服务名: purchase.stock.in.data.disapprove
        """
        return self.call_service("purchase.stock.in.data.disapprove", data)

    def delete_purchase_stockin(self, data: dict[str, Any]) -> dict[str, Any]:
        """删除采购入库单

        服务名: purchase.stock.in.data.delete
        """
        return self.call_service("purchase.stock.in.data.delete", data)

    def invalid_purchase_stockin(self, data: dict[str, Any]) -> dict[str, Any]:
        """作废采购入库单

        服务名: purchase.stock.in.data.invalid
        """
        return self.call_service("purchase.stock.in.data.invalid", data)

    # ----------------------------------------------------------
    # 销货出库 (sales_issue)
    # ----------------------------------------------------------

    def create_sales_issue(self, data: dict[str, Any]) -> dict[str, Any]:
        """创建销货出库单

        服务名: sales.issue.data.create
        """
        return self.call_service("sales.issue.data.create", data)

    def query_sales_issues(self, filters: dict[str, Any]) -> dict[str, Any]:
        """查询销货出库单列表

        服务名: sales.issue.list.data.query.get
        """
        return self.call_service("sales.issue.list.data.query.get", filters)

    def read_sales_issue(self, data: dict[str, Any]) -> dict[str, Any]:
        """查看销货出库单详情

        服务名: sales.issue.details.data.read.get
        """
        return self.call_service("sales.issue.details.data.read.get", data)

    def approve_sales_issue(self, data: dict[str, Any]) -> dict[str, Any]:
        """审核销货出库单"""
        return self.call_service("sales.issue.data.approve", data)

    def disapprove_sales_issue(self, data: dict[str, Any]) -> dict[str, Any]:
        """撤销审核销货出库单"""
        return self.call_service("sales.issue.data.disapprove", data)

    def delete_sales_issue(self, data: dict[str, Any]) -> dict[str, Any]:
        """删除销货出库单"""
        return self.call_service("sales.issue.data.delete", data)

    def invalid_sales_issue(self, data: dict[str, Any]) -> dict[str, Any]:
        """作废销货出库单"""
        return self.call_service("sales.issue.data.invalid", data)

    # ----------------------------------------------------------
    # 物料 (item)
    # ----------------------------------------------------------

    def get_items(self, data: dict[str, Any]) -> dict[str, Any]:
        """获取物料列表（支持分包）

        服务名: item.get
        支持分包参数: page_size, key_condition, sql_condition
        """
        return self.call_service("item.get", data)

    # ----------------------------------------------------------
    # 基础数据抛转
    # ----------------------------------------------------------

    def get_warehouse(self, data: dict[str, Any]) -> dict[str, Any]:
        """获取仓库数据

        服务名: warehouse.get
        """
        return self.call_service("warehouse.get", data)

    def get_customer(self, data: dict[str, Any]) -> dict[str, Any]:
        """获取客户数据

        服务名: customer.get
        """
        return self.call_service("customer.get", data)

    def get_supplier(self, data: dict[str, Any]) -> dict[str, Any]:
        """获取供应商数据

        服务名: supplier.get
        """
        return self.call_service("supplier.get", data)

    # ----------------------------------------------------------
    # 通用
    # ----------------------------------------------------------

    def get_enterprise_sites(self) -> dict[str, Any]:
        """获取使用者可选择的 Enterprise 及 Site

        服务名: enterprise.site.get
        """
        return self.call_service("enterprise.site.get", {})

    def get_user_info(self, data: dict[str, Any]) -> dict[str, Any]:
        """获取使用者信息

        服务名: user.info.get
        """
        return self.call_service("user.info.get", data)

    def get_doc_type(self, data: dict[str, Any]) -> dict[str, Any]:
        """取得单别

        服务名: doc.type.get
        """
        return self.call_service("doc.type.get", data)

    def upload_approve_post(self, data: dict[str, Any]) -> dict[str, Any]:
        """上传、审核、过账

        服务名: upload.approve.post
        """
        return self.call_service("upload.approve.post", data)


def create_client_from_env() -> DingjieClient:
    """从环境变量创建客户端"""
    required = ["DINGJIE_SERVER_URL", "DINGJIE_KEY"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"缺少必要环境变量: {', '.join(missing)}")

    return DingjieClient(
        server_url=os.getenv("DINGJIE_SERVER_URL", ""),
        key=os.getenv("DINGJIE_KEY", ""),
        ent_id=os.getenv("DINGJIE_ENT_ID", ""),
        company_id=os.getenv("DINGJIE_COMPANY_ID", ""),
        target_prod=os.getenv("DINGJIE_TARGET_PROD", "E10"),
        target_id=os.getenv("DINGJIE_TARGET_ID", ""),
        host_prod=os.getenv("DINGJIE_HOST_PROD", "APP"),
        host_ip=os.getenv("DINGJIE_HOST_IP", ""),
        lang=os.getenv("DINGJIE_LANG", "zh_TW"),
        timeout=int(os.getenv("DINGJIE_TIMEOUT", "30")),
        verify_ssl=os.getenv("DINGJIE_VERIFY_SSL", "1") == "1",
    )