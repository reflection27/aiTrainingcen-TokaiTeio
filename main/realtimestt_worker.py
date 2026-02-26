
# -*- coding: utf-8 -*-
"""
RealtimeSTT 集成模块
用于在主程序中集成 RealtimeSTT 语音识别功能
"""

import sys
import os
import threading
import queue
from PyQt5.QtCore import QObject, pyqtSignal

# 添加 RealtimeSTT 路径
realtimestt_path = os.path.join(os.path.dirname(__file__), 'plugins', 'RealtimeSTT-master')
if realtimestt_path not in sys.path:
    sys.path.insert(0, realtimestt_path)

from RealtimeSTT import AudioToTextRecorder

class RealtimeSTTWorker(QObject):
    """RealtimeSTT 工作线程"""

    # 定义信号
    text_ready = pyqtSignal(str)  # 识别到的文本
    error_occurred = pyqtSignal(str)  # 错误信息
    recording_started = pyqtSignal()  # 录音开始
    recording_stopped = pyqtSignal()  # 录音结束

    def __init__(self, config=None):
        super().__init__()
        self.config = config or {}
        self.recorder = None
        self.is_running = False
        self.is_recording = False
        self.text_queue = queue.Queue()
        self.thread = None

    def init_recorder(self):
        """初始化语音识别器"""
        try:
            print("🎤 初始化 RealtimeSTT 语音识别器...")

            # 从配置中获取参数，如果没有则使用默认值
            model = self.config.get("asr_model", "large-v3")
            language = self.config.get("asr_language", "zh")
            silero_sensitivity = self.config.get("asr_silero_sensitivity", 0.4)
            post_speech_silence_duration = self.config.get("asr_post_speech_silence", 0.7)
            min_gap_between_recordings = self.config.get("asr_min_gap", 0.5)
            enable_realtime_transcription = self.config.get("asr_realtime", True)
            realtime_processing_pause = self.config.get("asr_realtime_pause", 0.2)
            realtime_batch_size = self.config.get("asr_realtime_batch", 5)

            # 创建 AudioToTextRecorder 实例
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
                on_realtime_transcription_stabilized=self._on_realtime_transcription,
            )

            print("✅ RealtimeSTT 语音识别器初始化成功")
            return True

        except Exception as e:
            error_msg = f"初始化 RealtimeSTT 失败: {str(e)}"
            print(f"❌ {error_msg}")
            self.error_occurred.emit(error_msg)
            return False

    def _on_realtime_transcription(self, text):
        """实时转录回调"""
        if text:
            self.text_ready.emit(text)

    def start(self):
        """启动语音识别"""
        if self.is_running:
            return

        if not self.recorder:
            if not self.init_recorder():
                return

        self.is_running = True
        print("✅ RealtimeSTT 已启动")

    def stop(self):
        """停止语音识别"""
        if not self.is_running:
            return

        self.is_running = False
        if self.recorder:
            self.recorder.shutdown()
            self.recorder = None

        print("✅ RealtimeSTT 已停止")

    def start_recording(self):
        """开始录音"""
        if not self.is_running or self.is_recording:
            return

        self.is_recording = True
        self.recording_started.emit()

        # 在新线程中录音
        self.thread = threading.Thread(target=self._record_audio, daemon=True)
        self.thread.start()

    def stop_recording(self):
        """停止录音"""
        if not self.is_recording:
            return

        self.is_recording = False
        self.recording_stopped.emit()

        if self.thread:
            self.thread.join(timeout=2.0)

    def _record_audio(self):
        """录音线程函数"""
        try:
            text = self.recorder.text()
            if text:
                self.text_ready.emit(text)
        except Exception as e:
            error_msg = f"录音失败: {str(e)}"
            print(f"❌ {error_msg}")
            self.error_occurred.emit(error_msg)
        finally:
            self.is_recording = False

    def shutdown(self):
        """关闭语音识别"""
        self.stop_recording()
        self.stop()
