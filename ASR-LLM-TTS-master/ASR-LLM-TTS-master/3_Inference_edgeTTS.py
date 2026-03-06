#!/usr/bin/env python3

"""
Basic example of edge_tts usage.
"""

import asyncio

import edge_tts

# TEXT = "今日特别报道，伊朗、舍沙特阿拉伯在北京中方见证下，决定恢复外交关系，重启大使馆并互相派驻外交大使"
# VOICE = "zh-CN-YunxiNeural"
# OUTPUT_FILE = "test_male.mp3"

# TEXT = "はそれぞれ"
# VOICE = "ja-JP-NanamiNeural"
# OUTPUT_FILE = "test_male.mp3"

# TEXT = "Estoy bien, gracias. ¿Y tú?"
# VOICE = "ca-ES-JoanaNeural"
# OUTPUT_FILE = "test_male.mp3"

# TEXT = "Ça va bien, merci. Et toi ?"
# VOICE = "fr-FR-DeniseNeural"
# OUTPUT_FILE = "test_male.mp3"

TEXT = "hello, whats your name"
VOICE = "en-US-AnaNeural"
OUTPUT_FILE = "test_male.mp3"

async def amain() -> None:
    """Main function"""
    communicate = edge_tts.Communicate(TEXT, VOICE)
    await communicate.save(OUTPUT_FILE)


if __name__ == "__main__":
    asyncio.run(amain())

'''
Name: zh-CN-XiaoyiNeural
Gender: Female

Name: zh-CN-YunjianNeural
Gender: Male

Name: zh-CN-YunxiNeural
Gender: Male

Name: zh-CN-YunxiaNeural
Gender: Male

Name: zh-CN-YunyangNeural
Gender: Male

Name: zh-CN-liaoning-XiaobeiNeural
Gender: Female

Name: zh-CN-shaanxi-XiaoniNeural
Gender: Female

Name: zh-HK-HiuGaaiNeural
Gender: Female

Name: zh-HK-HiuMaanNeural
Gender: Female

Name: zh-HK-WanLungNeural
Gender: Male

Name: zh-TW-HsiaoChenNeural
Gender: Female
'''