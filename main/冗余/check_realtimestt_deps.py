
# -*- coding: utf-8 -*-
"""
检查 RealtimeSTT 依赖是否已安装
"""

import subprocess
import sys

def check_package(package):
    """检查 Python 包是否已安装"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", package],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"✅ {package} 已安装")
            return True
        else:
            print(f"❌ {package} 未安装")
            return False
    except Exception as e:
        print(f"❌ 检查 {package} 时出错: {e}")
        return False

def main():
    """主函数"""
    print("📦 检查 RealtimeSTT 依赖...")

    # 依赖列表
    packages = [
        "PyAudio",
        "faster-whisper",
        "pvporcupine",
        "webrtcvad-wheels",
        "halo",
        "torch",
        "torchaudio",
        "scipy",
        "openwakeword",
        "websockets",
        "websocket-client",
        "soundfile"
    ]

    # 检查每个包
    missing_packages = []
    for package in packages:
        if not check_package(package):
            missing_packages.append(package)

    # 打印检查结果
    if missing_packages:
        print(f"\n⚠️ 以下包未安装: {', '.join(missing_packages)}")
        print("\n请运行以下命令安装缺失的包:")
        print(f"pip install {' '.join(missing_packages)}")
    else:
        print("\n✅ 所有依赖已安装！")

if __name__ == "__main__":
    main()
