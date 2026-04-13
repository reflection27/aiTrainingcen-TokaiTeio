
"""
RealtimeSTT 使用示例
实时语音转文字演示
"""

import requests
import json
import time
from RealtimeSTT import AudioToTextRecorder

def send_text_to_main(text):
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
            "http://127.0.0.1:5000/api/text_input",
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

def wait_for_main(max_retries=5, retry_delay=2):
    """
    等待主程序启动
    
    Args:
        max_retries: 最大重试次数
        retry_delay: 重试延迟（秒）
        
    Returns:
        如果主程序就绪返回True，否则返回False
    """
    for i in range(max_retries):
        try:
            response = requests.get(
                "http://127.0.0.1:5000/api/status",
                timeout=2
            )
            if response.status_code == 200:
                print("✅ 主程序已就绪")
                return True
        except:
            pass
        
        print(f"⏳ 等待主程序启动... ({i+1}/{max_retries})")
        time.sleep(retry_delay)
    
    print("❌ 主程序启动超时")
    return False

def main():
    # 创建 AudioToTextRecorder 实例
    print("🎤 初始化语音识别器...")
    recorder = AudioToTextRecorder(
        model="large-v3",  # 使用 Whisper large-v3 模型
        language="zh",     # 设置为中文
        spinner=True,      # 显示加载动画
        silero_sensitivity=0.4,  # 语音活动检测灵敏度
        post_speech_silence_duration=0.7,  # 说话结束后的静默时间
        min_gap_between_recordings=0.5,  # 两次录音之间的最小间隔
        enable_realtime_transcription=True,  # 启用实时转录
        realtime_processing_pause=0.2,  # 实时处理暂停时间
        realtime_batch_size=5,  # 实时处理批次大小
        on_realtime_transcription_stabilized=lambda text: print(f"\n⚡ 实时: {text}"),  # 实时转录回调
    )

    print("✅ 语音识别器初始化完成！")
    print("\n📝 使用说明：")
    print("  - 按住空格键开始录音")
    print("  - 松开空格键停止录音并转录")
    print("  - 按 Ctrl+C 退出程序\n")

    try:
        # 等待主程序启动
        if not wait_for_main():
            print("❌ 无法连接到主程序，请确保主程序已启动")
            return
        
        while True:
            # 开始录音
            text = recorder.text()

            if text:
                # 将识别到的文本输出到标准输出，以便通过管道传递给stt_to_main.py
                print(text)
                # 同时也将文本发送到主程序
                send_text_to_main(text)
            else:
                print("\n⚠️  未检测到语音，请重试\n")

    except KeyboardInterrupt:
        print("\n\n👋 程序已退出")
    finally:
        recorder.shutdown()

if __name__ == '__main__':
    main()
