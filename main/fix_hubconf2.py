
import os

path = r'C:\Users\Admin\.cache\torch\hub\snakers4_silero-vad_master\hubconf.py'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 替换导入语句
old_import = 'from silero_vad.utils_vad import (init_jit_model,\nget_speech_timestamps,\nsave_audio,\nread_audio,\nVADIterator,\ncollect_chunks,\nOnnxWrapper)'
new_import = 'from silero_vad.utils_vad import (init_jit_model,\nget_speech_timestamps,\nsave_audio,\nread_audio,\nVADIterator,\ncollect_chunks,\nOnnxWrapper,\ndrop_chunks)'

new_content = content.replace(old_import, new_import)

with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print('修改完成')
