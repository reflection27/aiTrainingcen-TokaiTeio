# 东海帝王 AI

基于 GPT-SoVITS v2pro 的桌面 AI 语音助手，使用东海帝王（赛马娘）角色音色，支持实时语音输入与语音合成。

## 功能

- **语音合成（TTS）**：GPT-SoVITS v2pro，东海帝王专属音色
- **语音识别（STT）**：RealtimeSTT + Whisper large-v3，实时转文字
- **大语言模型**：DeepSeek / GLM-4V，支持多模态（截图分析）
- **记忆系统**：对话历史摘要与持久化
- **MCP 支持**：可扩展外部工具调用（开发中）
- **Godot 动画**：联动 Godot 角色表情与动作

## 环境要求

- Windows 10/11
- Python 3.11
- NVIDIA 显卡，CUDA 12.x（推理 TTS 使用）
- ffmpeg（setup.bat 自动安装）

## 快速部署

### 1. 克隆仓库

```bash
git clone <仓库地址>
cd <仓库目录>
```

### 2. 一键安装

```
main\setup.bat
```

脚本会自动完成：
- 创建 Python 虚拟环境
- 安装 PyTorch（CUDA 12.1）及所有依赖
- 从 HuggingFace 下载预训练底模（国内走 hf-mirror.com 镜像）
- 从 GitHub Release 下载东海帝王角色权重
- 下载 Godot 4.6.2 可执行文件

### 3. 配置 API Key

编辑 `main/.env`，填入你的 API Key：

```
DEEPSEEK_API_KEY=sk-xxx
GLM4V_API_KEY=xxx
```

也可在 `main/ai_agent_config.json` 中调整其他设置（TTS 参数、模型选择等）。

### 4. 启动

双击根目录的 `start.bat`，依次启动：

1. GPT-SoVITS TTS 服务（端口 9880）
2. 主程序（端口 5000）
3. 实时语音识别

## 项目结构

```
├── start.bat                  # 总启动脚本
└── main/
    ├── setup.bat              # 一键部署脚本
    ├── main.py                # 主程序入口
    ├── ai_agent_config.json   # 主配置文件
    ├── requirements.txt       # Python 依赖
    ├── character/
    │   └── TokaiTeio/         # 角色音色文件与权重
    ├── core/                  # 核心逻辑（AI Agent、STT 等）
    ├── ui/                    # PySide6 界面
    ├── plugins/
    │   ├── GPT-SoVITS/        # TTS 推理引擎
    │   └── godot/             # Godot 角色动画
    └── mcp/                   # MCP 工具扩展（开发中）
```

## 训练新角色

本项目仅保留推理部分。如需训练新角色音色，请使用完整版 [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS) 单独训练，将生成的 `.ckpt` 和 `.pth` 权重文件放入 `character/<角色名>/weights/`，并更新 `ai_agent_config.json` 中的路径即可切换角色。

## 常见问题

**TTS 启动慢** — 首次加载模型需要较长时间，`start.bat` 会自动等待服务就绪后再启动主程序。

**STT 超时退出** — 确保主程序完全启动后（控制台出现"主程序已就绪"）STT 才会开始，无需手动等待。

**CUDA 版本不匹配** — 本项目使用 torch cu121，适配 CUDA 12.x。若使用其他版本请手动替换 `setup.bat` 中的 torch 安装命令。
