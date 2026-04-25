# -*- coding: utf-8 -*-
"""
配置管理模块
处理应用程序的配置加载、保存和默认配置
"""

import json
import os

# 配置文件路径（相对 __file__ 定位，避免依赖工作目录）
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(_ROOT, "ai_agent_config.json")

def load_config():
    """加载配置"""
    default_config = {
        "openai_key": "",
        "deepseek_key": "",
        "default_browser": "",  # 默认浏览器
        "default_search_engine": "baidu",  # 默认搜索引擎
        "selected_model": "deepseek-v4-flash",
        "thinking_mode": False,  # 是否启用 deepseek-v4-flash 思考模式
        "memory_summary_model": "deepseek-v4-flash",  # 记忆系统总结使用的模型
        "max_tokens": 1000,  # AI最大token数，0表示无限制
        "window_transparency": 100,  # 窗口透明度，100表示完全不透明
        "show_remember_details": True,  # 是否显示"记住这个时刻"的详细信息
        "note_filename_format": "timestamp",  # 笔记文件名格式：timestamp(时间戳格式) 或 simple(简单格式)
        # TTS设置
        "tts_enabled": False,  # 是否启用TTS
        "tts_engine": "gpt_sovits",  # TTS引擎
        "gpt_sovits_api_url": "http://127.0.0.1:9880",  # GPT-SoVITS API地址 (已迁移到main/plugins/GPT-SoVITS)
        "gpt_sovits_ref_audio": "",  # GPT-SoVITS参考音频路径
        "skip_streaming_duplicate_play": True,  # 是否跳过流式播放的重复播放（当使用api_v2时）
        # ASR设置
        "asr_enabled": True,  # 是否启用ASR（默认开启）
        "ai_fallback_enabled": True,  # 是否启用AI智能创建的后备机制（关键词识别）
        "website_map": {
            "哔哩哔哩": "https://www.bilibili.com",
            "b站": "https://www.bilibili.com",
            "百度": "https://www.baidu.com",
            "谷歌": "https://www.google.com",
            "知乎": "https://www.zhihu.com",
            "github": "https://github.com",
            "youtube": "https://www.youtube.com"
        },
        "app_map": {},
    }

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return default_config
    return default_config

def save_config(config):
    """保存配置"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
