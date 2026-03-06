import cv2
import pyaudio
import wave
import threading
from transformers import Qwen2VLForConditionalGeneration, AutoTokenizer, AutoProcessor
from qwen_vl_utils import process_vision_info
import torch
from funasr import AutoModel

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
# OUTPUT_FILE = "output.mp4"

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
    file_path = "captured_image.jpg"  # 设置保存路径
    cap = cv2.VideoCapture(TEMP_VIDEO_FILE)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_index = int(total_frames // 2)
    # 设置视频帧位置
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ret, frame = cap.read()
    if not ret:
        print(f"无法读取帧索引 {frame_index}")
    else:
        # 显示帧
        cv2.imwrite(file_path, frame)
        # cv2.imshow(f"Frame {frame_index}", frame)

    # -------------- Load QWen2-VL Model ------------
    # default: Load the model on the available device(s)
    model = Qwen2VLForConditionalGeneration.from_pretrained(
        "Qwen/Qwen2-VL-2B-Instruct", torch_dtype="auto", device_map="auto"
    )
    # ------- 设置分辨率，降低现存占用 -------
    min_pixels = 256*28*28
    max_pixels = 1280*28*28
    processor = AutoProcessor.from_pretrained("Qwen/Qwen2-VL-2B-Instruct", min_pixels=min_pixels, max_pixels=max_pixels)
    # --------------------------------------

    # -------- SenceVoice 语音识别 -------
    model_dir = r"E:\2_PYTHON\Project\GPT\QWen\pretrained_models\SenseVoiceSmall"
    model_senceVoice = AutoModel( model=model_dir, trust_remote_code=True, )
    input_file = (TEMP_AUDIO_FILE)
    res = model_senceVoice.generate(
        input=input_file,
        cache={},
        language="auto", # "zn", "en", "yue", "ja", "ko", "nospeech"
        use_itn=False,
    )
    prompt = res[0]['text'].split(">")[-1]
    # ---------SenceVoice --end----------

    # -------- QWen2-VL 模型推理 ---------
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "image": f"{file_path}",
                },
                {"type": "text", "text": f"{prompt}"},
            ],
        }
    ]

    # Preparation for inference
    text = processor.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    image_inputs, video_inputs = process_vision_info(messages)
    inputs = processor(
        text=[text],
        images=image_inputs,
        videos=video_inputs,
        padding=True,
        return_tensors="pt",
    )
    inputs = inputs.to("cuda")

    # Inference: Generation of the output
    generated_ids = model.generate(**inputs, max_new_tokens=128)
    generated_ids_trimmed = [
        out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
    ]
    output_text = processor.batch_decode(
        generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
    )
    print(output_text)
