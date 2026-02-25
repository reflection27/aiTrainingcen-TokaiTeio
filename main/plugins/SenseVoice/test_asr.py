# -*- coding: utf-8 -*-
"""
SenseVoice ASR测试脚本
"""

import os
import sys
from sensevoice_asr import SenseVoiceASR

def test_asr():
    """测试ASR功能"""
    print("=" * 50)
    print("SenseVoice ASR 测试")
    print("=" * 50)

    # 初始化ASR
    print("
1. 初始化ASR模型...")
    asr = SenseVoiceASR()

    if not asr.is_available():
        print("❌ ASR模型初始化失败")
        return

    print("✅ ASR模型初始化成功")

    # 测试录音并识别
    print("
2. 开始录音测试")
    print("   按下Enter键开始录音，再次按下Enter键结束录音...")
    input()

    text, audio_file = asr.record_and_transcribe(
        duration=None,
        language="auto",
        use_itn=False,
        keep_audio=True
    )

    if text:
        print(f"
✅ 识别成功")
        print(f"   识别结果: {text}")
        print(f"   音频文件: {audio_file}")
    else:
        print("
❌ 识别失败")

    print("
" + "=" * 50)
    print("测试完成")
    print("=" * 50)

if __name__ == "__main__":
    test_asr()
