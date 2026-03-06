# -*- coding: utf-8 -*-
"""
ASR集成模块
提供RealtimeSTT与主程序ASR功能的集成
"""

from PyQt5.QtCore import QObject, pyqtSignal

# 注释掉原有的STT调用方式
# from realtimestt_worker import RealtimeSTTWorker

# 使用新的直接集成方式
from realtime_stt_direct import RealtimeSTTThread

class ASRIntegration(QObject):
    """ASR集成类，用于将RealtimeSTT集成到主程序ASR中"""

    # 定义信号
    text_ready = pyqtSignal(str)  # 识别到的文本
    error_occurred = pyqtSignal(str)  # 错误信息

    def __init__(self, config=None):
        super().__init__()
        self.config = config or {}
        # 注释掉原有的worker
        # self.realtimestt_worker = None
        # 使用新的线程
        self.realtimestt_thread = None

    def _init_worker(self):
        """初始化RealtimeSTT工作线程"""
        try:
            # 使用RealtimeSTT进行语音识别
            print("🎤 开始使用RealtimeSTT进行语音识别...")

            # 注释掉原有的初始化方式
            # from realtimestt_worker import RealtimeSTTWorker
            # self.realtimestt_worker = RealtimeSTTWorker(self.config)
            # print("🎤 初始化录音器...")
            # if not self.realtimestt_worker.init_recorder():
            #     raise Exception("RealtimeSTT初始化失败")

            # 使用新的直接集成方式
            self.realtimestt_thread = RealtimeSTTThread(self.config)

            # 连接信号
            print("🎤 连接信号...")
            self.realtimestt_thread.text_ready.connect(self._on_asr_text_ready)
            self.realtimestt_thread.error_occurred.connect(self._on_asr_error)

            print("✅ RealtimeSTT已初始化")
            return True
        except Exception as e:
            print(f"❌ ASR初始化错误: {str(e)}")
            import traceback
            traceback.print_exc()
            self.error_occurred.emit(f"ASR初始化错误: {str(e)}")
            return False

    def start_asr(self):
        """启动ASR"""
        # 注释掉原有的启动方式
        # if not self.realtimestt_worker:
        #     if not self._init_worker():
        #         return False

        if not self.realtimestt_thread:
            if not self._init_worker():
                return False

        try:
            # 注释掉原有的启动方式
            # self.realtimestt_worker.start()
            # self.realtimestt_worker.start_recording()

            # 使用新的直接集成方式
            self.realtimestt_thread.start()

            print("✅ RealtimeSTT已启动")
            return True
        except Exception as e:
            print(f"❌ ASR启动错误: {str(e)}")
            import traceback
            traceback.print_exc()
            self.error_occurred.emit(f"ASR启动错误: {str(e)}")
            return False

    def stop_asr(self):
        """停止ASR"""
        # 注释掉原有的停止方式
        # if self.realtimestt_worker:
        #     try:
        #         self.realtimestt_worker.stop_recording()
        #         self.realtimestt_worker.stop()
        #         print("✅ RealtimeSTT已停止")
        #     except Exception as e:
        #         print(f"❌ ASR停止错误: {str(e)}")
        #         self.error_occurred.emit(f"ASR停止错误: {str(e)}")

        # 使用新的直接集成方式
        if self.realtimestt_thread:
            try:
                self.realtimestt_thread.stop()
                # 等待线程结束
                if self.realtimestt_thread.isRunning():
                    self.realtimestt_thread.wait(5000)  # 最多等待5秒
                print("✅ RealtimeSTT已停止")
            except Exception as e:
                print(f"❌ ASR停止错误: {str(e)}")
                self.error_occurred.emit(f"ASR停止错误: {str(e)}")

    def _on_asr_text_ready(self, text):
        """ASR文本识别完成回调 - 实时转录版本"""
        print(f"🎤 实时识别到文本: {text}")
        # 转发识别到的文本
        if text and text.strip():
            self.text_ready.emit(text.strip())
        # 注意：不再停止录音，以支持持续实时转录

    def _on_asr_error(self, error_msg):
        """ASR错误回调"""
        print(f"❌ ASR错误: {error_msg}")
        # 转发错误消息
        self.error_occurred.emit(f"语音识别错误: {error_msg}")

    def shutdown(self):
        """关闭ASR"""
        self.stop_asr()
        # 注释掉原有的关闭方式
        # if self.realtimestt_worker:
        #     self.realtimestt_worker.shutdown()
        #     self.realtimestt_worker = None

        # 使用新的直接集成方式
        if self.realtimestt_thread:
            self.realtimestt_thread = None
