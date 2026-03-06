import cv2
import pyaudio
import wave
import threading
import numpy as np
import time
from queue import Queue
import webrtcvad
import os
import threading
from transformers import Qwen2VLForConditionalGeneration, AutoTokenizer, AutoProcessor
from transformers import AutoModelForCausalLM, AutoTokenizer
from qwen_vl_utils import process_vision_info
import torch
from funasr import AutoModel
import pygame
import edge_tts
import asyncio
from time import sleep
import langid
from langdetect import detect
import re
from pypinyin import pinyin, Style
from modelscope.pipelines import pipeline

# --- 配置huggingFace国内镜像 ---
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

# 参数设置
AUDIO_RATE = 16000        # 音频采样率
AUDIO_CHANNELS = 1        # 单声道
CHUNK = 1024              # 音频块大小
VAD_MODE = 3              # VAD 模式 (0-3, 数字越大越敏感)
OUTPUT_DIR = "./output"   # 输出目录
NO_SPEECH_THRESHOLD = 1   # 无效语音阈值，单位：秒
folder_path = "./Test_QWen2_VL/"
audio_file_count = 0
audio_file_count_tmp = 0

# 确保输出目录存在
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(folder_path, exist_ok=True)

# 队列用于音频和视频同步缓存
audio_queue = Queue()
video_queue = Queue()

# 全局变量
last_active_time = time.time()
recording_active = True
segments_to_save = []
saved_intervals = []
last_vad_end_time = 0  # 上次保存的 VAD 有效段结束时间


# --- 唤醒词、声纹变量配置 ---
# set_KWS = "ni hao xiao qian"
# set_KWS = "shuo hua xiao qian"
set_KWS = "zhan qi lai"
flag_KWS = 0

flag_KWS_used = 1
flag_sv_used = 1

flag_sv_enroll = 0
thred_sv = 0.35

# 初始化 WebRTC VAD
vad = webrtcvad.Vad()
vad.set_mode(VAD_MODE)


def extract_chinese_and_convert_to_pinyin(input_string):
    """
    提取字符串中的汉字，并将其转换为拼音。
    
    :param input_string: 原始字符串
    :return: 转换后的拼音字符串
    """
    # 使用正则表达式提取所有汉字
    chinese_characters = re.findall(r'[\u4e00-\u9fa5]', input_string)
    # 将汉字列表合并为字符串
    chinese_text = ''.join(chinese_characters)
    
    # 转换为拼音
    pinyin_result = pinyin(chinese_text, style=Style.NORMAL)
    # 将拼音列表拼接为字符串
    pinyin_text = ' '.join([item[0] for item in pinyin_result])
    
    return pinyin_text


# 音频录制线程
def audio_recorder():
    global audio_queue, recording_active, last_active_time, segments_to_save, last_vad_end_time
    
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16,
                    channels=AUDIO_CHANNELS,
                    rate=AUDIO_RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
    
    audio_buffer = []
    print("音频录制已开始")
    
    while recording_active:
        data = stream.read(CHUNK)
        audio_buffer.append(data)
        
        # 每 0.5 秒检测一次 VAD
        if len(audio_buffer) * CHUNK / AUDIO_RATE >= 0.5:
            # 拼接音频数据并检测 VAD
            raw_audio = b''.join(audio_buffer)
            vad_result = check_vad_activity(raw_audio)
            
            if vad_result:
                print("检测到语音活动")
                last_active_time = time.time()
                segments_to_save.append((raw_audio, time.time()))
            else:
                print("静音中...")
            
            audio_buffer = []  # 清空缓冲区
        
        # 检查无效语音时间
        if time.time() - last_active_time > NO_SPEECH_THRESHOLD:
            # 检查是否需要保存
            if segments_to_save and segments_to_save[-1][1] > last_vad_end_time:
                save_audio_video()
                last_active_time = time.time()
            else:
                pass
                # print("无新增语音段，跳过保存")
    
    stream.stop_stream()
    stream.close()
    p.terminate()

