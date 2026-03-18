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
└── README.md                   # 使用说明
```

## 配置文件

多模态处理器使用 `config.json` 文件进行配置，该文件位于 Multimodal 插件目录下。配置文件包含以下内容：

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
  "character_info": {
    "name": "东海帝王",
    "role": "赛马娘世界观特雷森学园的一名学生赛马娘"
  },
  "multimodal_instruction": "【多模态处理能力】\n你具备同时处理文本和图像内容的能力..."
}
```

### 配置参数说明

- `glm4v_api_key`: 智谱AI的API密钥（必需）
- `glm4v_base_url`: API基础URL（默认为智谱AI的API地址）
- `default_model`: 默认使用的多模态模型（默认为"glm-4v-flash"）
- `text_model`: 纯文本模型名称（默认为"deepseek-chat"）
- `default_temperature`: 默认温度参数（默认为0.7）
- `default_max_tokens`: 默认最大token数（默认为1024）
- `screenshot_save_dir`: 截图保存目录（默认为"temp_screenshots"）
- `auto_capture`: 是否启用自动截屏（默认为false）
- `character_info`: 角色信息，包含name和role
- `multimodal_instruction`: 多模态处理指令

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
# 处理全屏截图和文本
result = processor.process_screen_with_text(
    text="请描述屏幕上的内容",
    system_prompt="你是一个屏幕内容分析专家",
    capture_type="full",
    keep_screenshot=True
)

# 获取模型响应
print(result["response"])
```

### 4. 处理指定图片和文本输入

```python
# 处理指定图片和文本
result = processor.process_image_with_text(
    text="这张图片中有什么？",
    image_path="path/to/image.jpg",
    system_prompt="你是一个图像分析专家"
)

# 获取模型响应
print(result["response"])
```

## 参数说明

### MultimodalProcessor 初始化参数

- `api_key`: 智谱AI的API密钥（必需）
- `base_url`: API基础URL（默认为智谱AI的API地址）
- `save_dir`: 截图保存目录（默认为"temp_screenshots"）
- `default_model`: 默认使用的模型（默认为"glm-4v-flash"）
- `default_temperature`: 默认温度参数（默认为0.7）
- `default_max_tokens`: 默认最大token数（默认为None）
- `text_model`: 纯文本模型名称，用于处理与截屏无关的对话（默认为"deepseek-chat"）

### 自动截屏和话题判断功能

#### set_auto_capture 方法
- `enabled`: 是否启用自动截屏（布尔值）

#### process_with_auto_capture 参数
- `user_text`: 用户输入的文本（必需）
- `system_prompt`: 系统提示词（可选）
- `capture_type`: 截图类型，可选值为 "full"、"region"、"window"（默认为"full"）
- `region`: 区域坐标 (x, y, width, height)，当capture_type="region"时使用（可选）
- `temperature`: 温度参数（可选）
- `max_tokens`: 最大token数（可选）
- `keep_screenshot`: 是否保留截图文件（默认为False）

返回值包含：
- `response`: 模型响应文本
- `screenshot_path`: 截图路径（如果保留）
- `model`: 使用的模型
- `temperature`: 使用的温度参数
- `used_screenshot`: 是否使用了截屏（布尔值）

### process_screen_with_text 参数

- `text`: 用户输入的文本（必需）
- `system_prompt`: 系统提示词（可选）
- `capture_type`: 截图类型，可选值为 "full"、"region"、"window"（默认为"full"）
- `region`: 区域坐标 (x, y, width, height)，当capture_type="region"时使用（可选）
- `resize`: 是否调整截图大小（默认为False）
- `max_width`: 最大宽度，当resize=True时使用（默认为1024）
- `max_height`: 最大高度，当resize=True时使用（默认为1024）
- `temperature`: 温度参数（可选）
- `max_tokens`: 最大token数（可选）
- `keep_screenshot`: 是否保留截图文件（默认为False）

## 依赖项

- requests: 用于HTTP请求
- pyautogui: 用于屏幕捕获
- Pillow: 用于图像处理

## 注意事项

1. 使用前请确保已获取智谱AI的API密钥
2. 屏幕捕获功能在不同操作系统上可能有差异
3. 调整截图大小可以提高API调用速度，但可能会降低识别精度
4. 建议根据实际需求调整temperature和max_tokens参数

## 示例应用场景

1. **屏幕内容分析**：分析当前屏幕显示的内容，提取关键信息
2. **UI测试**：检查应用程序界面的显示效果
3. **辅助功能**：为视障用户提供屏幕内容描述
4. **自动化测试**：结合屏幕截图进行自动化测试
5. **内容审核**：检查屏幕内容是否符合规范
6. **智能对话助手**：自动截屏并智能判断用户是否在讨论屏幕内容，根据判断结果选择合适的模型进行响应

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
