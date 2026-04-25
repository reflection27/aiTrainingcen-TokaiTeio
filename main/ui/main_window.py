# -*- coding: utf-8 -*-
import sys
import os
import datetime
import threading
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTextEdit, QLineEdit, QPushButton,
                             QLabel, QProgressBar, QSplitter, QGroupBox,
                             QFileDialog, QDialog, QSizePolicy, QMenu,
                             QGridLayout, QFrame, QScrollArea)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QPixmap, QKeyEvent

from core.improved_ai_agent import ImprovedAIAgent


class BubbleLabel(QLabel):
    """自动根据宽度计算换行高度的气泡标签"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWordWrap(True)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        h = self.heightForWidth(self.width())
        if h > 0:
            self.setMinimumHeight(h)

    def setText(self, text):
        super().setText(text)
        h = self.heightForWidth(self.width())
        if h > 0:
            self.setMinimumHeight(h)


class ChatInputEdit(QTextEdit):
    """支持回车发送、Shift+回车换行的输入框"""
    send_triggered = Signal()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if event.modifiers() & Qt.ShiftModifier:
                super().keyPressEvent(event)   # Shift+Enter → 换行
            else:
                self.send_triggered.emit()      # Enter → 发送
        else:
            super().keyPressEvent(event)
class ClockLoadingWidget(QWidget):
    """发送消息时显示的旋转秒表动画"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self.setFixedSize(44, 44)
        self.hide()

    def _tick(self):
        self._angle = (self._angle + 4) % 360
        self.update()

    def start(self):
        self._angle = 0
        self._timer.start(16)
        self.show()

    def stop(self):
        self._timer.stop()
        self.hide()

    def paintEvent(self, event):
        import math
        from PySide6.QtGui import QPainter, QColor, QPen, QBrush
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()
        cx = W // 2
        cy = H // 2 + 2          # 向下偏移给顶部小环留空间
        r_outer = 17
        # 外圈（金色）
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#E8A020"))
        p.drawEllipse(cx - r_outer, cy - r_outer, r_outer * 2, r_outer * 2)
        # 表盘（奶油色）
        r_face = r_outer - 4
        p.setBrush(QColor("#FFF8E1"))
        p.drawEllipse(cx - r_face, cy - r_face, r_face * 2, r_face * 2)
        # 12个刻度点
        p.setBrush(QColor("#6B3A2A"))
        r_tick = r_face - 3
        for i in range(12):
            a = math.radians(i * 30 - 90)
            tx = cx + r_tick * math.cos(a)
            ty = cy + r_tick * math.sin(a)
            p.drawEllipse(int(tx - 1.5), int(ty - 1.5), 3, 3)
        # 旋转指针
        a_hand = math.radians(self._angle - 90)
        r_hand = r_face - 5
        hx = cx + r_hand * math.cos(a_hand)
        hy = cy + r_hand * math.sin(a_hand)
        pen = QPen(QColor("#6B3A2A"), 2, Qt.SolidLine, Qt.RoundCap)
        p.setPen(pen)
        p.drawLine(cx, cy, int(hx), int(hy))
        # 顶部小环
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#E8A020"))
        p.drawEllipse(cx - 3, cy - r_outer - 3, 6, 6)
        # 右侧按钮
        p.setBrush(QColor("#C07010"))
        p.drawRoundedRect(cx + r_outer - 2, cy - 4, 5, 7, 2, 2)
        p.end()


from ui.ui_dialogs import MemoryDialog
from ui.settings_dialog import SettingsDialog
from core.config import load_config

