import os

path = r'C:\Users\Admin\.cache\torch\hub\snakers4_silero-vad_master\hubconf.py'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 替换导入语句 - 处理不同的换行符
old_import = 'from silero_vad.utils_vad import (init_jit_model,\nget_speech_timestamps,\nsave_audio,\nread_audio,\nVADIterator,\ncollect_chunks,\nOnnxWrapper)'
new_import = 'from silero_vad.utils_vad import (init_jit_model,\nget_speech_timestamps,\nsave_audio,\nread_audio,\nVADIterator,\ncollect_chunks,\nOnnxWrapper,\ndrop_chunks)'

# 尝试替换
if old_import in content:
    new_content = content.replace(old_import, new_import)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print('修改完成')
else:
    # 尝试使用 \r\n
    old_import_rn = old_import.replace('\n', '\r\n')
    new_import_rn = new_import.replace('\n', '\r\n')

    if old_import_rn in content:
        new_content = content.replace(old_import_rn, new_import_rn)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print('修改完成 (使用 \r\n)')
    else:
        print('未找到要替换的内容')
        print('尝试直接在 OnnxWrapper 后添加 drop_chunks')
        # 直接在 OnnxWrapper 后添加 drop_chunks
        new_content = content.replace('OnnxWrapper)', 'OnnxWrapper,\n    drop_chunks)')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print('修改完成')