# 视频录制线程
def video_recorder():
    global video_queue, recording_active
    
    cap = cv2.VideoCapture(0)  # 使用默认摄像头
    print("视频录制已开始")
    
    while recording_active:
        ret, frame = cap.read()
        if ret:
            video_queue.put((frame, time.time()))
            
            # 实时显示摄像头画面
            cv2.imshow("Real Camera", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):  # 按 Q 键退出
                break
        else:
            print("无法获取摄像头画面")
    
    cap.release()
    cv2.destroyAllWindows()

# 检测 VAD 活动
def check_vad_activity(audio_data):
    # 将音频数据分块检测
    num, rate = 0, 0.5
    step = int(AUDIO_RATE * 0.02)  # 20ms 块大小
    flag_rate = round(rate * len(audio_data) // step)

    for i in range(0, len(audio_data), step):
        chunk = audio_data[i:i + step]
        if len(chunk) == step:
            if vad.is_speech(chunk, sample_rate=AUDIO_RATE):
                num += 1

    if num > flag_rate:
        return True
    return False

# 保存音频和视频
def save_audio_video():
    pygame.mixer.init()

    global segments_to_save, video_queue, last_vad_end_time, saved_intervals

    # 全局变量，用于保存音频文件名计数
    global audio_file_count
    global flag_sv_enroll
    global set_SV_enroll

    if flag_sv_enroll:
        audio_output_path = f"{set_SV_enroll}/enroll_0.wav"
    else:
        audio_file_count += 1
        audio_output_path = f"{OUTPUT_DIR}/audio_{audio_file_count}.wav"
    # audio_output_path = f"{OUTPUT_DIR}/audio_0.wav"

    if not segments_to_save:
        return
    
    # 停止当前播放的音频
    if pygame.mixer.music.get_busy():
        pygame.mixer.music.stop()
        print("检测到新的有效音，已停止当前音频播放")
        
    # 获取有效段的时间范围
    start_time = segments_to_save[0][1]
    end_time = segments_to_save[-1][1]
    
    # 检查是否与之前的片段重叠
    if saved_intervals and saved_intervals[-1][1] >= start_time:
        print("当前片段与之前片段重叠，跳过保存")
        segments_to_save.clear()
        return
    
    # 保存音频
    audio_frames = [seg[0] for seg in segments_to_save]
    if flag_sv_enroll:
        audio_length = 0.5 * len(segments_to_save)
        if audio_length < 3:
            print("声纹注册语音需大于3秒，请重新注册")
            return 1

    wf = wave.open(audio_output_path, 'wb')
    wf.setnchannels(AUDIO_CHANNELS)
    wf.setsampwidth(2)  # 16-bit PCM
    wf.setframerate(AUDIO_RATE)
    wf.writeframes(b''.join(audio_frames))
    wf.close()
    print(f"音频保存至 {audio_output_path}")

    # Inference()

    if flag_sv_enroll:
        text = "声纹注册完成！现在只有你可以命令我啦！"
        print(text)
        flag_sv_enroll = 0
        system_introduction(text)
    else:
    # 使用线程执行推理
        inference_thread = threading.Thread(target=Inference, args=(audio_output_path,))
        inference_thread.start()
        
        # 记录保存的区间
        saved_intervals.append((start_time, end_time))
        
    # 清空缓冲区
    segments_to_save.clear()

# --- 播放音频 -
def play_audio(file_path):
    try:
        pygame.mixer.init()
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(1)  # 等待音频播放结束
        print("播放完成！")
    except Exception as e:
        print(f"播放失败: {e}")
    finally:
        pygame.mixer.quit()

async def amain(TEXT, VOICE, OUTPUT_FILE) -> None:
    """Main function"""
    communicate = edge_tts.Communicate(TEXT, VOICE)
    await communicate.save(OUTPUT_FILE)

import os

def is_folder_empty(folder_path):
    """
    检测指定文件夹内是否有文件。
    
    :param folder_path: 文件夹路径
    :return: 如果文件夹为空返回 True，否则返回 False
    """
    # 获取文件夹中的所有条目（文件或子文件夹）
    entries = os.listdir(folder_path)
    # 检查是否存在文件
    for entry in entries:
        # 获取完整路径
        full_path = os.path.join(folder_path, entry)
        # 如果是文件，返回 False
        if os.path.isfile(full_path):
            return False
    # 如果没有文件，返回 True
    return True


# -------- SenceVoice 语音识别 --模型加载-----
model_dir = r"E:\2_PYTHON\Project\GPT\QWen\pretrained_models\SenseVoiceSmall"
model_senceVoice = AutoModel( model=model_dir, trust_remote_code=True, )

# -------- CAM++声纹识别 -- 模型加载 --------
set_SV_enroll = r'.\SpeakerVerification_DIR\enroll_wav\\'
sv_pipeline = pipeline(
    task='speaker-verification',
    model='damo/speech_campplus_sv_zh-cn_16k-common',
    model_revision='v1.0.0'
)

# --------- QWen2.5大语言模型 ---------------
# model_name = r"E:\2_PYTHON\Project\GPT\QWen\Qwen2.5-0.5B-Instruct"
model_name = r"E:\2_PYTHON\Project\GPT\QWen\Qwen2.5-1.5B-Instruct"
# model_name = r'E:\2_PYTHON\Project\GPT\QWen\Qwen2.5-7B-Instruct-GPTQ-Int4'
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype="auto",
    device_map="auto"
)
tokenizer = AutoTokenizer.from_pretrained(model_name)
# ---------- 模型加载结束 -----------------------

