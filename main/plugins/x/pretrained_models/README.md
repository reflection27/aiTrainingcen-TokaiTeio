# 预训练模型目录

此目录用于存放SenseVoice预训练模型。

## 模型下载

请将SenseVoice模型下载到此目录下的`SenseVoiceSmall`子目录中。

### 下载方式

1. **从Hugging Face下载**
   - 访问: https://huggingface.co/FunAudioLLM/SenseVoiceSmall
   - 下载模型文件到 `SenseVoiceSmall/` 目录

2. **使用ModelScope下载**
   ```bash
   pip install modelscope
   python -c "from modelscope import snapshot_download; snapshot_download('iic/SenseVoiceSmall', cache_dir='./pretrained_models')"
   ```

### 目录结构

```
pretrained_models/
└── SenseVoiceSmall/
    ├── config.yaml
    ├── model.pt
    └── ...
```

## 注意事项

1. 确保下载的模型版本与插件兼容
2. 模型文件较大，请确保有足够的磁盘空间
3. 首次使用时需要下载模型，之后可以离线使用
