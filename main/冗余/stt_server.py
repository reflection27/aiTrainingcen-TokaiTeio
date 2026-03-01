
# -*- coding: utf-8 -*-
"""
STT服务器
在单独的虚拟环境中运行，提供语音识别API
"""

import sys
import os
import json
import tempfile
import wave
import base64
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# 添加 RealtimeSTT 路径
realtimestt_path = os.path.join(os.path.dirname(__file__), 'plugins', 'RealtimeSTT-master')
if realtimestt_path not in sys.path:
    sys.path.insert(0, realtimestt_path)

from RealtimeSTT import AudioToTextRecorder

# 全局变量
recorder = None

def init_recorder():
    """初始化语音识别器"""
    global recorder
    try:
        print("🎤 初始化 RealtimeSTT 语音识别器...")

        # 导入RealtimeSTT配置
        from realtimestt_config import REALTIMESTT_CONFIG

        # 检查ASR是否启用
        if not REALTIMESTT_CONFIG.get("asr_enabled", False):
            print("⚠️ ASR功能未启用，请在配置中设置asr_enabled为True")
            return False

        # 从RealtimeSTT配置中获取参数，如果没有则使用默认值
        model = REALTIMESTT_CONFIG.get("asr_model", "large-v3")
        language = REALTIMESTT_CONFIG.get("asr_language", "zh")
        silero_sensitivity = REALTIMESTT_CONFIG.get("asr_silero_sensitivity", 0.4)
        post_speech_silence_duration = REALTIMESTT_CONFIG.get("asr_post_speech_silence", 0.7)
        min_gap_between_recordings = REALTIMESTT_CONFIG.get("asr_min_gap", 0.5)
        enable_realtime_transcription = REALTIMESTT_CONFIG.get("asr_realtime", True)
        realtime_processing_pause = REALTIMESTT_CONFIG.get("asr_realtime_pause", 0.2)
        realtime_batch_size = REALTIMESTT_CONFIG.get("asr_realtime_batch", 5)

        # 创建 AudioToTextRecorder 实例
        recorder = AudioToTextRecorder(
            model=model,
            language=language,
            spinner=True,
            silero_sensitivity=silero_sensitivity,
            post_speech_silence_duration=post_speech_silence_duration,
            min_gap_between_recordings=min_gap_between_recordings,
            enable_realtime_transcription=enable_realtime_transcription,
            realtime_processing_pause=realtime_processing_pause,
            realtime_batch_size=realtime_batch_size,
            on_realtime_transcription_stabilized=lambda text: print(f"⚡ 实时: {text}"),  # 实时转录回调
        )

        print("✅ RealtimeSTT 语音识别器初始化成功")
        return True
    except Exception as e:
        print(f"❌ 初始化 RealtimeSTT 失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

class STTRequestHandler(BaseHTTPRequestHandler):
    """STT请求处理器"""

    def _send_json_response(self, status_code, data):
        """发送JSON响应"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def _send_cors_headers(self):
        """发送CORS头"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        """处理OPTIONS请求"""
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        """处理GET请求"""
        parsed_path = urlparse(self.path)

        if parsed_path.path == '/api/stt/status':
            # 状态API
            self._send_json_response(200, {
                "status": "ready" if recorder else "not_initialized"
            })
        else:
            self._send_json_response(404, {"error": "Not found"})

    def do_POST(self):
        """处理POST请求"""
        global recorder
        parsed_path = urlparse(self.path)

        if parsed_path.path == '/api/stt/recognize':
            # 语音识别API
            if not recorder:
                if not init_recorder():
                    self._send_json_response(500, {"error": "语音识别器初始化失败"})
                    return

            try:
                # 获取音频数据
                content_length = int(self.headers['Content-Length'])
                print(f"🎤 接收到音频数据，大小: {content_length} 字节")
                audio_data = self.rfile.read(content_length)

                if not audio_data:
                    print("❌ 未提供音频数据")
                    self._send_json_response(400, {"error": "未提供音频数据"})
                    return

                # 验证音频数据是否为有效的WAV文件
                if len(audio_data) < 44:
                    print("❌ 音频数据太小，不是有效的WAV文件")
                    self._send_json_response(400, {"error": "音频数据太小，不是有效的WAV文件"})
                    return

                # 检查WAV文件头
                if not audio_data.startswith(b'RIFF') or not audio_data[8:12] == b'WAVE':
                    print("❌ 音频数据不是有效的WAV文件格式")
                    self._send_json_response(400, {"error": "音频数据不是有效的WAV文件格式"})
                    return

                # 使用RealtimeSTT进行语音识别
                print("🎤 正在进行语音识别...")
                try:
                    # 直接使用音频数据进行识别
                    text = recorder.text(audio_data)
                    print(f"📝 识别结果: {text}")

                    if text and text.strip():
                        self._send_json_response(200, {"text": text.strip()})
                    else:
                        print("⚠️ 未识别到有效文本")
                        self._send_json_response(200, {"text": ""})  # 返回空字符串而不是错误
                except Exception as e:
                    print(f"❌ 识别过程异常: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    self._send_json_response(500, {"error": f"识别异常: {str(e)}"})
            except Exception as e:
                print(f"❌ 语音识别失败: {str(e)}")
                import traceback
                traceback.print_exc()
                self._send_json_response(500, {"error": f"语音识别失败: {str(e)}"})
        elif parsed_path.path == '/api/stt/shutdown':
            # 关闭API
            if recorder:
                try:
                    recorder.shutdown()
                    recorder = None
                    print("✅ RealtimeSTT 已关闭")
                except Exception as e:
                    print(f"❌ 关闭RealtimeSTT失败: {str(e)}")
            self._send_json_response(200, {"status": "shutdown"})
        else:
            self._send_json_response(404, {"error": "Not found"})

    def log_message(self, format, *args):
        """重写日志方法，减少输出"""
        pass

if __name__ == '__main__':
    # 初始化语音识别器
    if init_recorder():
        # 启动HTTP服务器
        print("🚀 启动STT服务器...")
        server = HTTPServer(('127.0.0.1', 5001), STTRequestHandler)
        print("✅ STT服务器已启动，监听地址: http://127.0.0.1:5001")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 正在停止STT服务器...")
            server.shutdown()
            print("✅ STT服务器已停止")
    else:
        print("❌ 无法启动STT服务器")
        sys.exit(1)
