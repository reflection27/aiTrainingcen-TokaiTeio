
# -*- coding: utf-8 -*-
"""
RealtimeSTT直接集成模块
直接集成realtimestt_process.py的实时语音识别功能
"""
import sys
import os
from PySide6.QtCore import QObject, Signal, QThread

# 添加 RealtimeSTT 路径
realtimestt_path = os.path.join(os.path.dirname(__file__), 'plugins', 'RealtimeSTT-master')
if realtimestt_path not in sys.path:
    sys.path.insert(0, realtimestt_path)

from RealtimeSTT import AudioToTextRecorder

class RealtimeSTTThread(QThread):
    """RealtimeSTT工作线程"""

    # 定义信号
    text_ready = Signal(str)  # 识别到的文本
    error_occurred = Signal(str)  # 错误信息

    def __init__(self, config=None):
        super().__init__()
        self.config = config or {}
        self.recorder = None
        self.is_running = False

    def run(self):
        """运行语音识别"""
        try:
            # 创建 AudioToTextRecorder 实例
            print("🎤 初始化语音识别器...")

            # 从配置中获取参数，如果没有则使用默认值
            model = self.config.get("asr_model", "large-v3")
            language = self.config.get("asr_language", "zh")
            silero_sensitivity = self.config.get("asr_silero_sensitivity", 0.4)
            post_speech_silence_duration = self.config.get("asr_post_speech_silence", 0.7)
            min_gap_between_recordings = self.config.get("asr_min_gap", 0.5)
            enable_realtime_transcription = self.config.get("asr_realtime", True)
            realtime_processing_pause = self.config.get("asr_realtime_pause", 0.2)
            realtime_batch_size = self.config.get("asr_realtime_batch", 5)

            self.recorder = AudioToTextRecorder(
                model=model,
                language=language,
                spinner=True,
                silero_sensitivity=silero_sensitivity,
                post_speech_silence_duration=post_speech_silence_duration,
                min_gap_between_recordings=min_gap_between_recordings,
                enable_realtime_transcription=enable_realtime_transcription,
                realtime_processing_pause=realtime_processing_pause,
                realtime_batch_size=realtime_batch_size,
                on_realtime_transcription_stabilized=lambda text: self.text_ready.emit(text),
            )

            print("✅ 语音识别器初始化完成！")

            self.is_running = True

            # 持续进行语音识别
            while self.is_running:
                try:
                    # 开始录音并识别
                    text = self.recorder.text()

                    if text:
                        print(f"🎯 识别结果: {text}")
                        self.text_ready.emit(text)
                except Exception as e:
                    print(f"❌ 识别过程异常: {str(e)}")
                    if self.is_running:
                        self.error_occurred.emit(f"识别异常: {str(e)}")

        except Exception as e:
            print(f"❌ RealtimeSTT初始化失败: {str(e)}")
            import traceback
            traceback.print_exc()
            self.error_occurred.emit(f"初始化失败: {str(e)}")
        finally:
            if self.recorder:
                self.recorder.shutdown()

    def stop(self):
        """停止语音识别"""
        self.is_running = False
        if self.recorder:
            try:
                self.recorder.shutdown()
            except Exception as e:
                print(f"❌ 关闭语音识别器失败: {str(e)}")
