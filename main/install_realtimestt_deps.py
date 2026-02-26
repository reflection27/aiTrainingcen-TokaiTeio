
# -*- coding: utf-8 -*-
"""
安装 RealtimeSTT 依赖
"""

import subprocess
import sys

def install_package(package):
    """安装 Python 包"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ {package} 安装成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {package} 安装失败: {e}")
        return False

def main():
    """主函数"""
    print("📦 开始安装 RealtimeSTT 依赖...")

    # 依赖列表
    packages = [
        "PyAudio==0.2.14",
        "faster-whisper==1.1.1",
        "pvporcupine==1.9.5",
        "webrtcvad-wheels==2.0.14",
        "halo==0.0.31",
        "torch",
        "torchaudio",
        "scipy==1.15.2",
        "openwakeword>=0.4.0",
        "websockets==15.0.1",
        "websocket-client==1.8.0",
        "soundfile==0.13.1"
    ]

    # 安装每个包
    failed_packages = []
    for package in packages:
        if not install_package(package):
            failed_packages.append(package)

    # 打印安装结果
    if failed_packages:
        print(f"\n⚠️ 以下包安装失败: {', '.join(failed_packages)}")
        print("请手动安装这些包")
    else:
        print("\n✅ 所有依赖安装成功！")

if __name__ == "__main__":
    main()
