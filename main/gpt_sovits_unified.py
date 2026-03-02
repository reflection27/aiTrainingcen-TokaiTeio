
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

    def __init__(self, api_url="http://127.0.0.1:9880", ref_audio_path="", api_type="api_v2"):  # 默认使用api_v2，端口9880
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

        # 初始化pygame音频（延迟到获取音频参数后）
        self.audio_available = True
        self.mixer_initialized = False  # 标记是否已根据实际参数初始化

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
                "streaming_mode": True,  # 启用流式模式，加快响应速度
                "parallel_infer": True,
                "repetition_penalty": 1.35
            }

            # 发送请求
            print(f"🔍 调用GPT-SoVITS API v2（流式模式），文本: {text[:50]}...")
            print(f"🔍 参考音频: {self.ref_audio_path}")
            response = requests.post(
                f"{self.api_url}/tts",
                json=data,
                timeout=60,
                stream=True  # 启用流式响应
            )

            if response.status_code == 200:
                # 流式接收音频数据
                import queue
                import threading
                import wave
                import struct

                # 创建两个队列：一个用于播放，一个用于保存
                play_queue = queue.Queue(maxsize=10)  # 播放队列
                save_queue = queue.Queue(maxsize=10)  # 保存队列
                audio_params = None
                first_chunk_received = False
                total_bytes = 0
                chunk_count = 0

                # 接收音频数据的线程
                def receive_audio():
                    nonlocal audio_params, first_chunk_received, total_bytes, chunk_count
                    try:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                # 同时放入两个队列
                                play_queue.put(chunk)
                                save_queue.put(chunk)

                                total_bytes += len(chunk)
                                chunk_count += 1

                                # 第一个chunk，解析WAV头
                                if not first_chunk_received and len(chunk) >= 44:
                                    if chunk[:4] == b'RIFF' and chunk[8:12] == b'WAVE':
                                        # 提取音频参数
                                        audio_params = {
                                            'channels': struct.unpack('<H', chunk[22:24])[0],
                                            'sample_rate': struct.unpack('<I', chunk[24:28])[0],
                                            'sample_width': struct.unpack('<H', chunk[34:36])[0] // 8
                                        }
                                        print(f"🔍 音频参数: 声道={audio_params['channels']}, 采样率={audio_params['sample_rate']}Hz, 位深={audio_params['sample_width']*8}bit")
                                        first_chunk_received = True

                                # 实时反馈进度（每10个chunk输出一次）
                                if chunk_count % 10 == 0:
                                    print(f"📥 接收音频数据: {chunk_count} chunks, 总计: {total_bytes} bytes")

                        print(f"📥 音频接收完成: {chunk_count} chunks, {total_bytes} bytes")
                    except Exception as e:
                        print(f"❌ 接收音频数据失败: {e}")
                        import traceback
                        traceback.print_exc()
                    finally:
                        # 发送结束信号到两个队列
                        play_queue.put(None)
                        save_queue.put(None)

                # 启动接收线程
                receive_thread = threading.Thread(target=receive_audio)
                receive_thread.start()

                # 等待音频参数
                while audio_params is None:
                    time.sleep(0.1)

                # 播放音频的线程
                def play_audio():
                    try:
                        import numpy as np
                        import pygame.sndarray as sndarray

                        # 初始化pygame mixer（使用实际音频参数）
                        # 检查是否已初始化
                        if not pygame.mixer.get_init():
                            # 初始化pygame mixer
                            pygame.mixer.init(
                                frequency=audio_params['sample_rate'],
                                size=-16 if audio_params['sample_width'] == 2 else -8,
                                channels=audio_params['channels'],
                                buffer=512
                            )
                            print(f"✅ Pygame mixer已初始化: {audio_params['sample_rate']}Hz, {audio_params['channels']}声道")
                        print(f"🔍 Mixer状态: init={pygame.mixer.get_init()}, num_channels={pygame.mixer.get_num_channels()}")

                        # 累积PCM数据
                        pcm_data = b''

                        while True:
                            chunk = play_queue.get()
                            if chunk is None:  # 结束信号
                                break

                            # 查找data chunk的位置
                            if len(chunk) >= 44 and chunk[:4] == b'RIFF' and chunk[8:12] == b'WAVE':
                                # 跳过WAV头，只保留PCM数据
                                data_pos = 36
                                while data_pos < len(chunk) - 8:
                                    chunk_id = chunk[data_pos:data_pos+4]
                                    chunk_size = struct.unpack('<I', chunk[data_pos+4:data_pos+8])[0]

                                    if chunk_id == b'data':
                                        pcm_data += chunk[data_pos+8:]
                                        break

                                    data_pos += 8 + chunk_size
                            else:
                                pcm_data += chunk

                            # 当积累足够的PCM数据时，播放
                            if len(pcm_data) >= audio_params['sample_width'] * audio_params['channels'] * audio_params['sample_rate']:
                                # 将PCM数据转换为numpy数组
                                audio_array = np.frombuffer(pcm_data, dtype=np.int16)

                                print(f"🔍 调试信息: channels={audio_params['channels']}, sample_width={audio_params['sample_width']}, array_shape={audio_array.shape}, mixer_channels={pygame.mixer.get_num_channels()}")

                                # 根据声道数调整数组形状
                                if audio_params['channels'] == 2:
                                    # 立体声：确保数据长度是偶数
                                    if len(audio_array) % 2 != 0:
                                        audio_array = audio_array[:-1]
                                    audio_array = audio_array.reshape(-1, 2)
                                    print(f"🔍 立体声数组形状: {audio_array.shape}")
                                else:
                                    # 单声道：确保是一维数组
                                    audio_array = audio_array.reshape(-1)
                                    # 如果mixer是立体声，需要将单声道转换为立体声
                                    if pygame.mixer.get_init()[2] == 2:
                                        audio_array = np.column_stack((audio_array, audio_array))
                                        print(f"🔍 单声道转立体声数组形状: {audio_array.shape}")
                                    else:
                                        print(f"🔍 单声道数组形状: {audio_array.shape}")

                                # 播放音频
                                sound = sndarray.make_sound(audio_array)
                                sound.play()

                                # 等待播放完成
                                while pygame.mixer.get_busy():
                                    time.sleep(0.01)

                                # 清空PCM数据
                                pcm_data = b''

                        # 播放剩余的PCM数据
                        if len(pcm_data) > 0:
                            audio_array = np.frombuffer(pcm_data, dtype=np.int16)

                            # 根据声道数调整数组形状
                            if audio_params['channels'] == 2:
                                # 立体声：确保数据长度是偶数
                                if len(audio_array) % 2 != 0:
                                    audio_array = audio_array[:-1]
                                audio_array = audio_array.reshape(-1, 2)
                            else:
                                # 单声道：确保是一维数组
                                audio_array = audio_array.reshape(-1)
                                # 如果mixer是立体声，需要将单声道转换为立体声
                                if pygame.mixer.get_init()[2] == 2:
                                    audio_array = np.column_stack((audio_array, audio_array))

                            sound = sndarray.make_sound(audio_array)
                            sound.play()

                            while pygame.mixer.get_busy():
                                time.sleep(0.01)
                    except Exception as e:
                        print(f"❌ 播放音频失败: {e}")
                        import traceback
                        traceback.print_exc()

                # 启动播放线程
                play_thread = threading.Thread(target=play_audio)
                play_thread.start()

                # 从save_queue中获取数据并保存
                audio_chunks = []
                while True:
                    chunk = save_queue.get()
                    if chunk is None:  # 结束信号
                        break
                    audio_chunks.append(chunk)

                # 等待接收线程和播放线程结束
                receive_thread.join()
                play_thread.join()

                # 验证文件大小
                if total_bytes < 1000:
                    print(f"⚠️ 音频文件过小: {total_bytes} bytes，可能生成失败")
                    try:
                        os.unlink(temp_file.name)
                    except:
                        pass
                    return None

                # 合并所有音频块
                full_audio_data = b''.join(audio_chunks)

                # 流式模式下，API返回的是WAV头+raw PCM数据
                # 需要重新构建完整的WAV文件
                try:
                    import wave
                    import struct

                    if len(full_audio_data) < 44:
                        print(f"⚠️ 音频数据过小: {len(full_audio_data)} bytes")
                        try:
                            os.unlink(temp_file.name)
                        except:
                            pass
                        return None

                    # 检查是否是有效的WAV头
                    if full_audio_data[:4] == b'RIFF' and full_audio_data[8:12] == b'WAVE':
                        print(f"✅ 检测到流式WAV格式，重新构建完整WAV文件")

                        # 解析WAV头，提取音频参数
                        # WAV头结构:
                        # 0-3: "RIFF"
                        # 4-7: 文件大小-8
                        # 8-11: "WAVE"
                        # 12-15: "fmt "
                        # 16-19: fmt chunk大小
                        # 20-21: 音频格式(1=PCM)
                        # 22-23: 声道数
                        # 24-27: 采样率
                        # 28-31: 字节率
                        # 32-33: 块对齐
                        # 34-35: 位深度

                        # 提取音频参数
                        num_channels = struct.unpack('<H', full_audio_data[22:24])[0]
                        sample_rate = struct.unpack('<I', full_audio_data[24:28])[0]
                        sample_width = struct.unpack('<H', full_audio_data[34:36])[0] // 8

                        print(f"🔍 音频参数: 声道={num_channels}, 采样率={sample_rate}Hz, 位深={sample_width*8}bit")

                        # 查找data chunk的位置
                        data_pos = 36  # fmt chunk之后
                        while data_pos < len(full_audio_data) - 8:
                            chunk_id = full_audio_data[data_pos:data_pos+4]
                            chunk_size = struct.unpack('<I', full_audio_data[data_pos+4:data_pos+8])[0]

                            if chunk_id == b'data':
                                print(f"✅ 找到data chunk，位置={data_pos}, 大小={chunk_size}")
                                # 提取PCM数据（跳过data chunk的8字节头）
                                pcm_data = full_audio_data[data_pos+8:]
                                print(f"🔍 PCM数据长度: {len(pcm_data)} bytes")
                                break

                            data_pos += 8 + chunk_size

                        if 'pcm_data' not in locals():
                            print(f"⚠️ 未找到data chunk，假设所有数据都是PCM")
                            # 假设从44字节后都是PCM数据
                            pcm_data = full_audio_data[44:]

                        # 重新构建完整的WAV文件
                        with wave.open(temp_file.name, 'wb') as wav_file:
                            wav_file.setnchannels(num_channels)
                            wav_file.setsampwidth(sample_width)
                            wav_file.setframerate(sample_rate)
                            wav_file.writeframes(pcm_data)

                        print(f"✅ WAV文件重新构建完成")
                    else:
                        print(f"⚠️ 检测到raw PCM数据，需要构建WAV文件")
                        # 假设是raw PCM数据，构建WAV文件
                        # 默认参数：22050Hz, 16位, 单声道
                        sample_rate = 22050
                        num_channels = 1
                        sample_width = 2  # 16-bit = 2 bytes

                        # 计算PCM数据长度
                        pcm_data = full_audio_data
                        num_samples = len(pcm_data) // sample_width

                        # 构建WAV文件
                        with wave.open(temp_file.name, 'wb') as wav_file:
                            wav_file.setnchannels(num_channels)
                            wav_file.setsampwidth(sample_width)
                            wav_file.setframerate(sample_rate)
                            wav_file.writeframes(pcm_data)

                        print(f"✅ WAV文件构建完成")
                except Exception as e:
                    print(f"❌ 处理WAV文件失败: {e}")
                    import traceback
                    traceback.print_exc()
                    try:
                        os.unlink(temp_file.name)
                    except:
                        pass
                    return None

                # 验证文件大小
                final_size = os.path.getsize(temp_file.name)
                print(f"🔍 最终文件大小: {final_size} bytes")

                if final_size < 1000:
                    print(f"⚠️ 最终文件过小: {final_size} bytes")
                    try:
                        os.unlink(temp_file.name)
                    except:
                        pass
                    return None

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
                    # 验证文件是否存在且大小合理
                    try:
                        file_size = os.path.getsize(temp_file_path)
                        print(f"🔍 音频文件大小: {file_size} bytes")

                        if file_size < 1000:
                            print(f"❌ 音频文件过小: {file_size} bytes，跳过播放")
                            try:
                                os.unlink(temp_file_path)
                            except:
                                pass
                            return
                    except Exception as e:
                        print(f"❌ 检查音频文件失败: {e}")
                        try:
                            os.unlink(temp_file_path)
                        except:
                            pass
                        return

                    # 播放音频
                    try:
                        # 当使用api_v2时，跳过播放本地文件（因为流式播放已经播放了）
                        if self.api_type == "api_v2":
                            print(f"✅ 跳过播放本地文件（api_v2流式播放已播放）")
                            # 删除临时文件
                            try:
                                os.unlink(temp_file_path)
                            except:
                                pass
                            return

                        pygame.mixer.music.load(temp_file_path)
                        pygame.mixer.music.play()
                        print(f"🔊 开始播放音频")

                        # 等待播放完成
                        while pygame.mixer.music.get_busy():
                            time.sleep(0.1)

                        # 删除临时文件
                        try:
                            os.unlink(temp_file_path)
                        except:
                            pass
                        print(f"✅ GPT-SoVITS TTS播放成功: {text[:50]}...")
                    except pygame.error as e:
                        print(f"❌ 播放音频失败 (pygame错误): {e}")
                        print(f"   文件路径: {temp_file_path}")
                        print(f"   文件大小: {os.path.getsize(temp_file_path) if os.path.exists(temp_file_path) else '文件不存在'}")
                        # 尝试读取文件头进行诊断
                        try:
                            with open(temp_file_path, 'rb') as f:
                                header = f.read(44)
                                print(f"   文件头: {header[:20]}")
                                if b'RIFF' in header[:4]:
                                    print(f"   RIFF标识: 正常")
                                else:
                                    print(f"   RIFF标识: 缺失或错误")
                                if b'WAVE' in header[8:12]:
                                    print(f"   WAVE标识: 正常")
                                else:
                                    print(f"   WAVE标识: 缺失或错误")
                                if b'data' in header:
                                    print(f"   data chunk: 正常")
                                else:
                                    print(f"   data chunk: 缺失")
                        except Exception as header_e:
                            print(f"   读取文件头失败: {header_e}")
                        try:
                            os.unlink(temp_file_path)
                        except:
                            pass
                    except Exception as e:
                        print(f"❌ 播放音频失败 (未知错误): {e}")
                        import traceback
                        traceback.print_exc()
                        try:
                            os.unlink(temp_file_path)
                        except:
                            pass
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
