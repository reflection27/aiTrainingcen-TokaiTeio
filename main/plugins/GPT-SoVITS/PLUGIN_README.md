# GPT-SoVITS 插件迁移说明

## 目录结构

GPT-SoVITS已迁移到 `main/plugins/GPT-SoVITS` 目录下。

## 配置说明

### API配置
- **API地址**: `http://127.0.0.1:9880`
- **API类型**: 默认使用 `api_v2`
- **配置文件**: `GPT_SoVITS/configs/tts_infer.yaml`

### 模型路径
所有模型路径已更新为相对于插件目录的路径：
- cnhubert: `GPT_SoVITS/pretrained_models/chinese-hubert-base`
- bert: `GPT_SoVITS/pretrained_models/chinese-roberta-wwm-ext-large`
- pretrained_sovits: `GPT_SoVITS/pretrained_models/s2G488k.pth`
- pretrained_gpt: `GPT_SoVITS/pretrained_models/s1bert25hz-2kh-longer-epoch=68e-step=50232.ckpt`

## 启动方式

### 启动API服务
运行 `start_api_v2.bat` 启动API服务

### 启动WebUI
运行 `go-webui.bat` 启动Web界面

## 修改的文件

### GPT-SoVITS核心文件
1. `api_v2.py` - 更新了路径设置，使用 `os.path.dirname(os.path.abspath(__file__))` 获取插件目录
2. `config.py` - 更新了所有模型路径为相对于插件目录的路径
3. `webui.py` - 更新了工作目录设置

### main文件夹中的文件
1. `config.py` - 更新了GPT-SoVITS API URL为 `http://127.0.0.1:9880`
2. `gpt_sovits_tts.py` - 更新了默认API URL
3. `gpt_sovits_unified.py` - 更新了默认API URL和API类型
4. `gpt_sovits_simple.py` - 更新了默认API URL

## 注意事项

1. 所有路径都使用相对路径，确保从任何位置运行都能正常工作
2. API端口统一使用9880
3. 默认使用api_v2方式调用，性能更好
4. 运行时工作目录会自动设置为插件目录
