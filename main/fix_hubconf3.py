import os

path = r'C:\Users\Admin\.cache\torch\hub\snakers4_silero-vad_master\hubconf.py'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 替换导入语句
old_import = '''from silero_vad.utils_vad import (init_jit_model,
get_speech_timestamps,
save_audio,
read_audio,
VADIterator,
collect_chunks,
OnnxWrapper)'''

new_import = '''from silero_vad.utils_vad import (init_jit_model,
get_speech_timestamps,
save_audio,
read_audio,
VADIterator,
collect_chunks,
OnnxWrapper,
drop_chunks)'''

if old_import in content:
    new_content = content.replace(old_import, new_import)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print('修改完成')
else:
    print('未找到要替换的内容')
    print('当前导入语句:')
    # 查找并打印当前的导入语句
    import re
    match = re.search(r'from silero_vad\.utils_vad import \([^)]+\)', content, re.DOTALL)
    if match:
        print(match.group(0))
