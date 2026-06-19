"""SDK 客户端测试"""

import json
import pytest
from unittest.mock import patch, MagicMock

from dingjie_erp_mcp.sdk import DingjieClient, DingjieAPIError


class TestDingjieClient:
    """DingjieClient 测试"""

    def test_init(self, mock_client):
        """测试客户端初始化"""
        assert mock_client.server_url == "https://erp.test.com"
        assert mock_client.app_id == "test_app"
        assert mock_client.app_secret == "test_secret"

    def test_auth_headers_with_app_key(self, mock_client):
        """测试 API Key 认证头"""
        headers = mock_client._get_auth_headers()
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_secret"
        assert headers["X-App-Id"] == "test_app"

    def test_auth_headers_with_username(self):
        """测试用户名密码认证头"""
        with patch("dingjie_erp_mcp.sdk.DingjieClient._authenticate"):
            client = DingjieClient(
                server_url="https://erp.test.com",
                username="admin",
                password="secret",
            )
        headers = client._get_auth_headers()
        assert headers["X-Username"] == "admin"
        assert headers["X-Password"] == "secret"

    def test_session_expired_detection(self, mock_client):
        """测试会话过期检测"""
        assert mock_client._is_session_expired('{"message": "会话信息已丢失"}')
        assert mock_client._is_session_expired('{"error": "session expired"}')
        assert not mock_client._is_session_expired('{"status": "ok"}')

    @patch.object(DingjieClient, "_request")
    def test_create_purchase_receipt(self, mock_request, mock_client):
        """测试创建采购入库单"""
        mock_request.return_value = {"doc_no": "PI-2024-001", "status": "created"}
        result = mock_client.create_purchase_receipt({"om_site_id": "SITE01"})
        assert result["doc_no"] == "PI-2024-001"

    @patch.object(DingjieClient, "_request")
    def test_query_purchase_receipts(self, mock_request, mock_client):
        """测试查询采购入库单"""
        mock_request.return_value = {"rows": [{"doc_no": "PI-001"}], "row_count": 1}
        result = mock_client.query_purchase_receipts({"limit": 10})
        assert result["row_count"] == 1

    @patch.object(DingjieClient, "_request")
    def test_create_sales_issue(self, mock_request, mock_client):
        """测试创建销货出库单"""
        mock_request.return_value = {"doc_no": "SI-2024-001", "status": "created"}
        result = mock_client.create_sales_issue({"om_site_id": "SITE01"})
        assert result["doc_no"] == "SI-2024-001"

    @patch.object(DingjieClient, "_request")
    def test_query_materials(self, mock_request, mock_client):
        """测试查询物料"""
        mock_request.return_value = {"rows": [{"code": "MAT001"}], "row_count": 1}
        result = mock_client.query_materials({"limit": 10})
        assert result["row_count"] == 1


class TestDingjieAPIError:
    """DingjieAPIError 测试"""

    def test_error_creation(self):
        """测试错误创建"""
        error = DingjieAPIError("test error", status_code=404, response_body="not found")
        assert str(error) == "test error"
        assert error.status_code == 404
        assert error.response_body == "not found"
