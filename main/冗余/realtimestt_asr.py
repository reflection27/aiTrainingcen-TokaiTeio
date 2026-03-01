# -*- coding: utf-8 -*-
"""
RealtimeSTT ASR管理器
封装RealtimeSTT库，提供统一的ASR接口
"""

from typing import Optional
import logging

logger = logging.getLogger(__name__)

class RealtimeSTTASR:
    """RealtimeSTT ASR管理器"""

    def __init__(
        self,
        model: str = "small",
        language: str = "zh",
        device: str = "cuda",
        enable_realtime_transcription: bool = True,
        silero_sensitivity: float = 0.4,
        post_speech_silence_duration: float = 0.6,
        min_length_of_recording: float = 0.5,
        spinner: bool = False
    ):
        """
        初始化RealtimeSTT ASR管理器

        Args:
            model: 模型大小（tiny, base, small, medium, large-v1, large-v2）
            language: 语言代码（zh, en等）
            device: 设备类型（cuda或cpu）
            enable_realtime_transcription: 是否启用实时转录
            silero_sensitivity: Silero VAD灵敏度（0-1）
            post_speech_silence_duration: 语音结束后的静音时长（秒）
            min_length_of_recording: 最小录音时长（秒）
            spinner: 是否显示加载动画
        """
        self.model = model
        self.language = language
        self.device = device
        self.enable_realtime_transcription = enable_realtime_transcription
        self.silero_sensitivity = silero_sensitivity
        self.post_speech_silence_duration = post_speech_silence_duration
        self.min_length_of_recording = min_length_of_recording
        self.spinner = spinner
        self.recorder = None
        self._initialized = False

        try:
            print("📦 尝试导入RealtimeSTT...")
            import sys
            import os
            # 添加 plugins/RealtimeSTT-master 到 Python 路径
            plugins_path = os.path.join(os.path.dirname(__file__), 'plugins', 'RealtimeSTT-master')
            if plugins_path not in sys.path:
                sys.path.insert(0, plugins_path)
            from RealtimeSTT import AudioToTextRecorder
            print("✅ RealtimeSTT导入成功")
            self.AudioToTextRecorder = AudioToTextRecorder
            print("🔧 开始初始化录音器...")
            self._initialize_recorder()
        except ImportError as e:
            logger.error(f"无法导入RealtimeSTT: {e}")
            print(f"❌ 无法导入RealtimeSTT: {e}")
            raise ImportError("请先安装RealtimeSTT: pip install RealtimeSTT")
        except Exception as e:
            logger.error(f"RealtimeSTT初始化异常: {e}")
            print(f"❌ RealtimeSTT初始化异常: {e}")
            import traceback
            traceback.print_exc()
            raise

    def _initialize_recorder(self):
        """初始化录音器"""
        try:
            print("📝 开始初始化RealtimeSTT录音器...")
            print(f"📋 参数: model={self.model}, language={self.language}, device={self.device}")
            print(f"📋 参数: enable_realtime_transcription={self.enable_realtime_transcription}, silero_sensitivity={self.silero_sensitivity}")
            print(f"📋 参数: post_speech_silence_duration={self.post_speech_silence_duration}, min_length_of_recording={self.min_length_of_recording}")
            
            print("🎙️ 创建AudioToTextRecorder实例...")
            self.recorder = self.AudioToTextRecorder(
                model=self.model,
                language=self.language,
                device=self.device,
                enable_realtime_transcription=False,  # 禁用实时转录
                spinner=self.spinner,
                use_microphone=False  # 禁用麦克风
            )
            print("✅ AudioToTextRecorder实例创建成功")
            self._initialized = True
            print(f"✅ RealtimeSTT初始化成功，模型: {self.model}, 语言: {self.language}")
        except Exception as e:
            logger.error(f"RealtimeSTT初始化失败: {e}")
            import traceback
            traceback.print_exc()
            raise

    def is_available(self) -> bool:
        """检查ASR是否可用"""
        return self._initialized and self.recorder is not None

    def transcribe(self, on_transcription_finished=None) -> str:
        """
        进行语音转录

        Args:
            on_transcription_finished: 转录完成回调函数

        Returns:
            转录的文本
        """
        if not self.is_available():
            raise RuntimeError("ASR未初始化或不可用")

        try:
            return self.recorder.text(on_transcription_finished=on_transcription_finished)
        except Exception as e:
            logger.error(f"转录失败: {e}")
            raise

    def start(self):
        """开始录音"""
        if not self.is_available():
            raise RuntimeError("ASR未初始化或不可用")
        self.recorder.start()

    def stop(self):
        """停止录音"""
        if not self.is_available():
            return
        try:
            self.recorder.stop()
        except Exception as e:
            logger.error(f"停止录音失败: {e}")

    def shutdown(self):
        """关闭ASR"""
        if self.recorder:
            try:
                self.recorder.shutdown()
            except Exception as e:
                logger.error(f"关闭ASR失败: {e}")
            finally:
                self.recorder = None
                self._initialized = False