class ChatMemory:
    def __init__(self, max_length=2048):
        self.history = []
        self.max_length = max_length  # 最大输入长度

    def add_to_history(self, user_input, model_response):
        """
        添加用户输入和模型响应到历史记录。
        """
        self.history.append(f"User: {user_input}")
        self.history.append(f"system: {model_response}")

    def get_context(self):
        """
        获取拼接后的对话上下文。
        """
        context = "\n".join(self.history)
        # 截断上下文，使其不超过 max_length
        if len(context) > self.max_length:
            context = context[-self.max_length :]
        return context
    
# -------- memory 初始化 --------
memory = ChatMemory(max_length=512)

def system_introduction(text):
    global audio_file_count
    global folder_path
    text = text
    print("LLM output:", text)
    used_speaker = "zh-CN-XiaoyiNeural"
    asyncio.run(amain(text, used_speaker, os.path.join(folder_path,f"sft_tmp_{audio_file_count}.mp3")))
    play_audio(f'{folder_path}/sft_tmp_{audio_file_count}.mp3')

def Inference(TEMP_AUDIO_FILE=f"{OUTPUT_DIR}/audio_0.wav"):
    '''
    1. 使用senceVoice做asr，转换为拼音，检测唤醒词
        - 首先检测声纹注册文件夹是否有注册文件，如果无，启动声纹注册
    2. 使用CAM++做声纹识别
        - 设置固定声纹注册语音目录，每次输入音频均进行声纹对比
    3. 以上两者均通过，则进行大模型推理
    '''
    global audio_file_count

    global set_SV_enroll
    global flag_sv_enroll
    global thred_sv
    global flag_sv_used

    global set_KWS
    global flag_KWS
    global flag_KWS_used
    
    os.makedirs(set_SV_enroll, exist_ok=True)
    # --- 如果开启声纹识别，且声纹文件夹为空，则开始声纹注册。设定注册语音有效长度需大于3秒
    if flag_sv_used and is_folder_empty(set_SV_enroll):
        text = f"无声纹注册文件！请先注册声纹，需大于三秒哦~"
        print(text)
        system_introduction(text)
        flag_sv_enroll = 1
    
    else:
        # -------- SenceVoice 推理 ---------
        input_file = (TEMP_AUDIO_FILE)
        res = model_senceVoice.generate(
            input=input_file,
            cache={},
            language="auto", # "zn", "en", "yue", "ja", "ko", "nospeech"
            use_itn=False,
        )
        prompt = res[0]['text'].split(">")[-1]
        prompt_pinyin = extract_chinese_and_convert_to_pinyin(prompt)
        print(prompt, prompt_pinyin)

        # --- 判断是否启动KWS
        if not flag_KWS_used:
            flag_KWS = 1
        if not flag_KWS:
            if set_KWS in prompt_pinyin:
                flag_KWS = 1
        
        # --- KWS成功，或不设置KWS
        if flag_KWS:
            sv_score = sv_pipeline([os.path.join(set_SV_enroll, "enroll_0.wav"), TEMP_AUDIO_FILE], thr=thred_sv)
            print(sv_score)
            sv_result = sv_score['text']
            if sv_result == "yes":

                # --- 读取历史对话 ---
                context = memory.get_context()
                
                # prompt_tmp = res[0]['text'].split(">")[-1] + "，回答简短一些，保持50字以内！"
                prompt_tmp = res[0]['text'].split(">")[-1]
                prompt = f"{context}\nUser:{prompt_tmp}\n"

                print("History:", context)
                print("ASR OUT:", prompt)
                # ---------SenceVoice --end----------
                # -------- 模型推理阶段，将语音识别结果作为大模型Prompt ------
                messages = [
                    {"role": "system", "content": "你叫小千，是一个18岁的女大学生，性格活泼开朗，说话俏皮简洁，回答问题不会超过50字。"},
                    {"role": "user", "content": prompt},
                ]
                text = tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                )
                model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

                generated_ids = model.generate(
                    **model_inputs,
                    max_new_tokens=512,
                )
                generated_ids = [
                    output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
                ]

                output_text = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

                print("answer", output_text)

                # -------- 更新记忆库 -----
                memory.add_to_history(prompt_tmp, output_text)

                # 输入文本
                text = output_text
                # 语种识别 -- langid
                language, confidence = langid.classify(text)
                # 语种识别 -- langdetect 
                # language = detect(text).split("-")[0]

                language_speaker = {
                "ja" : "ja-JP-NanamiNeural",            # ok
                "fr" : "fr-FR-DeniseNeural",            # ok
                "es" : "ca-ES-JoanaNeural",             # ok
                "de" : "de-DE-KatjaNeural",             # ok
                "zh" : "zh-CN-XiaoyiNeural",            # ok
                "en" : "en-US-AnaNeural",               # ok
                }

                if language not in language_speaker.keys():
                    used_speaker = "zh-CN-XiaoyiNeural"
                else:
                    used_speaker = language_speaker[language]
                    print("检测到语种：", language, "使用音色：", language_speaker[language])

                asyncio.run(amain(text, used_speaker, os.path.join(folder_path,f"sft_{audio_file_count}.mp3")))
                play_audio(f'{folder_path}/sft_{audio_file_count}.mp3')
            else:
                text = "很抱歉，声纹验证失败，我无法为您服务"
                print(text)
                # system_introduction(text)
        else:
            text = "很抱歉，唤醒词错误，请说出正确的唤醒词哦"
            system_introduction(text)

# 主函数
if __name__ == "__main__":

    try:
        # 启动音视频录制线程
        audio_thread = threading.Thread(target=audio_recorder)
        # video_thread = threading.Thread(target=video_recorder)
        audio_thread.start()
        # video_thread.start()

        flag_info = f'{flag_sv_used}-{flag_KWS_used}'
        dict_flag_info = {
            "1-1": "您已开启声纹识别和关键词唤醒，",
            "0-1":"您已开启关键词唤醒",
            "1-0":"您已开启声纹识别",
            "0-0":"",
        }
        if flag_sv_used or flag_KWS_used:
            text = dict_flag_info[flag_info]
            system_introduction(text)

        print("按 Ctrl+C 停止录制")
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("录制停止中...")
        recording_active = False
        audio_thread.join()
        # video_thread.join()
        print("录制已停止")
