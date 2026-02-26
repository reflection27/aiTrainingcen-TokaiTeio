
# -*- coding: utf-8 -*-
"""
RealtimeSTT 配置文件
存储 RealtimeSTT 的配置参数
"""

# RealtimeSTT 配置
REALTIMESTT_CONFIG = {
    # ASR 模型配置
    "asr_enabled": True,  # 是否启用 ASR
    "asr_model": "large-v3",  # Whisper 模型: tiny, base, small, medium, large-v3
    "asr_language": "zh",  # 语言: zh(中文), en(英文), auto(自动检测)

    # 语音活动检测配置
    "asr_silero_sensitivity": 0.4,  # Silero VAD 灵敏度 (0.0-1.0)
    "asr_post_speech_silence": 0.7,  # 说话结束后的静默时间(秒)
    "asr_min_gap": 0.5,  # 两次录音之间的最小间隔(秒)

    # 实时转录配置
    "asr_realtime": True,  # 是否启用实时转录
    "asr_realtime_pause": 0.2,  # 实时处理暂停时间(秒)
    "asr_realtime_batch": 5,  # 实时处理批次大小
}
