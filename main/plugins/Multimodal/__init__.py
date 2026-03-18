"""
Multimodal 插件模块
用于集成 GLM-4V-Flash 多模态模型，实现屏幕内容识别和图像理解功能
"""

from .multimodal_processor import MultimodalProcessor
from .glm4v_client import GLM4VFlashClient
from .screen_capture import ScreenCapture

__all__ = [
    'MultimodalProcessor',
    'GLM4VFlashClient',
    'ScreenCapture'
]
