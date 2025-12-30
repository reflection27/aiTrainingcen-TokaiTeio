# -*- coding: utf-8 -*-
"""
简化的GPT-SoVITS TTS调用模块
通过Gradio客户端调用GPT-SoVITS的TTS功能
"""

import tempfile
import os
import pygame
import threading
import time
from gradio_client import Client, file

class SimpleGPTSoVITS:
    """简化的GPT-SoVITS TTS调用类"""

    def __init__(self, api_url="http://127.0.0.1:9872", ref_audio_path=""):
        self.api_url = api_url
        self.ref_audio_path = ref_audio_path
        self.enabled = False
        self.client = None

        # 初始化pygame音频
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            self.audio_available = True
        except Exception as e:
            print(f"⚠️ 音频初始化失败: {e}")
            self.audio_available = False

        # 检查API是否可用
        self._check_api_availability()

    def _check_api_availability(self):
        """检查API是否可用"""
        try:
            print(f"🔍 尝试连接GPT-SoVITS API: {self.api_url}")
            self.client = Client(self.api_url)
            self.enabled = True
            print("✅ GPT-SoVITS API连接成功")
        except Exception as e:
            print(f"⚠️ GPT-SoVITS API连接失败: {e}")
            self.enabled = False
            import traceback
            traceback.print_exc()

    def speak_text(self, text):
        """文本转语音并播放"""
        print(f"🔍 TTS状态检查: enabled={self.enabled}, audio_available={self.audio_available}, client={self.client is not None}")
        if not self.enabled or not self.audio_available or not self.client:
            print(f"🔍 TTS未启用或管理器不可用: enabled={self.enabled}, audio_available={self.audio_available}, client={self.client is not None}")
            return

        # 在新线程中处理TTS
        def tts_worker():
            try:
                # 调用Gradio API
                ref_wav_path = file(self.ref_audio_path) if self.ref_audio_path else file('https://github.com/gradio-app/gradio/raw/main/test/test_files/audio_sample.wav')
                print(f"🔍 调用GPT-SoVITS API，文本: {text[:50]}...")
                print(f"🔍 参考音频: {ref_wav_path}")
                result = self.client.predict(
                    ref_wav_path=ref_wav_path,
                    prompt_text="",
                    prompt_language="中文",
                    text=text,
                    text_language="中文",
                    how_to_cut="凑四句一切",
                    top_k=15,
                    top_p=1,
                    temperature=1,
                    ref_free=False,
                    speed=1,
                    if_freeze=False,
                    inp_refs=[],
                    api_name="/get_tts_wav"
                )
                print(f"🔍 API返回类型: {type(result)}")
                print(f"🔍 API返回值: {result}")

                if result:
                    # 检查返回的是文件路径还是二进制数据
                    if isinstance(result, str):
                        # 如果是文件路径，直接使用
                        temp_file_path = result
                        print(f"✅ GPT-SoVITS TTS生成成功，文件路径: {temp_file_path}")
                    else:
                        # 如果是二进制数据，创建临时文件保存
                        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
                        temp_file.close()

                        # 保存音频数据
                        with open(temp_file.name, 'wb') as f:
                            f.write(result)
                        temp_file_path = temp_file.name
                        print(f"✅ GPT-SoVITS TTS生成成功，保存到临时文件: {temp_file_path}")

                    # 播放音频
                    pygame.mixer.music.load(temp_file_path)
                    pygame.mixer.music.play()

                    # 等待播放完成
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.1)

                    # 只有临时文件才需要删除
                    if isinstance(result, str) == False:
                        os.unlink(temp_file_path)
                    print(f"✅ GPT-SoVITS TTS播放成功: {text[:50]}...")
                else:
                    print("❌ GPT-SoVITS TTS合成失败: 无返回结果")

            except Exception as e:
                print(f"❌ GPT-SoVITS TTS处理异常: {e}")

        thread = threading.Thread(target=tts_worker, daemon=True)
        thread.start()

    def set_speaking_rate(self, rate):
        """设置语速"""
        # SimpleGPTSoVITS 不支持动态语速调整，但为了兼容性保留此方法
        print(f"ℹ️ SimpleGPTSoVITS 不支持动态语速调整，语速将保持默认值")

    def is_available(self):
        """检查TTS是否可用"""
        return self.enabled and self.audio_available
