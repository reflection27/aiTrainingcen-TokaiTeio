# SenseVoice 语音识别插件

## 插件简介

SenseVoice是由阿里巴巴达摩院开源的多语言语音识别模型，支持中文、英文、日文、粤语、韩语等多种语言的语音识别。

## 目录结构

```
SenseVoice/
├── PLUGIN_README.md       # 插件说明文档
├── sensevoice_asr.py      # ASR核心模块
├── config.py             # 插件配置
├── requirements.txt      # 依赖包列表
├── pretrained_models/    # 预训练模型目录
│   └── SenseVoiceSmall/  # SenseVoice小模型
└── api.py               # API服务接口
```

## 功能特性

1. **多语言支持**：自动识别中文、英文、日文、粤语、韩语等多种语言
2. **本地推理**：所有语音识别处理在本地进行，保护隐私
3. **灵活配置**：支持自定义采样率、语言设置等参数
4. **简单易用**：提供简洁的API接口，易于集成

## 安装说明

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 下载模型

将SenseVoice模型下载到`pretrained_models/SenseVoiceSmall/`目录下。

模型下载地址：
- Hugging Face: https://huggingface.co/FunAudioLLM/SenseVoiceSmall

### 3. 配置模型路径

在`config.py`中配置模型路径，默认路径为：
```python
MODEL_PATH = os.path.join(os.path.dirname(__file__), "pretrained_models", "SenseVoiceSmall")
```

## 使用方法

### 基本使用

```python
from sensevoice_asr import SenseVoiceASR

# 初始化ASR
asr = SenseVoiceASR(model_path="path/to/model")

# 录音并识别
text = asr.record_and_transcribe(duration=5)  # 录音5秒
print(f"识别结果: {text}")
```

### API服务

启动API服务：
```bash
python api.py
```

API端点：
- `POST /transcribe` - 语音识别
- `POST /record` - 录音并识别

## 配置参数

- `model_path`: SenseVoice模型路径
- `sample_rate`: 音频采样率（默认16000）
- `language`: 语言设置（默认"auto"）
- `use_itn`: 是否使用ITN（默认False）

## 注意事项

1. 首次使用需要下载模型文件，模型大小约200MB
2. 建议使用GPU加速，CPU推理速度较慢
3. 确保麦克风设备正常工作
4. 录音时注意环境噪音，影响识别准确率

## 技术支持

- SenseVoice项目地址: https://github.com/FunAudioLLM/SenseVoice
- FunASR文档: https://github.com/alibaba-damo-academy/FunASR
