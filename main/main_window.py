# -*- coding: utf-8 -*-
import sys
import os
import datetime
import threading
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTextEdit, QLineEdit, QPushButton, 
                             QLabel, QProgressBar, QSplitter, QGroupBox, 
                             QFormLayout, QStatusBar, QFileDialog, QDialog, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap

from improved_ai_agent import ImprovedAIAgent
from ui_dialogs import MemoryLakeDialog, MCPToolsDialog
from settings_dialog import SettingsDialog
from config import load_config

class AIAgentApp(QMainWindow):
    """东海帝王AI担当主窗口"""
    
    # 定义信号
    response_ready = pyqtSignal(str)
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.agent = ImprovedAIAgent(config)
        
        # 初始化ASR状态 - 根据agent的ASR状态来设置，而不是直接从配置文件获取
        self.asr_enabled = getattr(self.agent, 'asr_enabled', False) and config.get("asr_enabled", True)
        self.asr_recording = False  # 是否正在录音
        self.asr_thread = None  # ASR线程

        # 初始化ASR集成模块
        self.asr_integration = None
        self._init_asr_integration()

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

            # 检查ASR管理器是否可用
            if not hasattr(self.agent, 'asr_manager') or self.agent.asr_manager is None:
                print("ℹ️ ASR管理器不可用，跳过ASR集成模块初始化")
                return

            # 初始化ASR集成模块
            from asr_integration import ASRIntegration
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
        from PyQt5.QtWidgets import QSizePolicy
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
        
        # 聊天历史
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                color: #333333;
                border: none;
                border-style: none;
                outline: none;
                padding: 10px;
                font-family: 'Microsoft YaHei UI', sans-serif;
                font-size: 14px;
            }
            QTextEdit:focus {
                border: none;
                border-style: none;
                outline: none;
            }
        """)
        
        # 输入区域
        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)
        
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("输入消息...")
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
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #AED581, stop:1 #4CAF50);
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 8px 12px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #9CCC65, stop:1 #388E3C);
                box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #8BC34A, stop:1 #2E7D32);
            }
        """)

        # 录音按钮（切换开关）
        self.record_btn = QPushButton("🎤")
        self.record_btn.setCheckable(True)  # 设置为可切换状态
        self.record_btn.setToolTip("语音识别开关")
        self.record_btn.clicked.connect(self.toggle_asr)
        self.record_btn.setChecked(self.asr_enabled)  # 设置初始状态
        self.update_record_button_style()  # 更新按钮样式

        send_btn = QPushButton("发送")
        send_btn.setShortcut("Ctrl+Return")
        send_btn.clicked.connect(self.send_message)
        send_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #AED581, stop:1 #4CAF50);
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 14px;
                min-height: 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #9CCC65, stop:1 #388E3C);
                box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #8BC34A, stop:1 #2E7D32);
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

        # 创建水平布局，让输入元素与右侧按钮对齐
        input_container = QHBoxLayout()
        input_container.setSpacing(10)
        
        input_container.addWidget(self.input_edit)
        input_container.addWidget(image_btn)
        input_container.addWidget(self.record_btn)
        input_container.addWidget(send_btn)
        input_container.addWidget(self.progress_bar)

        chat_layout.addWidget(self.chat_history, 3)
        chat_layout.addStretch()  # 添加弹性空间，让输入区域向下移动
        chat_layout.addLayout(input_container, 1)
        chat_widget.setLayout(chat_layout)

        # 右侧预留区域 (占用1/4宽度，用于Live2D)
        right_widget = QWidget()
        right_widget.setAutoFillBackground(True)  # 启用自动填充背景，使用调色板颜色
        # 不设置样式表，让调色板控制颜色
        right_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        right_layout = QVBoxLayout()
        right_layout.setSpacing(5)  # 进一步减少间距，让半身像更接近状态栏
        right_layout.setContentsMargins(10, 8, 10, 8)  # 减少上下边距，让按钮更接近底部
        right_layout.addStretch()  # 添加弹性空间，让按钮推到底部

        # 状态信息
        status_group = QGroupBox("")
        status_group.setStyleSheet("""
            QGroupBox {
                color: #333333;
                font-size: 10px;
                border: 1px solid #d0d0d0;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
                padding-bottom: 10px;
                max-width: 320px;
                min-width: 320px;
                min-height: 120px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 4px 8px;
                background-color: #f5f5f5 !important;
                font-size: 12px !important;
                font-weight: bold !important;
                color: #333333 !important;
                font-family: "Microsoft YaHei", "SimHei", sans-serif !important;
                border: 1px solid #f5f5f5 !important;
                border-radius: 3px !important;
                margin-top: 3px !important;
                margin-bottom: 3px !important;
            }
        """)
        status_layout = QFormLayout()
        status_layout.setVerticalSpacing(12)  # 进一步增加垂直间距，配合更大的字体
        status_layout.setHorizontalSpacing(8)  # 增加水平间距，配合更大的字体
        
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

        status_group.setLayout(status_layout)


        # 东海帝王半身像区域
        live2d_label = QLabel()
        live2d_label.setAlignment(Qt.AlignCenter)
        live2d_label.setScaledContents(False)  # 不自动缩放，保持原始比例
        live2d_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)  # 固定尺寸，防止拉伸
        live2d_label.setStyleSheet("""
            QLabel {
                background-color: #ffffff;
                border: 2px solid #4a90e2;
                border-radius: 15px;
                padding: 5px;
            }
        """)
        
        # 加载东海帝王图片
        try:
            pixmap = QPixmap("TokaiTeio.png")
            if not pixmap.isNull():
                # 重新计算适合增加高度后的9:16比例尺寸
                # 系统状态栏宽度固定为320px，东海帝王图片宽度也要320px
                # 窗口高度增加到900px，为Live2D区域提供更多垂直空间
                # 为了保持9:16比例，高度 = 320*(16/9) = 569px
                target_width = 320
                target_height = int(target_width * 16 / 9)  # 569px
                
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
                        border: 2px solid #4a90e2;
                        border-radius: 15px;
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

        # 按钮区域
        button_layout = QHBoxLayout()

        # 设置按钮
        settings_btn = QPushButton("设置")
        settings_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #AED581, stop:1 #4CAF50);
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 10px 15px;
                font-weight: bold;
                font-size: 14px;
                min-height: 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #9CCC65, stop:1 #388E3C);
                box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #8BC34A, stop:1 #2E7D32);
            }
        """)
        settings_btn.clicked.connect(self.open_settings)
        
        # 记忆系统按钮
        memory_btn = QPushButton("记忆系统")
        memory_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #AED581, stop:1 #4CAF50);
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 10px 15px;
                font-weight: bold;
                font-size: 14px;
                min-height: 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #9CCC65, stop:1 #388E3C);
                box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #8BC34A, stop:1 #2E7D32);
            }
        """)
        memory_btn.clicked.connect(self.open_memory_lake)
        
        # MCP工具按钮
        mcp_btn = QPushButton("MCP工具")
        mcp_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #AED581, stop:1 #4CAF50);
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 10px 15px;
                font-weight: bold;
                font-size: 14px;
                min-height: 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #9CCC65, stop:1 #388E3C);
                box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #8BC34A, stop:1 #2E7D32);
            }
        """)
        mcp_btn.clicked.connect(self.open_mcp_tools)

        button_layout.addWidget(settings_btn)
        button_layout.addWidget(memory_btn)
        button_layout.addWidget(mcp_btn)

        right_layout.addWidget(status_group)
        right_layout.addWidget(live2d_label)  # 移除stretch参数，让图片按实际尺寸显示
        right_layout.addLayout(button_layout)
        right_widget.setLayout(right_layout)

        # 添加分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(chat_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([1000, 350])  # 增加聊天区域宽度，右侧保持不变
        # 禁用分割器拖拽功能
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(0)
        # 设置分割器保持等比例缩放
        splitter.setStretchFactor(0, 1)  # 聊天区域可拉伸
        splitter.setStretchFactor(1, 0)  # 右侧区域固定比例

        main_layout.addWidget(splitter)
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
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {sender}: {message}\n"
        
        # 获取当前文本并添加新消息
        current_text = self.chat_history.toPlainText()
        new_text = current_text + formatted_msg
        self.chat_history.setPlainText(new_text)
        
        # 滚动到底部
        self.chat_history.verticalScrollBar().setValue(
            self.chat_history.verticalScrollBar().maximum()
        )

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
            self.timeout_timer.start(180000)  # 180秒超时，给图片分析更多时间

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
        if not user_input:
            return

        self.add_message("训练员", user_input)
        self.input_edit.clear()

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
        self.timeout_timer.start(240000)  # 240秒超时，给AI更多时间

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

            # 使用异步处理
            response = await self.agent.process_command_async(user_input)

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

    def process_ai_response(self, user_input):
        """处理AI响应"""
        try:
            print(f"🔄 开始处理AI响应: {user_input}")
            
            # 获取AI响应
            response = self.agent.process_command(user_input)
            
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

        # 播放TTS
        self._play_tts(response)
        
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
            # 如果ASR管理器可用，启动录音
            if hasattr(self.agent, 'asr_manager') and self.agent.asr_manager.is_available():
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
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #AED581, stop:1 #4CAF50);
                    color: #FFFFFF;
                    border: none;
                    border-radius: 8px;
                    padding: 8px 12px;
                    font-weight: bold;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #9CCC65, stop:1 #388E3C);
                    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #8BC34A, stop:1 #2E7D32);
                }
            """)

    def start_asr_recording(self):
        """开始ASR录音"""
        if not hasattr(self.agent, 'asr_manager') or self.agent.asr_manager is None:
            self.add_message("系统", "⚠️ ASR未配置或不可用")
            self.record_btn.setChecked(False)
            self.asr_enabled = False
            self.update_record_button_style()
            return

        if self.asr_recording:
            return

        self.asr_recording = True
        self.add_message("系统", "🎤 开始录音...")

        # 在单独的线程中处理录音和识别
        self.asr_thread = threading.Thread(target=self._run_asr, daemon=True)
        self.asr_thread.start()

    def stop_asr_recording(self):
        """停止ASR录音"""
        self.asr_recording = False
        if hasattr(self, 'asr_thread') and self.asr_thread:
            # 注意：这里只是设置标志，实际停止需要在_run_asr中处理
            pass

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
        settings_dialog.exec_()
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

    def open_memory_lake(self):
        """打开记忆系统窗口"""
        memory_dialog = MemoryLakeDialog(self.agent.memory_lake, self)
        memory_dialog.exec_()

    def open_mcp_tools(self):
        """打开MCP工具窗口"""
        mcp_dialog = MCPToolsDialog(self.agent.mcp_tools, self)
        mcp_dialog.exec_()

    def sync_time(self):
        """同步网络时间"""
        try:
            import requests
            response = requests.get('http://worldtimeapi.org/api/timezone/Asia/Shanghai', timeout=5)
            data = response.json()
            current_time = datetime.datetime.fromisoformat(data['datetime'].replace('Z', '+00:00'))
            time_str = current_time.strftime("%H:%M:%S")
            self.ai_time.setText(time_str)
        except:
            # 如果网络时间同步失败，使用本地时间
            self.ai_time.setText(datetime.datetime.now().strftime("%H:%M:%S"))

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
        """保存未保存的会话记录到记忆系统"""
        try:
            # 检查开发者模式，如果开启则不保存
            if getattr(self.agent, 'developer_mode', False):
                print("🔧 开发者模式已开启，跳过会话记录保存")
                return
            
            # 获取当前会话中的对话记录
            session_conversations = getattr(self.agent, 'session_conversations', [])
            
            if not session_conversations:
                print("📝 没有需要保存的会话记录")
                return
            
            print(f"📝 开始保存 {len(session_conversations)} 条会话记录到记忆系统")
            
            # 🚀 修复：过滤出未保存的对话记录
            unsaved_conversations = []
            for conv in session_conversations:
                # 检查对话是否已经被保存过（通过检查saved标记）
                if not conv.get('saved', False):
                    unsaved_conversations.append(conv)
            
            if not unsaved_conversations:
                print("📝 所有对话记录都已经保存过了")
                return
            
            print(f"📝 找到 {len(unsaved_conversations)} 条未保存的对话记录")
            
            # 🚀 修复：遍历未保存的对话记录，将它们添加到记忆系统中
            for conv in unsaved_conversations:
                user_input = conv.get('user_input', '')
                ai_response = conv.get('ai_response', '')
                
                if user_input and ai_response:
                    # 添加到记忆系统的当前会话中
                    self.agent.memory_lake.add_conversation(user_input, ai_response, self.agent.developer_mode, self.agent._mark_conversation_as_saved)
            
            # 🚀 修复：强制保存当前会话（即使不足3条）
            if self.agent.memory_lake.current_conversation:
                topic = self.agent.memory_lake.summarize_and_save_topic(force_save=True)
                if topic:
                    print(f"✅ 退出时保存会话主题: {topic}")
                    # 🚀 修复：在成功保存后，标记所有对话为已保存
                    for conv in unsaved_conversations:
                        conv['saved'] = True
                else:
                    print("✅ 退出时保存会话记录完成")
                    # 🚀 修复：即使保存失败，也标记为已保存，避免重复尝试
                    for conv in unsaved_conversations:
                        conv['saved'] = True
            
            # 🚀 修复：不清空session_conversations，只标记为已保存
            # 这样可以避免重复保存，同时保留对话历史
            
        except Exception as e:
            print(f"❌ 保存会话记录失败: {str(e)}")
            raise
    
    def check_first_run_and_introduce(self):
        """检查是否是第一次运行，如果是则进行自我介绍"""
        try:
            # 检查记忆系统中的记忆条数
            memory_stats = self.agent.memory_lake.get_memory_stats()
            total_topics = memory_stats.get("total_topics", 0)
            
            # 如果记忆条数为0，说明是第一次运行
            if total_topics == 0:
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
        
