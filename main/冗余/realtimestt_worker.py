
# -*- coding: utf-8 -*-
"""
RealtimeSTT 集成模块
用于在主程序中集成 RealtimeSTT 语音识别功能
"""

import sys
import os
import threading
import queue
import pyaudio
import wave
import io
from PyQt5.QtCore import QObject, pyqtSignal

# 导入STT客户端
from stt_client import STTClient

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
        self.stt_client = STTClient()
        self.is_running = False
        self.is_recording = False
        self.text_queue = queue.Queue()
        self.thread = None

        # 音频参数
        self.audio_format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.chunk = 1024
        self.audio = None
        self.stream = None
        self.frames = []

    def init_recorder(self):
        """初始化语音识别器"""
        try:
            print("🎤 初始化 STT 客户端...")

            # 检查STT服务器状态
            if not self.stt_client.check_status():
                raise Exception("STT服务器不可用，请确保STT服务器已启动")

            # 初始化recorder属性
            self.recorder = True  # 标记录音器已初始化

            print("✅ STT 客户端初始化成功")
            return True

        except Exception as e:
            error_msg = f"初始化 STT 客户端失败: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
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

        # 确保录音器已初始化
        if not self.recorder:
            print("🔧 录音器未初始化，尝试初始化...")
            if not self.init_recorder():
                print("❌ 录音器初始化失败")
                return

        self.is_running = True
        print("✅ RealtimeSTT 已启动")

    def stop(self):
        """停止语音识别"""
        if not self.is_running:
            return

        self.is_running = False
        self.recorder = False

        print("✅ RealtimeSTT 已停止")

    def start_recording(self):
        """开始录音"""
        if not self.is_running or self.is_recording:
            return

        # 确保录音器已初始化
        if not self.recorder:
            print("❌ 录音器未初始化")
            self.error_occurred.emit("录音器未初始化")
            return

        self.is_recording = True
        self.recording_started.emit()

        # 在新线程中录音
        self.thread = threading.Thread(target=self._record_audio, daemon=True)
        self.thread.start()
        print("✅ 录音线程已启动")

    def stop_recording(self):
        """停止录音"""
        if not self.is_recording:
            return

        self.is_recording = False
        self.recording_stopped.emit()

        # 等待录音线程完成
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5.0)  # 最多等待5秒
            if self.thread.is_alive():
                print("⚠️ 录音线程未在指定时间内完成")

        # 清理线程对象
        self.thread = None

    def _record_audio(self):
        """录音线程函数 - 实时转录版本"""
        try:
            print("🎤 开始录音...")

            # 初始化PyAudio
            self.audio = pyaudio.PyAudio()

            # 打开音频流
            self.stream = self.audio.open(
                format=self.audio_format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk
            )

            print("🎤 正在录音...")
            self.frames = []

            # 实时转录参数
            chunk_duration = 2.0  # 每次识别2秒的音频
            frames_per_recognition = int(self.rate / self.chunk * chunk_duration)
            current_frames = []
            overlap_frames = int(self.rate / self.chunk * 0.5)  # 重叠0.5秒的音频

            # 实时录音和识别循环
            while self.is_recording:
                try:
                    # 读取音频数据
                    data = self.stream.read(self.chunk)
                    self.frames.append(data)
                    current_frames.append(data)

                    # 当累积到足够帧数时进行识别
                    if len(current_frames) >= frames_per_recognition:
                        print("🎤 检测到语音，进行实时识别...")

                        # 将音频帧转换为WAV格式的字节数据
                        audio_buffer = io.BytesIO()
                        with wave.open(audio_buffer, 'wb') as wf:
                            wf.setnchannels(self.channels)
                            wf.setsampwidth(self.audio.get_sample_size(self.audio_format))
                            wf.setframerate(self.rate)
                            wf.writeframes(b''.join(current_frames))

                        # 获取音频数据
                        audio_data = audio_buffer.getvalue()
                        audio_buffer.close()

                        # 使用STT客户端进行语音识别
                        text = self.stt_client.recognize(audio_data)

                        # 发出识别结果
                        if text and text.strip():
                            print(f"📝 实时识别结果: {text.strip()}")
                            self.text_ready.emit(text.strip())

                        # 使用滑动窗口：保留部分重叠的帧
                        current_frames = current_frames[-overlap_frames:] if len(current_frames) > overlap_frames else []

                except IOError as e:
                    if self.is_recording:
                        print(f"⚠️ 音频流读取错误: {e}")
                    continue

            print("🎤 录音完成")

            # 处理剩余的音频帧
            if current_frames:
                print("🎤 处理剩余音频...")
                audio_buffer = io.BytesIO()
                with wave.open(audio_buffer, 'wb') as wf:
                    wf.setnchannels(self.channels)
                    wf.setsampwidth(self.audio.get_sample_size(self.audio_format))
                    wf.setframerate(self.rate)
                    wf.writeframes(b''.join(current_frames))

                audio_data = audio_buffer.getvalue()
                audio_buffer.close()

                text = self.stt_client.recognize(audio_data)

                if text and text.strip():
                    print(f"📝 最后识别结果: {text.strip()}")
                    self.text_ready.emit(text.strip())

        except Exception as e:
            error_msg = f"录音失败: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            self.error_occurred.emit(error_msg)
        finally:
            # 清理资源
            self.is_recording = False
            print("🎤 录音结束")

            # 关闭音频流
            if self.stream:
                try:
                    self.stream.stop_stream()
                    self.stream.close()
                except Exception as e:
                    print(f"❌ 关闭音频流失败: {str(e)}")
                finally:
                    self.stream = None

            # 关闭PyAudio
            if self.audio:
                try:
                    self.audio.terminate()
                except Exception as e:
                    print(f"❌ 关闭PyAudio失败: {str(e)}")
                finally:
                    self.audio = None

    def shutdown(self):
        """关闭语音识别"""
        self.stop_recording()
        print("✅ STT 客户端已关闭")
