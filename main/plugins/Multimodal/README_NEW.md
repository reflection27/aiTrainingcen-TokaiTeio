# Multimodal 插件

多模态处理插件，用于集成 GLM-4V-Flash 多模态模型，实现屏幕内容识别和图像理解功能。

## 功能特性

1. **屏幕捕获**：支持全屏、指定区域和活动窗口的截图
2. **图像识别**：使用 GLM-4V-Flash 模型进行图像内容理解
3. **多模态对话**：结合图像和文本进行智能对话
4. **灵活配置**：支持自定义模型参数和截图选项

## 文件结构

```
Multimodal/
├── __init__.py                 # 模块初始化文件
├── glm4v_client.py             # GLM-4V-Flash 客户端实现
├── screen_capture.py           # 屏幕捕获模块
├── multimodal_processor.py     # 多模态处理器
├── config.json                 # 配置文件
├── integration_example.py      # 集成示例
├── INTEGRATION_GUIDE.md       # 集成指南
└── README.md                  # 使用说明
```

## 配置文件

多模态处理器使用 `config.json` 文件进行配置，该文件位于 Multimodal 插件目录下。配置文件包含以下内容：

```json
{
  "glm4v_base_url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
  "default_model": "glm-4v-flash",
  "text_model": "deepseek-chat",
  "default_temperature": 0.7,
  "default_max_tokens": 1024,
  "screenshot_save_dir": "temp_screenshots",
  "auto_capture": false,
  "character_info": {
    "name": "东海帝王",
    "role": "赛马娘世界观特雷森学园的一名学生赛马娘"
  },
  "multimodal_instruction": "【多模态处理能力】\n你具备同时处理文本和图像内容能力..."
}
```

### 环境变量配置

为了安全起见，API密钥应通过环境变量配置，而不是直接写在配置文件中。

1. 在项目根目录下创建 `.env` 文件（参考 `.env.example` 文件）
2. 添加以下内容：

```env
# GLM-4V API密钥
GLM4V_API_KEY=your_glm4v_api_key_here
```

3. 程序会自动从环境变量中读取API密钥

**注意**：`.env` 文件已被添加到 `.gitignore`，不会被提交到版本控制系统。

### 配置参数说明

- `glm4v_base_url`: API基础URL（默认为智谱AI的API地址）
- `default_model`: 默认使用的多模态模型（默认为"glm-4v-flash"）
- `text_model`: 纯文本模型名称（默认为"deepseek-chat"）
- `default_temperature`: 默认温度参数（默认为0.7）
- `default_max_tokens`: 默认最大token数（默认为1024）
- `screenshot_save_dir`: 截图保存目录（默认为"temp_screenshots"）
- `auto_capture`: 是否启用自动截屏（默认为false）
- `character_info`: 角色信息，包含name和role
- `multimodal_instruction`: 多模态处理指令

**注意**：`GLM4V_API_KEY` 应通过环境变量配置，不应出现在配置文件中。

## 使用方法

### 1. 初始化多模态处理器

```python
from plugins.Multimodal.multimodal_processor import MultimodalProcessor

# 方式1：使用配置文件（推荐）
processor = MultimodalProcessor()

# 方式2：使用配置文件，但覆盖部分参数
processor = MultimodalProcessor(
    api_key="your_api_key",  # 覆盖配置文件中的API密钥
    auto_capture=True  # 覆盖配置文件中的自动截屏设置
)

# 方式3：不使用配置文件，完全使用参数
processor = MultimodalProcessor(
    api_key="your_api_key",
    base_url="https://open.bigmodel.cn/api/paas/v4/chat/completions",
    save_dir="temp_screenshots",
    default_model="glm-4v-flash",
    text_model="deepseek-chat"
)
```

**注意**：推荐使用配置文件方式初始化，这样可以统一管理所有配置参数，便于维护和修改。

### 2. 自动截屏和智能判断

```python
# 启用自动截屏
processor.set_auto_capture(True)

# 处理用户消息，自动截屏并让模型自行判断是否需要参考截屏
result = processor.process_with_auto_capture(
    user_text="屏幕上显示的是什么？",
    system_prompt="你是一个屏幕内容分析专家",
    capture_type="full"
)

# 获取模型响应和是否使用了截屏
print(result["response"])
print(f"是否使用了截屏: {result['used_screenshot']}")
print(f"使用的模型: {result['model']}")
```

**说明**：
- 系统会自动截屏，然后将截屏和用户问题一起发送给多模态模型
- 模型会根据系统提示词的指导，自行判断是否需要参考截屏内容
- 如果问题与屏幕相关，模型会参考截屏内容回答
- 如果问题与屏幕无关，模型会忽略截屏，直接基于知识库回答
- 这种方式只需要一次模型调用，响应更快，决策更准确

### 3. 处理屏幕内容和文本输入

```python
# 截取屏幕
screenshot_path = processor.capture_full_screen()

# 处理屏幕内容和文本输入
response = processor.process_screen_with_text(
    image_path=screenshot_path,
    text="请描述屏幕上的内容",
    system_prompt="你是一个屏幕内容分析专家"
)
```

## 自动截屏和智能判断功能说明

自动截屏和智能判断功能允许系统在用户发送消息时自动截屏，并让多模态模型自行判断是否需要参考截屏：

1. **启用自动截屏**：通过 `set_auto_capture(True)` 启用自动截屏功能
2. **智能判断**：多模态模型会根据用户的问题自行判断是否需要参考截屏内容
3. **模型处理**：
   - 系统始终使用多模态模型（GLM-4V-Flash）处理
   - 模型会根据问题内容决定是否参考截屏
   - 如果问题与屏幕无关，模型会忽略截屏，直接基于知识库回答
4. **结果反馈**：返回结果中包含 `used_screenshot` 字段，指示是否使用了截屏

这种设计的优势：
- **更低的延迟**：只需要一次模型调用，无需额外的判断步骤
- **更智能的决策**：模型能够更准确地判断是否需要参考截屏
- **更简洁的流程**：减少了系统复杂度，提高了可维护性
- **更好的用户体验**：响应更快，决策更准确

## 应用场景

1. **屏幕内容分析**：分析屏幕上显示的内容
2. **界面导航**：帮助用户理解和操作界面
3. **错误诊断**：识别和分析屏幕上的错误信息
4. **内容审核**：检查屏幕内容是否符合规范
5. **智能对话助手**：自动截屏并智能判断用户是否在讨论屏幕内容，根据判断结果选择合适的模型进行响应

## 注意事项

1. **API密钥安全**：请勿将API密钥提交到版本控制系统，使用环境变量配置
2. **屏幕权限**：确保程序有权限访问屏幕进行截屏
3. **性能考虑**：多模态处理会增加响应延迟，可以根据需要调整 `auto_capture` 设置
4. **成本控制**：多模态模型调用会产生额外费用，请注意控制使用频率
5. **隐私保护**：截屏可能包含敏感信息，请注意保护用户隐私

## 集成指南

详细的集成指南请参考 [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)。

## 环境变量配置

详细的环境变量配置指南请参考 [ENV_SETUP.md](../../ENV_SETUP.md)。
