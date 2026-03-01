
# -*- coding: utf-8 -*-
"""
STT客户端
用于在主程序中调用STT服务器
"""

import requests
import json
from typing import Optional

class STTClient:
    """STT客户端类"""

    def __init__(self, base_url: str = "http://127.0.0.1:5001"):
        self.base_url = base_url
        self.timeout = 10  # 请求超时时间（秒），降低以支持实时转录

    def recognize(self, audio_data: bytes) -> Optional[str]:
        """
        语音识别

        Args:
            audio_data: 音频数据（bytes）

        Returns:
            识别到的文本，如果失败则返回None
        """
        try:
            # 调用STT服务器的识别API
            response = requests.post(
                f"{self.base_url}/api/stt/recognize",
                data=audio_data,
                headers={'Content-Type': 'application/octet-stream'},
                timeout=self.timeout
            )

            # 检查响应状态码
            if response.status_code == 200:
                result = response.json()
                text = result.get("text", "")
                # 返回空字符串而不是None，以便调用方可以区分"未识别到文本"和"请求失败"
                return text if text is not None else ""
            else:
                print(f"❌ STT服务器返回错误: {response.status_code}")
                return None
        except requests.exceptions.Timeout:
            print("❌ STT服务器请求超时")
            return None
        except requests.exceptions.ConnectionError:
            print("❌ 无法连接到STT服务器")
            return None
        except Exception as e:
            print(f"❌ STT客户端错误: {str(e)}")
            return None

    def check_status(self) -> bool:
        """
        检查STT服务器状态

        Returns:
            如果STT服务器可用则返回True，否则返回False
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/stt/status",
                timeout=5
            )

            if response.status_code == 200:
                result = response.json()
                return result.get("status") == "ready"
            else:
                return False
        except Exception as e:
            print(f"❌ 检查STT服务器状态失败: {str(e)}")
            return False

    def shutdown(self) -> bool:
        """
        关闭STT服务器

        Returns:
            如果成功关闭则返回True，否则返回False
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/stt/shutdown",
                timeout=5
            )

            return response.status_code == 200
        except Exception as e:
            print(f"❌ 关闭STT服务器失败: {str(e)}")
            return False
