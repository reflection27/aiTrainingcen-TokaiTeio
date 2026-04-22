# -*- coding: utf-8 -*-
"""
设置对话框模块 - 浅色主题版本
"""

import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
                             QPushButton, QLabel, QComboBox, QSplitter, QListWidget,
                             QGroupBox, QFormLayout, QMessageBox, QInputDialog,
                             QFileDialog, QProgressBar, QListWidgetItem, QTabWidget,
                             QSlider, QCheckBox, QScrollArea, QWidget)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QPalette, QColor

from core.config import save_config
from core.utils import scan_windows_apps

class SettingsDialog(QDialog):
    """设置对话框"""

    def __init__(self, config, parent=None, transparency_callback=None):
        super().__init__(parent)
        self.config = config
        self.transparency_callback = transparency_callback  # 透明度更新回调
        self.setWindowTitle("东海帝王AI设置")
        # 导入Qt模块
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QPalette, QColor
        # 设置窗口标志，确保可以拖动和关闭
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMinMaxButtonsHint)
        # 设置窗口模态，确保它可以正常拖动
        self.setModal(True)

        # 添加拖动功能
        self.drag_pos = None

        # 设置浅色背景调色板
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(245, 245, 245))  # 浅色背景
        palette.setColor(QPalette.WindowText, QColor(30, 30, 30))  # 深色文本
        palette.setColor(QPalette.Base, QColor(255, 255, 255))  # 白色基础色
        palette.setColor(QPalette.AlternateBase, QColor(240, 240, 240))  # 交替基础色
        palette.setColor(QPalette.ToolTipBase, QColor(240, 240, 240))  # 工具提示基础色
        palette.setColor(QPalette.ToolTipText, QColor(30, 30, 30))  # 工具提示文本
        palette.setColor(QPalette.Text, QColor(30, 30, 30))  # 文本颜色
        palette.setColor(QPalette.Button, QColor(240, 240, 240))  # 按钮颜色
        palette.setColor(QPalette.ButtonText, QColor(30, 30, 30))  # 按钮文本
        palette.setColor(QPalette.BrightText, QColor(0, 0, 0))  # 亮色文本
        palette.setColor(QPalette.Highlight, QColor(76, 163, 255))  # 高亮色
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))  # 高亮文本
        self.setPalette(palette)

        # 设置样式表，确保所有子控件使用浅色主题
        self.setStyleSheet("""
            QDialog { 
                background-color: #f5f5f5; 
            }
            QGroupBox {
                background-color: #f5f5f5;
                color: #1e1e1e;
                border: 1px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QLineEdit, QTextEdit, QComboBox {
                background-color: #ffffff;
                color: #1e1e1e;
                border: 1px solid #cccccc;
                border-radius: 3px;
                padding: 3px;
            }
            QPushButton {
                background-color: #e0e0e0;
                color: #1e1e1e;
                border: 1px solid #cccccc;
                border-radius: 3px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
            QPushButton:pressed {
                background-color: #c0c0c0;
            }
            QCheckBox {
                color: #1e1e1e;
            }
            QSlider::groove:horizontal {
                border: 1px solid #cccccc;
                height: 8px;
                background: #ffffff;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #4ca3ff;
                border: 1px solid #cccccc;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QListWidget {
                background-color: #ffffff;
                color: #1e1e1e;
                border: 1px solid #cccccc;
                border-radius: 3px;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #eeeeee;
            }
            QListWidget::item:selected {
                background-color: #4ca3ff;
                color: #ffffff;
            }
            QScrollArea {
                background-color: #f5f5f5;
                border: none;
            }
            QWidget {
                background-color: #f5f5f5;
                color: #1e1e1e;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                background: #f5f5f5;
            }
            QTabBar::tab {
                background: #e0e0e0;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #f5f5f5;
                border-bottom: 2px solid #4ca3ff;
            }
            QProgressBar {
                border: 1px solid #cccccc;
                border-radius: 3px;
                text-align: center;
                background-color: #ffffff;
            }
            QProgressBar::chunk {
                background-color: #4ca3ff;
                border-radius: 2px;
            }
            QFileDialog {
                background-color: #f5f5f5;
            }
            QMessageBox {
                background-color: #f5f5f5;
            }
        """)

        # 居中显示窗口
        from PySide6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen().availableGeometry()
        x = (screen.width() - 600) // 2
        y = (screen.height() - 1200) // 2
        # 确保窗口不会显示在屏幕外
        x = max(0, min(x, screen.width() - 600))
        y = max(0, min(y, screen.height() - 400))
        self.setGeometry(x, y, 600, 1200)  # 设置初始高度为1200px

        # 设置窗口大小策略，只允许垂直调整高度，不允许调整宽度
        from PySide6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        self.setMinimumWidth(600)  # 设置最小宽度
        self.setMaximumWidth(600)  # 设置最大宽度，与最小宽度相同，锁定宽度
        self.setMinimumHeight(400)  # 设置最小高度

        # 设置图标
        if os.path.exists("icon.ico"):
            self.setWindowIcon(QIcon("icon.ico"))

        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # 创建内容部件和布局
        content_widget = QWidget()
        layout = QVBoxLayout()
        content_widget.setLayout(layout)

        # 创建主布局并添加滚动区域
        main_layout = QVBoxLayout()
        main_layout.addWidget(scroll)

        # API设置
        api_group = QGroupBox("API设置")
        api_layout = QFormLayout()

        self.openai_key_edit = QLineEdit()
        self.openai_key_edit.setText(self.config.get("openai_key", ""))
        self.openai_key_edit.setPlaceholderText("输入OpenAI API密钥")
        api_layout.addRow("OpenAI API密钥:", self.openai_key_edit)

        self.deepseek_key_edit = QLineEdit()
        self.deepseek_key_edit.setText(self.config.get("deepseek_key", ""))
        self.deepseek_key_edit.setPlaceholderText("输入DeepSeek API密钥")
        api_layout.addRow("DeepSeek API密钥:", self.deepseek_key_edit)

        api_group.setLayout(api_layout)

        # 浏览器设置
        browser_group = QGroupBox("浏览器设置")
        browser_layout = QFormLayout()

        self.default_browser_combo = QComboBox()
        self.default_browser_combo.addItems(["默认浏览器", "chrome", "firefox", "edge", "opera", "safari"])
        current_browser = self.config.get("default_browser", "")
        if current_browser:
            index = self.default_browser_combo.findText(current_browser)
            if index >= 0:
                self.default_browser_combo.setCurrentIndex(index)
        browser_layout.addRow("默认浏览器:", self.default_browser_combo)

        self.default_search_engine_combo = QComboBox()
        self.default_search_engine_combo.addItems(["baidu", "google", "bing", "sogou", "360"])
        current_engine = self.config.get("default_search_engine", "baidu")
        index = self.default_search_engine_combo.findText(current_engine)
        if index >= 0:
            self.default_search_engine_combo.setCurrentIndex(index)
        browser_layout.addRow("默认搜索引擎:", self.default_search_engine_combo)

        browser_group.setLayout(browser_layout)

        # 模型选择
        model_group = QGroupBox("模型设置")
        model_layout = QFormLayout()

        self.chat_model_combo = QComboBox()
        self.chat_model_combo.addItems(["deepseek-chat", "deepseek-coder", "deepseek-reasoner", "gpt-4-turbo", "gpt-3.5-turbo"])
        self.chat_model_combo.setCurrentText(self.config.get("selected_model", "deepseek-chat"))
        model_layout.addRow("AI模型:", self.chat_model_combo)

        # 记忆系统模型选择
        self.memory_model_combo = QComboBox()
        self.memory_model_combo.addItems(["deepseek-chat", "deepseek-coder", "deepseek-reasoner", "gpt-4-turbo", "gpt-3.5-turbo"])
        self.memory_model_combo.setCurrentText(self.config.get("memory_summary_model", "deepseek-reasoner"))
        model_layout.addRow("记忆系统模型:", self.memory_model_combo)

        # 锁定模型选择
        self.lock_model_checkbox = QCheckBox("锁定模型选择（防止误操作）")
        lock_model = self.config.get("lock_model", False)
        self.lock_model_checkbox.setChecked(lock_model)
        self.lock_model_checkbox.stateChanged.connect(self.on_lock_model_changed)
        model_layout.addRow("", self.lock_model_checkbox)

        # 根据锁定状态启用/禁用模型选择
        self.on_lock_model_changed(self.lock_model_checkbox.checkState())

        model_group.setLayout(model_layout)

        # UI设置
        ui_group = QGroupBox("界面设置")
        ui_layout = QFormLayout()

        # 透明度设置
        self.transparency_slider = QSlider(Qt.Horizontal)
        self.transparency_slider.setMinimum(50)  # 50%透明度
        self.transparency_slider.setMaximum(100)  # 100%不透明
        transparency_value = self.config.get("window_transparency", 100)
        self.transparency_slider.setValue(transparency_value)
        self.transparency_label = QLabel(f"{transparency_value}%")
        self.transparency_slider.valueChanged.connect(self.on_transparency_changed)
        transparency_layout = QHBoxLayout()
        transparency_layout.addWidget(self.transparency_slider)
        transparency_layout.addWidget(self.transparency_label)
        ui_layout.addRow("窗口透明度:", transparency_layout)

        # 记忆系统显示设置
        self.show_remember_details_checkbox = QCheckBox("显示'记住这个时刻'的详细信息")
        show_remember_details = self.config.get("show_remember_details", True)
        self.show_remember_details_checkbox.setChecked(show_remember_details)
        ui_layout.addRow("记忆系统:", self.show_remember_details_checkbox)

        # AI智能创建后备机制设置
        self.ai_fallback_checkbox = QCheckBox("启用AI智能创建的后备机制（关键词识别）")
        ai_fallback_enabled = self.config.get("ai_fallback_enabled", True)
        self.ai_fallback_checkbox.setChecked(ai_fallback_enabled)
        ui_layout.addRow("AI创建:", self.ai_fallback_checkbox)

        # AI智能总结后备方案设置
        self.ai_summary_checkbox = QCheckBox("启用AI智能总结后备方案（关键词识别）")
        ai_summary_enabled = self.config.get("ai_summary_enabled", True)
        self.ai_summary_checkbox.setChecked(ai_summary_enabled)
        ui_layout.addRow("AI总结后备:", self.ai_summary_checkbox)

        # 默认保存路径设置
        default_save_path_layout = QHBoxLayout()
        self.default_save_path_edit = QLineEdit()
        self.default_save_path_edit.setText(self.config.get("default_save_path", "D:/东海帝王文件/"))
        self.default_save_path_edit.setPlaceholderText("输入默认保存路径")
        self.browse_path_button = QPushButton("浏览...")
        self.browse_path_button.clicked.connect(self.browse_default_save_path)
        default_save_path_layout.addWidget(self.default_save_path_edit)
        default_save_path_layout.addWidget(self.browse_path_button)
        ui_layout.addRow("默认保存路径:", default_save_path_layout)

        # 笔记文件名格式设置
        self.filename_format_combo = QComboBox()
        self.filename_format_combo.addItems(["时间戳格式 (推荐)", "简单格式"])
        filename_format = self.config.get("note_filename_format", "timestamp")
        if filename_format == "simple":
            self.filename_format_combo.setCurrentIndex(1)
        else:
            self.filename_format_combo.setCurrentIndex(0)
        ui_layout.addRow("笔记文件名格式:", self.filename_format_combo)

        ui_group.setLayout(ui_layout)

        # TTS设置
        tts_group = QGroupBox("语音合成 (TTS) 设置")
        tts_layout = QFormLayout()

        # TTS启用开关
        self.tts_enabled_checkbox = QCheckBox("启用语音合成")
        tts_enabled = self.config.get("tts_enabled", False)
        self.tts_enabled_checkbox.setChecked(tts_enabled)
        tts_layout.addRow("TTS功能:", self.tts_enabled_checkbox)

        # TTS引擎选择
        self.tts_engine_combo = QComboBox()
        self.tts_engine_combo.addItems(["Azure TTS", "GPT-SoVITS"])
        current_engine = self.config.get("tts_engine", "azure")
        if current_engine == "gpt_sovits":
            self.tts_engine_combo.setCurrentIndex(1)
        else:
            self.tts_engine_combo.setCurrentIndex(0)
        self.tts_engine_combo.currentTextChanged.connect(self.on_tts_engine_changed)
        tts_layout.addRow("TTS引擎:", self.tts_engine_combo)

        # Azure TTS设置组
        self.azure_group = QGroupBox("Azure TTS 设置")
        azure_layout = QFormLayout()
        
        # Azure TTS API密钥
        self.azure_tts_key_edit = QLineEdit()
        self.azure_tts_key_edit.setText(self.config.get("azure_tts_key", ""))
        self.azure_tts_key_edit.setPlaceholderText("输入Azure Speech Service API密钥")
        self.azure_tts_key_edit.setEchoMode(QLineEdit.Password)
        azure_layout.addRow("Azure TTS API密钥:", self.azure_tts_key_edit)

        # Azure区域
        self.azure_region_combo = QComboBox()
        self.azure_region_combo.addItems([
            "eastasia (东亚)",
            "southeastasia (东南亚)",
            "eastus (美国东部)",
            "westus (美国西部)",
            "northeurope (北欧)",
            "westeurope (西欧)"
        ])
        current_region = self.config.get("azure_region", "eastasia")
        region_text = f"{current_region} ({self._get_region_name(current_region)})"
        index = self.azure_region_combo.findText(region_text)
        if index >= 0:
            self.azure_region_combo.setCurrentIndex(index)
        azure_layout.addRow("Azure区域:", self.azure_region_combo)

        # TTS语音选择
        self.tts_voice_combo = QComboBox()
        voices = [
            ("zh-CN-XiaoxiaoNeural", "晓晓 (推荐)"),
            ("zh-CN-XiaoyiNeural", "晓伊"),
            ("zh-CN-YunxiNeural", "云希"),
            ("zh-CN-YunyangNeural", "云扬"),
            ("zh-CN-XiaochenNeural", "晓辰"),
            ("zh-CN-XiaohanNeural", "晓涵"),
            ("zh-CN-XiaomoNeural", "晓墨"),
            ("zh-CN-XiaoxuanNeural", "晓萱"),
            ("zh-CN-XiaoyanNeural", "晓颜"),
            ("zh-CN-XiaoyouNeural", "晓悠"),
        ]
        for voice_id, voice_name in voices:
            self.tts_voice_combo.addItem(f"{voice_name} ({voice_id})", voice_id)

        current_voice = self.config.get("tts_voice", "zh-CN-XiaoxiaoNeural")
        for i in range(self.tts_voice_combo.count()):
            if self.tts_voice_combo.itemData(i) == current_voice:
                self.tts_voice_combo.setCurrentIndex(i)
                break
        azure_layout.addRow("语音选择:", self.tts_voice_combo)

        # TTS语速设置
        self.tts_speed_slider = QSlider(Qt.Horizontal)
        self.tts_speed_slider.setMinimum(50)  # 0.5倍速
        self.tts_speed_slider.setMaximum(200)  # 2.0倍速
        speed_value = int(self.config.get("tts_speaking_rate", 1.0) * 100)
        self.tts_speed_slider.setValue(speed_value)
        self.tts_speed_label = QLabel(f"{speed_value/100:.1f}x")
        self.tts_speed_slider.valueChanged.connect(self.on_speed_changed)
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(self.tts_speed_slider)
        speed_layout.addWidget(self.tts_speed_label)
        azure_layout.addRow("语速:", speed_layout)
        
        # 设置Azure组布局并添加到TTS布局
        self.azure_group.setLayout(azure_layout)
        tts_layout.addRow(self.azure_group)

        # GPT-SoVITS设置组
        self.gpt_sovits_group = QGroupBox("GPT-SoVITS 设置")
        gpt_sovits_layout = QFormLayout()

        # GPT-SoVITS API类型选择
        self.gpt_sovits_api_type_combo = QComboBox()
        self.gpt_sovits_api_type_combo.addItems(["gradio", "api_v2"])
        current_api_type = self.config.get("gpt_sovits_api_type", "gradio")
        index = self.gpt_sovits_api_type_combo.findText(current_api_type)
        if index >= 0:
            self.gpt_sovits_api_type_combo.setCurrentIndex(index)
        self.gpt_sovits_api_type_combo.currentTextChanged.connect(self.on_gpt_sovits_api_type_changed)
        gpt_sovits_layout.addRow("API类型:", self.gpt_sovits_api_type_combo)

        # GPT-SoVITS API地址
        self.gpt_sovits_api_url_edit = QLineEdit()
        self.gpt_sovits_api_url_edit.setText(self.config.get("gpt_sovits_api_url", "http://127.0.0.1:9880"))
        self.gpt_sovits_api_url_edit.setPlaceholderText("输入GPT-SoVITS API地址")
        gpt_sovits_layout.addRow("API地址:", self.gpt_sovits_api_url_edit)

        # 参考音频路径
        ref_audio_layout = QHBoxLayout()
        self.gpt_sovits_ref_audio_edit = QLineEdit()
        self.gpt_sovits_ref_audio_edit.setText(self.config.get("gpt_sovits_ref_audio", ""))
        self.gpt_sovits_ref_audio_edit.setPlaceholderText("选择参考音频文件")
        self.browse_ref_audio_button = QPushButton("浏览...")
        self.browse_ref_audio_button.clicked.connect(self.browse_ref_audio)
        ref_audio_layout.addWidget(self.gpt_sovits_ref_audio_edit)
        ref_audio_layout.addWidget(self.browse_ref_audio_button)
        gpt_sovits_layout.addRow("参考音频:", ref_audio_layout)

        # T2S模型权重路径
        t2s_weights_layout = QHBoxLayout()
        self.gpt_sovits_t2s_weights_edit = QLineEdit()
        self.gpt_sovits_t2s_weights_edit.setText(self.config.get("gpt_sovits_t2s_weights", "GPT_SoVITS/pretrained_models/gsv-v2final-pretrained/s1bert25hz-5kh-longer-epoch=12-step=369668.ckpt"))
        self.gpt_sovits_t2s_weights_edit.setPlaceholderText("选择T2S模型权重文件")
        self.browse_t2s_weights_button = QPushButton("浏览...")
        self.browse_t2s_weights_button.clicked.connect(self.browse_t2s_weights)
        t2s_weights_layout.addWidget(self.gpt_sovits_t2s_weights_edit)
        t2s_weights_layout.addWidget(self.browse_t2s_weights_button)
        gpt_sovits_layout.addRow("T2S模型权重:", t2s_weights_layout)

        # VITS模型权重路径
        vits_weights_layout = QHBoxLayout()
        self.gpt_sovits_vits_weights_edit = QLineEdit()
        self.gpt_sovits_vits_weights_edit.setText(self.config.get("gpt_sovits_vits_weights", "GPT_SoVITS/pretrained_models/gsv-v2final-pretrained/s2G2333k.pth"))
        self.gpt_sovits_vits_weights_edit.setPlaceholderText("选择VITS模型权重文件")
        self.browse_vits_weights_button = QPushButton("浏览...")
        self.browse_vits_weights_button.clicked.connect(self.browse_vits_weights)
        vits_weights_layout.addWidget(self.gpt_sovits_vits_weights_edit)
        vits_weights_layout.addWidget(self.browse_vits_weights_button)
        gpt_sovits_layout.addRow("VITS模型权重:", vits_weights_layout)

        # 应用模型权重按钮
        apply_weights_layout = QHBoxLayout()
        self.apply_weights_button = QPushButton("应用模型权重")
        self.apply_weights_button.clicked.connect(self.apply_model_weights)
        self.apply_weights_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        apply_weights_layout.addWidget(self.apply_weights_button)
        gpt_sovits_layout.addRow("", apply_weights_layout)

        self.gpt_sovits_group.setLayout(gpt_sovits_layout)
        tts_layout.addRow(self.gpt_sovits_group)

        # 根据当前引擎设置显示相应的组
        current_engine = self.config.get("tts_engine", "azure")
        if current_engine == "gpt_sovits":
            self.azure_group.setVisible(False)
            self.gpt_sovits_group.setVisible(True)
        else:
            self.azure_group.setVisible(True)
            self.gpt_sovits_group.setVisible(False)

        tts_group.setLayout(tts_layout)

        # 快捷工具设置
        tool_group = QGroupBox("快捷工具设置")
        tool_layout = QVBoxLayout()

        # 网站快捷方式
        website_group = QGroupBox("网站快捷方式")
        website_layout = QVBoxLayout()

        self.website_list = QListWidget()
        websites = self.config.get("websites", [])
        for site in websites:
            self.website_list.addItem(site)

        website_btn_layout = QHBoxLayout()
        add_site_btn = QPushButton("添加网站")
        add_site_btn.clicked.connect(self.add_website)
        remove_site_btn = QPushButton("移除网站")
        remove_site_btn.clicked.connect(self.remove_website)
        website_btn_layout.addWidget(add_site_btn)
        website_btn_layout.addWidget(remove_site_btn)

        website_layout.addWidget(self.website_list)
        website_layout.addLayout(website_btn_layout)
        website_group.setLayout(website_layout)

        # 应用程序快捷方式
        app_group = QGroupBox("应用程序快捷方式")
        app_layout = QVBoxLayout()

        self.app_list = QListWidget()
        apps = self.config.get("applications", [])
        for app in apps:
            self.app_list.addItem(app)

        app_layout.addWidget(self.app_list)

        app_btn_layout = QHBoxLayout()
        scan_apps_btn = QPushButton("扫描应用")
        scan_apps_btn.clicked.connect(self.scan_applications)
        add_app_btn = QPushButton("添加应用")
        add_app_btn.clicked.connect(self.add_application)
        remove_app_btn = QPushButton("移除应用")
        remove_app_btn.clicked.connect(self.remove_application)
        app_btn_layout.addWidget(scan_apps_btn)
        app_btn_layout.addWidget(add_app_btn)
        app_btn_layout.addWidget(remove_app_btn)

        app_layout.addLayout(app_btn_layout)
        app_group.setLayout(app_layout)

        tool_layout.addWidget(website_group)
        tool_layout.addWidget(app_group)
        tool_group.setLayout(tool_layout)

        # 按钮
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("保存设置")
        save_btn.clicked.connect(self.save_settings)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)

        # 添加所有组到布局
        layout.addWidget(api_group)
        layout.addWidget(browser_group)
        layout.addWidget(model_group)
        layout.addWidget(ui_group)
        layout.addWidget(tts_group)
        layout.addWidget(tool_group)
        layout.addLayout(btn_layout)

        # 将滚动区域设置为主布局
        content_widget.setLayout(layout)
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)

    def on_transparency_changed(self, value):
        """透明度滑块值改变时的处理"""
        # 更新标签显示
        self.transparency_label.setText(f"{value}%")

        # 如果有回调函数，实时更新主窗口透明度
        if self.transparency_callback:
            try:
                self.transparency_callback(value)
            except Exception as e:
                print(f"⚠️ 实时更新透明度失败: {str(e)}")

    def on_speed_changed(self, value):
        """语速滑块值改变时的处理"""
        # 更新标签显示
        self.tts_speed_label.setText(f"{value/100:.1f}x")

    def add_website(self):
        """添加网站"""
        site, ok1 = QInputDialog.getText(self, "添加网站", "输入网站名称:")
        if not ok1 or not site:
            return

        url, ok2 = QInputDialog.getText(self, "添加网站", "输入网站URL:")
        if ok2 and url:
            self.website_list.addItem(f"{site}: {url}")

    def remove_website(self):
        """移除网站"""
        if self.website_list.currentRow() >= 0:
            self.website_list.takeItem(self.website_list.currentRow())

    def scan_applications(self):
        """扫描应用程序"""
        apps = scan_windows_apps()
        if not apps:
            QMessageBox.information(self, "扫描结果", "未找到任何应用程序")
            return

        # 显示选择对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("选择应用程序")
        dialog.resize(400, 300)
        layout = QVBoxLayout()

        app_list = QListWidget()
        for app in apps:
            item = QListWidgetItem(app["name"])
            item.setData(Qt.UserRole, app)
            app_list.addItem(item)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        cancel_btn = QPushButton("取消")
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)

        layout.addWidget(app_list)
        layout.addLayout(btn_layout)
        dialog.setLayout(layout)

        ok_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)

        if dialog.exec() == QDialog.Accepted:
            selected_items = app_list.selectedItems()
            for item in selected_items:
                app_data = item.data(Qt.UserRole)
                self.app_list.addItem(f"{app_data['name']}: {app_data['path']}")

    def add_application(self):
        """添加应用程序"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择应用程序", "", "可执行文件 (*.exe);;所有文件 (*.*)"
        )
        if file_path:
            app_name = os.path.basename(file_path).replace('.exe', '')
            self.app_list.addItem(f"{app_name}: {file_path}")

    def remove_application(self):
        """移除应用程序"""
        if self.app_list.currentRow() >= 0:
            self.app_list.takeItem(self.app_list.currentRow())

    def browse_default_save_path(self):
        """浏览默认保存路径"""
        path = QFileDialog.getExistingDirectory(self, "选择默认保存路径")
        if path:
            self.default_save_path_edit.setText(path)

    def _get_region_name(self, region_code):
        """获取Azure区域名称"""
        region_names = {
            "eastasia": "东亚",
            "southeastasia": "东南亚",
            "eastus": "美国东部",
            "westus": "美国西部",
            "northeurope": "北欧",
            "westeurope": "西欧"
        }
        return region_names.get(region_code, region_code)

    def save_settings(self):
        """保存设置"""
        # API设置
        self.config["openai_key"] = self.openai_key_edit.text()
        self.config["deepseek_key"] = self.deepseek_key_edit.text()

        # 浏览器设置
        self.config["default_browser"] = self.default_browser_combo.currentText()
        self.config["default_search_engine"] = self.default_search_engine_combo.currentText()

        # 模型设置
        self.config["selected_model"] = self.chat_model_combo.currentText()
        self.config["memory_summary_model"] = self.memory_model_combo.currentText()
        self.config["lock_model"] = self.lock_model_checkbox.isChecked()

        # UI设置
        self.config["window_transparency"] = self.transparency_slider.value()
        self.config["show_remember_details"] = self.show_remember_details_checkbox.isChecked()
        self.config["ai_fallback_enabled"] = self.ai_fallback_checkbox.isChecked()
        self.config["ai_summary_enabled"] = self.ai_summary_checkbox.isChecked()
        self.config["default_save_path"] = self.default_save_path_edit.text()
        filename_format = "timestamp" if self.filename_format_combo.currentIndex() == 0 else "simple"
        self.config["note_filename_format"] = filename_format

        # TTS设置
        self.config["tts_enabled"] = self.tts_enabled_checkbox.isChecked()
        engine_text = self.tts_engine_combo.currentText()
        if engine_text == "Azure TTS":
            self.config["tts_engine"] = "azure"
        elif engine_text == "GPT-SoVITS":
            self.config["tts_engine"] = "gpt_sovits"
        
        self.config["azure_tts_key"] = self.azure_tts_key_edit.text()
        region_code = self.azure_region_combo.currentText().split(" ")[0]
        self.config["azure_region"] = region_code
        self.config["tts_voice"] = self.tts_voice_combo.currentData()
        self.config["tts_speaking_rate"] = self.tts_speed_slider.value() / 100.0
        
        # GPT-SoVITS设置
        self.config["gpt_sovits_api_type"] = self.gpt_sovits_api_type_combo.currentText()
        self.config["gpt_sovits_api_url"] = self.gpt_sovits_api_url_edit.text()
        self.config["gpt_sovits_ref_audio"] = self.gpt_sovits_ref_audio_edit.text()
        self.config["gpt_sovits_t2s_weights"] = self.gpt_sovits_t2s_weights_edit.text()
        self.config["gpt_sovits_vits_weights"] = self.gpt_sovits_vits_weights_edit.text()

        # 网站快捷方式
        websites = []
        for i in range(self.website_list.count()):
            websites.append(self.website_list.item(i).text())
        self.config["websites"] = websites

        # 应用程序快捷方式
        applications = []
        for i in range(self.app_list.count()):
            applications.append(self.app_list.item(i).text())
        self.config["applications"] = applications

        # 保存配置
        save_config(self.config)

        QMessageBox.information(self, "设置", "设置已保存")
        self.accept()

    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if event.buttons() == Qt.LeftButton and self.drag_pos is not None:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton:
            self.drag_pos = None
            event.accept()

    def on_tts_engine_changed(self, engine_name):
        """TTS引擎切换事件处理"""
        if engine_name == "Azure TTS":
            self.azure_group.setVisible(True)
            self.gpt_sovits_group.setVisible(False)
        elif engine_name == "GPT-SoVITS":
            self.azure_group.setVisible(False)
            self.gpt_sovits_group.setVisible(True)

    def on_gpt_sovits_api_type_changed(self, api_type):
        """GPT-SoVITS API类型切换事件处理"""
        # 根据API类型设置默认API地址
        if api_type == "gradio":
            self.gpt_sovits_api_url_edit.setText("http://127.0.0.1:9872")
        elif api_type == "api_v2":
            self.gpt_sovits_api_url_edit.setText("http://127.0.0.1:9880")

    def browse_ref_audio(self):
        """浏览参考音频文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择参考音频文件",
            "",
            "音频文件 (*.wav;*.mp3;*.flac;*.ogg);;All Files (*)"
        )
        if file_path:
            self.gpt_sovits_ref_audio_edit.setText(file_path)

    def browse_t2s_weights(self):
        """浏览T2S模型权重文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择T2S模型权重文件",
            "",
            "权重文件 (*.ckpt);;All Files (*)"
        )
        if file_path:
            self.gpt_sovits_t2s_weights_edit.setText(file_path)

    def browse_vits_weights(self):
        """浏览VITS模型权重文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择VITS模型权重文件",
            "",
            "权重文件 (*.pth);;All Files (*)"
        )
        if file_path:
            self.gpt_sovits_vits_weights_edit.setText(file_path)

    def apply_model_weights(self):
        """应用模型权重"""
        # 检查是否选择了GPT-SoVITS作为TTS引擎
        engine_text = self.tts_engine_combo.currentText()
        if engine_text != "GPT-SoVITS":
            QMessageBox.warning(self, "警告", "请先选择GPT-SoVITS作为TTS引擎")
            return

        # 检查是否选择了api_v2作为API类型
        api_type = self.gpt_sovits_api_type_combo.currentText()
        if api_type != "api_v2":
            QMessageBox.warning(self, "警告", "只有api_v2类型支持动态切换模型权重")
            return

        # 检查是否设置了模型权重路径
        t2s_weights_path = self.gpt_sovits_t2s_weights_edit.text()
        vits_weights_path = self.gpt_sovits_vits_weights_edit.text()

        if not t2s_weights_path and not vits_weights_path:
            QMessageBox.warning(self, "警告", "请先设置模型权重路径")
            return

        # 检查文件是否存在
        if t2s_weights_path and not os.path.exists(t2s_weights_path):
            QMessageBox.warning(self, "错误", f"T2S模型权重文件不存在: {t2s_weights_path}")
            return

        if vits_weights_path and not os.path.exists(vits_weights_path):
            QMessageBox.warning(self, "错误", f"VITS模型权重文件不存在: {vits_weights_path}")
            return

        # 应用模型权重
        try:
            # 获取主窗口的agent实例
            parent = self.parent()
            while parent and not hasattr(parent, 'agent'):
                parent = parent.parent()

            if not parent or not hasattr(parent, 'agent'):
                QMessageBox.warning(self, "错误", "无法获取AI Agent实例")
                return

            # 先更新config中的模型权重路径
            parent.agent.config["gpt_sovits_t2s_weights"] = t2s_weights_path
            parent.agent.config["gpt_sovits_vits_weights"] = vits_weights_path
            
            # 应用模型权重
            result = parent.agent.apply_tts_model_weights()
            if result:
                QMessageBox.information(self, "成功", "模型权重应用成功")
            else:
                QMessageBox.warning(self, "失败", "模型权重应用失败，请查看控制台日志")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"应用模型权重时发生异常: {str(e)}")
            import traceback
            traceback.print_exc()

    def on_speed_changed(self, value):
        """语速改变事件处理"""
        self.tts_speed_label.setText(f"{value/100:.1f}x")

    def on_lock_model_changed(self, state):
        """锁定模型选择状态变化事件处理"""
        is_locked = (state == Qt.Checked)
        # 根据锁定状态启用/禁用模型选择
        self.chat_model_combo.setEnabled(not is_locked)
        self.memory_model_combo.setEnabled(not is_locked)

    def _get_region_name(self, region_code: str) -> str:
        """获取区域名称"""
        region_names = {
            "eastasia": "东亚",
            "southeastasia": "东南亚",
            "eastus": "美国东部",
            "westus": "美国西部",
            "northeurope": "北欧",
            "westeurope": "西欧"
        }
        return region_names.get(region_code, region_code)
