from typing import Any

import time
import hashlib
import urllib.parse
from decimal import Decimal
import qrcode
from io import BytesIO
import base64
from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError


class PayProvider(ToolProvider):

    def _url_to_qr_code_base64(self,url):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        # 添加URL数据
        qr.add_data(url)
        qr.make(fit=True)
        # 生成二维码图片
        img = qr.make_image(fill_color="black", back_color="white")
        # 将图片转换为Base64编码
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
        return qr_code_base64
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
                    "return_url": "https://www.cuupay.com/login/qqlogin/paySuccess",
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

