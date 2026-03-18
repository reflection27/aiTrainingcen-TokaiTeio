# 多模态处理器集成指南

本指南说明如何在主程序中集成多模态处理器。

## 1. 在主程序中初始化多模态处理器

在 `improved_ai_agent.py` 的 `ImprovedAIAgent` 类中添加多模态处理器的初始化：

```python
def __init__(self, config: Dict):
    # ... 现有代码 ...

    # 初始化多模态处理器
    self.multimodal_processor = None
    self.multimodal_enabled = False
    self._init_multimodal_processor(config)

def _init_multimodal_processor(self, config: Dict):
    """初始化多模态处理器"""
    try:
        from plugins.Multimodal.multimodal_processor import MultimodalProcessor

        # 检查是否配置了多模态API密钥
        import os
        glm4v_api_key = config.get("glm4v_api_key", "") or os.getenv("GLM4V_API_KEY", "")
        if not glm4v_api_key:
            print("ℹ️ 未配置多模态API密钥，多模态功能已禁用")
            return

        # 初始化多模态处理器
        self.multimodal_processor = MultimodalProcessor(
            api_key=glm4v_api_key,
            base_url=config.get("glm4v_base_url", "https://open.bigmodel.cn/api/paas/v4/chat/completions"),
            save_dir=config.get("screenshot_save_dir", "temp_screenshots"),
            default_model=config.get("default_model", "glm-4v-flash"),
            text_model=config.get("text_model", "deepseek-chat"),
            auto_capture=config.get("auto_capture", False)
        )

        # 设置是否启用多模态处理
        self.multimodal_enabled = config.get("multimodal_enabled", False)

        if self.multimodal_enabled:
            self.multimodal_processor.set_auto_capture(True)
            print("✅ 多模态处理器已初始化并启用")
        else:
            print("✅ 多模态处理器已初始化但未启用")

    except Exception as e:
        print(f"⚠️ 多模态处理器初始化失败: {str(e)}")
        self.multimodal_processor = None
        self.multimodal_enabled = False
```

## 2. 在处理用户消息时调用多模态处理器

修改 `improved_ai_agent.py` 中的 `_process_request` 方法，添加多模态处理逻辑：

```python
async def _process_request(
    self,
    user_input: str,
    user_id: str,
    session_id: str,
    cache_key: str,
    fast_mode: bool = None,
    stream_callback=None
) -> str:
    """处理请求的核心逻辑"""
    import time
    start_time = time.time()

    # 获取当前事件循环
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # 如果fast_mode未指定，则判断是否使用快速模式
    if fast_mode is None:
        fast_mode = self._is_simple_query(user_input)

    try:
        # 检查是否启用多模态处理
        if self.multimodal_enabled and self.multimodal_processor:
            # 使用多模态处理器处理用户消息
            result = self.multimodal_processor.process_with_auto_capture(
                user_text=user_input,
                system_prompt=self._get_system_prompt(),
                capture_type="full"
            )

            # 如果多模态处理器返回了响应，直接使用
            if result["response"]:
                response = result["response"]
                print(f"📸 多模态处理完成，使用截屏: {result['used_screenshot']}")
            else:
                # 多模态处理器未返回响应，使用常规处理流程
                response = await self._process_with_memory(user_input, session_id, fast_mode, stream_callback)
        else:
            # 未启用多模态处理，使用常规处理流程
            response = await self._process_with_memory(user_input, session_id, fast_mode, stream_callback)

        # ... 现有的保存对话、缓存等逻辑 ...

        return response
    finally:
        # 清除待处理请求标记
        if cache_key in self.pending_requests:
            del self.pending_requests[cache_key]

async def _process_with_memory(
    self,
    user_input: str,
    session_id: str,
    fast_mode: bool,
    stream_callback=None
) -> str:
    """使用记忆系统处理用户消息"""
    # ... 现有的处理逻辑 ...
    # 这里是原有的处理流程，包括获取上下文、调用AI等
    pass
```

## 3. 在配置文件中添加多模态相关配置

在 `ai_agent_config.json` 中添加多模态相关配置：

```json
{
  "glm4v_api_key": "",
  "glm4v_base_url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
  "default_model": "glm-4v-flash",
  "text_model": "deepseek-chat",
  "default_temperature": 0.7,
  "default_max_tokens": 1024,
  "screenshot_save_dir": "temp_screenshots",
  "auto_capture": false,
  "multimodal_enabled": false,
  "character_info": {
    "name": "东海帝王",
    "role": "赛马娘世界观特雷森学园的一名学生赛马娘"
  }
}
```

## 4. 在设置界面中添加多模态开关

在 `settings_dialog.py` 中添加多模态开关：

```python
# 在设置对话框中添加多模态开关
self.multimodal_enabled_checkbox = QCheckBox("启用多模态处理")
self.multimodal_enabled_checkbox.setChecked(self.config.get("multimodal_enabled", False))
self.multimodal_enabled_checkbox.stateChanged.connect(self.on_multimodal_enabled_changed)

def on_multimodal_enabled_changed(self, state):
    """多模态开关状态改变"""
    enabled = state == Qt.Checked
    self.config["multimodal_enabled"] = enabled

    # 更新AI Agent的多模态设置
    if hasattr(self, 'ai_agent') and self.ai_agent:
        if enabled:
            self.ai_agent.multimodal_enabled = True
            if self.ai_agent.multimodal_processor:
                self.ai_agent.multimodal_processor.set_auto_capture(True)
        else:
            self.ai_agent.multimodal_enabled = False
            if self.ai_agent.multimodal_processor:
                self.ai_agent.multimodal_processor.set_auto_capture(False)
```

## 5. 测试多模态功能

完成集成后，可以通过以下步骤测试多模态功能：

1. 在 `ai_agent_config.json` 中配置 `glm4v_api_key`
2. 启用 `multimodal_enabled` 和 `auto_capture`
3. 运行主程序
4. 发送与屏幕相关的问题，例如："屏幕上显示的是什么？"
5. 观察日志输出，确认是否使用了截屏

## 注意事项

1. **API密钥**：确保在配置文件中正确配置了 `glm4v_api_key`
2. **权限**：确保程序有权限访问屏幕进行截屏
3. **性能**：多模态处理会增加响应延迟，可以根据需要调整 `auto_capture` 设置
4. **成本**：多模态模型调用会产生额外费用，请注意控制使用频率
5. **隐私**：截屏可能包含敏感信息，请注意保护用户隐私
