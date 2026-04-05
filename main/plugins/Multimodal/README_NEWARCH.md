# 多模态处理功能说明

## 概述

多模态处理功能现在采用新的架构，将图片识别和角色扮演分离：
1. 多模态模型仅负责识别图片内容
2. 主程序负责角色扮演和对话生成
3. 主程序结合用户对话和图片识别结果来生成回复

## 工作流程

1. **截屏**: 系统自动截取当前屏幕
2. **图片识别**: 多模态模型识别图片内容，生成客观描述
3. **增强输入**: 将图片描述添加到用户输入中
4. **角色扮演**: 主程序根据增强后的用户输入生成角色扮演回复

## 配置

在 `ai_agent_config.json` 中配置以下参数：

```json
{
  "glm4v_api_key": "your_api_key",  // GLM-4V API密钥
  "glm4v_base_url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",  // API基础URL
  "default_model": "glm-4v",  // 默认多模态模型
  "text_model": "deepseek-chat",  // 文本模型
  "multimodal_enabled": true  // 是否启用多模态处理
}
```

## 使用方法

1. 在 `ai_agent_config.json` 中设置 `multimodal_enabled` 为 `true`
2. 配置 `glm4v_api_key`
3. 重启程序

## 注意事项

- 多模态模型仅识别图片内容，不进行角色扮演
- 主程序负责角色扮演和对话生成
- 图片描述会自动添加到用户输入中，格式为 `[图片内容]\n{description}`
- 临时截图会在处理完成后自动清理
