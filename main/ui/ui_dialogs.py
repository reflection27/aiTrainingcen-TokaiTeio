# -*- coding: utf-8 -*-
"""
UI对话框模块
包含设置、记忆系统、MCP工具等对话框
"""

import os
import json
import datetime

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
                             QPushButton, QLabel, QComboBox, QSplitter, QListWidget,
                             QGroupBox, QFormLayout, QMessageBox, QInputDialog,
                             QFileDialog, QProgressBar, QListWidgetItem, QTabWidget,
                             QSlider, QCheckBox, QWidget)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon

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
        from PySide6.QtWidgets import QScrollArea, QWidget
        from PySide6.QtCore import Qt

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

        self.weather_key_edit = QLineEdit()
        self.weather_key_edit.setText(self.config.get("heweather_key", ""))
        self.weather_key_edit.setPlaceholderText("输入和风天气API密钥")
        api_layout.addRow("和风天气API密钥:", self.weather_key_edit)

        self.amap_key_edit = QLineEdit()
        self.amap_key_edit.setText(self.config.get("amap_key", ""))
        self.amap_key_edit.setPlaceholderText("输入高德地图API密钥")
        api_layout.addRow("高德地图API密钥:", self.amap_key_edit)

        # 天气数据来源设置
        self.weather_source_combo = QComboBox()
        self.weather_source_combo.addItems(["和风天气API", "高德地图API"])
        current_source = self.config.get("weather_source", "和风天气API")
        index = self.weather_source_combo.findText(current_source)
        if index >= 0:
            self.weather_source_combo.setCurrentIndex(index)
        api_layout.addRow("天气数据来源:", self.weather_source_combo)

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

        # AI Token数设置
        self.max_tokens_edit = QLineEdit()
        max_tokens = self.config.get("max_tokens", "1000")
        self.max_tokens_edit.setText(str(max_tokens))
        self.max_tokens_edit.setPlaceholderText("输入最大token数，0表示无限制")
        model_layout.addRow("最大Token数:", self.max_tokens_edit)

        model_group.setLayout(model_layout)

        # 界面设置
        ui_group = QGroupBox("界面设置")
        ui_layout = QFormLayout()

        # 窗口透明度设置
        self.transparency_slider = QSlider(Qt.Horizontal)
        self.transparency_slider.setMinimum(30)  # 最小30%透明度
        self.transparency_slider.setMaximum(100)  # 最大100%不透明
        transparency_value = self.config.get("window_transparency", 100)
        self.transparency_slider.setValue(transparency_value)
        self.transparency_slider.setTickPosition(QSlider.TicksBelow)
        self.transparency_slider.setTickInterval(10)
        
        self.transparency_label = QLabel(f"{transparency_value}%")
        self.transparency_slider.valueChanged.connect(self.on_transparency_changed)
        
        transparency_layout = QHBoxLayout()
        transparency_layout.addWidget(self.transparency_slider)
        transparency_layout.addWidget(self.transparency_label)
        ui_layout.addRow("窗口透明度:", transparency_layout)

        # 记忆系统设置
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
        self.tts_speed_slider.setTickPosition(QSlider.TicksBelow)
        self.tts_speed_slider.setTickInterval(25)
        
        self.tts_speed_label = QLabel(f"{speed_value/100:.1f}x")
        self.tts_speed_slider.valueChanged.connect(
            lambda value: self.tts_speed_label.setText(f"{value/100:.1f}x")
        )
        
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(self.tts_speed_slider)
        speed_layout.addWidget(self.tts_speed_label)
        azure_layout.addRow("语速设置:", speed_layout)

        # 设置Azure组布局并添加到TTS布局
        self.azure_group.setLayout(azure_layout)
        tts_layout.addRow(self.azure_group)

        # GPT-SoVITS设置组
        self.gpt_sovits_group = QGroupBox("GPT-SoVITS 设置")
        gpt_sovits_layout = QFormLayout()

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

        self.gpt_sovits_group.setLayout(gpt_sovits_layout)
        tts_layout.addRow(self.gpt_sovits_group)

        tts_group.setLayout(tts_layout)

        # 添加所有组件到主布局
        layout.addWidget(api_group)
        layout.addWidget(browser_group)
        layout.addWidget(model_group)
        layout.addWidget(ui_group)
        layout.addWidget(tts_group)

        # 工具管理
        tool_group = QGroupBox("工具管理")
        tool_layout = QVBoxLayout()

        # 网站管理
        website_group = QGroupBox("网站管理")
        website_layout = QVBoxLayout()

        self.website_list = QListWidget()
        for site, url in self.config.get("website_map", {}).items():
            self.website_list.addItem(f"{site}: {url}")
        website_layout.addWidget(self.website_list)

        website_btn_layout = QHBoxLayout()
        add_website_btn = QPushButton("添加网站")
        add_website_btn.clicked.connect(self.add_website)
        remove_website_btn = QPushButton("移除网站")
        remove_website_btn.clicked.connect(self.remove_website)
        website_btn_layout.addWidget(add_website_btn)
        website_btn_layout.addWidget(remove_website_btn)

        website_layout.addLayout(website_btn_layout)
        website_group.setLayout(website_layout)

        # 应用管理
        app_group = QGroupBox("应用管理")
        app_layout = QVBoxLayout()

        self.app_list = QListWidget()
        for app, path in self.config.get("app_map", {}).items():
            self.app_list.addItem(f"{app}: {path}")
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
        self.app_list.clear()
        for app_name, app_path in apps.items():
            self.app_list.addItem(f"{app_name}: {app_path}")

    def add_application(self):
        """添加应用程序"""
        app_name, ok1 = QInputDialog.getText(self, "添加应用", "输入应用名称:")
        if not ok1 or not app_name:
            return

        app_path, ok2 = QFileDialog.getOpenFileName(self, "选择应用程序", "",
                                                    "Executable Files (*.exe;*.lnk);;All Files (*)")
        if ok2 and app_path:
            self.app_list.addItem(f"{app_name}: {app_path}")

    def remove_application(self):
        """移除应用程序"""
        if self.app_list.currentRow() >= 0:
            self.app_list.takeItem(self.app_list.currentRow())

    def browse_default_save_path(self):
        """浏览默认保存路径"""
        current_path = self.default_save_path_edit.text().strip()
        if not current_path:
            current_path = "D:/"
        
        # 确保路径存在，如果不存在则创建
        if not os.path.exists(current_path):
            try:
                os.makedirs(current_path, exist_ok=True)
            except:
                current_path = "D:/"
        
        folder_path = QFileDialog.getExistingDirectory(
            self, 
            "选择默认保存路径", 
            current_path,
            QFileDialog.ShowDirsOnly
        )
        
        if folder_path:
            # 确保路径以斜杠结尾
            if not folder_path.endswith('/') and not folder_path.endswith('\\'):
                folder_path += '/'
            self.default_save_path_edit.setText(folder_path)

    def save_settings(self):
        """保存设置"""
        # 保存API密钥
        self.config["openai_key"] = self.openai_key_edit.text()
        self.config["deepseek_key"] = self.deepseek_key_edit.text()
        self.config["heweather_key"] = self.weather_key_edit.text()
        self.config["amap_key"] = self.amap_key_edit.text()

        # 保存天气数据来源设置
        self.config["weather_source"] = self.weather_source_combo.currentText()

        # 保存浏览器设置
        browser_text = self.default_browser_combo.currentText()
        if browser_text == "默认浏览器":
            self.config["default_browser"] = ""
        else:
            self.config["default_browser"] = browser_text
        self.config["default_search_engine"] = self.default_search_engine_combo.currentText()

        # 保存模型选择
        self.config["selected_model"] = self.chat_model_combo.currentText()
        
        # 保存记忆系统模型选择
        self.config["memory_summary_model"] = self.memory_model_combo.currentText()

        # 保存AI Token数设置
        try:
            max_tokens = int(self.max_tokens_edit.text())
            if max_tokens < 0:
                max_tokens = 0  # 0表示无限制
            self.config["max_tokens"] = max_tokens
        except ValueError:
            self.config["max_tokens"] = 1000  # 默认值

        # 保存窗口透明度设置
        self.config["window_transparency"] = self.transparency_slider.value()

        # 保存记忆系统设置
        self.config["show_remember_details"] = self.show_remember_details_checkbox.isChecked()

        # 保存AI智能创建后备机制设置
        self.config["ai_fallback_enabled"] = self.ai_fallback_checkbox.isChecked()

        # 保存AI智能总结设置
        self.config["ai_summary_enabled"] = self.ai_summary_checkbox.isChecked()

        # 保存默认保存路径设置
        self.config["default_save_path"] = self.default_save_path_edit.text().strip()

        # 保存笔记文件名格式设置
        filename_format_index = self.filename_format_combo.currentIndex()
        if filename_format_index == 1:  # 简单格式
            self.config["note_filename_format"] = "simple"
        else:  # 时间戳格式
            self.config["note_filename_format"] = "timestamp"

        # 保存TTS设置
        self.config["tts_enabled"] = self.tts_enabled_checkbox.isChecked()
        self.config["azure_tts_key"] = self.azure_tts_key_edit.text()
        
        # 保存Azure区域
        region_text = self.azure_region_combo.currentText()
        self.config["azure_region"] = self._get_region_code(region_text)
        
        # 保存TTS语音
        voice_index = self.tts_voice_combo.currentIndex()
        if voice_index >= 0:
            self.config["tts_voice"] = self.tts_voice_combo.itemData(voice_index)
        
        # 保存TTS语速
        speed_value = self.tts_speed_slider.value() / 100.0
        self.config["tts_speaking_rate"] = speed_value
        
        # 保存TTS引擎选择
        engine_text = self.tts_engine_combo.currentText()
        if engine_text == "GPT-SoVITS":
            self.config["tts_engine"] = "gpt_sovits"
        else:
            self.config["tts_engine"] = "azure"
            
        # 保存GPT-SoVITS设置
        self.config["gpt_sovits_api_url"] = self.gpt_sovits_api_url_edit.text()
        self.config["gpt_sovits_ref_audio"] = self.gpt_sovits_ref_audio_edit.text()

        # 保存网站映射
        website_map = {}
        for i in range(self.website_list.count()):
            item_text = self.website_list.item(i).text()
            if ": " in item_text:
                site, url = item_text.split(": ", 1)
                website_map[site] = url
        self.config["website_map"] = website_map

        # 保存应用映射
        app_map = {}
        for i in range(self.app_list.count()):
            item_text = self.app_list.item(i).text()
            if ": " in item_text:
                app, path = item_text.split(": ", 1)
                app_map[app] = path
        self.config["app_map"] = app_map

        # 保存到文件
        save_config(self.config)
        self.accept()
    
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
    
    def _get_region_code(self, region_text: str) -> str:
        """从区域文本中提取区域代码"""
        return region_text.split(" ")[0]

    def on_tts_engine_changed(self, engine_name):
        """处理TTS引擎切换"""
        if engine_name == "GPT-SoVITS":
            self.azure_group.hide()
            self.gpt_sovits_group.show()
        else:
            self.azure_group.show()
            self.gpt_sovits_group.hide()

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


