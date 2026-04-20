# -*- coding: utf-8 -*-
import sys
import os
import datetime
import threading
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTextEdit, QLineEdit, QPushButton,
                             QLabel, QProgressBar, QSplitter, QGroupBox,
                             QFormLayout, QStatusBar, QFileDialog, QDialog, QSizePolicy, QMenu,
                             QGridLayout, QFrame)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QPixmap

from core.improved_ai_agent import ImprovedAIAgent
from ui.ui_dialogs import MemoryDialog
from ui.settings_dialog import SettingsDialog
from core.config import load_config

class AIAgentApp(QMainWindow):
    """东海帝王AI担当主窗口"""
    
    # 定义信号
    response_ready = Signal(str)
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.agent = ImprovedAIAgent(config)
        
        # 初始化ASR状态
        self.asr_enabled = config.get("asr_enabled", False)
        self.asr_recording = False  # 是否正在录音
        self.asr_thread = None  # ASR线程

        # 初始化ASR集成模块
        self.asr_integration = None
        # 延迟初始化ASR集成模块，避免启动时闪退
        # ASR将在用户点击录音按钮时才初始化

        # 初始化UI
        self.init_ui()
        
        # 应用窗口透明度设置
        self.apply_transparency()
        
        # 连接信号
        self.response_ready.connect(self.update_ui_with_response)
        
        # 启动状态更新定时器
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(1000)  # 每秒更新一次状态
        
        # 检查是否是第一次运行，如果是则进行自我介绍
        self.check_first_run_and_introduce()
    
    def _init_asr_integration(self):
        """初始化ASR集成模块"""
        try:
            # 检查ASR是否启用
            if not self.asr_enabled:
                print("ℹ️ ASR未启用，跳过ASR集成模块初始化")
                return

            # 初始化ASR集成模块
            from core.asr_integration import ASRIntegration
            self.asr_integration = ASRIntegration(self.config)

            # 连接信号
            self.asr_integration.text_ready.connect(self._on_asr_text_ready)
            self.asr_integration.error_occurred.connect(self._on_asr_error)

            print("✅ ASR集成模块初始化成功")
        except Exception as e:
            print(f"⚠️ ASR集成模块初始化失败: {str(e)}")
            import traceback
            traceback.print_exc()
            self.asr_integration = None
            raise  # 重新抛出异常，让调用者处理

    def _on_asr_text_ready(self, text):
        """ASR文本识别完成回调"""
        print(f"🎤 识别到文本: {text}")

        # 停止录音
        if self.asr_integration:
            self.asr_integration.stop_asr()

        # 如果识别到的文本不为空，则发送消息
        if text and text.strip():
            # 将识别到的文本添加到输入框
            self.input_edit.setText(text.strip())
            # 自动发送消息
            self.send_message()

        # 更新录音状态
        self.asr_recording = False

    def _on_asr_error(self, error_msg):
        """ASR错误回调"""
        print(f"❌ ASR错误: {error_msg}")

        # 停止录音
        if self.asr_integration:
            self.asr_integration.stop_asr()

        # 更新录音状态
        self.asr_recording = False

        # 显示错误消息
        self.response_ready.emit(f"⚠️ 语音识别错误: {error_msg}")

    def apply_transparency(self):
        """应用窗口透明度设置"""
        try:
            transparency = self.config.get("window_transparency", 100)
            if transparency < 100:
                # 将百分比转换为0-1之间的值
                opacity = transparency / 100.0
                self.setWindowOpacity(opacity)
                print(f"✅ 窗口透明度已设置为 {transparency}%")
            else:
                # 100%表示完全不透明
                self.setWindowOpacity(1.0)
        except Exception as e:
            print(f"⚠️ 设置窗口透明度失败: {str(e)}")
    
    def update_transparency(self, value):
        """实时更新窗口透明度（用于设置对话框的实时预览）"""
        try:
            if value < 100:
                # 将百分比转换为0-1之间的值
                opacity = value / 100.0
                self.setWindowOpacity(opacity)
            else:
                # 100%表示完全不透明
                self.setWindowOpacity(1.0)
        except Exception as e:
            print(f"⚠️ 实时更新透明度失败: {str(e)}")

    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("东海帝王AI担当")
        # 增加一点点高度和宽度，让按钮对齐并保持比例
        # 原来：1300x800，现在：1350x850
        # 聊天区域：1000px，右侧区域：350px，高度增加50px
        window_width = 1350  # 增加50px宽度，主要给聊天区域
        window_height = 850  # 增加50px高度，让按钮向下移动对齐
        
        self.setGeometry(100, 100, window_width, window_height)
        
        # 设置窗口尺寸策略，固定大小不可拖拽
        from PySide6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setFixedSize(window_width, window_height)  # 固定窗口大小
        
        # 不为主窗口设置样式表，让调色板控制整体颜色
        
        # 创建中央部件
        main_widget = QWidget()
        main_widget.setAutoFillBackground(True)  # 启用自动填充背景，使用调色板颜色
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 聊天区域 (占用3/4宽度)
        chat_widget = QWidget()
        chat_widget.setAutoFillBackground(True)  # 启用自动填充背景，使用调色板颜色
        # 不设置样式表，让调色板控制颜色
        chat_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        chat_layout = QVBoxLayout()
        chat_layout.setSpacing(10)
        chat_layout.setContentsMargins(10, 10, 10, 10)
        
        # 聊天区标题
        chat_header = QLabel("聊天记录")
        chat_header.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #AEEA00, stop:1 #4CAF50);
                color: #ffffff;
                font-weight: bold;
                font-size: 14px;
                padding: 8px 14px;
                border-radius: 6px 6px 0px 0px;
                font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
            }
        """)

        # 聊天历史
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #e0e0e0;
                border-top: none;
                border-radius: 0px 0px 6px 6px;
                outline: none;
                padding: 10px;
                font-family: 'Microsoft YaHei UI', sans-serif;
                font-size: 14px;
            }
            QTextEdit:focus {
                border: 1px solid #e0e0e0;
                border-top: none;
                outline: none;
            }
        """)
        
        # 输入区域
        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)
        
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("输入消息，按回车键发送...")
        self.input_edit.returnPressed.connect(self.send_message_shortcut)
        self.input_edit.setStyleSheet("""
            QLineEdit {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #d0d0d0;
                border-radius: 15px;
                padding: 10px 15px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #4a90e2;
            }
        """)

        # 图片上传按钮
        image_btn = QPushButton("📷")
        image_btn.setToolTip("上传图片")
        image_btn.clicked.connect(self.send_image)
        image_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #AEEA00, stop:1 #4CAF50);
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 8px 12px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #9CCC00, stop:1 #388E3C);
                box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #8BC300, stop:1 #2E7D32);
            }
        """)

        # 录音按钮（切换开关）- 已禁用，因为现在通过HTTP接口接收STT文本
        self.record_btn = QPushButton("🎤")
        self.record_btn.setCheckable(True)  # 设置为可切换状态
        self.record_btn.setToolTip("语音识别已通过STT服务器处理")
        self.record_btn.setEnabled(False)  # 禁用按钮
        self.record_btn.setChecked(False)  # 设置初始状态
        self.update_record_button_style()  # 更新按钮样式

        send_btn = QPushButton("发送")
        send_btn.setShortcut("Ctrl+Return")
        send_btn.clicked.connect(self.send_message)
        send_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #AEEA00, stop:1 #4CAF50);
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 14px;
                min-height: 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #9CCC00, stop:1 #388E3C);
                box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #8BC300, stop:1 #2E7D32);
            }
        """)

        # 添加进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #d0d0d0;
                border-radius: 5px;
                text-align: center;
                background-color: #f0f0f0;
                color: #333333;
            }
            QProgressBar::chunk {
                background-color: #4a90e2;
                border-radius: 3px;
            }
        """)

        # 输入区白色卡片
        input_wrapper = QWidget()
        input_wrapper.setObjectName("inputWrapper")
        input_wrapper.setStyleSheet("""
            QWidget#inputWrapper {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
            }
        """)
        input_container = QHBoxLayout()
        input_container.setSpacing(10)
        input_container.setContentsMargins(10, 8, 10, 8)
        input_container.addWidget(self.input_edit)
        input_container.addWidget(image_btn)
        input_container.addWidget(self.record_btn)
        input_container.addWidget(send_btn)
        input_container.addWidget(self.progress_bar)
        input_wrapper.setLayout(input_container)

        chat_layout.addWidget(chat_header)
        chat_layout.addWidget(self.chat_history, 1)
        chat_layout.addWidget(input_wrapper)
        chat_widget.setLayout(chat_layout)

        # 右侧预留区域 (占用1/4宽度，用于Live2D)
        right_widget = QWidget()
        right_widget.setAutoFillBackground(True)  # 启用自动填充背景，使用调色板颜色
        # 不设置样式表，让调色板控制颜色
        right_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        right_layout = QVBoxLayout()
        right_layout.setSpacing(8)
        right_layout.setContentsMargins(10, 8, 10, 8)

        # 状态信息卡片
        status_container = QWidget()
        status_container_layout = QVBoxLayout()
        status_container_layout.setSpacing(0)
        status_container_layout.setContentsMargins(0, 0, 0, 0)

        status_header = QLabel("系统状态")
        status_header.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        status_header.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #AEEA00, stop:1 #4CAF50);
                color: #ffffff;
                font-weight: bold;
                font-size: 14px;
                padding: 8px 14px;
                border-radius: 6px 6px 0px 0px;
                font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
            }
        """)

        status_body = QWidget()
        status_body.setObjectName("statusBody")
        status_body.setStyleSheet("""
            QWidget#statusBody {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-top: none;
                border-radius: 0px 0px 6px 6px;
            }
        """)

        status_layout = QFormLayout()
        status_layout.setVerticalSpacing(8)
        status_layout.setHorizontalSpacing(8)
        status_layout.setContentsMargins(10, 16, 10, 8)

        # 设置标签样式
        status_layout.setLabelAlignment(Qt.AlignRight)

        # 创建标签样式
        label_style = "color: #333333; font-size: 14px; font-weight: bold; font-family: 'Microsoft YaHei', 'SimHei', sans-serif;"
        value_style = "color: #4a90e2; font-size: 14px; font-weight: bold; font-family: 'Microsoft YaHei', 'SimHei', sans-serif;"
        
        # 当前模型
        model_label = QLabel("当前模型:")
        model_label.setStyleSheet(label_style)
        model_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.ai_model = QLabel(self.config.get("selected_model", "deepseek-reasoner"))
        self.ai_model.setStyleSheet(value_style)
        status_layout.addRow(model_label, self.ai_model)


        # 角色选择
        role_label = QLabel("角色选择:")
        role_label.setStyleSheet(label_style)
        role_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.role_value = QLabel("东海帝王")
        self.role_value.setStyleSheet(value_style)
        status_layout.addRow(role_label, self.role_value)

        # 记忆系统
        memory_label = QLabel("记忆系统:")
        memory_label.setStyleSheet(label_style)
        memory_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.ai_memory = QLabel("记忆系统")
        self.ai_memory.setStyleSheet(value_style)
        status_layout.addRow(memory_label, self.ai_memory)

        # 预加载应用
        apps_label = QLabel(" 预载应用:")  # 在开头添加一个空格，向右移动一个字节
        apps_label.setStyleSheet(label_style)
        apps_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)  # 确保右对齐和垂直居中
        self.ai_apps = QLabel(f"{getattr(self.agent, 'app_count', 0)}")
        self.ai_apps.setStyleSheet(value_style)
        status_layout.addRow(apps_label, self.ai_apps)

        # 登录位置信息已隐藏
        # location_label = QLabel("登录位置:")
        # location_label.setStyleSheet(label_style)
        # location_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        # self.ai_location = QLabel(getattr(self.agent, 'location', '未知'))
        # self.ai_location.setStyleSheet(value_style)
        # status_layout.addRow(location_label, self.ai_location)

        # 当前时间
        time_label = QLabel("当前时间:")
        time_label.setStyleSheet(label_style)
        time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.ai_time = QLabel("同步中...")
        self.ai_time.setStyleSheet(value_style)
        status_layout.addRow(time_label, self.ai_time)
        
        # 启动时间同步
        self.sync_time()

        status_body.setLayout(status_layout)
        status_container_layout.addWidget(status_header)
        status_container_layout.addWidget(status_body)
        status_container.setLayout(status_container_layout)


        # 东海帝王半身像区域
        live2d_label = QLabel()
        live2d_label.setAlignment(Qt.AlignCenter)
        live2d_label.setScaledContents(False)  # 不自动缩放，保持原始比例
        live2d_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)  # 固定尺寸，防止拉伸
        live2d_label.setStyleSheet("""
            QLabel {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
            }
        """)

        # 加载东海帝王图片
        try:
            pixmap = QPixmap(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "TokaiTeio.png"))
            if not pixmap.isNull():
                target_width = 270
                target_height = int(target_width * 16 / 9)
                
                # 缩放图片到目标尺寸，保持宽高比
                scaled_pixmap = pixmap.scaled(target_width, target_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                live2d_label.setPixmap(scaled_pixmap)
                
                # 设置固定尺寸，确保不与其他元素重合
                live2d_label.setFixedSize(target_width, target_height)  # 使用固定尺寸，防止挤压其他元素
                print(f"✅ 成功加载东海帝王半身像，尺寸: {target_width}x{target_height}")
            else:
                print("❌ 无法加载TokaiTeio.png图片")
                live2d_label.setText("图片加载失败")
                live2d_label.setStyleSheet("""
                    QLabel {
                        background-color: #ffffff;
                        color: #333333;
                        border: 1px solid #e0e0e0;
                        border-radius: 6px;
                        font-size: 18px;
                        padding: 20px;
                    }
                """)
        except Exception as e:
            print(f"❌ 加载图片时出错: {e}")
            live2d_label.setText("图片加载失败")
            live2d_label.setStyleSheet("""
                QLabel {
                    background-color: #ffffff;
                    color: #333333;
                    border: 2px solid #4a90e2;
                    border-radius: 15px;
                    font-size: 18px;
                    padding: 20px;
                }
            """)

        # 按钮区域 4列×2行
        button_layout = QGridLayout()
        button_layout.setSpacing(6)

        # 设置按钮
        settings_btn = QPushButton("设置")
        settings_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #AEEA00, stop:1 #4CAF50);
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 7px 10px;
                font-weight: bold;
                font-size: 13px;
                min-height: 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #9CCC00, stop:1 #388E3C);
                box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #8BC300, stop:1 #2E7D32);
            }
        """)
        settings_btn.clicked.connect(self.open_settings)
        
        # 记忆系统按钮
        memory_btn = QPushButton("记忆系统")
        memory_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #AEEA00, stop:1 #4CAF50);
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 7px 10px;
                font-weight: bold;
                font-size: 13px;
                min-height: 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #9CCC00, stop:1 #388E3C);
                box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #8BC300, stop:1 #2E7D32);
            }
        """)
        memory_btn.clicked.connect(self.open_memory)
        
        # 测试按钮
        test_btn = QPushButton("测试")
        test_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #EF5350, stop:1 #C62828);
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 7px 10px;
                font-weight: bold;
                font-size: 13px;
                min-height: 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #E53935, stop:1 #B71C1C);
                box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #D32F2F, stop:1 #8B0000);
            }
        """)
        test_btn.clicked.connect(self.test_add_message)

        # 测试自定义事件按钮
        test_event_btn = QPushButton("测试事件")
        test_event_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #AB47BC, stop:1 #7B1FA2);
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 7px 10px;
                font-weight: bold;
                font-size: 13px;
                min-height: 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #9C27B0, stop:1 #6A1B9A);
                box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #8E24AA, stop:1 #4A148C);
            }
        """)
        test_event_btn.clicked.connect(self.test_custom_event)

        # 多模态开关按钮
        self.multimodal_btn = QPushButton("多模态: 关")
        self.multimodal_btn.setCheckable(True)
        self.multimodal_btn.setChecked(False)
        self.multimodal_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #B0BEC5, stop:1 #78909C);
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 7px 10px;
                font-weight: bold;
                font-size: 13px;
                min-height: 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #90A4AE, stop:1 #546E7A);
                box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #78909C, stop:1 #455A64);
            }
            QPushButton:checked {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #42A5F5, stop:1 #1976D2);
            }
        """)
        self.multimodal_btn.clicked.connect(self.toggle_multimodal)

        # 陪伴模式按钮
        companion_btn = QPushButton("陪伴模式")
        companion_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #F06292, stop:1 #C2185B);
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 7px 10px;
                font-weight: bold;
                font-size: 13px;
                min-height: 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #E91E63, stop:1 #AD1457);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #C2185B, stop:1 #880E4F);
            }
        """)
        companion_btn.clicked.connect(self._companion_and_compact)

        # 游戏模式按钮
        self.game_mode_btn = QPushButton("游戏模式")
        self.game_mode_btn.setCheckable(True)
        self.game_mode_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #42A5F5, stop:1 #1565C0);
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 7px 10px;
                font-weight: bold;
                font-size: 13px;
                min-height: 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1E88E5, stop:1 #0D47A1);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1976D2, stop:1 #0A3D91);
            }
            QPushButton:checked {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFA726, stop:1 #E65100);
            }
        """)
        self.game_mode_btn.clicked.connect(self._game_and_compact)

        # 悬浮窗模式按钮
        compact_btn = QPushButton("悬浮窗模式")
        compact_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #78909C, stop:1 #455A64);
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 7px 10px;
                font-weight: bold;
                font-size: 13px;
                min-height: 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #546E7A, stop:1 #37474F);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #455A64, stop:1 #263238);
            }
        """)
        compact_btn.clicked.connect(self.enter_compact_mode)

        # 第一排：游戏模式 陪伴模式 悬浮窗模式 多模态
        button_layout.addWidget(self.game_mode_btn, 0, 0)
        button_layout.addWidget(companion_btn,      0, 1)
        button_layout.addWidget(compact_btn,        0, 2)
        button_layout.addWidget(self.multimodal_btn, 0, 3)
        # 第二排：记忆系统 设置 测试 测试事件
        button_layout.addWidget(memory_btn,    1, 0)
        button_layout.addWidget(settings_btn,  1, 1)
        button_layout.addWidget(test_btn,      1, 2)
        button_layout.addWidget(test_event_btn, 1, 3)

        right_layout.addWidget(status_container)
        right_layout.addWidget(live2d_label)
        right_layout.addLayout(button_layout)
        right_widget.setLayout(right_layout)

        # 精简模式按钮栏（默认隐藏）
        self._compact_bar = QWidget()
        compact_bar_layout = QHBoxLayout()
        compact_bar_layout.setContentsMargins(0, 4, 0, 0)
        compact_bar_layout.setSpacing(6)

        compact_companion_btn = QPushButton("陪伴模式")
        compact_companion_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #F06292,stop:1 #C2185B);
                color:#FFF; border:none; border-radius:8px;
                padding:8px 12px; font-weight:bold; font-size:13px;
            }
            QPushButton:hover { background:#E91E63; }
        """)
        compact_companion_btn.clicked.connect(self.launch_companion_mode)

        self._compact_game_btn = QPushButton("游戏模式")
        self._compact_game_btn.setCheckable(True)
        self._compact_game_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #66BB6A,stop:1 #388E3C);
                color:#FFF; border:none; border-radius:8px;
                padding:8px 12px; font-weight:bold; font-size:13px;
            }
            QPushButton:hover { background:#4CAF50; }
            QPushButton:checked {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #FFA726,stop:1 #E65100);
            }
        """)
        self._compact_game_btn.clicked.connect(self._compact_game_toggle)

        fullscreen_btn = QPushButton("大屏模式")
        fullscreen_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #78909C,stop:1 #455A64);
                color:#FFF; border:none; border-radius:8px;
                padding:8px 12px; font-weight:bold; font-size:13px;
            }
            QPushButton:hover { background:#546E7A; }
        """)
        fullscreen_btn.clicked.connect(self.exit_compact_mode)

        compact_bar_layout.addWidget(compact_companion_btn)
        compact_bar_layout.addWidget(self._compact_game_btn)
        compact_bar_layout.addStretch()
        compact_bar_layout.addWidget(fullscreen_btn)
        self._compact_bar.setLayout(compact_bar_layout)
        self._compact_bar.hide()

        chat_layout.addWidget(self._compact_bar)

        # 添加分割器
        self._splitter = QSplitter(Qt.Horizontal)
        self._right_widget = right_widget
        self._splitter.addWidget(chat_widget)
        self._splitter.addWidget(right_widget)
        self._splitter.setSizes([1000, 350])
        self._splitter.setChildrenCollapsible(False)
        self._splitter.setHandleWidth(0)
        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 0)

        main_layout.addWidget(self._splitter)
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        # 添加状态栏
        self.statusBar().showMessage("就绪")
        
        # 显示启动欢迎信息
        # location = getattr(self.agent, 'location', '未知')
        app_count = getattr(self.agent, 'app_count', 0)
        self.add_message("系统", f"预载应用：{app_count}个")

    def add_message(self, sender, message):
        """添加消息到聊天历史"""
        print(f"📝 add_message被调用，发送者: {sender}, 消息: {message}")

        # 检查chat_history是否可见
        print(f"👁️ chat_history是否可见: {self.chat_history.isVisible()}")
        print(f"👁️ chat_history是否启用: {self.chat_history.isEnabled()}")

        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {sender}: {message}\n"
        
        # 获取当前文本并添加新消息
        current_text = self.chat_history.toPlainText()
        print(f"📄 当前聊天历史长度: {len(current_text)}")
        new_text = current_text + formatted_msg
        print(f"📄 新聊天历史长度: {len(new_text)}")
        self.chat_history.setPlainText(new_text)
        print(f"✅ 文本已设置到chat_history")
        
        # 滚动到底部
        self.chat_history.verticalScrollBar().setValue(
            self.chat_history.verticalScrollBar().maximum()
        )

        # 验证文本是否正确设置
        actual_text = self.chat_history.toPlainText()
        print(f"📄 实际聊天历史长度: {len(actual_text)}")
        if len(actual_text) != len(new_text):
            print("⚠️ 文本设置失败！")

    def send_image(self):
        """上传并分析图片"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择图片文件",
            "",
            "图片文件 (*.jpg *.jpeg *.png *.gif *.bmp *.tiff *.webp)"
        )

        if file_path:
            self.add_message("训练员", f"📷 上传图片: {file_path}")

            # 显示进度条
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("分析图片中... 0%")

            # 启动进度条更新定时器
            self.progress_timer = QTimer()
            self.progress_timer.timeout.connect(self.update_progress)
            self.progress_timer.start(30)
            self.progress_value = 0

            # 添加超时保护
            self.timeout_timer = QTimer()
            self.timeout_timer.timeout.connect(self.handle_timeout)
            self.timeout_timer.start(15000)  # 15秒超时，与AI代理的10秒超时保持一致，留5秒余量

            # 在单独的线程中处理图片分析（使用asyncio）
            threading.Thread(target=self._run_async_image_analysis, args=(file_path,), daemon=True).start()

    def _run_async_image_analysis(self, file_path):
        """在单独的线程中运行异步图片分析"""
        import asyncio
        try:
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 运行异步方法
            loop.run_until_complete(self.process_image_analysis_async(file_path))
        except Exception as e:
            print(f"❌ 异步图片分析错误: {str(e)}")
            error_response = f"抱歉，图片分析时出现了问题：{str(e)}"
            self.response_ready.emit(error_response)
        finally:
            loop.close()

    async def process_image_analysis_async(self, file_path):
        """处理图片分析（异步版本）"""
        try:
            print(f"🖼️ 开始分析图片: {file_path}")

            # 使用异步处理
            response = await self.agent.process_image_async(file_path)

            print(f"✅ 图片分析完成: {response[:50]}...")

            # 确保响应不为空
            if not response or response.strip() == "":
                response = "抱歉，图片分析失败，请重试。"

            # 发送信号到主线程
            self.response_ready.emit(response)

        except Exception as e:
            print(f"❌ 图片分析错误: {str(e)}")
            error_response = f"抱歉，图片分析时出现了问题：{str(e)}"
            self.response_ready.emit(error_response)

    def process_image_analysis(self, file_path):
        """处理图片分析"""
        try:
            print(f"🖼️ 开始分析图片: {file_path}")

            # 获取图片分析结果
            response = self.agent.process_image(file_path)

            print(f"✅ 图片分析完成: {response[:50]}...")

            # 确保响应不为空
            if not response or response.strip() == "":
                response = "抱歉，图片分析失败，请重试。"

            # 发送信号到主线程
            self.response_ready.emit(response)

        except Exception as e:
            print(f"❌ 图片分析错误: {str(e)}")
            error_response = f"抱歉，图片分析时出现了问题：{str(e)}"
            self.response_ready.emit(error_response)

    def send_message(self):
        """发送消息"""
        user_input = self.input_edit.text().strip()
        print(f"📝 send_message被调用，用户输入: {user_input}")
        if not user_input:
            print("⚠️ 用户输入为空，不发送消息")
            return

        print(f"📤 添加消息到聊天历史: {user_input}")
        self.add_message("训练员", user_input)
        self.input_edit.clear()
        print("✅ 输入框已清空")

        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("处理中... 0%")

        # 启动进度条更新定时器
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self.update_progress)
        self.progress_timer.start(30)  # 每30毫秒更新一次，更平滑
        self.progress_value = 0
        
        # 添加超时保护，防止进度条无限卡住
        self.timeout_timer = QTimer()
        self.timeout_timer.timeout.connect(self.handle_timeout)
        self.timeout_timer.start(15000)  # 15秒超时，与AI代理的10秒超时保持一致，留5秒余量

        # 在单独的线程中处理响应（使用asyncio）
        threading.Thread(target=self._run_async_response, args=(user_input,), daemon=True).start()

    def send_message_shortcut(self):
        """快捷键发送消息"""
        if QApplication.keyboardModifiers() & Qt.ControlModifier:
            self.send_message()

    def _run_async_response(self, user_input):
        """在单独的线程中运行异步响应处理"""
        import asyncio
        try:
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 运行异步方法
            loop.run_until_complete(self.process_ai_response_async(user_input))
        except Exception as e:
            print(f"❌ 异步响应处理错误: {str(e)}")
            error_response = f"抱歉，处理您的请求时出现了问题：{str(e)}"
            self.response_ready.emit(error_response)
        finally:
            loop.close()

    async def process_ai_response_async(self, user_input):
        """处理AI响应（异步版本）"""
        try:
            print(f"🔄 开始处理AI响应: {user_input}")

            # 创建流式文本回调函数
            def stream_callback(chunk):
                """流式文本回调函数"""
                print(f"📝 收到流式文本块: {chunk}")
                # 发送信号到主线程，更新UI（添加特殊标记）
                self.response_ready.emit("STREAM_CHUNK:" + chunk)

            # 使用异步处理，传入流式回调函数
            response = await self.agent.process_command_async(user_input, session_id=self.agent.current_session_id, stream_callback=stream_callback)

            print(f"✅ AI响应获取成功: {response[:50]}...")

            # 确保响应不为空
            if not response or response.strip() == "":
                response = "抱歉，我没有理解您的意思，请重新表述一下。"

            # 发送完成信号到主线程（不包含响应内容，因为已经通过流式回调显示）
            print(f"📡 发送完成信号")
            self.response_ready.emit("STREAM_COMPLETE")

        except Exception as e:
            # 如果出现异常，也要更新UI
            print(f"❌ AI响应处理错误: {str(e)}")
            error_response = f"抱歉，处理您的请求时出现了问题：{str(e)}"
            self.response_ready.emit(error_response)

    def process_ai_response(self, user_input):
        """处理AI响应"""
        try:
            print(f"🔄 开始处理AI响应: {user_input}")
            
            # 获取AI响应
            response = self.agent.process_command(user_input, session_id=self.agent.current_session_id)
            
            print(f"✅ AI响应获取成功: {response[:50]}...")
            
            # 确保响应不为空
            if not response or response.strip() == "":
                response = "抱歉，我没有理解您的意思，请重新表述一下。"

            # 发送信号到主线程
            print(f"📡 发送信号: {response[:50]}...")
            self.response_ready.emit(response)
            
        except Exception as e:
            # 如果出现异常，也要更新UI
            print(f"❌ AI响应处理错误: {str(e)}")
            error_response = f"抱歉，处理您的请求时出现了问题：{str(e)}"
            self.response_ready.emit(error_response)

    def update_progress(self):
        """更新进度条"""
        if hasattr(self, 'progress_value'):
            # 检查是否是图片分析
            is_image_analysis = "分析图片中" in self.progress_bar.format()
            
            if is_image_analysis:
                # 图片分析使用更慢的进度增长
                if self.progress_value < 20:
                    self.progress_value += 0.5  # 前20%很慢增长
                elif self.progress_value < 50:
                    self.progress_value += 0.3  # 中间30%极慢增长
                elif self.progress_value < 80:
                    self.progress_value += 0.2  # 后30%极慢增长
                else:
                    self.progress_value = 80  # 最多到80%，留20%给完成时
            else:
                # 普通对话使用正常进度增长
                if self.progress_value < 30:
                    self.progress_value += 2  # 前30%快速增长
                elif self.progress_value < 70:
                    self.progress_value += 1  # 中间40%中等速度
                elif self.progress_value < 85:
                    self.progress_value += 0.5  # 后15%慢速增长
                else:
                    self.progress_value = 85  # 最多到85%，留15%给完成时
            
            self.progress_bar.setValue(int(self.progress_value))
            current_format = self.progress_bar.format()
            if "分析图片中" in current_format:
                self.progress_bar.setFormat(f"分析图片中... {int(self.progress_value)}%")
            else:
                self.progress_bar.setFormat(f"处理中... {int(self.progress_value)}%")

    def update_ui_with_response(self, response):
        """在主线程中更新UI"""
        print(f"🔄 开始更新UI: {response[:50]}...")

        # 检查是否是流式文本块（以特殊标记开头）
        if response.startswith("STREAM_CHUNK:"):
            # 提取流式文本块内容
            chunk = response[len("STREAM_CHUNK:"):]
            print(f"📝 处理流式文本块: {chunk}")
            
            # 检查是否是第一条流式文本
            if not hasattr(self, '_current_streaming_response'):
                self._current_streaming_response = ""
                # 添加初始消息到聊天历史
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                formatted_msg = f"[{timestamp}] 东海帝王: "
                self.chat_history.setPlainText(self.chat_history.toPlainText() + formatted_msg)
            
            # 追加流式文本到当前消息
            self._current_streaming_response += chunk
            current_text = self.chat_history.toPlainText()
            self.chat_history.setPlainText(current_text + chunk)
            
            # 滚动到底部
            self.chat_history.verticalScrollBar().setValue(
                self.chat_history.verticalScrollBar().maximum()
            )
            return
            
        # 检查是否是流式完成信号
        if response == "STREAM_COMPLETE":
            print(f"✅ 流式回复完成")
            
            # 添加回车到流式回复末尾
            if hasattr(self, '_current_streaming_response'):
                current_text = self.chat_history.toPlainText()
                self.chat_history.setPlainText(current_text + "\n")
                # 清除流式回复状态
                delattr(self, '_current_streaming_response')
            
            # 停止所有定时器
            if hasattr(self, 'progress_timer'):
                self.progress_timer.stop()
            if hasattr(self, 'timeout_timer'):
                self.timeout_timer.stop()

            # 立即完成进度条
            self.progress_bar.setValue(100)
            self.progress_bar.setFormat("完成")

            # 延迟隐藏进度条
            QTimer.singleShot(800, lambda: self.progress_bar.setVisible(False))
            return
        
        # 停止所有定时器
        if hasattr(self, 'progress_timer'):
            self.progress_timer.stop()
        if hasattr(self, 'timeout_timer'):
            self.timeout_timer.stop()
        
        # 立即完成进度条
        self.progress_bar.setValue(100)
        self.progress_bar.setFormat("完成")
        
        # 添加消息到聊天历史
        print(f"📝 添加消息到聊天历史: 东海帝王 - {response[:50]}...")
        self.add_message("东海帝王", response)

        # 播放TTS - 已注释，避免与text_queue_manager重复调用
        # self._play_tts(response)
        
        # 延迟隐藏进度条
        QTimer.singleShot(800, lambda: self.progress_bar.setVisible(False))

    def handle_timeout(self):
        """处理超时"""
        print("⏰ 处理超时")

    def toggle_asr(self):
        """切换ASR开关状态"""
        self.asr_enabled = self.record_btn.isChecked()
        self.update_record_button_style()

        # 更新配置
        self.config["asr_enabled"] = self.asr_enabled

        # 显示状态消息
        if self.asr_enabled:
            self.add_message("系统", "🎤 语音识别已开启")
            # 启动录音
            self.start_asr_recording()
        else:
            self.add_message("系统", "🎤 语音识别已关闭")
            # 停止录音
            self.stop_asr_recording()

    def update_record_button_style(self):
        """更新录音按钮样式"""
        if self.asr_enabled:
            # 开启状态：使用红色渐变
            self.record_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #EF5350, stop:1 #C62828);
                    color: #FFFFFF;
                    border: none;
                    border-radius: 8px;
                    padding: 8px 12px;
                    font-weight: bold;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #E53935, stop:1 #B71C1C);
                    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #D32F2F, stop:1 #8B0000);
                }
            """)
        else:
            # 关闭状态：使用绿色渐变
            self.record_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #AEEA00, stop:1 #4CAF50);
                    color: #FFFFFF;
                    border: none;
                    border-radius: 8px;
                    padding: 8px 12px;
                    font-weight: bold;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #9CCC00, stop:1 #388E3C);
                    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #8BC300, stop:1 #2E7D32);
                }
            """)

    def start_asr_recording(self):
        """开始ASR录音"""
        # 延迟初始化ASR集成模块
        if not self.asr_integration:
            try:
                self._init_asr_integration()
                if not self.asr_integration:
                    self.add_message("系统", "⚠️ ASR未配置或不可用")
                    self.record_btn.setChecked(False)
                    self.asr_enabled = False
                    self.update_record_button_style()
                    return
            except Exception as e:
                self.add_message("系统", f"⚠️ ASR初始化失败: {str(e)}")
                self.record_btn.setChecked(False)
                self.asr_enabled = False
                self.update_record_button_style()
                return

        if self.asr_recording:
            return

        self.asr_recording = True
        self.add_message("系统", "🎤 开始录音...")

        # 启动ASR
        self.asr_integration.start_asr()

    def stop_asr_recording(self):
        """停止ASR录音"""
        self.asr_recording = False
        if self.asr_integration:
            self.asr_integration.stop_asr()

    def _run_asr(self):
        """在单独的线程中运行ASR"""
        # ASR功能未配置
        self.asr_recording = False
        self.response_ready.emit("⚠️ ASR功能未配置，请先配置ASR模型")
        # ASR功能未配置，不再需要超时处理
        
        # 检查是否是图片分析
        is_image_analysis = "分析图片中" in self.progress_bar.format()
        
        if is_image_analysis:
            timeout_message = "抱歉，图片分析时间过长，请稍后重试。如果图片较大或内容复杂，可能需要更长时间处理。"
        else:
            timeout_message = "抱歉，处理时间过长，请重试。"
        
        self.response_ready.emit(timeout_message)

    def open_settings(self):
        """打开设置窗口"""
        settings_dialog = SettingsDialog(self.config, self, self.update_transparency)
        settings_dialog.exec()
        # 重新加载配置
        self.config = load_config()
        
        # 设置保存后，更新TTS配置
        try:
            self.agent.update_tts_config(self.config)
            print("✅ TTS配置已更新")
        except Exception as e:
            print(f"⚠️ TTS配置更新失败: {str(e)}")
            
        # 设置保存后，重新应用透明度设置
        self.apply_transparency()

    def open_memory(self):
        """打开记忆系统窗口"""
        memory_dialog = MemoryDialog(self.agent.memory, agent=self.agent, parent=self)
        memory_dialog.exec()

    def test_add_message(self):
        """测试添加消息到聊天历史"""
        test_message = "这是一条测试消息，用于验证文本是否能够正确显示在聊天历史中。"
        print(f"🧪 测试添加消息: {test_message}")

        # 将测试消息设置到输入框
        self.input_edit.setText(test_message)
        # 调用send_message方法，触发AI的回复
        self.send_message()

    def test_custom_event(self):
        """测试自定义事件"""
        test_message = "这是一条测试消息，用于验证自定义事件是否能够正确处理。"
        print(f"🧪 测试自定义事件: {test_message}")

        # 创建自定义事件（使用与main.py中相同的TextEvent类）
        from PySide6.QtCore import QEvent
        class TextEvent(QEvent):
            EVENT_TYPE = QEvent.User + 1

            def __init__(self, text):
                super().__init__(TextEvent.EVENT_TYPE)
                self.text = text

        # 创建事件对象
        text_event = TextEvent(test_message)
        print(f"📝 创建了自定义事件对象: {text_event.text}")
        print(f"📝 事件类型: {text_event.type()}, TextEvent.EVENT_TYPE: {TextEvent.EVENT_TYPE}")

        # 直接调用custom_event函数
        print(f"📤 准备调用custom_event函数...")
        import main
        # 获取main.py中定义的custom_event函数
        # 注意：这里我们需要访问main.py中的window.event，但window是局部变量
        # 所以我们直接调用self.event方法，它应该已经被custom_event函数覆盖
        self.event(text_event)
        print(f"✅ custom_event函数已调用")

    def sync_time(self):
        """在后台线程同步网络时间，避免阻塞主线程"""
        def _fetch():
            try:
                import requests
                response = requests.get(
                    'http://worldtimeapi.org/api/timezone/Asia/Shanghai', timeout=3)
                data = response.json()
                current_time = datetime.datetime.fromisoformat(
                    data['datetime'].replace('Z', '+00:00'))
                time_str = current_time.strftime("%H:%M:%S")
            except Exception:
                time_str = datetime.datetime.now().strftime("%H:%M:%S")
            # 回到主线程更新 UI
            QTimer.singleShot(0, lambda: self.ai_time.setText(time_str))

        threading.Thread(target=_fetch, daemon=True).start()

    def update_status(self):
        """更新状态"""
        # 更新记忆系统状态
        mem_status = "开发者模式" if getattr(self.agent, 'developer_mode', False) else "正常"
        self.ai_memory.setText(mem_status)

        # 更新时间（每5秒同步一次网络时间）
        if hasattr(self, 'time_sync_counter'):
            self.time_sync_counter += 1
        else:
            self.time_sync_counter = 0
        
        if self.time_sync_counter % 5 == 0:  # 每5次更新同步一次网络时间
            self.sync_time()
        else:
            # 使用本地时间更新
            current_time = datetime.datetime.now()
            time_str = current_time.strftime("%H:%M:%S")
            self.ai_time.setText(time_str)

        # 更新状态栏
        time_str = self.ai_time.text()
        self.statusBar().showMessage(
            f"就绪 | 模型: {self.config.get('selected_model', 'deepseek-reasoner')} | 记忆系统: {mem_status} | {time_str}")

    def closeEvent(self, event):
        """程序退出时的处理"""
        try:
            # 保存未保存的会话记录到记忆系统
            self.save_unsaved_conversations()
            
            # 显示退出消息
            self.statusBar().showMessage("正在保存会话记录...")
            
            # 接受关闭事件
            event.accept()
            
        except Exception as e:
            print(f"退出时保存会话记录失败: {str(e)}")
            # 即使保存失败也允许退出
            event.accept()

    def save_unsaved_conversations(self):
        """ImprovedMemorySystem 在每次对话时已自动保存，此方法保留为空"""
        pass
    
    def check_first_run_and_introduce(self):
        """检查是否是第一次运行，如果是则进行自我介绍"""
        try:
            # 检查记忆系统中的记忆条数
            memory_stats = self.agent.memory.get_memory_stats()
            total_conversations = memory_stats.get("total_conversations", 0)

            # 如果对话条数为0，说明是第一次运行
            if total_conversations == 0:
                # 生成自我介绍内容
                introduction = self.generate_introduction()
                
                # 将自我介绍添加到聊天历史
                self.add_message("东海帝王", introduction)
                
                # 将自我介绍添加到AI代理的会话记录中，标记为系统消息
                self.agent._add_session_conversation("系统", introduction)
                
        except Exception as e:
            pass
    
    def generate_introduction(self):
        """生成东海帝王的自我介绍"""
        current_time = datetime.datetime.now()
        time_str = current_time.strftime("%H:%M")
        
        introduction = f"""（轻轻整理了一下衣服）训练员，您好！我是东海帝王，特雷森学园的赛马娘。

很高兴见到您！作为您的AI担当，我具备以下能力：
• 智能对话和问题解答
• 天气查询和实时信息
• 音乐推荐和文件管理
• 编程代码生成和帮助
• 多语言交流和翻译
• 记忆系统

现在时间是 {time_str}，我已经准备好为您服务了。请告诉我您需要什么帮助吧！

（对了，如果您想了解我的更多功能，可以直接问我"你能做什么"哦~）"""

    def _companion_and_compact(self):
        # 1. 先切紧凑布局
        if not self._compact_bar.isVisible():
            self.enter_compact_mode()
        # 2. 最小化
        self.showMinimized()
        # 3. 启动 Godot（不再 showMinimized，直接启动进程）
        self._launch_godot_process()

    def _game_and_compact(self):
        self.toggle_game_mode()
        if not self._compact_bar.isVisible():
            self.enter_compact_mode()

    def enter_compact_mode(self):
        """进入悬浮窗小屏模式"""
        if self._compact_bar.isVisible():
            return
        self._normal_size = self.size()
        self._normal_pos = self.pos()
        self._right_widget.hide()
        self._compact_bar.show()
        # setWindowFlag 不重建窗口句柄，避免任务栏条目失效
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.setFixedSize(520, 420)
        self.show()

    def exit_compact_mode(self):
        """退出悬浮窗，恢复大屏"""
        self._compact_bar.hide()
        self._right_widget.show()
        self.setWindowFlag(Qt.WindowStaysOnTopHint, False)
        self.setFixedSize(self._normal_size)
        if hasattr(self, '_normal_pos'):
            self.move(self._normal_pos)
        if self.isMinimized():
            self.showNormal()
        else:
            self.show()

    def changeEvent(self, event):
        """处理最小化恢复，确保任务栏点击能正常唤起窗口"""
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.WindowStateChange:
            was_minimized = bool(event.oldState() & Qt.WindowMinimized)
            is_minimized  = bool(self.windowState() & Qt.WindowMinimized)
            # 只在"从最小化恢复"时处理，避免切换窗口时抢焦点
            if was_minimized and not is_minimized:
                self.show()
                self.raise_()
                self.activateWindow()
        super().changeEvent(event)

    def _compact_game_toggle(self):
        """精简模式下的游戏模式按钮，与主按钮保持同步"""
        self.game_mode_btn.setChecked(self._compact_game_btn.isChecked())
        self.toggle_game_mode(source_btn=self._compact_game_btn)
        self._compact_game_btn.setText(self.game_mode_btn.text())

    def _launch_godot_process(self):
        """启动 Godot 桌宠进程"""
        import subprocess
        _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        godot_exe = os.path.join(
            _root,
            "plugins", "godot",
            "Godot_v4.6.2-stable_win64.exe",
            "Godot_v4.6.2-stable_win64.exe"
        )
        project_dir = os.path.join(
            _root,
            "plugins", "godot", "tokai-teio"
        )
        if not os.path.exists(godot_exe):
            self.add_message("系统", f"⚠️ 找不到 Godot: {godot_exe}")
            return
        subprocess.Popen([godot_exe, "--path", project_dir],
                         creationflags=subprocess.DETACHED_PROCESS)

    def launch_companion_mode(self):
        """最小化主窗口并启动 Godot 桌宠"""
        self.showMinimized()
        self._launch_godot_process()

    def toggle_game_mode(self, source_btn=None):
        """游戏模式开关：关闭时弹菜单选游戏，开启时停止监控"""
        if not self.agent.multimodal_processor:
            self.game_mode_btn.setChecked(False)
            self.add_message("系统", "⚠️ 多模态处理器未初始化，无法启用游戏模式")
            return

        if not self.game_mode_btn.isChecked():
            # 刚切换到关闭 → 停止监控
            self.agent.multimodal_processor.stop_game_monitoring()
            self.game_mode_btn.setText("游戏模式")
            self.add_message("系统", "🎮 游戏模式已关闭")
            return

        # 菜单弹出位置：优先用传入的按钮，否则用主按钮
        anchor = source_btn if (source_btn and source_btn.isVisible()) else self.game_mode_btn

        games = {
            "赛马娘": "umamusume",
            "Minecraft": "minecraft",
            "云顶之弈": "云顶之弈",
        }
        menu = QMenu(self)
        for label, key in games.items():
            menu.addAction(label, lambda k=key, l=label: self._start_game_monitoring(k, l))
        menu.aboutToHide.connect(
            lambda: self.game_mode_btn.setChecked(
                self.game_mode_btn.text() != "游戏模式"
            )
        )
        menu.exec_(anchor.mapToGlobal(anchor.rect().bottomLeft()))

    def _start_game_monitoring(self, game_key: str, game_label: str):
        try:
            self.agent.multimodal_processor.start_game_monitoring_from_config(game_key)
            self.game_mode_btn.setChecked(True)
            self.game_mode_btn.setText(f"游戏: {game_label}")
            self.add_message("系统", f"🎮 游戏模式已启动：{game_label}")
        except Exception as e:
            self.game_mode_btn.setChecked(False)
            self.game_mode_btn.setText("游戏模式")
            self.add_message("系统", f"❌ 启动游戏模式失败：{e}")

    def toggle_multimodal(self):
        """切换多模态功能开关"""
        if not self.agent.multimodal_processor:
            self.multimodal_btn.setChecked(False)
            self.add_message("系统", "⚠️ 多模态处理器未初始化，无法启用多模态功能")
            return

        is_enabled = self.multimodal_btn.isChecked()
        self.agent.multimodal_enabled = is_enabled

        if is_enabled:
            self.multimodal_btn.setText("多模态: 开")
            self.agent.multimodal_processor.set_auto_capture(True)
            self.add_message("系统", "✅ 多模态功能已启用")
        else:
            self.multimodal_btn.setText("多模态: 关")
            self.agent.multimodal_processor.set_auto_capture(False)
            self.add_message("系统", "ℹ️ 多模态功能已禁用")



    def _play_tts(self, text):
        """播放TTS语音"""
        try:
            tts_enabled = self.config.get("tts_enabled", False)
            has_tts_manager = hasattr(self.agent, 'tts_manager') and self.agent.tts_manager
            tts_available = has_tts_manager and self.agent.tts_manager.is_available()

            print(f"🔍 TTS播放检查: tts_enabled={tts_enabled}, has_tts_manager={has_tts_manager}, tts_available={tts_available}")

            if tts_enabled and has_tts_manager:
                if not tts_available:
                    print("⚠️ TTS不可用，跳过语音播放")
                else:
                    # 提取纯文本内容（去除表情符号等）
                    import re
                    clean_text = re.sub(r'[（\(].*?[）\)]', '', text)  # 移除括号内容
                    clean_text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s，。！？、；：""''（）]', '', clean_text)  # 保留中文、英文、数字和标点
                    clean_text = clean_text.strip()

                    if clean_text and len(clean_text) > 0:
                        print(f"🎤 开始TTS播放: {clean_text[:50]}...")
                        self.agent.tts_manager.speak_text(clean_text)
                    else:
                        print("⚠️ 清理后的文本为空，跳过TTS播放")
            else:
                print("ℹ️ TTS未启用或管理器不可用")
        except Exception as e:
            print(f"⚠️ TTS播放失败: {str(e)}")
        
