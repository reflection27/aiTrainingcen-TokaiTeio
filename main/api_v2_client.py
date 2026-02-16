
import requests
import json
import time
from typing import Optional, Dict, Any, Union
from io import BytesIO
import wave
import soundfile as sf
import numpy as np


class TTSClientV2:
    """
    GPT-SoVITS API v2 客户端，支持流式和非流式语音合成
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 9880):
        """
        初始化TTS客户端

        参数:
            host: API服务器地址，默认为127.0.0.1
            port: API服务器端口，默认为9880
        """
        self.base_url = f"http://{host}:{port}"

    def tts(
        self,
        text: str,
        text_lang: str = "zh",
        ref_audio_path: str = None,
        aux_ref_audio_paths: list = None,
        prompt_text: str = "",
        prompt_lang: str = "zh",
        top_k: int = 5,
        top_p: float = 1,
        temperature: float = 1,
        text_split_method: str = "cut5",
        batch_size: int = 1,
        batch_threshold: float = 0.75,
        split_bucket: bool = True,
        speed_factor: float = 1.0,
        fragment_interval: float = 0.3,
        seed: int = -1,
        media_type: str = "wav",
        streaming_mode: bool = False,
        parallel_infer: bool = True,
        repetition_penalty: float = 1.35
    ) -> Union[bytes, None]:
        """
        文本转语音（非流式）

        参数:
            text: 要合成的文本
            text_lang: 文本语言
            ref_audio_path: 参考音频路径
            aux_ref_audio_paths: 辅助参考音频路径列表
            prompt_text: 参考音频的提示文本
            prompt_lang: 参考音频的提示文本语言
            top_k: top k采样参数
            top_p: top p采样参数
            temperature: 温度采样参数
            text_split_method: 文本分割方法
            batch_size: 批处理大小
            batch_threshold: 批处理阈值
            split_bucket: 是否分割批次
            speed_factor: 语速因子
            fragment_interval: 片段间隔
            seed: 随机种子
            media_type: 媒体类型（wav, raw, ogg, aac）
            streaming_mode: 是否流式输出
            parallel_infer: 是否并行推理
            repetition_penalty: 重复惩罚

        返回:
            音频数据（bytes）或None（如果失败）
        """
        if ref_audio_path is None:
            print("错误: ref_audio_path 是必需的参数")
            return None

        # 准备请求数据
        data = {
            "text": text,
            "text_lang": text_lang,
            "ref_audio_path": ref_audio_path,
            "prompt_text": prompt_text,
            "prompt_lang": prompt_lang,
            "top_k": top_k,
            "top_p": top_p,
            "temperature": temperature,
            "text_split_method": text_split_method,
            "batch_size": batch_size,
            "batch_threshold": batch_threshold,
            "split_bucket": split_bucket,
            "speed_factor": speed_factor,
            "fragment_interval": fragment_interval,
            "seed": seed,
            "media_type": media_type,
            "streaming_mode": streaming_mode,
            "parallel_infer": parallel_infer,
            "repetition_penalty": repetition_penalty
        }

        if aux_ref_audio_paths:
            data["aux_ref_audio_paths"] = aux_ref_audio_paths

        try:
            # 发送POST请求
            response = requests.post(
                f"{self.base_url}/tts",
                json=data,
                stream=streaming_mode,
                timeout=60
            )

            # 检查响应状态
            if response.status_code != 200:
                try:
                    error_info = response.json()
                    print(f"TTS请求失败: {error_info}")
                except:
                    print(f"TTS请求失败，状态码: {response.status_code}")
                return None

            return response.content
        except Exception as e:
            print(f"TTS请求异常: {str(e)}")
            return None

    def tts_streaming(
        self,
        text: str,
        text_lang: str = "zh",
        ref_audio_path: str = None,
        aux_ref_audio_paths: list = None,
        prompt_text: str = "",
        prompt_lang: str = "zh",
        top_k: int = 5,
        top_p: float = 1,
        temperature: float = 1,
        text_split_method: str = "cut5",
        batch_size: int = 1,
        batch_threshold: float = 0.75,
        split_bucket: bool = True,
        speed_factor: float = 1.0,
        fragment_interval: float = 0.3,
        seed: int = -1,
        media_type: str = "wav",
        parallel_infer: bool = True,
        repetition_penalty: float = 1.35,
        chunk_callback: callable = None
    ) -> Union[bytes, None]:
        """
        文本转语音（流式）

        参数:
            text: 要合成的文本
            text_lang: 文本语言
            ref_audio_path: 参考音频路径
            aux_ref_audio_paths: 辅助参考音频路径列表
            prompt_text: 参考音频的提示文本
            prompt_lang: 参考音频的提示文本语言
            top_k: top k采样参数
            top_p: top p采样参数
            temperature: 温度采样参数
            text_split_method: 文本分割方法
            batch_size: 批处理大小
            batch_threshold: 批处理阈值
            split_bucket: 是否分割批次
            speed_factor: 语速因子
            fragment_interval: 片段间隔
            seed: 随机种子
            media_type: 媒体类型（wav, raw, ogg, aac）
            parallel_infer: 是否并行推理
            repetition_penalty: 重复惩罚
            chunk_callback: 接收音频块的回调函数

        返回:
            完整音频数据（bytes）或None（如果失败）
        """
        if ref_audio_path is None:
            print("错误: ref_audio_path 是必需的参数")
            return None

        # 准备请求数据
        data = {
            "text": text,
            "text_lang": text_lang,
            "ref_audio_path": ref_audio_path,
            "prompt_text": prompt_text,
            "prompt_lang": prompt_lang,
            "top_k": top_k,
            "top_p": top_p,
            "temperature": temperature,
            "text_split_method": text_split_method,
            "batch_size": batch_size,
            "batch_threshold": batch_threshold,
            "split_bucket": split_bucket,
            "speed_factor": speed_factor,
            "fragment_interval": fragment_interval,
            "seed": seed,
            "media_type": media_type,
            "streaming_mode": True,  # 强制启用流式模式
            "parallel_infer": parallel_infer,
            "repetition_penalty": repetition_penalty
        }

        if aux_ref_audio_paths:
            data["aux_ref_audio_paths"] = aux_ref_audio_paths

        try:
            # 发送POST请求
            response = requests.post(
                f"{self.base_url}/tts",
                json=data,
                stream=True,
                timeout=60
            )

            # 检查响应状态
            if response.status_code != 200:
                try:
                    error_info = response.json()
                    print(f"TTS流式请求失败: {error_info}")
                except:
                    print(f"TTS流式请求失败，状态码: {response.status_code}")
                return None

            # 收集所有音频块
            audio_chunks = []

            # 处理流式响应
            for chunk in response.iter_content(chunk_size=4096):
                if chunk:  # 过滤掉keep-alive新块
                    audio_chunks.append(chunk)
                    # 如果提供了回调函数，则调用它
                    if chunk_callback:
                        chunk_callback(chunk)

            # 合并所有音频块
            if audio_chunks:
                return b''.join(audio_chunks)
            return None

        except Exception as e:
            print(f"TTS流式请求异常: {str(e)}")
            return None

    def save_audio(self, audio_data: bytes, output_path: str):
        """
        保存音频数据到文件

        参数:
            audio_data: 音频数据
            output_path: 输出文件路径
        """
        try:
            with open(output_path, "wb") as f:
                f.write(audio_data)
            print(f"音频已保存到: {output_path}")
        except Exception as e:
            print(f"保存音频失败: {str(e)}")

    def set_refer_audio(self, refer_audio_path: str) -> bool:
        """
        设置参考音频

        参数:
            refer_audio_path: 参考音频路径

        返回:
            操作是否成功
        """
        try:
            response = requests.get(
                f"{self.base_url}/set_refer_audio",
                params={"refer_audio_path": refer_audio_path},
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("message") == "success":
                    print("参考音频设置成功")
                    return True
                else:
                    print(f"设置参考音频失败: {result.get('message')}")
                    return False
            else:
                print(f"设置参考音频失败，状态码: {response.status_code}")
                return False
        except Exception as e:
            print(f"设置参考音频异常: {str(e)}")
            return False

    def set_gpt_weights(self, weights_path: str) -> bool:
        """
        设置GPT模型权重

        参数:
            weights_path: 权重文件路径

        返回:
            操作是否成功
        """
        try:
            response = requests.get(
                f"{self.base_url}/set_gpt_weights",
                params={"weights_path": weights_path},
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("message") == "success":
                    print("GPT权重设置成功")
                    return True
                else:
                    print(f"设置GPT权重失败: {result.get('message')}")
                    return False
            else:
                print(f"设置GPT权重失败，状态码: {response.status_code}")
                return False
        except Exception as e:
            print(f"设置GPT权重异常: {str(e)}")
            return False

    def set_sovits_weights(self, weights_path: str) -> bool:
        """
        设置SoVITS模型权重

        参数:
            weights_path: 权重文件路径

        返回:
            操作是否成功
        """
        try:
            response = requests.get(
                f"{self.base_url}/set_sovits_weights",
                params={"weights_path": weights_path},
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("message") == "success":
                    print("SoVITS权重设置成功")
                    return True
                else:
                    print(f"设置SoVITS权重失败: {result.get('message')}")
                    return False
            else:
                print(f"设置SoVITS权重失败，状态码: {response.status_code}")
                return False
        except Exception as e:
            print(f"设置SoVITS权重异常: {str(e)}")
            return False

    def control(self, command: str) -> bool:
        """
        发送控制命令

        参数:
            command: 控制命令（restart 或 exit）

        返回:
            操作是否成功
        """
        try:
            response = requests.get(
                f"{self.base_url}/control",
                params={"command": command},
                timeout=10
            )

            if response.status_code == 200:
                print(f"控制命令 {command} 发送成功")
                return True
            else:
                print(f"发送控制命令失败，状态码: {response.status_code}")
                return False
        except Exception as e:
            print(f"发送控制命令异常: {str(e)}")
            return False


# 示例用法
if __name__ == "__main__":
    # 创建客户端实例
    client = TTSClientV2(host="127.0.0.1", port=9880)

    # 示例1: 非流式文本转语音
    print("示例1: 非流式文本转语音")
    audio_data = client.tts(
        text="你好，我是东海帝王，很高兴见到你！",
        text_lang="zh",
        ref_audio_path="reference.wav",  # 请替换为实际的参考音频路径
        prompt_lang="zh",
        prompt_text="",  # 空prompt_text，让模型自动从参考音频中学习
        text_split_method="cut5",
        batch_size=1,
        media_type="wav",
        streaming_mode=False
    )

    if audio_data:
        client.save_audio(audio_data, "output_non_streaming.wav")

    # 示例2: 流式文本转语音
    print("示例2: 流式文本转语音")

    # 定义接收音频块的回调函数
    def audio_chunk_callback(chunk):
        print(f"接收到音频块，大小: {len(chunk)} 字节")

    audio_data_stream = client.tts_streaming(
        text="今天天气真好，一起去跑步吧！",
        text_lang="zh",
        ref_audio_path="reference.wav",  # 请替换为实际的参考音频路径
        prompt_lang="zh",
        prompt_text="",  # 空prompt_text，让模型自动从参考音频中学习
        text_split_method="cut5",
        batch_size=1,
        media_type="wav",
        chunk_callback=audio_chunk_callback
    )

    if audio_data_stream:
        client.save_audio(audio_data_stream, "output_streaming.wav")

    # 示例3: 设置参考音频
    print("示例3: 设置参考音频")
    client.set_refer_audio("new_reference.wav")

    # 示例4: 切换模型权重
    print("示例4: 切换模型权重")
    client.set_gpt_weights("GPT_SoVITS/pretrained_models/gsv-v2final-pretrained/s1bert25hz-5kh-longer-epoch=12-step=369668.ckpt")
    client.set_sovits_weights("GPT_SoVITS/pretrained_models/gsv-v2final-pretrained/s2G2333k.pth")

    # 示例5: 发送控制命令
    print("示例5: 发送控制命令")
    # client.control("restart")  # 重启服务
    # client.control("exit")     # 退出服务