class MemoryDialog(QDialog):
    """记忆系统对话框 — 基于 ImprovedMemorySystem（SQLite + FAISS）"""

    # 当用户在对话框里切换/新建会话时，通知主程序
    session_changed = None  # 由外部赋值为回调函数 (session_id: str) -> None

    def __init__(self, memory, agent=None, parent=None):
        super().__init__(parent)
        self.memory = memory
        self.agent = agent          # 可选，用于新建/切换会话
        self._current_session = None
        self.setWindowTitle("记忆系统")
        self.resize(980, 660)
        self._build_ui()
        self.refresh_stats()
        self._load_session_list()

    # ================================================================ UI ===
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # 统计栏
        self.stats_label = QLabel("加载中...")
        self.stats_label.setStyleSheet("color:#555; padding:4px;")
        layout.addWidget(self.stats_label)

        tabs = QTabWidget()
        layout.addWidget(tabs)

        # ── Tab1：对话历史记录 ────────────────────────────────────────────
        conv_widget = QWidget()
        cv = QVBoxLayout(conv_widget)

        # 会话管理栏
        session_bar = QHBoxLayout()
        session_bar.addWidget(QLabel("当前会话:"))
        self.session_combo = QComboBox()
        self.session_combo.setMinimumWidth(320)
        self.session_combo.currentIndexChanged.connect(self._on_session_selected)
        session_bar.addWidget(self.session_combo)
        new_session_btn = QPushButton("新建会话")
        new_session_btn.clicked.connect(self._new_session)
        session_bar.addWidget(new_session_btn)
        switch_btn = QPushButton("切换到此会话")
        switch_btn.setToolTip("将 AI 的当前对话切换到选中的会话")
        switch_btn.clicked.connect(self._switch_session)
        session_bar.addWidget(switch_btn)
        session_bar.addStretch()
        cv.addLayout(session_bar)

        # 搜索栏
        search_bar = QHBoxLayout()
        self.conv_search = QLineEdit()
        self.conv_search.setPlaceholderText("在当前会话中搜索对话内容...")
        self.conv_search.returnPressed.connect(self._load_conv_list)
        search_bar.addWidget(self.conv_search)
        search_btn = QPushButton("搜索")
        search_btn.clicked.connect(self._load_conv_list)
        search_bar.addWidget(search_btn)
        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self._clear_search)
        search_bar.addWidget(clear_btn)
        cv.addLayout(search_bar)

        splitter = QSplitter(Qt.Horizontal)
        self.conv_list = QListWidget()
        self.conv_list.setMinimumWidth(300)
        self.conv_list.currentItemChanged.connect(self._show_conv_detail)
        splitter.addWidget(self.conv_list)

        self.conv_detail = QTextEdit()
        self.conv_detail.setReadOnly(True)
        splitter.addWidget(self.conv_detail)
        splitter.setSizes([300, 620])
        cv.addWidget(splitter)

        # 操作栏
        conv_btn_bar = QHBoxLayout()
        del_conv_btn = QPushButton("删除选中记录")
        del_conv_btn.clicked.connect(self._delete_conversation)
        del_session_btn = QPushButton("删除整个会话")
        del_session_btn.clicked.connect(self._delete_session)
        conv_btn_bar.addStretch()
        conv_btn_bar.addWidget(del_conv_btn)
        conv_btn_bar.addWidget(del_session_btn)
        cv.addLayout(conv_btn_bar)

        tabs.addTab(conv_widget, "对话历史记录")

        # ── Tab2：知识库 ──────────────────────────────────────────────────
        kb_widget = QWidget()
        kb = QVBoxLayout(kb_widget)

        kb_search_bar = QHBoxLayout()
        self.kb_search = QLineEdit()
        self.kb_search.setPlaceholderText("输入关键词语义搜索知识库...")
        self.kb_search.returnPressed.connect(self.search_knowledge)
        kb_search_bar.addWidget(self.kb_search)
        kb_search_btn = QPushButton("搜索")
        kb_search_btn.clicked.connect(self.search_knowledge)
        kb_search_bar.addWidget(kb_search_btn)
        kb_show_all_btn = QPushButton("显示全部")
        kb_show_all_btn.clicked.connect(self._show_all_knowledge)
        kb_search_bar.addWidget(kb_show_all_btn)
        kb.addLayout(kb_search_bar)

        self.kb_list = QListWidget()
        self.kb_list.currentItemChanged.connect(self._show_kb_detail)
        kb.addWidget(self.kb_list)

        self.kb_detail = QTextEdit()
        self.kb_detail.setReadOnly(True)
        self.kb_detail.setMaximumHeight(100)
        kb.addWidget(self.kb_detail)

        # 手动添加知识条目
        kb_add_label = QLabel("手动添加知识条目：")
        kb.addWidget(kb_add_label)
        self.kb_input = QTextEdit()
        self.kb_input.setPlaceholderText("输入要添加到知识库的内容（每行一条）...")
        self.kb_input.setMaximumHeight(80)
        kb.addWidget(self.kb_input)

        kb_btn_bar = QHBoxLayout()
        add_kb_btn = QPushButton("添加到知识库")
        add_kb_btn.clicked.connect(self._add_knowledge_manual)
        kb_btn_bar.addWidget(add_kb_btn)
        kb_btn_bar.addStretch()
        del_kb_btn = QPushButton("删除选中条目")
        del_kb_btn.clicked.connect(self._delete_kb_item)
        kb_btn_bar.addWidget(del_kb_btn)
        kb.addLayout(kb_btn_bar)

        tabs.addTab(kb_widget, "知识库")

        # 底部刷新
        bottom = QHBoxLayout()
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self._refresh_all)
        bottom.addStretch()
        bottom.addWidget(refresh_btn)
        layout.addLayout(bottom)

    # ============================================================= 统计 ===
    def refresh_stats(self):
        try:
            s = self.memory.get_memory_stats()
            self.stats_label.setText(
                f"对话条数: {s['total_conversations']}  |  "
                f"会话数: {s['total_sessions']}  |  "
                f"知识条目: {s['total_knowledge']}"
            )
        except Exception as e:
            self.stats_label.setText(f"统计加载失败: {e}")

    # ========================================================= 会话管理 ===
    def _load_session_list(self):
        """加载会话列表到下拉框"""
        self.session_combo.blockSignals(True)
        self.session_combo.clear()
        try:
            sessions = self.memory.get_all_sessions()
            current_sid = self.agent.current_session_id if self.agent else None
            for s in sessions:
                start = (s['start_time'] or '')[:16]
                last  = (s['last_time']  or '')[:16]
                label = f"{start} ~ {last}  ({s['count']} 条)  [{s['session_id'][:8]}...]"
                self.session_combo.addItem(label, userData=s['session_id'])
            # 默认选中当前 agent 会话
            if current_sid:
                for i in range(self.session_combo.count()):
                    if self.session_combo.itemData(i) == current_sid:
                        self.session_combo.setCurrentIndex(i)
                        break
        except Exception as e:
            print(f"加载会话列表失败: {e}")
        self.session_combo.blockSignals(False)
        self._on_session_selected()

    def _on_session_selected(self):
        """下拉框选择变化时刷新对话列表"""
        sid = self.session_combo.currentData()
        if sid and sid != self._current_session:
            self._current_session = sid
            self.conv_search.clear()
            self._load_conv_list()

    def _new_session(self):
        """新建会话"""
        if not self.agent:
            QMessageBox.warning(self, "提示", "无法获取 Agent 实例")
            return
        new_sid = self.agent.new_session()
        self._load_session_list()
        # 选中新会话
        for i in range(self.session_combo.count()):
            if self.session_combo.itemData(i) == new_sid:
                self.session_combo.setCurrentIndex(i)
                break
        self.refresh_stats()

    def _switch_session(self):
        """将 Agent 当前会话切换到选中的会话"""
        if not self.agent:
            QMessageBox.warning(self, "提示", "无法获取 Agent 实例")
            return
        sid = self.session_combo.currentData()
        if not sid:
            return
        self.agent.switch_session(sid)
        QMessageBox.information(self, "已切换", f"已切换到会话:\n{sid[:8]}...")

    # ======================================================= 对话历史 ===
    def _load_conv_list(self):
        self.conv_list.clear()
        self.conv_detail.clear()
        sid = self._current_session
        if not sid:
            return
        keyword = self.conv_search.text().strip()
        try:
            rows = self.memory.get_session_conversations(sid, limit=500)
            if keyword:
                rows = [r for r in rows
                        if keyword in (r['user_input'] or '')
                        or keyword in (r['ai_response'] or '')]
            for r in rows:
                preview = (r['user_input'] or '')[:60].replace("\n", " ")
                item = QListWidgetItem(f"[{(r['timestamp'] or '')[:16]}] {preview}")
                item.setData(Qt.UserRole, r)
                self.conv_list.addItem(item)
        except Exception as e:
            self.conv_detail.setPlainText(f"加载失败: {e}")

    def _show_conv_detail(self, current, _prev):
        if not current:
            return
        d = current.data(Qt.UserRole)
        self.conv_detail.setPlainText(
            f"时间: {d['timestamp']}\n"
            f"{'─' * 40}\n"
            f"用户:\n{d['user_input']}\n\n"
            f"AI:\n{d['ai_response']}"
        )

    def _clear_search(self):
        self.conv_search.clear()
        self._load_conv_list()

    def _delete_conversation(self):
        """删除选中的单条对话记录"""
        item = self.conv_list.currentItem()
        if not item:
            QMessageBox.information(self, "提示", "请先选中一条对话记录")
            return
        d = item.data(Qt.UserRole)
        preview = (d['user_input'] or '')[:40]
        reply = QMessageBox.warning(
            self, "确认删除",
            f"确认删除以下对话记录？\n\n"
            f"时间: {d['timestamp']}\n"
            f"内容: {preview}...\n\n"
            f"此操作不可撤销。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                self.memory.delete_conversation(d['id'])
                self.conv_list.takeItem(self.conv_list.row(item))
                self.conv_detail.clear()
                self.refresh_stats()
            except Exception as e:
                QMessageBox.critical(self, "删除失败", str(e))

    def _delete_session(self):
        """删除当前选中会话的全部记录"""
        sid = self._current_session
        if not sid:
            QMessageBox.information(self, "提示", "请先选择一个会话")
            return
        count = self.conv_list.count()
        reply = QMessageBox.warning(
            self, "确认删除整个会话",
            f"确认删除该会话的全部 {count} 条对话记录？\n\n"
            f"会话 ID: {sid[:8]}...\n\n"
            f"此操作不可撤销！",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                deleted = self.memory.delete_session(sid)
                self.conv_list.clear()
                self.conv_detail.clear()
                self._current_session = None
                self.refresh_stats()
                self._load_session_list()
                QMessageBox.information(self, "完成", f"已删除 {deleted} 条对话记录")
            except Exception as e:
                QMessageBox.critical(self, "删除失败", str(e))

    # =========================================================== 知识库 ===
    def search_knowledge(self):
        self.kb_list.clear()
        self.kb_detail.clear()
        query = self.kb_search.text().strip()
        if not query:
            self.kb_detail.setPlainText("请输入关键词后搜索")
            return
        try:
            results = self.memory.search_knowledge(query, k=20)
            if not results:
                self.kb_detail.setPlainText("未找到相关知识条目")
                return
            for text in results:
                item = QListWidgetItem(text[:80].replace("\n", " "))
                item.setData(Qt.UserRole, text)
                self.kb_list.addItem(item)
        except Exception as e:
            self.kb_detail.setPlainText(f"搜索失败: {e}")

    def _show_kb_detail(self, current, _prev):
        if not current:
            return
        self.kb_detail.setPlainText(current.data(Qt.UserRole))

    def _delete_kb_item(self):
        item = self.kb_list.currentItem()
        if not item:
            return
        reply = QMessageBox.question(self, "确认删除", "确认删除该知识条目？",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                self.memory.delete_knowledge_by_content(item.data(Qt.UserRole))
                self.kb_list.takeItem(self.kb_list.row(item))
                self.kb_detail.clear()
                self.refresh_stats()
            except Exception as e:
                QMessageBox.warning(self, "删除失败", str(e))

    def _show_all_knowledge(self):
        self.kb_list.clear()
        self.kb_detail.clear()
        try:
            results = self.memory.get_all_knowledge(limit=200)
            if not results:
                self.kb_detail.setPlainText("知识库暂无内容")
                return
            for text in results:
                item = QListWidgetItem(text[:80].replace("\n", " "))
                item.setData(Qt.UserRole, text)
                self.kb_list.addItem(item)
        except Exception as e:
            self.kb_detail.setPlainText(f"加载失败: {e}")

    def _add_knowledge_manual(self):
        text = self.kb_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "内容为空", "请输入要添加的知识条目内容")
            return
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        added = 0
        failed = []
        from datetime import datetime
        for line in lines:
            try:
                self.memory.add_knowledge(line, {"source": "manual", "timestamp": datetime.now().isoformat()})
                added += 1
            except Exception as e:
                failed.append(f"{line[:30]}... ({e})")
        self.kb_input.clear()
        self.refresh_stats()
        msg = f"成功添加 {added} 条知识条目"
        if failed:
            msg += f"\n失败 {len(failed)} 条:\n" + "\n".join(failed)
        QMessageBox.information(self, "添加完成", msg)
        self._show_all_knowledge()

    # ============================================================== 刷新 ===
    def _refresh_all(self):
        self.refresh_stats()
        self._load_session_list()
        if self.kb_search.text().strip():
            self.search_knowledge()

