import cv2
import pyaudio
import wave
import threading
import ffmpeg
import os

# 配置音频参数
AUDIO_FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024

# 配置视频参数
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FRAME_RATE = 20.0

# 文件保存路径
TEMP_AUDIO_FILE = "temp_audio.wav"
TEMP_VIDEO_FILE = "temp_video.avi"
OUTPUT_FILE = "output.mp4"

# 音频录制线程
def record_audio(stop_event):
    audio = pyaudio.PyAudio()
    stream = audio.open(format=AUDIO_FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    frames = []
    print("开始录音...")

    while not stop_event.is_set():
        data = stream.read(CHUNK)
        frames.append(data)

    print("录音结束。")
    stream.stop_stream()
    stream.close()
    audio.terminate()

    # 保存音频
    with wave.open(TEMP_AUDIO_FILE, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(audio.get_sample_size(AUDIO_FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))

# 视频录制线程
def record_video(stop_event):
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, FRAME_RATE)

    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(TEMP_VIDEO_FILE, fourcc, FRAME_RATE, (FRAME_WIDTH, FRAME_HEIGHT))
    print("开始录像...")

    while not stop_event.is_set():
        ret, frame = cap.read()
        if ret:
            out.write(frame)
            cv2.imshow('Recording Video', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):  # 按 Q 退出摄像头窗口
                stop_event.set()
        else:
            break

    print("录像结束。")
    cap.release()
    out.release()
    cv2.destroyAllWindows()

# 合并音视频
def merge_audio_video(audio_file, video_file, output_file):
    print("正在合并音频和视频...")
    ffmpeg.input(video_file).output(audio_file, output_file, vcodec='copy', acodec='aac', strict='experimental').run(overwrite_output=True)
    print(f"合并完成，文件保存为: {output_file}")

# 主函数
def main():
    stop_event = threading.Event()
    
    # 启动音频和视频录制线程
    audio_thread = threading.Thread(target=record_audio, args=(stop_event,))
    video_thread = threading.Thread(target=record_video, args=(stop_event,))

    print("按 Enter 键开始录制...")
    input()  # 等待用户按下 Enter 键
    print("录制中... 再次按 Enter 键停止录制。")
    
    audio_thread.start()
    video_thread.start()

    input()  # 等待用户再次按下 Enter 键
    stop_event.set()

    audio_thread.join()
    video_thread.join()

    # # 合并音频和视频
    # merge_audio_video(TEMP_AUDIO_FILE, TEMP_VIDEO_FILE, OUTPUT_FILE)

    # # 清理临时文件
    # os.remove(TEMP_AUDIO_FILE)
    # os.remove(TEMP_VIDEO_FILE)

    print("录制完成！")

if __name__ == "__main__":
    main()
