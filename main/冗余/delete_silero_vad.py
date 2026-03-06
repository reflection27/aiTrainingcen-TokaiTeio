
import os
import shutil

path = r'C:\Users\Admin\.cache\torch\hub\snakers4_silero-vad_master\src\silero_vad\data\silero_vad.jit'

try:
    # 删除文件
    os.remove(path)
    print("✅ silero_vad.jit 文件已删除")
except Exception as e:
    print(f"❌ 删除文件失败: {e}")
