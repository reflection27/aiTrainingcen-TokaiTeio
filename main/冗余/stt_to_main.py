
# -*- coding: utf-8 -*-
"""
STT到主程序的桥接脚本
用于将STT识别的文本发送到主程序
"""

import sys
import time
import requests
import json

class STTToMainBridge:
    """STT到主程序的桥接类"""

    def __init__(self, main_url="http://127.0.0.1:5000"):
        self.main_url = main_url
        self.max_retries = 5
        self.retry_delay = 2  # 秒

    def send_text_to_main(self, text):
        """
        将文本发送到主程序

        Args:
            text: 要发送的文本

        Returns:
            如果成功返回True，否则返回False
        """
        try:
            # 尝试发送文本到主程序
            response = requests.post(
                f"{self.main_url}/api/text_input",
                json={"text": text},
                timeout=5
            )

            if response.status_code == 200:
                print(f"✅ 文本已发送到主程序: {text}")
                return True
            else:
                print(f"❌ 主程序返回错误: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            print("❌ 无法连接到主程序，请确保主程序已启动")
            return False
        except Exception as e:
            print(f"❌ 发送文本失败: {str(e)}")
            return False

    def wait_for_main(self):
        """等待主程序启动"""
        for i in range(self.max_retries):
            try:
                response = requests.get(
                    f"{self.main_url}/api/status",
                    timeout=2
                )
                if response.status_code == 200:
                    print("✅ 主程序已就绪")
                    return True
            except:
                pass

            print(f"⏳ 等待主程序启动... ({i+1}/{self.max_retries})")
            time.sleep(self.retry_delay)

        print("❌ 主程序启动超时")
        return False

def main():
    """主函数"""
    bridge = STTToMainBridge()

    # 等待主程序启动
    if not bridge.wait_for_main():
        sys.exit(1)

    # 如果有命令行参数，则处理命令行参数
    if len(sys.argv) >= 2:
        text = " ".join(sys.argv[1:])
        # 发送文本到主程序
        if bridge.send_text_to_main(text):
            sys.exit(0)
        else:
            sys.exit(1)
    else:
        # 否则从标准输入读取文本（用于管道输入）
        print("📡 准备从标准输入接收文本...")
        try:
            for line in sys.stdin:
                text = line.strip()
                if text:
                    # 发送文本到主程序
                    bridge.send_text_to_main(text)
        except KeyboardInterrupt:
            print("\n👋 程序已退出")
            sys.exit(0)

if __name__ == "__main__":
    main()
