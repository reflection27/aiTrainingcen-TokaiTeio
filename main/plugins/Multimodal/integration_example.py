"""
多模态处理器集成示例
展示如何在主程序中集成多模态处理器
"""

from plugins.Multimodal.multimodal_processor import MultimodalProcessor
from typing import Optional, Dict, Any

class MultimodalIntegration:
    """多模态集成类，用于在主程序中集成多模态处理"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化多模态集成

        Args:
            config: 主程序配置字典
        """
        # 初始化多模态处理器
        self.multimodal_processor = MultimodalProcessor(
            api_key=config.get("glm4v_api_key", ""),
            base_url=config.get("glm4v_base_url", "https://open.bigmodel.cn/api/paas/v4/chat/completions"),
            save_dir=config.get("screenshot_save_dir", "temp_screenshots"),
            default_model=config.get("default_model", "glm-4v-flash"),
            text_model=config.get("text_model", "deepseek-chat"),
            auto_capture=config.get("auto_capture", False)
        )

        # 是否启用多模态处理
        self.enabled = config.get("multimodal_enabled", False)

    def enable(self):
        """启用多模态处理"""
        self.enabled = True
        self.multimodal_processor.set_auto_capture(True)

    def disable(self):
        """禁用多模态处理"""
        self.enabled = False
        self.multimodal_processor.set_auto_capture(False)

    def process_user_message(
        self,
        user_text: str,
        system_prompt: Optional[str] = None,
        capture_type: str = "full"
    ) -> Dict[str, Any]:
        """
        处理用户消息，使用多模态处理器

        Args:
            user_text: 用户输入的文本
            system_prompt: 系统提示词
            capture_type: 截图类型 ("full", "region", "window")

        Returns:
            包含处理结果的字典:
            {
                "response": 模型响应文本,
                "used_screenshot": 是否使用了截屏,
                "model": 使用的模型
            }
        """
        if not self.enabled:
            return {
                "response": None,
                "used_screenshot": False,
                "model": None,
                "error": "多模态处理未启用"
            }

        # 使用多模态处理器处理用户消息
        result = self.multimodal_processor.process_with_auto_capture(
            user_text=user_text,
            system_prompt=system_prompt,
            capture_type=capture_type
        )

        return {
            "response": result["response"],
            "used_screenshot": result["used_screenshot"],
            "model": result["model"]
        }


# 使用示例
if __name__ == "__main__":
    # 示例配置
    config = {
        "glm4v_api_key": "your_api_key",  # 替换为你的API密钥
        "glm4v_base_url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        "screenshot_save_dir": "temp_screenshots",
        "default_model": "glm-4v-flash",
        "text_model": "deepseek-chat",
        "auto_capture": True,
        "multimodal_enabled": True
    }

    # 创建多模态集成实例
    multimodal_integration = MultimodalIntegration(config)

    # 处理用户消息
    result = multimodal_integration.process_user_message(
        user_text="屏幕上显示的是什么？",
        system_prompt="你是一个屏幕内容分析专家"
    )

    # 打印结果
    print(f"响应: {result['response']}")
    print(f"是否使用了截屏: {result['used_screenshot']}")
    print(f"使用的模型: {result['model']}")
