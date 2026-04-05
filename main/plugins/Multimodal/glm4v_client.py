"""
GLM-4V-Flash 客户端实现
用于调用智谱AI的多模态模型 GLM-4V-Flash
"""

import requests
import base64
from typing import Optional, Dict, Any

class GLM4VFlashClient:
    """GLM-4V-Flash 客户端类"""

    def __init__(self, api_key: str, base_url: str = "https://open.bigmodel.cn/api/paas/v4/chat/completions", model: str = "glm-4v-flash"):
        """
        初始化 GLM-4V 客户端

        Args:
            api_key: 智谱AI的API密钥
            base_url: API基础URL
            model: 模型名称
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def encode_image(self, image_path: str) -> str:
        """
        将图片文件编码为base64字符串

        Args:
            image_path: 图片文件路径

        Returns:
            base64编码的图片字符串
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def call_model(
        self,
        messages: list,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        调用 GLM-4V-Flash 模型

        Args:
            messages: 消息列表，支持文本和图片
            model: 模型名称
            temperature: 温度参数，控制随机性
            max_tokens: 最大生成token数
            top_p: 核采样参数

        Returns:
            模型响应结果
        """
        payload = {
            "model": model if model is not None else self.model,
            "messages": messages,
            "temperature": temperature
        }

        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if top_p is not None:
            payload["top_p"] = top_p

        response = requests.post(
            self.base_url,
            headers=self.headers,
            json=payload
        )

        response.raise_for_status()
        return response.json()

    def chat_with_image(
        self,
        text: str,
        image_path: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> str:
        """
        使用图片和文本进行对话

        Args:
            text: 用户输入的文本
            image_path: 图片文件路径
            system_prompt: 系统提示词
            temperature: 温度参数
            max_tokens: 最大生成token数
            stream: 是否使用流式输出

        Returns:
            模型生成的文本响应
        """
        # 构建消息列表
        messages = []

        # 添加系统提示词（如果有）
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })

        # 添加用户消息，包含文本和图片
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": text
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{self.encode_image(image_path)}"
                    }
                }
            ]
        })

        # 调用模型
        if stream:
            return self._stream_chat_with_image(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
        else:
            response = self.call_model(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            # 提取并返回生成的文本
            return response["choices"][0]["message"]["content"]

    def _stream_chat_with_image(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        流式调用GLM-4V模型

        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大生成token数

        Returns:
            模型生成的完整文本响应
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": True
        }

        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        response = requests.post(
            self.base_url,
            headers=self.headers,
            json=payload,
            stream=True
        )

        response.raise_for_status()
        
        full_response = ""
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data = line[6:]  # 移除 'data: ' 前缀
                    if data == '[DONE]':
                        break
                    try:
                        import json
                        chunk = json.loads(data)
                        if 'choices' in chunk and len(chunk['choices']) > 0:
                            delta = chunk['choices'][0].get('delta', {})
                            content = delta.get('content', '')
                            full_response += content
                    except json.JSONDecodeError:
                        continue

        return full_response
