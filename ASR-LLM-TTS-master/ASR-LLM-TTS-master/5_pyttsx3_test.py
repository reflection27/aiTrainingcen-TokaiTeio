import pyttsx3
# 初始化 TTS 引擎
engine = pyttsx3.init()

voices = engine.getProperty('voices')
# 打印出所有的音色信息
for voice in voices:
    print(f'id = {voice.id}----name = {voice.name}')

# 设置语音属性
engine.setProperty('rate', 150)    # 语速engine.setProperty('volume', 0.9)  # 音量（0.0 到 1.0）
# 选择语音
voices = engine.getProperty('voices')
print(voices)
engine.setProperty('voice', voices[0].id)  # 使用第一个语音
# 输入文本
text = "你好，今天天气很好，适合爬山"
# 朗读文本
engine.say(text)
# 等待朗读完成
engine.runAndWait()
