from typing import Any

import time
import hashlib
import urllib.request
import urllib.parse
from decimal import Decimal
import base64
from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError


class PayProvider(ToolProvider):

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

    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        base_url = "https://www.cuupay.com/submit"
        try:

            payload = {
                    "uid": credentials.get("uid"),
                    "key": credentials.get("api_key"),
                    "trade_name": "测试订单",
                    "remarks": "测试描述",
                    "time": int(time.time()),
                    "mod": "api",
                    "type": "alipay",
                    "third_trade_no": str(credentials.get("uid")) + str(int(time.time() * 1000)),
                    "notify_url": credentials.get("notify_url"),
                    "return_url": "https://www.cuupay.com/paySuccess.html",
                    "money": Decimal(100)
                    }

            sorted_items = sorted(payload.items(), key=lambda x: x[0])
            param_str = ""
            for key, value in sorted_items:
                if key is not None and key != "":
                    if value is not None and value != "":
                        param_str += f"{key}={value}&"
            sign_str = param_str[:-1]
            # 生成签名并移除key
            payload["sign"] = hashlib.md5(sign_str.encode('utf-8')).hexdigest()
            payload.pop("key", None)
            encoded_params = urllib.parse.urlencode(payload)
            full_url = f"{base_url}?{encoded_params}"
            return self._url_to_qr_code_base64(full_url)
        except Exception as e:
            raise ToolProviderCredentialValidationError(str(e))

