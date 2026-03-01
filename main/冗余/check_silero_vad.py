
import os

path = r'C:\Users\Admin\.cache\torch\hub\snakers4_silero-vad_master\src\silero_vad\data\silero_vad.jit'

if os.path.exists(path):
    size = os.path.getsize(path)
    print(f"✅ 文件存在")
    print(f"📏 文件大小: {size} 字节")
    print(f"📏 文件大小: {size / 1024 / 1024:.2f} MB")

    # 检查文件是否为空或过小
    if size < 1000:
        print("⚠️ 文件大小异常，可能已损坏")
    else:
        print("✅ 文件大小正常")
else:
    print("❌ 文件不存在")
