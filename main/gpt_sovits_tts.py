# -*- coding: utf-8 -*-
"""
GPT-SoVITS TTS管理器
处理通过api_v2.py调用GPT-SoVITS语音合成功能
"""

import asyncio
import threading
import queue
import time
import requests
import tempfile
import os
import json
import pygame
from typing import Optional, Callable

class GPTSoVITSManager:
    """GPT-SoVITS TTS管理器"""

    def __init__(self, api_url="http://127.0.0.1:9880", ref_audio_path=""):
        self.api_url = api_url
        self.ref_audio_path = ref_audio_path
        self.enabled = False
        self.audio_queue = queue.Queue()
        self.is_playing = False
        self.stop_playback = False
        self.default_params = {
            "text_lang": "zh",
            "prompt_lang": "zh",
            "prompt_text": "",  # 空prompt_text，让模型自动从参考音频中学习
            "top_k": 15,  # 与gradio调用保持一致
            "top_p": 1,  # 与gradio调用保持一致
            "temperature": 1,  # 与gradio调用保持一致
            "text_split_method": "cut5",  # 与gradio的"凑四句一切"对应
            "batch_size": 1,
            "batch_threshold": 0.75,
            "speed_factor": 1.0,
            "seed": -1,
            "media_type": "wav",
            "streaming_mode": False,
            "parallel_infer": True,
            "repetition_penalty": 1.35
        }

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
            response = requests.get(f"{self.api_url}/control?command=status", timeout=5)
            if response.status_code == 200:
                self.enabled = True
                print("✅ GPT-SoVITS API连接成功")
            else:
                print(f"⚠️ GPT-SoVITS API响应异常: {response.status_code}")
                self.enabled = False
        except Exception as e:
            print(f"⚠️ GPT-SoVITS API连接失败: {e}")
            self.enabled = False

    def set_ref_audio(self, ref_audio_path: str):
        """设置参考音频路径"""
        self.ref_audio_path = ref_audio_path

    def set_speaking_rate(self, rate: float):
        """设置语速"""
        self.default_params["speed_factor"] = rate

    def synthesize_text(self, text: str) -> Optional[str]:
        """合成文本为音频文件"""
        if not self.enabled:
            return None

        try:
            # 创建临时音频文件
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            temp_file.close()

            # 准备请求数据
            data = self.default_params.copy()
            data["text"] = text
            data["ref_audio_path"] = self.ref_audio_path

            # 发送请求
            response = requests.post(
                f"{self.api_url}/tts",
                json=data,
                timeout=60
            )

            if response.status_code == 200:
                # 保存音频数据
                with open(temp_file.name, 'wb') as f:
                    f.write(response.content)
                print(f"✅ GPT-SoVITS TTS合成成功: {text[:50]}...")
                return temp_file.name
            else:
                print(f"❌ GPT-SoVITS TTS合成失败: {response.status_code}")
                try:
                    error_info = response.json()
                    print(f"错误详情: {error_info}")
                except:
                    pass
                os.unlink(temp_file.name)
                return None

        except Exception as e:
            print(f"❌ GPT-SoVITS TTS合成异常: {e}")
            return None

    def play_audio(self, audio_file: str):
        """播放音频文件"""
        if not self.audio_available:
            return

        try:
            # 停止当前播放
            if self.is_playing:
                pygame.mixer.music.stop()

            # 播放新音频
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()
            self.is_playing = True

            # 等待播放完成
            while pygame.mixer.music.get_busy() and not self.stop_playback:
                time.sleep(0.1)

            self.is_playing = False

            # 清理临时文件
            try:
                os.unlink(audio_file)
            except:
                pass

        except Exception as e:
            print(f"❌ 音频播放失败: {e}")
            self.is_playing = False

    def speak_text(self, text: str):
        """文本转语音并播放"""
        if not self.enabled:
            return

        # 在新线程中处理TTS
        def tts_worker():
            audio_file = self.synthesize_text(text)
            if audio_file:
                self.play_audio(audio_file)

        thread = threading.Thread(target=tts_worker, daemon=True)
        thread.start()

    def stop_speaking(self):
        """停止当前播放"""
        self.stop_playback = True
        if self.is_playing:
            pygame.mixer.music.stop()
            self.is_playing = False

    def is_available(self) -> bool:
        """检查TTS是否可用"""
        return self.enabled and self.audio_available

    def cleanup(self):
        """清理资源"""
        self.stop_speaking()
        try:
            pygame.mixer.quit()
        except:
            pass
