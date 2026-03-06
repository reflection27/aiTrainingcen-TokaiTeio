import pygame
import time
import sys
import sounddevice as sd
from scipy.io.wavfile import write
import numpy as np

def record_audio(filename="output.wav", sample_rate=44100):
    print("按下 Enter 开始录音...")
    input()  # 等待用户按下 Enter 键开始录音
    print("录音中... 按下 Enter 键结束录音")
    
    # 开始录音
    recording = []
    try:
        def callback(indata, frames, time, status):
            recording.append(indata.copy())
        with sd.InputStream(samplerate=sample_rate, channels=1, callback=callback):
            input()  # 等待用户再次按下 Enter 键结束录音
    except Exception as e:
        print(f"录音出现错误: {e}")
        return
    
    # 将录音数据合并并保存为 WAV 文件
    audio_data = np.concatenate(recording, axis=0)
    write(filename, sample_rate, (audio_data * 32767).astype(np.int16))
    print(f"录音已保存为 {filename}")


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

# 使用函数录音，作为输入
record_audio("my_recording.wav")
play_audio('my_recording.wav')