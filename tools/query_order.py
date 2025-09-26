from collections.abc import Generator
from typing import Any
import logging
import time
import hashlib

from dify_plugin.config.logger_format import plugin_logger_handler
import httpx
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(plugin_logger_handler)

ORDER_STATUS_MAP = {
    0: "未支付",
    1: "支付成功",
    2: "已退款"
}

def _get_params(payload):
    sorted_items = sorted(payload.items(), key=lambda x: x[0])
    param_str = ""
    for key, value in sorted_items:
        if key is not None and key != "":
            if value is not None and value != "":
                param_str += f"{key}={value}&"
    sign_str = param_str[:-1]
    payload["sign"] = hashlib.md5(sign_str.encode('utf-8')).hexdigest()
    payload.pop("key", None)
    return payload

class QueryOrderTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        order_no = tool_parameters.get("order_no")
        if not order_no and self.session.storage.exist(self.session.conversation_id):
            order_no = self.session.storage.get(self.session.conversation_id).decode("utf-8")
        if not order_no:
            raise ValueError("未获取到订单号")
        
        url = "https://www.cuupay.com/api/query_order"
        payload = {
            "uid": self.runtime.credentials.get("uid"),
            "key": self.runtime.credentials.get("api_key"),
            "time": int(time.time()),
            "third_trade_no": order_no
        }
        logger.info(f"发送订单参数: {payload}")
        payload = _get_params(payload)
        response = httpx.get(url, params=payload).json()
        logger.info(f"查询订单响应: {response}")
        if response.get("code") != 200:
            raise ValueError(response.get("message"))
        
        status = response.get("data").get("state")
        count = 0 
        while status == 0:
            time.sleep(1)
            count += 1
            if count > 120:
                logger.info(f"订单超时未支付")
                break
            response = httpx.get(url, params=payload).json()
            status = response.get("data").get("status")
        order_status = ORDER_STATUS_MAP.get(status, "未知状态")
        yield self.create_text_message(order_status)
        yield self.create_json_message(response)
        