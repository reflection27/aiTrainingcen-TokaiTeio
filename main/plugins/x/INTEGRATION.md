# SenseVoice插件集成说明

## 插件结构

```
SenseVoice/
├── PLUGIN_README.md       # 插件说明文档
├── INTEGRATION.md         # 集成说明文档（本文件）
├── sensevoice_asr.py      # ASR核心模块
├── config.py             # 插件配置
├── requirements.txt      # 依赖包列表
├── api.py               # API服务接口
├── test_asr.py          # 测试脚本
├── start_api.bat        # 启动API服务的批处理脚本
└── pretrained_models/    # 预训练模型目录
    └── README.md        # 模型下载说明
```

## 集成步骤

### 1. 安装依赖

在SenseVoice插件目录下运行：
```bash
pip install -r requirements.txt
```

### 2. 下载模型

将SenseVoice模型下载到`pretrained_models/SenseVoiceSmall/`目录下。

模型下载地址：
- Hugging Face: https://huggingface.co/FunAudioLLM/SenseVoiceSmall
- ModelScope: https://modelscope.cn/models/iic/SenseVoiceSmall

### 3. 配置主项目

在主项目的`config.py`中添加ASR配置：

```python
# ASR设置
"asr_enabled": False,  # 是否启用ASR
"asr_plugin_path": "plugins/SenseVoice",  # SenseVoice插件路径
"asr_sample_rate": 16000,  # 音频采样率
"asr_language": "auto",  # ASR语言设置：auto, zh, en等
"asr_use_itn": False,  # 是否使用ITN（数字文本化）
```

### 4. 在AI代理中初始化ASR

在`ai_agent.py`的`AIAgent.__init__`方法中添加ASR初始化代码：

```python
# 初始化ASR管理器
try:
    asr_enabled = config.get("asr_enabled", False)
    if asr_enabled:
        asr_plugin_path = config.get("asr_plugin_path", "plugins/SenseVoice")
        asr_sample_rate = config.get("asr_sample_rate", 16000)

        # 导入SenseVoice插件
        import sys
        plugin_dir = os.path.join(os.path.dirname(__file__), asr_plugin_path)
        if plugin_dir not in sys.path:
            sys.path.insert(0, plugin_dir)

        from sensevoice_asr import SenseVoiceASR

        print(f"🔍 初始化ASR管理器，插件路径: {asr_plugin_path}, 采样率: {asr_sample_rate}")
        self.asr_manager = SenseVoiceASR(
            sample_rate=asr_sample_rate,
            language=config.get("asr_language", "auto"),
            use_itn=config.get("asr_use_itn", False)
        )
        self.asr_enabled = True
        print(f"✅ ASR管理器初始化成功，可用性: {self.asr_manager.is_available()}")
    else:
        self.asr_manager = None
        self.asr_enabled = False
        print("ℹ️ ASR功能未启用")
except Exception as e:
    print(f"⚠️ ASR管理器初始化失败: {str(e)}")
    self.asr_manager = None
    self.asr_enabled = False
```

### 5. 在主窗口中添加录音功能

在`main_window.py`中：

1. 添加录音按钮：
```python
# 录音按钮
record_btn = QPushButton("🎤")
record_btn.setToolTip("录音")
record_btn.clicked.connect(self.record_audio)
```

2. 添加录音处理方法：
```python
def record_audio(self):
    """录音并识别"""
    if not hasattr(self.agent, 'asr_manager') or not self.agent.asr_manager.is_available():
        self.add_message("系统", "ASR未配置或不可用")
        return

    self.add_message("系统", "🎤 开始录音，再次点击结束录音...")

    # 在单独的线程中处理录音和识别
    threading.Thread(target=self._run_asr, daemon=True).start()

def _run_asr(self):
    """在单独的线程中运行ASR"""
    try:
        # 获取配置
        language = self.config.get("asr_language", "auto")
        use_itn = self.config.get("asr_use_itn", False)

        # 录音并识别
        text, audio_file = self.agent.asr_manager.record_and_transcribe(
            language=language,
            use_itn=use_itn
        )

        if text:
            # 将识别结果作为用户输入
            self.response_ready.emit(text)
        else:
            self.response_ready.emit("录音识别失败，请重试")
    except Exception as e:
        self.response_ready.emit(f"录音识别错误: {str(e)}")
```

## 使用方式

### 1. 直接使用插件

```python
from plugins.SenseVoice.sensevoice_asr import SenseVoiceASR

# 初始化ASR
asr = SenseVoiceASR()

# 录音并识别
text, audio_file = asr.record_and_transcribe()
print(f"识别结果: {text}")
```

### 2. 使用API服务

启动API服务：
```bash
cd plugins/SenseVoice
python api.py
```

或使用批处理脚本：
```bash
cd plugins/SenseVoice
start_api.bat
```

API端点：
- `GET /` - 服务状态
- `GET /health` - 健康检查
- `POST /transcribe` - 语音识别
- `POST /record` - 录音并识别

### 3. 测试插件

运行测试脚本：
```bash
cd plugins/SenseVoice
python test_asr.py
```

## 注意事项

1. **模型下载**：首次使用需要下载SenseVoice模型，模型大小约200MB
2. **硬件要求**：建议使用GPU加速，CPU推理速度较慢
3. **麦克风设备**：确保麦克风设备正常工作
4. **环境噪音**：录音时注意环境噪音，影响识别准确率
5. **路径配置**：确保插件路径配置正确，使用相对路径

## 故障排除

### 模型加载失败

- 检查模型路径是否正确
- 确认模型文件完整下载
- 检查是否有足够的内存

### 录音失败

- 检查麦克风设备是否正常
- 确认音频采样率配置正确
- 检查是否有权限访问音频设备

### 识别失败

- 检查音频文件格式是否正确
- 确认语言设置是否匹配
- 尝试提高录音质量

## 技术支持

- SenseVoice项目地址: https://github.com/FunAudioLLM/SenseVoice
- FunASR文档: https://github.com/alibaba-damo-academy/FunASR
- 插件问题反馈: 请在项目仓库提交Issue
