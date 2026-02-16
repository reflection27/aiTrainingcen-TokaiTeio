
# -*- coding: utf-8 -*-
"""
统一的GPT-SoVITS TTS调用模块
支持通过Gradio客户端和api_v2两种方式调用GPT-SoVITS的TTS功能
"""

import tempfile
import os
import pygame
import threading
import time
from typing import Optional

try:
    from gradio_client import Client, file
    GRADIO_AVAILABLE = True
except ImportError:
    GRADIO_AVAILABLE = False
    print("⚠️ Gradio客户端未安装，Gradio方式调用GPT-SoVITS将不可用")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("⚠️ Requests库未安装，api_v2方式调用GPT-SoVITS将不可用")


class UnifiedGPTSoVITS:
    """统一的GPT-SoVITS TTS调用类，支持gradio和api_v2两种方式"""

    def __init__(self, api_url="http://127.0.0.1:9872", ref_audio_path="", api_type="gradio"):
        """
        初始化统一的GPT-SoVITS TTS调用类

        参数:
            api_url: API地址
            ref_audio_path: 参考音频路径
            api_type: API类型，可选值为"gradio"或"api_v2"
        """
        self.api_url = api_url
        self.ref_audio_path = ref_audio_path
        self.api_type = api_type
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
            print(f"🔍 尝试连接GPT-SoVITS API: {self.api_url}, 类型: {self.api_type}")

            if self.api_type == "gradio":
                if not GRADIO_AVAILABLE:
                    print("⚠️ Gradio客户端未安装，无法使用gradio方式")
                    self.enabled = False
                    return

                self.client = Client(self.api_url)
                self.enabled = True
                print("✅ GPT-SoVITS Gradio API连接成功")

            elif self.api_type == "api_v2":
                if not REQUESTS_AVAILABLE:
                    print("⚠️ Requests库未安装，无法使用api_v2方式")
                    self.enabled = False
                    return

                # 检查api_v2是否可用
                response = requests.get(f"{self.api_url}/control?command=status", timeout=5)
                if response.status_code == 200:
                    self.enabled = True
                    print("✅ GPT-SoVITS API v2连接成功")
                else:
                    print(f"⚠️ GPT-SoVITS API v2响应异常: {response.status_code}")
                    self.enabled = False

        except Exception as e:
            print(f"⚠️ GPT-SoVITS API连接失败: {e}")
            self.enabled = False
            import traceback
            traceback.print_exc()

    def _synthesize_with_gradio(self, text: str) -> Optional[str]:
        """使用Gradio API合成语音"""
        if not self.client:
            return None

        try:
            # 调用Gradio API
            ref_wav_path = file(self.ref_audio_path) if self.ref_audio_path else file('https://github.com/gradio-app/gradio/raw/main/test/test_files/audio_sample.wav')
            print(f"🔍 调用GPT-SoVITS Gradio API，文本: {text[:50]}...")
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
                return temp_file_path
            else:
                print("❌ GPT-SoVITS TTS合成失败: 无返回结果")
                return None

        except Exception as e:
            print(f"❌ GPT-SoVITS TTS处理异常: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _synthesize_with_api_v2(self, text: str) -> Optional[str]:
        """使用api_v2合成语音"""
        try:
            # 创建临时音频文件
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            temp_file.close()

            # 准备请求数据
            data = {
                "text": text,
                "text_lang": "zh",
                "ref_audio_path": self.ref_audio_path,
                "prompt_text": "",  # 空prompt_text，与gradio调用保持一致
                "prompt_lang": "zh",
                "top_k": 12,  # 降低top_k值，使语音更稳定
                "top_p": 0.85,  # 降低top_p值，减少随机性
                "temperature": 0.7,  # 降低temperature，使语音更自然
                "text_split_method": "cut5",  # 与gradio的"凑四句一切"对应
                "batch_size": 1,
                "batch_threshold": 0.75,
                "speed_factor": 1.15,  # 稍微提高语速，减少大喘气
                "seed": -1,
                "media_type": "wav",
                "streaming_mode": False,
                "parallel_infer": True,
                "repetition_penalty": 1.35
            }

            # 发送请求
            print(f"🔍 调用GPT-SoVITS API v2，文本: {text[:50]}...")
            print(f"🔍 参考音频: {self.ref_audio_path}")
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
            import traceback
            traceback.print_exc()
            return None

    def speak_text(self, text: str):
        """文本转语音并播放"""
        print(f"🔍 TTS状态检查: enabled={self.enabled}, audio_available={self.audio_available}, api_type={self.api_type}")
        if not self.enabled or not self.audio_available:
            print(f"🔍 TTS未启用或管理器不可用: enabled={self.enabled}, audio_available={self.audio_available}")
            return

        # 在新线程中处理TTS
        def tts_worker():
            try:
                # 根据API类型选择不同的合成方法
                if self.api_type == "gradio":
                    temp_file_path = self._synthesize_with_gradio(text)
                elif self.api_type == "api_v2":
                    temp_file_path = self._synthesize_with_api_v2(text)
                else:
                    print(f"❌ 不支持的API类型: {self.api_type}")
                    return

                if temp_file_path:
                    # 播放音频
                    pygame.mixer.music.load(temp_file_path)
                    pygame.mixer.music.play()

                    # 等待播放完成
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.1)

                    # 删除临时文件
                    try:
                        os.unlink(temp_file_path)
                    except:
                        pass
                    print(f"✅ GPT-SoVITS TTS播放成功: {text[:50]}...")
                else:
                    print("❌ GPT-SoVITS TTS合成失败")

            except Exception as e:
                print(f"❌ GPT-SoVITS TTS处理异常: {e}")
                import traceback
                traceback.print_exc()

        thread = threading.Thread(target=tts_worker, daemon=True)
        thread.start()

    def set_speaking_rate(self, rate: float):
        """设置语速"""
        # 目前UnifiedGPTSoVITS 不支持动态语速调整，但为了兼容性保留此方法
        print(f"ℹ️ UnifiedGPTSoVITS 不支持动态语速调整，语速将保持默认值")

    def set_model_weights(self, t2s_weights_path: str = None, vits_weights_path: str = None):
        """设置模型权重路径（仅对api_v2有效）"""
        if self.api_type != "api_v2":
            print("ℹ️ 只有api_v2类型支持动态切换模型权重")
            return False

        if not REQUESTS_AVAILABLE:
            print("⚠️ Requests库未安装，无法设置模型权重")
            return False

        try:
            # 设置T2S模型权重
            if t2s_weights_path:
                print(f"🔍 设置T2S模型权重: {t2s_weights_path}")
                # 检查文件是否存在
                if not os.path.exists(t2s_weights_path):
                    print(f"❌ T2S模型权重文件不存在: {t2s_weights_path}")
                    return False

                response = requests.get(
                    f"{self.api_url}/set_gpt_weights",
                    params={"weights_path": t2s_weights_path},
                    timeout=10
                )
                if response.status_code == 200:
                    print("✅ T2S模型权重设置成功")
                else:
                    print(f"❌ T2S模型权重设置失败: {response.status_code}")
                    result = response.json()
                    print(f"错误详情: {result}")
                    return False

            # 设置VITS模型权重
            if vits_weights_path:
                print(f"🔍 设置VITS模型权重: {vits_weights_path}")
                # 检查文件是否存在
                if not os.path.exists(vits_weights_path):
                    print(f"❌ VITS模型权重文件不存在: {vits_weights_path}")
                    return False

                response = requests.get(
                    f"{self.api_url}/set_sovits_weights",
                    params={"weights_path": vits_weights_path},
                    timeout=10
                )
                if response.status_code == 200:
                    print("✅ VITS模型权重设置成功")
                else:
                    print(f"❌ VITS模型权重设置失败: {response.status_code}")
                    result = response.json()
                    print(f"错误详情: {result}")
                    return False

            return True
        except Exception as e:
            print(f"❌ 设置模型权重异常: {e}")
            import traceback
            traceback.print_exc()
            return False

    def is_available(self) -> bool:
        """检查TTS是否可用"""
        return self.enabled and self.audio_available
