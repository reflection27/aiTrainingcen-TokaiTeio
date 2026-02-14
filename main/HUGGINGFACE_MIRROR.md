
# HuggingFace镜像源配置说明

本项目已经配置了HuggingFace镜像源，可以解决连接超时的问题。

## 已配置的镜像源

在以下文件中已经添加了HuggingFace镜像源配置：
- `improved_memory.py`
- `async_ai_agent.py`

## 镜像源地址

使用的镜像源是：`https://hf-mirror.com`

## 如何使用

1. 确保已经安装了所有依赖：
```bash
pip install -r requirements.txt
```

2. 直接运行程序即可，镜像源会自动生效：
```bash
python main.py
```

## 如果仍然遇到连接问题

如果仍然遇到连接问题，可以尝试以下方法：

1. 手动设置环境变量：
```bash
export HF_ENDPOINT=https://hf-mirror.com
```

2. 或者使用其他镜像源：
```python
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
```

## 参考链接

- HuggingFace镜像源：https://hf-mirror.com
- HuggingFace官方文档：https://huggingface.co/docs
