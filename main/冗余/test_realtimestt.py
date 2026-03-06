
# -*- coding: utf-8 -*-
"""
测试 RealtimeSTT 是否可以正常导入和使用
"""

import sys
import os

# 添加 plugins/RealtimeSTT-master 到 Python 路径
plugins_path = os.path.join(os.path.dirname(__file__), 'plugins', 'RealtimeSTT-master')
if plugins_path not in sys.path:
    sys.path.insert(0, plugins_path)

try:
    print("📦 尝试导入 RealtimeSTT...")
    from RealtimeSTT import AudioToTextRecorder
    print("✅ RealtimeSTT 导入成功")

    print("\n🔧 尝试创建 AudioToTextRecorder 实例...")
    recorder = AudioToTextRecorder(
        model="tiny",
        language="zh",
        device="cpu",
        enable_realtime_transcription=False,
        spinner=False,
        use_microphone=False
    )
    print("✅ AudioToTextRecorder 实例创建成功")

    print("\n🎉 RealtimeSTT 部署成功！")

except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()
