
"""
RealtimeSTT 使用示例
实时语音转文字演示
"""

from RealtimeSTT import AudioToTextRecorder

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
        while True:
            # 开始录音
            text = recorder.text()

            if text:
                print(f"\n🎯 识别结果: {text}\n")
            else:
                print("\n⚠️  未检测到语音，请重试\n")

    except KeyboardInterrupt:
        print("\n\n👋 程序已退出")
    finally:
        recorder.shutdown()

if __name__ == '__main__':
    main()
