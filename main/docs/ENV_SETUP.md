# 环境变量配置指南

本文档说明如何配置环境变量，以便安全地使用API密钥。

## 为什么使用环境变量？

使用环境变量存储敏感信息（如API密钥）有以下好处：

1. **安全性**：避免将敏感信息提交到版本控制系统
2. **灵活性**：可以在不同环境中使用不同的配置
3. **便捷性**：无需修改代码即可更改配置

## 配置步骤

### 1. 创建环境变量文件

在项目根目录下创建 `.env` 文件：

```bash
# 复制示例文件
cp .env.example .env
```

### 2. 编辑环境变量文件

使用文本编辑器打开 `.env` 文件，填入你的API密钥：

```env
# DeepSeek API密钥
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# GLM-4V API密钥
GLM4V_API_KEY=your_glm4v_api_key_here
```

### 3. 加载环境变量

程序会自动从环境变量中读取API密钥。如果环境变量未设置，程序会尝试从配置文件中读取。

## 获取API密钥

### DeepSeek API密钥

1. 访问 [DeepSeek官网](https://platform.deepseek.com/)
2. 注册/登录账号
3. 在控制台中创建API密钥
4. 将API密钥复制到 `.env` 文件中

### GLM-4V API密钥

1. 访问 [智谱AI开放平台](https://open.bigmodel.cn/)
2. 注册/登录账号
3. 在控制台中创建API密钥
4. 将API密钥复制到 `.env` 文件中

## 配置文件说明

### ai_agent_config.json

配置文件包含应用程序的各种设置，但不包含敏感信息。主要配置项包括：

- `selected_model`: 选择的AI模型
- `glm4v_base_url`: GLM-4V API基础URL
- `default_model`: 默认使用的多模态模型
- `text_model`: 纯文本模型名称
- `default_temperature`: 默认温度参数
- `default_max_tokens`: 默认最大token数
- `screenshot_save_dir`: 截图保存目录
- `auto_capture`: 是否启用自动截屏
- `multimodal_enabled`: 是否启用多模态处理

### .gitignore

`.gitignore` 文件确保以下文件不会被提交到版本控制系统：

- `.env`: 环境变量文件
- `ai_agent_config.json`: 配置文件
- `temp_screenshots/`: 截图目录
- 其他临时和敏感文件

## 注意事项

1. **不要提交敏感信息**：永远不要将 `.env` 文件或包含API密钥的配置文件提交到版本控制系统
2. **定期更换密钥**：定期更换API密钥以提高安全性
3. **限制权限**：确保 `.env` 文件的权限设置正确，只有授权用户可以访问
4. **使用示例文件**：使用 `.env.example` 和 `ai_agent_config.example.json` 作为模板，创建实际的配置文件

## 故障排除

### 问题：程序提示未配置API密钥

**解决方案**：
1. 检查 `.env` 文件是否存在
2. 检查 `.env` 文件中的API密钥是否正确填写
3. 检查环境变量名称是否正确（区分大小写）

### 问题：程序无法读取环境变量

**解决方案**：
1. 确保在程序启动前设置了环境变量
2. 重启程序，确保环境变量生效
3. 检查操作系统环境变量的设置方式

## 更多信息

- [Python-dotenv文档](https://pypi.org/project/python-dotenv/)
- [环境变量最佳实践](https://12factor.net/config)
