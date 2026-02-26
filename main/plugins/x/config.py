# -*- coding: utf-8 -*-
"""
SenseVoice插件配置
"""

import os

# 获取插件目录
PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))

# 模型配置
MODEL_PATH = os.path.join(PLUGIN_DIR, "pretrained_models", "iic", "SenseVoiceSmall")
MODEL_NAME = "SenseVoiceSmall"

# 音频配置
SAMPLE_RATE = 16000  # 音频采样率
CHANNELS = 1  # 音频通道数

# ASR配置
LANGUAGE = "auto"  # 语言设置: auto, zh, en, yue, ja, ko, nospeech
USE_ITN = False  # 是否使用ITN（数字文本化）

# API配置
API_HOST = "127.0.0.1"
API_PORT = 9876
API_DEBUG = False

# 日志配置
LOG_LEVEL = "INFO"
LOG_FILE = os.path.join(PLUGIN_DIR, "sensevoice.log")

# 缓存配置
CACHE_DIR = os.path.join(PLUGIN_DIR, "cache")
ENABLE_CACHE = True
