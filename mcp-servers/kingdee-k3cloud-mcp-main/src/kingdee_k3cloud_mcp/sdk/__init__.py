"""SDK 封装：仅包含会话自动恢复的 RetryableK3CloudApiSdk。"""

import logging
import time

from k3cloud_webapi_sdk.const.const_define import InvokeMethod
from k3cloud_webapi_sdk.main import K3CloudApiSdk
from k3cloud_webapi_sdk.model.cookie_store import CookieStore

from kingdee_k3cloud_mcp.utils import _is_session_expired

logger = logging.getLogger(__name__)


class RetryableK3CloudApiSdk(K3CloudApiSdk):
    """K3CloudApiSdk with automatic session recovery on expiry.

    When K3Cloud returns "会话信息已丢失", the recovery flow is:
      1. If the last session reset was more than _RESET_COOLDOWN seconds ago:
         clear cookiesStore so BuildHeader() sends no session headers on retry.
         The retry call lets the server issue a fresh SID (stored by
         FillCookieAndHeader), even though the response body still reports
         "session lost" while the new session activates server-side.
      2. If we reset recently (within cooldown), skip clearing — the freshly
         issued SID is preserved and retried directly.

    Rapid consecutive resets would destroy each newly-issued SID before it
    activates, so the 300-second cooldown keeps the latest SID intact until
    the server accepts it.
    """

    _RESET_COOLDOWN = 300  # seconds — new SID takes several minutes to activate server-side

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._session_reset_at = 0.0

    def Execute(self, service_name, json_data=None, invoke_type=InvokeMethod.SYNC):
        result = super().Execute(service_name, json_data, invoke_type)
        if isinstance(result, str) and _is_session_expired(result):
            now = time.monotonic()
            if now - self._session_reset_at >= self._RESET_COOLDOWN:
                logger.warning("[k3cloud] session expired, re-establishing SID...")
                self._session_reset_at = now
                if hasattr(self, "cookiesStore"):
                    self.cookiesStore = CookieStore()
                else:
                    logger.warning(
                        "[k3cloud] SDK internals changed: cookiesStore not found, cannot reset SID"
                    )
                super().Execute(
                    service_name, json_data, invoke_type
                )  # establishes SID, result discarded
            else:
                logger.warning("[k3cloud] session recovering, SID not yet active — skipping retry")
        return result
