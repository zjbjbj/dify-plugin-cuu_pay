from collections.abc import Generator
from typing import Any
import logging
import time
import hashlib
import urllib.parse
import decimal
import urllib.request
import base64
import uuid
from dify_plugin.config.logger_format import plugin_logger_handler
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(plugin_logger_handler)

class CreateOrderTool(Tool):
    def _get_money(self, money):
        try:
            money_decimal = decimal.Decimal(str(money))
            if not (decimal.Decimal('1.00') <= money_decimal <= decimal.Decimal('2000.00')):
                raise ValueError(f"金额 {money} 超出范围 1.00-2000.00")
            if money_decimal.as_tuple().exponent < -2:
                raise ValueError(f"金额 {money} 小数位数超过2位")
        except (decimal.InvalidOperation, TypeError):
            raise ValueError(f"无效的金额格式: {money}")
        return money_decimal
    def _url_to_qr_code_base64(self,url):
        api_url = "https://api.qrserver.com/v1/create-qr-code/"
        params = {
            'data': url,
            'size': "200x200"
        }
        query_string = urllib.parse.urlencode(params)
        full_url = f"{api_url}?{query_string}"
        # 获取二维码图像
        with urllib.request.urlopen(full_url) as response:
            image_data = response.read()
        # 转换为base64
        base64_data = base64.b64encode(image_data).decode('utf-8')
        return f"data:image/png;base64,{base64_data}"

    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        money = self._get_money(tool_parameters.get("money"))
        title = tool_parameters.get("title")
        type = tool_parameters.get("type")
        return_url = tool_parameters.get("return_url")
        notify_url = self.runtime.credentials.get("notify_url")
        if type == "微信":
            pay_type = "wxpay"
        elif type == "支付宝":
            pay_type = "alipay"
        else:
            raise ValueError(f"不支持的支付类型: {type}")
        if len(title) > 100:
            raise ValueError(f"订单标题长度 {len(title)}， 超过100个字符")
        desc = tool_parameters.get("desc")
        if desc and len(desc) > 200:
            raise ValueError(f"订单描述长度 {len(desc)}， 超过200个字符")
        if not return_url:
            return_url = "https://www.cuupay.com/paySuccess.html"
        if not notify_url:
            notify_url = "https://www.cuupay.com/login/qqlogin/isSuccess"        
        base_url = "https://www.cuupay.com/submit"
        order_no =  str(uuid.uuid4()).replace('-', '')
        payload = {
            "uid": self.runtime.credentials.get("uid"),
            "key": self.runtime.credentials.get("api_key"),
            "trade_name": title,
            "remarks": desc,
            "time": int(time.time()),
            "mod": "api",
            "type": pay_type,
            "third_trade_no": order_no,
            "notify_url": notify_url,
            "return_url": return_url,
            "money":money
        }

        logger.info(f"发送订单参数: {payload}")
        sorted_items = sorted(payload.items(), key=lambda x: x[0])
        param_str = ""
        for key, value in sorted_items:
            if key is not None and key != "":
                if value is not None and value != "":
                    param_str += f"{key}={value}&"
        sign_str = param_str[:-1]
        payload["sign"] = hashlib.md5(sign_str.encode('utf-8')).hexdigest()
        payload.pop("key", None)
        encoded_params = urllib.parse.urlencode(payload)
        full_url = f"{base_url}?{encoded_params}"

        if self.session.conversation_id:
            self.session.storage.set(self.session.conversation_id, order_no.encode("utf-8"))
        yield self.create_text_message(order_no)

        b64 = self._url_to_qr_code_base64(full_url)
        if ',' in b64:
            prefix, b64 = b64.split(',', 1)
            mime_type = prefix.split(';')[0].split(':')[1]
        else:
            mime_type = 'image/png'
        
        try:
            binary_data = base64.b64decode(b64)
            yield self.create_blob_message(blob=binary_data, meta={"mime_type": mime_type})
        except Exception as e:
            raise ValueError(f"二维码数据解码失败: {str(e)}")
        
