from transformers import AutoModelForCausalLM, AutoTokenizer

from cosyvoice.cli.cosyvoice import CosyVoice
from cosyvoice.utils.file_utils import load_wav
import torchaudio

import pygame
import time

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

model_name = r".\QWen\Qwen2.5-0.5B-Instruct"
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype="auto",
    device_map="auto"
)
tokenizer = AutoTokenizer.from_pretrained(model_name)

cosyvoice = CosyVoice(r'../pretrained_models/CosyVoice-300M', load_jit=True, load_onnx=False, fp16=True)
# sft usage
print(cosyvoice.list_avaliable_spks())

prompt = "你好，你叫什么名字?"
messages = [
    {"role": "system", "content": "You are Qwen, created by Alibaba Cloud. You are a helpful assistant."},
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

response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

print("Input:", prompt)
print("Answer:", response)

# ['中文女', '中文男', '日语男', '粤语女', '英文女', '英文男', '韩语女']
for i, j in enumerate(cosyvoice.inference_sft(f'{prompt}', '中文男', stream=False)):
    torchaudio.save('prompt_sft_{}.wav'.format(i), j['tts_speech'], 22050)
    # play_audio('prompt_sft_{}.wav'.format(i))

# change stream=True for chunk stream inference
for i, j in enumerate(cosyvoice.inference_sft(f'{response}', '中文女', stream=False)):
    torchaudio.save('sft_{}.wav'.format(i), j['tts_speech'], 22050)
    # play_audio('sft_{}.wav'.format(i))

play_audio('prompt_sft_0.wav')
for i, j in enumerate(f'{response}'):
    play_audio('sft_{}.wav'.format(i))

