"""鼎捷 ERP MCP Server 测试配置"""

import pytest
from unittest.mock import MagicMock, patch
from dingjie_erp_mcp.sdk import DingjieClient


@pytest.fixture
def mock_client():
    """Mock 鼎捷 ERP 客户端"""
    with patch("dingjie_erp_mcp.sdk.DingjieClient._authenticate"):
        client = DingjieClient(
            server_url="https://erp.test.com",
            app_id="test_app",
            app_secret="test_secret",
        )
    return client


@pytest.fixture
def sample_purchase_receipt():
    """采购入库单示例数据"""
    return {
        "doc_no": "PI-2024-001",
        "om_site_id": "SITE01",
        "doc_type_no": "PI01",
        "doc_date": "2024-01-15",
        "supplier_no": "SUP001",
        "remark": "测试采购入库单",
        "details": [
            {
                "seq_no": 1,
                "business_qty": 100.5,
                "warehouse_no": "WH001",
                "lot_no": "LOT001",
            }
        ],
    }


@pytest.fixture
def sample_sales_issue():
    """销货出库单示例数据"""
    return {
        "doc_no": "SI-2024-001",
        "om_site_id": "SITE01",
        "doc_date": "2024-01-15",
        "customer_no": "CUS001",
        "remark": "测试销货出库单",
        "details": [
            {
                "seq": 1,
                "business_qty": 50.0,
                "warehouse_no": "WH001",
            }
        ],
    }
