
# -*- coding: utf-8 -*-
"""
统一的GPT-SoVITS TTS调用模块
支持通过Gradio客户端和api_v2两种方式调用GPT-SoVITS的TTS功能
"""

import os
import uuid
import pygame
import threading
import time
import queue
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
        self.is_playing = False  # 标记是否正在播放

        # 音频临时文件放到项目目录内，避免多实例共用系统 temp 导致序号冲突
        self._audio_tmp_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'temp', 'audio'
        )
        os.makedirs(self._audio_tmp_dir, exist_ok=True)

        # 初始化pygame音频（延迟到获取音频参数后）
        self.audio_available = True
        self.mixer_initialized = False  # 标记是否已根据实际参数初始化

        # 全局播放队列和合成顺序管理
        self.audio_play_queue = queue.PriorityQueue()  # 使用优先队列确保按合成顺序播放
        self.synthesis_counter = 0  # 合成顺序计数器
        self.synthesis_counter_lock = threading.Lock()  # 保护计数器的锁
        self.is_playing_audio = False  # 是否正在播放音频
        self.play_worker_thread = None  # 播放工作线程
        self.stop_playback_flag = False  # 停止播放标志

        # 播放顺序锁机制
        self.play_order_lock = threading.Lock()  # 播放顺序锁
        self.last_played_order = -1  # 上一个播放的音频序号
        self.played_orders = set()  # 已播放的音频序号集合
        self.pending_orders = set()  # 等待播放的音频序号集合
        self.play_order_condition = threading.Condition(self.play_order_lock)  # 播放顺序条件变量

        # 检查API是否可用
        self._check_api_availability()

        # 只在API可用时启动播放工作线程
        if self.enabled:
            self._start_play_worker()

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

    def _start_play_worker(self):
        """启动播放工作线程"""
        if self.play_worker_thread is None or not self.play_worker_thread.is_alive():
            self.stop_playback_flag = False
            self.play_worker_thread = threading.Thread(target=self._play_worker, daemon=True)
            self.play_worker_thread.start()
            print("✅ 播放工作线程已启动")

    def _play_worker(self):
        """播放工作线程，从全局队列中获取音频并按顺序播放"""
        while not self.stop_playback_flag:
            try:
                # 从优先队列中获取音频（顺序，音频文件）
                priority, audio_file = self.audio_play_queue.get(timeout=0.1)
                
                if audio_file is None:  # 结束信号
                    print("🛑 收到播放结束信号")
                    break
                
                print(f"🎵 开始播放音频 (顺序: {priority}): {audio_file}")
                self.is_playing_audio = True
                
                try:
                    # 播放音频文件
                    self._play_audio_file(audio_file)
                    print(f"✅ 音频播放完成 (顺序: {priority})")

                    # 更新播放顺序状态
                    with self.play_order_condition:
                        self.played_orders.add(priority)
                        self.pending_orders.discard(priority)
                        self.last_played_order = priority
                        print(f"📝 更新播放顺序: 已播放 {priority}, 等待中: {self.pending_orders}")
                        # 通知所有等待的线程
                        self.play_order_condition.notify_all()

                except Exception as e:
                    print(f"❌ 播放音频失败 (顺序: {priority}): {e}")
                    import traceback
                    traceback.print_exc()
                    # 即使播放失败也要更新状态
                    with self.play_order_condition:
                        self.played_orders.add(priority)
                        self.pending_orders.discard(priority)
                        self.last_played_order = priority
                        self.play_order_condition.notify_all()
                finally:
                    # 删除临时文件
                    try:
                        if os.path.exists(audio_file):
                            os.unlink(audio_file)
                            print(f"🗑️ 已删除临时音频文件: {audio_file}")
                    except Exception as e:
                        print(f"⚠️ 删除临时音频文件失败: {e}")
                    
                    self.is_playing_audio = False
                    self.audio_play_queue.task_done()
                    
            except queue.Empty:
                continue
            except Exception as e:
                print(f"❌ 播放工作线程异常: {e}")
                import traceback
                traceback.print_exc()
                self.is_playing_audio = False
        
        print("🛑 播放工作线程已停止")

    def _play_audio_file(self, audio_file: str):
        """播放音频文件"""
        if not self.audio_available:
            return
        
        try:
            # 初始化pygame mixer（如果尚未初始化）
            if not self.mixer_initialized:
                pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
                self.mixer_initialized = True
                print("✅ Pygame mixer已初始化")
            
            # 使用pygame播放音频
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()
            
            # 等待播放完成
            while pygame.mixer.music.get_busy() and not self.stop_playback_flag:
                time.sleep(0.1)
            
            # 停止播放
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
                
        except Exception as e:
            print(f"❌ 播放音频文件失败: {e}")
            raise

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
                    temp_file_path = os.path.join(self._audio_tmp_dir, f'{uuid.uuid4().hex}.wav')

                    # 保存音频数据
                    with open(temp_file_path, 'wb') as f:
                        f.write(result)
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
            # 创建临时音频文件（放到项目目录内）
            temp_file_path = os.path.join(self._audio_tmp_dir, f'{uuid.uuid4().hex}.wav')

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

                # 播放音频的线程（修改为保存音频数据到临时文件）
                def play_audio():
                    try:
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

                        # 将PCM数据保存到临时文件
                        if len(pcm_data) > 0:
                            # 创建WAV文件
                            with wave.open(temp_file_path, 'wb') as wav_file:
                                wav_file.setnchannels(audio_params['channels'])
                                wav_file.setsampwidth(audio_params['sample_width'])
                                wav_file.setframerate(audio_params['sample_rate'])
                                wav_file.writeframes(pcm_data)
                            
                            print(f"✅ 音频数据已保存到临时文件: {temp_file_path}")
                    except Exception as e:
                        print(f"❌ 保存音频数据失败: {e}")
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
                        os.unlink(temp_file_path)
                    except:
                        pass
                    return None

                # 验证文件大小
                final_size = os.path.getsize(temp_file_path)
                print(f"🔍 最终文件大小: {final_size} bytes")

                if final_size < 1000:
                    print(f"⚠️ 最终文件过小: {final_size} bytes")
                    try:
                        os.unlink(temp_file_path)
                    except:
                        pass
                    return None

                print(f"✅ GPT-SoVITS TTS合成成功: {text[:50]}...")
                return temp_file_path
            else:
                print(f"❌ GPT-SoVITS TTS合成失败: {response.status_code}")
                try:
                    error_info = response.json()
                    print(f"错误详情: {error_info}")
                except:
                    pass
                os.unlink(temp_file_path)
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

        # 在开始合成时就分配顺序号
        with self.synthesis_counter_lock:
            synthesis_order = self.synthesis_counter
            self.synthesis_counter += 1
        print(f"📝 分配音频序号: {synthesis_order}, 文本: {text[:50]}...")

        # 在新线程中处理TTS
        def tts_worker():
            try:
                # 设置播放状态
                self.is_playing = True

                # 根据API类型选择不同的合成方法
                if self.api_type == "gradio":
                    temp_file_path = self._synthesize_with_gradio(text)
                elif self.api_type == "api_v2":
                    temp_file_path = self._synthesize_with_api_v2(text)
                else:
                    print(f"❌ 不支持的API类型: {self.api_type}")
                    self.is_playing = False
                    # 等待前一个序号的音频放入队列或已播放
                    with self.play_order_condition:
                        expected_order = self.last_played_order + 1
                        while synthesis_order != expected_order:
                            # 如果前一个序号的音频已经放入队列或已播放,则允许当前音频标记为已播放
                            if (expected_order in self.played_orders) or (expected_order in self.pending_orders):
                                break
                            # 否则等待
                            print(f"⏳ API类型不支持等待音频序号 {expected_order} 完成, 当前序号: {synthesis_order}")
                            self.play_order_condition.wait(timeout=0.1)
                            if self.stop_playback_flag:
                                break

                        # 更新播放顺序状态，标记为已播放并更新last_played_order
                        self.played_orders.add(synthesis_order)
                        self.last_played_order = synthesis_order
                        print(f"📝 音频序号 {synthesis_order} API类型不支持，已标记为已播放，更新last_played_order为{synthesis_order}")
                        self.play_order_condition.notify_all()
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
                            # 等待前一个序号的音频放入队列或已播放
                            with self.play_order_condition:
                                expected_order = self.last_played_order + 1
                                while synthesis_order != expected_order:
                                    # 如果前一个序号的音频已经放入队列或已播放,则允许当前音频标记为已播放
                                    if (expected_order in self.played_orders) or (expected_order in self.pending_orders):
                                        break
                                    # 否则等待
                                    print(f"⏳ 文件过小等待音频序号 {expected_order} 完成, 当前序号: {synthesis_order}")
                                    self.play_order_condition.wait(timeout=0.1)
                                    if self.stop_playback_flag:
                                        break

                                # 更新播放顺序状态，标记为已播放并更新last_played_order
                                self.played_orders.add(synthesis_order)
                                self.last_played_order = synthesis_order
                                print(f"📝 音频序号 {synthesis_order} 文件过小，已标记为已播放，更新last_played_order为{synthesis_order}")
                                self.play_order_condition.notify_all()
                            self.is_playing = False
                            return
                    except Exception as e:
                        print(f"❌ 检查音频文件失败: {e}")
                        try:
                            os.unlink(temp_file_path)
                        except:
                            pass
                        # 等待前一个序号的音频放入队列或已播放
                        with self.play_order_condition:
                            expected_order = self.last_played_order + 1
                            while synthesis_order != expected_order:
                                # 如果前一个序号的音频已经放入队列或已播放,则允许当前音频标记为已播放
                                if (expected_order in self.played_orders) or (expected_order in self.pending_orders):
                                    break
                                # 否则等待
                                print(f"⏳ 检查失败等待音频序号 {expected_order} 完成, 当前序号: {synthesis_order}")
                                self.play_order_condition.wait(timeout=0.1)
                                if self.stop_playback_flag:
                                    break

                            # 更新播放顺序状态，标记为已播放并更新last_played_order
                            self.played_orders.add(synthesis_order)
                            self.last_played_order = synthesis_order
                            print(f"📝 音频序号 {synthesis_order} 检查失败，已标记为已播放，更新last_played_order为{synthesis_order}")
                            self.play_order_condition.notify_all()
                        self.is_playing = False
                        return

                    # 将音频文件放入全局播放队列
                    try:
                        print(f"✅ 将音频文件放入全局播放队列: {temp_file_path}")

                        # 播放顺序检查机制
                        with self.play_order_condition:
                            # 检查前一个序号的音频是否已经播放或正在等待
                            expected_order = self.last_played_order + 1
                            while synthesis_order != expected_order:
                                # 如果前一个序号的音频已经放入队列或已播放,则允许当前音频放入
                                if (expected_order in self.played_orders) or (expected_order in self.pending_orders):
                                    break
                                # 否则等待
                                print(f"⏳ 等待音频序号 {expected_order} 完成, 当前序号: {synthesis_order}")
                                self.play_order_condition.wait(timeout=0.1)
                                if self.stop_playback_flag:
                                    break

                            # 将当前序号添加到等待集合（必须在放入队列之前）
                            self.pending_orders.add(synthesis_order)
                            print(f"📝 音频序号 {synthesis_order} 已加入等待队列")

                        # 将音频文件放入优先队列
                        self.audio_play_queue.put((synthesis_order, temp_file_path))
                        print(f"✅ GPT-SoVITS TTS合成成功: {text[:50]}...")
                    except Exception as e:
                        print(f"❌ 放入播放队列失败 (未知错误): {e}")
                        import traceback
                        traceback.print_exc()
                        try:
                            os.unlink(temp_file_path)
                        except:
                            pass
                        # 等待前一个序号的音频放入队列或已播放
                        with self.play_order_condition:
                            expected_order = self.last_played_order + 1
                            while synthesis_order != expected_order:
                                # 如果前一个序号的音频已经放入队列或已播放,则允许当前音频标记为已播放
                                if (expected_order in self.played_orders) or (expected_order in self.pending_orders):
                                    break
                                # 否则等待
                                print(f"⏳ 放入队列失败等待音频序号 {expected_order} 完成, 当前序号: {synthesis_order}")
                                self.play_order_condition.wait(timeout=0.1)
                                if self.stop_playback_flag:
                                    break

                            # 更新播放顺序状态，标记为已播放并更新last_played_order
                            self.played_orders.add(synthesis_order)
                            self.pending_orders.discard(synthesis_order)
                            self.last_played_order = synthesis_order
                            print(f"📝 音频序号 {synthesis_order} 放入队列失败，已标记为已播放，更新last_played_order为{synthesis_order}")
                            self.play_order_condition.notify_all()
                        # 设置播放状态为False
                        self.is_playing = False
                        return
                else:
                    print("❌ GPT-SoVITS TTS合成失败")
                    # 等待前一个序号的音频放入队列或已播放
                    with self.play_order_condition:
                        expected_order = self.last_played_order + 1
                        while synthesis_order != expected_order:
                            # 如果前一个序号的音频已经放入队列或已播放,则允许当前音频标记为已播放
                            if (expected_order in self.played_orders) or (expected_order in self.pending_orders):
                                break
                            # 否则等待
                            print(f"⏳ 合成失败等待音频序号 {expected_order} 完成, 当前序号: {synthesis_order}")
                            self.play_order_condition.wait(timeout=0.1)
                            if self.stop_playback_flag:
                                break

                        # 更新播放顺序状态，标记为已播放并更新last_played_order
                        self.played_orders.add(synthesis_order)
                        self.last_played_order = synthesis_order
                        print(f"📝 音频序号 {synthesis_order} 合成失败，已标记为已播放，更新last_played_order为{synthesis_order}")
                        self.play_order_condition.notify_all()
                    # 设置播放状态为False
                    self.is_playing = False

            except Exception as e:
                print(f"❌ GPT-SoVITS TTS处理异常: {e}")
                import traceback
                traceback.print_exc()
                # 等待前一个序号的音频放入队列或已播放
                with self.play_order_condition:
                    expected_order = self.last_played_order + 1
                    while synthesis_order != expected_order:
                        # 如果前一个序号的音频已经放入队列或已播放,则允许当前音频标记为已播放
                        if (expected_order in self.played_orders) or (expected_order in self.pending_orders):
                            break
                        # 否则等待
                        print(f"⏳ 处理异常等待音频序号 {expected_order} 完成, 当前序号: {synthesis_order}")
                        self.play_order_condition.wait(timeout=0.1)
                        if self.stop_playback_flag:
                            break

                    # 更新播放顺序状态，标记为已播放并更新last_played_order
                    self.played_orders.add(synthesis_order)
                    self.last_played_order = synthesis_order
                    print(f"📝 音频序号 {synthesis_order} 处理异常，已标记为已播放，更新last_played_order为{synthesis_order}")
                    self.play_order_condition.notify_all()
                # 设置播放状态为False
                self.is_playing = False

        thread = threading.Thread(target=tts_worker, daemon=True)
        thread.start()

    def stop_speaking(self):
        """停止当前播放"""
        self.stop_all_playback()

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

    def clear_audio_queue(self):
        """清空音频播放队列"""
        while not self.audio_play_queue.empty():
            try:
                priority, audio_file = self.audio_play_queue.get_nowait()
                # 删除队列中的临时文件
                if audio_file and os.path.exists(audio_file):
                    try:
                        os.unlink(audio_file)
                        print(f"🗑️ 已删除队列中的临时音频文件: {audio_file}")
                    except Exception as e:
                        print(f"⚠️ 删除临时音频文件失败: {e}")
            except queue.Empty:
                break
        print("🗑️ 音频播放队列已清空")

    def stop_all_playback(self):
        """停止所有音频播放并清空队列"""
        print("🛑 停止所有音频播放")
        # 停止当前播放
        self.stop_playback_flag = True
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
        # 清空音频队列
        self.clear_audio_queue()
        # 重置播放标志
        self.stop_playback_flag = False
        # 重新启动播放工作线程
        self._start_play_worker()
