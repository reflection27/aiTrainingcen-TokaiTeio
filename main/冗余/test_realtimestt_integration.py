
# -*- coding: utf-8 -*-
"""
RealtimeSTT 集成测试脚本
测试 RealtimeSTT 在主程序中的集成
"""

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QTextEdit, QPushButton, QLabel
from PyQt5.QtCore import Qt, pyqtSlot

from realtimestt_worker import RealtimeSTTWorker
from realtimestt_config import REALTIMESTT_CONFIG

class RealtimeSTTTestWindow(QMainWindow):
    """RealtimeSTT 测试窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("RealtimeSTT 集成测试")
        self.setGeometry(100, 100, 800, 600)

        # 创建 RealtimeSTT 工作线程
        self.asr_worker = RealtimeSTTWorker(REALTIMESTT_CONFIG)

        # 连接信号
        self.asr_worker.text_ready.connect(self.on_text_ready)
        self.asr_worker.error_occurred.connect(self.on_error)
        self.asr_worker.recording_started.connect(self.on_recording_started)
        self.asr_worker.recording_stopped.connect(self.on_recording_stopped)

        # 初始化 UI
        self.init_ui()

        # 启动 ASR
        self.asr_worker.start()

    def init_ui(self):
        """初始化 UI"""
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建布局
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # 创建状态标签
        self.status_label = QLabel("状态: 已启动")
        self.status_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self.status_label)

        # 创建文本显示区域
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        self.text_display.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #d0d0d0;
                border-radius: 5px;
                padding: 10px;
                font-size: 14px;
            }
        """)
        layout.addWidget(self.text_display)

        # 创建录音按钮
        self.record_btn = QPushButton("按住录音")
        self.record_btn.setCheckable(True)
        self.record_btn.pressed.connect(self.on_record_pressed)
        self.record_btn.released.connect(self.on_record_released)
        self.record_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: #ffffff;
                border: none;
                border-radius: 5px;
                padding: 10px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:checked {
                background-color: #f44336;
            }
        """)
        layout.addWidget(self.record_btn)

        # 创建关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: #ffffff;
                border: none;
                border-radius: 5px;
                padding: 10px;
                font-size: 14px;
            }
        """)
        layout.addWidget(close_btn)

    @pyqtSlot()
    def on_record_pressed(self):
        """录音按钮按下"""
        self.asr_worker.start_recording()

    @pyqtSlot()
    def on_record_released(self):
        """录音按钮释放"""
        self.asr_worker.stop_recording()

    @pyqtSlot(str)
    def on_text_ready(self, text):
        """识别到的文本"""
        self.text_display.append(f"识别结果: {text}")

    @pyqtSlot(str)
    def on_error(self, error):
        """错误信息"""
        self.text_display.append(f"错误: {error}")

    @pyqtSlot()
    def on_recording_started(self):
        """录音开始"""
        self.status_label.setText("状态: 正在录音...")
        self.record_btn.setChecked(True)

    @pyqtSlot()
    def on_recording_stopped(self):
        """录音结束"""
        self.status_label.setText("状态: 录音已停止")
        self.record_btn.setChecked(False)

    def closeEvent(self, event):
        """窗口关闭事件"""
        self.asr_worker.shutdown()
        event.accept()

def main():
    """主函数"""
    app = QApplication(sys.argv)
    window = RealtimeSTTTestWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