class AIAgentApp(QMainWindow):
    """东海帝王AI担当主窗口"""
    
    # 定义信号
    response_ready = Signal(str)
    _tts_checked   = Signal(str, str)   # (text, color)
    _asr_checked   = Signal(str, str)
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.agent = ImprovedAIAgent(config)
        
        # 初始化ASR状态
        self.asr_enabled = config.get("asr_enabled", False)
        self.asr_recording = False  # 是否正在录音
        self.asr_thread = None  # ASR线程
        self.stt_enabled = True  # 是否接收STT信号（麦克风按钮控制）

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
        self._tts_checked.connect(self._apply_tts_status)
        self._asr_checked.connect(self._apply_asr_status)
        
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
            self.input_edit.setPlainText(text.strip())
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
        window_width = 900
        window_height = 567

        self.setGeometry(100, 100, window_width, window_height)

        from PySide6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setFixedSize(window_width, window_height)
        
        # 不为主窗口设置样式表，让调色板控制整体颜色
        
        # 创建中央部件
        main_widget = QWidget()
        main_widget.setAutoFillBackground(True)  # 启用自动填充背景，使用调色板颜色
        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(39, 12, 39, 12)
        
        # 聊天区域 (占用3/4宽度)
        chat_widget = QWidget()
        chat_widget.setAutoFillBackground(True)  # 启用自动填充背景，使用调色板颜色
        # 不设置样式表，让调色板控制颜色
        chat_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        chat_layout = QVBoxLayout()
        chat_layout.setSpacing(10)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        
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

        # 聊天气泡滚动区域
        self._chat_scroll = QScrollArea()
        self._chat_scroll.setWidgetResizable(True)
        self._chat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._chat_scroll.setStyleSheet("""
            QScrollArea {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-top: none;
                border-radius: 0px 0px 6px 6px;
            }
            QScrollBar:vertical { width: 6px; background: #f0f0f0; border-radius: 3px; }
            QScrollBar::handle:vertical { background: #cccccc; border-radius: 3px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)
        self._chat_content_widget = QWidget()
        self._chat_content_widget.setStyleSheet("background-color: #ffffff;")
        self._chat_vbox = QVBoxLayout()
        self._chat_vbox.setSpacing(6)
        self._chat_vbox.setContentsMargins(8, 8, 8, 8)
        self._chat_vbox.addStretch(1)
        self._chat_content_widget.setLayout(self._chat_vbox)
        self._chat_scroll.setWidget(self._chat_content_widget)
        
        # 输入区域
        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)
        
        self.input_edit = ChatInputEdit()
        self.input_edit.setPlaceholderText("输入消息，按回车键发送...")
        self.input_edit.setFixedHeight(44)
        self.input_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.input_edit.send_triggered.connect(self.send_message)
        self.input_edit.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #d0d0d0;
                border-radius: 20px;
                padding: 9px 16px;
                font-size: 14px;
            }
            QTextEdit:focus {
                border: 2px solid #4a90e2;
            }
        """)

        # 不显示的对象，保留供其他逻辑使用
        self.record_btn = QPushButton()
        self.record_btn.setCheckable(True)
        self.record_btn.setChecked(False)
        self.record_btn.hide()
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)

        # 输入区白色卡片（只含输入框）
        input_wrapper = QWidget()
        input_wrapper.setObjectName("inputWrapper")
        input_wrapper.setStyleSheet("""
            QWidget#inputWrapper {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
            }
        """)
        self.clock_widget = ClockLoadingWidget()

        # 麦克风开关按钮
        self.mic_btn = QPushButton("🎙")
        self.mic_btn.setCheckable(True)
        self.mic_btn.setChecked(True)
        self.mic_btn.setFixedSize(36, 36)
        self.mic_btn.setToolTip("点击关闭/开启语音输入")
        self.mic_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 16px;
            }
            QPushButton:checked {
                background-color: #4a90e2;
            }
            QPushButton:!checked {
                background-color: #bdbdbd;
            }
        """)
        self.mic_btn.toggled.connect(self._on_mic_toggled)

        input_container = QHBoxLayout()
        input_container.setSpacing(8)
        input_container.setContentsMargins(10, 8, 10, 8)
        input_container.addWidget(self.mic_btn)
        input_container.addWidget(self.input_edit)
        input_container.addWidget(self.clock_widget)
        input_wrapper.setLayout(input_container)

        # 状态栏标签（对应 HTML .status-bar，放在输入框下方）
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet(
            "color: #4a90e2; font-size: 12px; padding: 0 4px;"
        )

        # 对话内容子组件
        chat_content = QWidget()
        chat_content.setAutoFillBackground(True)
        self._chat_header = chat_header
        chat_layout.addWidget(chat_header)
        chat_layout.addWidget(self._chat_scroll, 1)
        chat_layout.addWidget(input_wrapper)
        chat_content.setLayout(chat_layout)

        # 竖排按钮列（按钮稍后创建后填入）
        side_col_widget = QWidget()
        side_col_widget.setFixedWidth(95)
        side_col_layout = QVBoxLayout()
        side_col_layout.setSpacing(6)
        side_col_layout.setContentsMargins(8, 0, 0, 0)
        side_col_widget.setLayout(side_col_layout)

        # chat_widget 外层用 HBoxLayout
        chat_outer = QHBoxLayout()
        chat_outer.setSpacing(0)
        chat_outer.setContentsMargins(0, 0, 0, 0)
        chat_outer.addWidget(chat_content, 1)
        chat_outer.addWidget(side_col_widget)
        chat_widget.setLayout(chat_outer)
        self._side_col_widget = side_col_widget

        # 右侧预留区域 (占用1/4宽度，用于Live2D)
        right_widget = QWidget()
        right_widget.setAutoFillBackground(True)  # 启用自动填充背景，使用调色板颜色
        # 不设置样式表，让调色板控制颜色
        right_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        right_widget.setFixedWidth(250)
        right_layout = QVBoxLayout()
        right_layout.setSpacing(6)
        right_layout.setContentsMargins(0, 0, 0, 0)

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

        label_style = "color: #888888; font-size: 13px; font-weight: bold; font-family: 'Microsoft YaHei', 'SimHei', sans-serif;"
        value_style = "color: #4a90e2; font-size: 13px; font-weight: bold; font-family: 'Microsoft YaHei', 'SimHei', sans-serif;"

        # 值标签
        self.ai_model   = QLabel(self.config.get("selected_model", "deepseek-v4-flash"))
        self.role_value = QLabel("东海帝王")
        self.ai_memory  = QLabel("记忆系统")   # 保留供状态栏更新使用
        self.ai_apps    = QLabel(f"{getattr(self.agent, 'app_count', 0)}")
        self.ai_time    = QLabel("--:--:--")
        self.tts_status = QLabel("检测中...")
        self.asr_status = QLabel("检测中...")
        for w in (self.ai_model, self.role_value, self.ai_memory, self.ai_apps,
                  self.ai_time, self.tts_status, self.asr_status):
            w.setStyleSheet(value_style)

        def _make_sep():
            sep = QFrame()
            sep.setFixedHeight(1)
            sep.setStyleSheet("background-color: #f0f0f0; border: none;")
            return sep

        def _make_row(text, value_widget):
            lbl = QLabel(text)
            lbl.setStyleSheet(label_style)
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            lbl.setFixedWidth(72)
            row = QHBoxLayout()
            row.setContentsMargins(0, 2, 0, 2)
            row.setSpacing(8)
            row.addWidget(lbl)
            row.addWidget(value_widget)
            return row

        status_layout = QVBoxLayout()
        status_layout.setSpacing(0)
        status_layout.setContentsMargins(14, 3, 14, 3)
        rows = [
            ("系统时间:", self.ai_time),
            ("角色选择:", self.role_value),
            ("当前模型:", self.ai_model),
            ("语音识别:", self.asr_status),
            ("语音合成:", self.tts_status),
        ]
        for i, (text, widget) in enumerate(rows):
            status_layout.addLayout(_make_row(text, widget))
            if i < len(rows) - 1:
                status_layout.addWidget(_make_sep())

        # 启动时间同步
        self.sync_time()

        status_body.setLayout(status_layout)
        status_container_layout.addWidget(status_header)
        status_container_layout.addWidget(status_body)
        status_container.setLayout(status_container_layout)


        # 东海帝王半身像区域
        live2d_label = QLabel()
        live2d_label.setAlignment(Qt.AlignCenter)
        live2d_label.setScaledContents(False)
        live2d_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # 横向纵向都撑满
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
                target_width = 200
                target_height = 380

                # 缩放图片到目标尺寸，保持宽高比
                scaled_pixmap = pixmap.scaled(target_width, target_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                live2d_label.setPixmap(scaled_pixmap)

                # 高度固定为图片实际高度，宽度由布局撑满（图片居中显示）
                # 不固定高度，让边框撑满右侧面板剩余空间
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

        # 按钮区域（竖排，加入对话区右侧列）
        button_layout = side_col_layout  # 复用 side_col_layout

        # 设置按钮
        settings_btn = QPushButton("设置")
        settings_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #AEEA00, stop:1 #4CAF50);
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 9px 10px;
                font-weight: bold;
                font-size: 13px;
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
                border-radius: 6px;
                padding: 9px 10px;
                font-weight: bold;
                font-size: 13px;
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
                border-radius: 6px;
                padding: 9px 10px;
                font-weight: bold;
                font-size: 13px;
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
                border-radius: 6px;
                padding: 9px 10px;
                font-weight: bold;
                font-size: 13px;
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
                border-radius: 6px;
                padding: 9px 10px;
                font-weight: bold;
                font-size: 13px;
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
                border-radius: 6px;
                padding: 9px 10px;
                font-weight: bold;
                font-size: 13px;
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
                border-radius: 6px;
                padding: 9px 10px;
                font-weight: bold;
                font-size: 13px;
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
                border-radius: 6px;
                padding: 9px 10px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #546E7A, stop:1 #37474F);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #455A64, stop:1 #263238);
            }
        """)
        compact_btn.clicked.connect(self.enter_compact_mode)

        # 竖排：8个按钮，上下居中
        button_layout.addStretch(1)
        for btn in (self.game_mode_btn, companion_btn, compact_btn, self.multimodal_btn,
                    memory_btn, settings_btn, test_btn, test_event_btn):
            button_layout.addWidget(btn)
        button_layout.addStretch(1)

        status_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        right_layout.addWidget(status_container)
        right_layout.addWidget(live2d_label, 1)
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
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #42A5F5,stop:1 #1565C0);
                color:#FFF; border:none; border-radius:8px;
                padding:8px 12px; font-weight:bold; font-size:13px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #1E88E5,stop:1 #0D47A1);
            }
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

        compact_bar_layout.addWidget(self._compact_game_btn)
        compact_bar_layout.addWidget(compact_companion_btn)
        compact_bar_layout.addStretch()
        compact_bar_layout.addWidget(fullscreen_btn)
        self._compact_bar.setLayout(compact_bar_layout)
        self._compact_bar.hide()

        chat_layout.addWidget(self._compact_bar)

        # 添加分割器
        self._splitter = QSplitter(Qt.Horizontal)
        self._right_widget = right_widget
        self._splitter.addWidget(right_widget)
        self._splitter.addWidget(chat_widget)
        self._splitter.setSizes([250, 567])
        self._splitter.setChildrenCollapsible(False)
        self._splitter.setHandleWidth(12)
        self._splitter.setStyleSheet("QSplitter::handle { background: transparent; }")
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)

        main_layout.addWidget(self._splitter)
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        # 隐藏 QMainWindow 内置状态栏（占用底部空间），改用 chat 区的 status_label
        self.statusBar().hide()
        
        # 显示启动欢迎信息
        try:
            history = self.agent.memory.get_session_conversations(
                self.agent.current_session_id, limit=5)
        except Exception:
            history = []
        if history:
            self.add_message("系统", "欢迎回来，历史对话加载成功")
        else:
            self.add_message("系统", "输入消息创建新的会话")

    def _make_bubble(self, sender: str, text: str, timestamp: str = None) -> tuple:
        """创建气泡容器和气泡标签，返回 (container, label)"""
        if timestamp is None:
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        # 时间 + 发送者标签
        meta = timestamp if sender == "系统" else f"{sender}  {timestamp}"
        time_lbl = QLabel(meta)
        time_lbl.setStyleSheet(
            "color: #aaaaaa; font-size: 11px; background-color: transparent;"
            " font-family: 'Microsoft YaHei UI', sans-serif;"
        )

        # 气泡
        bubble = BubbleLabel(text)
        bubble.setTextInteractionFlags(Qt.TextSelectableByMouse)

        if sender == "系统":
            bubble.setStyleSheet("""
                QLabel {
                    background-color: #ffffff;
                    color: #555555;
                    border: 1px solid #888888;
                    border-radius: 8px;
                    padding: 6px 10px;
                    font-size: 12px;
                    font-family: 'Microsoft YaHei UI', sans-serif;
                }
            """)
        elif sender == "训练员":
            bubble.setStyleSheet("""
                QLabel {
                    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #42A5F5,stop:1 #1565C0);
                    color: #ffffff;
                    border-radius: 10px;
                    padding: 8px 12px;
                    font-size: 13px;
                    font-family: 'Microsoft YaHei UI', sans-serif;
                }
            """)
        else:  # 东海帝王
            bubble.setStyleSheet("""
                QLabel {
                    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #F06292,stop:1 #C2185B);
                    color: #ffffff;
                    border-radius: 10px;
                    padding: 8px 12px;
                    font-size: 13px;
                    font-family: 'Microsoft YaHei UI', sans-serif;
                }
            """)

        container = QWidget()
        container.setStyleSheet("background-color: #ffffff;")
        v = QVBoxLayout()
        v.setSpacing(2)
        v.setContentsMargins(10, 2, 10, 2)
        v.addWidget(time_lbl, 0, Qt.AlignLeft)
        if sender == "系统":
            v.addWidget(bubble)
        else:
            v.addWidget(bubble, 0, Qt.AlignLeft)
        container.setLayout(v)

        return container, bubble

    def _append_bubble(self, container: QWidget):
        """将气泡容器插入到 vbox 末尾（stretch 之前）并滚动到底"""
        count = self._chat_vbox.count()
        self._chat_vbox.insertWidget(count - 1, container)
        QTimer.singleShot(50, lambda: self._chat_scroll.verticalScrollBar().setValue(
            self._chat_scroll.verticalScrollBar().maximum()))

    def add_message(self, sender, message):
        """添加消息气泡到聊天区域"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        container, _ = self._make_bubble(sender, message, timestamp)
        self._append_bubble(container)

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

            self.clock_widget.start()

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
        user_input = self.input_edit.toPlainText().strip()
        print(f"📝 send_message被调用，用户输入: {user_input}")
        if not user_input:
            print("⚠️ 用户输入为空，不发送消息")
            return

        print(f"📤 添加消息到聊天历史: {user_input}")
        self.add_message("训练员", user_input)
        self.input_edit.clear()
        print("✅ 输入框已清空")

        self.clock_widget.start()

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

        # 流式文本块
        if response.startswith("STREAM_CHUNK:"):
            chunk = response[len("STREAM_CHUNK:"):]

            if not hasattr(self, '_current_streaming_response'):
                self._current_streaming_response = ""
                ts = datetime.datetime.now().strftime("%H:%M:%S")
                container, self._streaming_bubble = self._make_bubble("东海帝王", "", ts)
                self._append_bubble(container)

            self._current_streaming_response += chunk
            self._streaming_bubble.setText(self._current_streaming_response)
            QTimer.singleShot(10, lambda: self._chat_scroll.verticalScrollBar().setValue(
                self._chat_scroll.verticalScrollBar().maximum()))
            return

        # 流式完成
        if response == "STREAM_COMPLETE":
            if hasattr(self, '_current_streaming_response'):
                delattr(self, '_current_streaming_response')
                self._streaming_bubble = None
            self.clock_widget.stop()
            return
        
        self.clock_widget.stop()
        self.add_message("东海帝王", response)

    def handle_timeout(self):
        """处理超时"""
        print("⏰ 处理超时")

    def _on_mic_toggled(self, checked: bool):
        """麦克风按钮切换：控制是否接收STT信号"""
        self.stt_enabled = checked

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
        self.input_edit.setPlainText(test_message)
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
        # 实时时间（每秒更新本地时间）
        self.ai_time.setText(datetime.datetime.now().strftime("%H:%M:%S"))

        # 记忆系统状态
        mem_status = "开发者模式" if getattr(self.agent, 'developer_mode', False) else "正常"
        self.ai_memory.setText(mem_status)

        # 每10秒检测一次 TTS / ASR 连接
        if not hasattr(self, '_status_counter'):
            self._status_counter = 0
        self._status_counter += 1
        if self._status_counter % 10 == 1:   # 启动后立即检测，之后每10秒一次
            threading.Thread(target=self._check_tts_status, daemon=True).start()
            threading.Thread(target=self._check_asr_status, daemon=True).start()

    def _check_tts_status(self):
        import socket
        try:
            s = socket.create_connection(("localhost", 9880), timeout=0.5)
            s.close()
            self._tts_checked.emit("就绪", "#4a90e2")
        except Exception:
            self._tts_checked.emit("连接失败", "#e53935")

    def _check_asr_status(self):
        try:
            import sys
            _main = sys.modules.get('__main__')
            if _main and getattr(_main, 'stt_connected', False):
                self._asr_checked.emit("就绪", "#4a90e2")
            else:
                self._asr_checked.emit("等待连接", "#f5a623")
        except Exception:
            self._asr_checked.emit("等待连接", "#f5a623")

    def _apply_tts_status(self, text: str, color: str):
        self.tts_status.setText(text)
        self.tts_status.setStyleSheet(
            f"color: {color}; font-size: 13px; font-weight: bold;"
            " font-family: 'Microsoft YaHei', 'SimHei', sans-serif;")

    def _apply_asr_status(self, text: str, color: str):
        self.asr_status.setText(text)
        self.asr_status.setStyleSheet(
            f"color: {color}; font-size: 13px; font-weight: bold;"
            " font-family: 'Microsoft YaHei', 'SimHei', sans-serif;")

    def closeEvent(self, event):
        """程序退出时的处理"""
        try:
            # 保存未保存的会话记录到记忆系统
            self.save_unsaved_conversations()
            
            # 显示退出消息
            self.status_label.setText("正在保存会话记录...")
            
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
        self._side_col_widget.hide()
        self._chat_header.hide()
        self._compact_bar.show()
        # setWindowFlag 不重建窗口句柄，避免任务栏条目失效
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.setFixedSize(347, 280)
        self.show()

    def exit_compact_mode(self):
        """退出悬浮窗，恢复大屏"""
        self._compact_bar.hide()
        self._chat_header.show()
        self._side_col_widget.show()
        self._right_widget.show()
        self.setWindowFlag(Qt.WindowStaysOnTopHint, False)
        self.setFixedSize(900, 567)
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
            self._compact_game_btn.setChecked(False)
            self._compact_game_btn.setText("游戏模式")
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
        menu.aboutToHide.connect(lambda: (
            self.game_mode_btn.setChecked(self.game_mode_btn.text() != "游戏模式"),
            self._compact_game_btn.setChecked(self.game_mode_btn.text() != "游戏模式"),
        ))
        menu.exec_(anchor.mapToGlobal(anchor.rect().bottomLeft()))

    def _start_game_monitoring(self, game_key: str, game_label: str):
        try:
            self.agent.multimodal_processor.start_game_monitoring_from_config(game_key)
            self.game_mode_btn.setChecked(True)
            self.game_mode_btn.setText(f"游戏: {game_label}")
            self._compact_game_btn.setChecked(True)
            self._compact_game_btn.setText(f"游戏: {game_label}")
            self.add_message("系统", f"🎮 游戏模式已启动：{game_label}")
        except Exception as e:
            self.game_mode_btn.setChecked(False)
            self.game_mode_btn.setText("游戏模式")
            self._compact_game_btn.setChecked(False)
            self._compact_game_btn.setText("游戏模式")
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
        
