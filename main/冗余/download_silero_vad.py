
import os
import requests

# 文件路径
model_dir = r'C:\Users\Admin\.cache\torch\hub\snakers4_silero-vad_master\src\silero_vad\data'
model_path = os.path.join(model_dir, 'silero_vad.jit')

# 确保目录存在
os.makedirs(model_dir, exist_ok=True)

# 下载 URL
url = 'https://raw.githubusercontent.com/snakers4/silero-vad/master/files/silero_vad.jit'

try:
    print("📥 开始下载 silero_vad.jit...")
    response = requests.get(url, stream=True)
    response.raise_for_status()

    # 写入文件
    with open(model_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    print(f"✅ 下载完成")
    print(f"📏 文件大小: {os.path.getsize(model_path)} 字节")
    print(f"📏 文件大小: {os.path.getsize(model_path) / 1024 / 1024:.2f} MB")
except Exception as e:
    print(f"❌ 下载失败: {e}")
    import traceback
    traceback.print_exc()
