# -*- coding: utf-8 -*-
import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
                               QPushButton, QLabel, QComboBox, QGroupBox,
                               QFormLayout, QMessageBox, QSlider, QCheckBox,
                               QScrollArea, QWidget, QFileDialog)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QColor

from core.config import save_config

_ENV_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")


def _load_env() -> dict:
    """从 .env 文件读取 key=value 键值对"""
    result = {}
    if not os.path.exists(_ENV_FILE):
        return result
    with open(_ENV_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                result[k.strip()] = v.strip()
    return result


def _save_env(updates: dict):
    """将更新后的键值对写回 .env，保留注释行"""
    lines = []
    if os.path.exists(_ENV_FILE):
        with open(_ENV_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()

    written = set()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k = stripped.partition("=")[0].strip()
            if k in updates:
                new_lines.append(f"{k}={updates[k]}\n")
                written.add(k)
                continue
        new_lines.append(line if line.endswith("\n") else line + "\n")

    for k, v in updates.items():
        if k not in written:
            new_lines.append(f"{k}={v}\n")

    with open(_ENV_FILE, "w", encoding="utf-8") as f:
        f.writelines(new_lines)


class SettingsDialog(QDialog):
    """设置对话框"""

    def __init__(self, config, parent=None, transparency_callback=None):
        super().__init__(parent)
        self.config = config
        self.transparency_callback = transparency_callback
        self.setWindowTitle("设置")
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMinMaxButtonsHint)
        self.setModal(True)
        self.drag_pos = None

        palette = QPalette()
        palette.setColor(QPalette.Window,      QColor(245, 245, 245))
        palette.setColor(QPalette.WindowText,  QColor(30, 30, 30))
        palette.setColor(QPalette.Base,        QColor(255, 255, 255))
        palette.setColor(QPalette.Text,        QColor(30, 30, 30))
        palette.setColor(QPalette.Button,      QColor(240, 240, 240))
        palette.setColor(QPalette.ButtonText,  QColor(30, 30, 30))
        palette.setColor(QPalette.Highlight,   QColor(76, 163, 255))
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        self.setPalette(palette)

        self.setStyleSheet("""
            QDialog { background-color: #f5f5f5; }
            QGroupBox {
                background-color: #f5f5f5; color: #1e1e1e;
                border: 1px solid #cccccc; border-radius: 5px;
                margin-top: 10px; padding-top: 10px; font-weight: bold;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QLineEdit, QComboBox {
                background-color: #ffffff; color: #1e1e1e;
                border: 1px solid #cccccc; border-radius: 3px; padding: 3px;
            }
            QPushButton {
                background-color: #e0e0e0; color: #1e1e1e;
                border: 1px solid #cccccc; border-radius: 3px; padding: 5px;
            }
            QPushButton:hover  { background-color: #d0d0d0; }
            QPushButton:pressed { background-color: #c0c0c0; }
            QCheckBox { color: #1e1e1e; }
            QSlider::groove:horizontal {
                border: 1px solid #cccccc; height: 8px;
                background: #ffffff; border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #4ca3ff; border: 1px solid #cccccc;
                width: 18px; margin: -5px 0; border-radius: 9px;
            }
            QWidget { background-color: #f5f5f5; color: #1e1e1e; }
            QScrollArea { background-color: #f5f5f5; border: none; }
        """)

        self.setMinimumWidth(520)
        self.setMaximumWidth(520)
        self.resize(520, 555)

        self._init_ui()

    def _init_ui(self):
        env = _load_env()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # ── API 设置 ──────────────────────────────────────────────
        api_group = QGroupBox("API 设置")
        api_layout = QFormLayout()

        self.deepseek_key_edit = QLineEdit()
        self.deepseek_key_edit.setText(env.get("DEEPSEEK_API_KEY", self.config.get("deepseek_key", "")))
        self.deepseek_key_edit.setPlaceholderText("输入 DeepSeek API 密钥")
        self.deepseek_key_edit.setEchoMode(QLineEdit.Password)
        api_layout.addRow("DeepSeek 密钥:", self.deepseek_key_edit)

        self.glm_key_edit = QLineEdit()
        self.glm_key_edit.setText(env.get("GLM4V_API_KEY", self.config.get("glm4v_key", "")))
        self.glm_key_edit.setPlaceholderText("输入 GLM-4V API 密钥")
        self.glm_key_edit.setEchoMode(QLineEdit.Password)
        api_layout.addRow("GLM-4V 密钥:", self.glm_key_edit)

        api_group.setLayout(api_layout)
        layout.addWidget(api_group)

        # ── 模型设置 ──────────────────────────────────────────────
        model_group = QGroupBox("模型设置")
        model_layout = QFormLayout()

        self.chat_model_combo = QComboBox()
        self.chat_model_combo.addItems(["deepseek-v4-flash"])
        current = self.config.get("selected_model", "deepseek-v4-flash")
        if self.chat_model_combo.findText(current) >= 0:
            self.chat_model_combo.setCurrentText(current)
        model_layout.addRow("AI 模型:", self.chat_model_combo)

        self.memory_model_combo = QComboBox()
        self.memory_model_combo.addItems(["deepseek-v4-flash"])
        mem_model = self.config.get("memory_summary_model", "deepseek-v4-flash")
        if self.memory_model_combo.findText(mem_model) >= 0:
            self.memory_model_combo.setCurrentText(mem_model)
        model_layout.addRow("记忆系统模型:", self.memory_model_combo)

        self.thinking_mode_checkbox = QCheckBox("启用思考模式（deepseek-v4-flash 深度推理，响应较慢）")
        self.thinking_mode_checkbox.setChecked(self.config.get("thinking_mode", False))
        model_layout.addRow("", self.thinking_mode_checkbox)

        self.lock_model_checkbox = QCheckBox("锁定模型选择（防止误操作）")
        self.lock_model_checkbox.setChecked(self.config.get("lock_model", False))
        self.lock_model_checkbox.stateChanged.connect(self._on_lock_model_changed)
        model_layout.addRow("", self.lock_model_checkbox)
        self._on_lock_model_changed(self.lock_model_checkbox.checkState())

        model_group.setLayout(model_layout)
        layout.addWidget(model_group)

        # ── 界面设置 ──────────────────────────────────────────────
        ui_group = QGroupBox("界面设置")
        ui_layout = QFormLayout()

        self.transparency_slider = QSlider(Qt.Horizontal)
        self.transparency_slider.setMinimum(50)
        self.transparency_slider.setMaximum(100)
        t_val = self.config.get("window_transparency", 100)
        self.transparency_slider.setValue(t_val)
        self.transparency_label = QLabel(f"{t_val}%")
        self.transparency_slider.valueChanged.connect(self._on_transparency_changed)
        t_layout = QHBoxLayout()
        t_layout.addWidget(self.transparency_slider)
        t_layout.addWidget(self.transparency_label)
        ui_layout.addRow("窗口透明度:", t_layout)

        ui_group.setLayout(ui_layout)
        layout.addWidget(ui_group)

        # ── 语音合成设置 ──────────────────────────────────────────
        tts_group = QGroupBox("语音合成 (TTS) 设置")
        tts_layout = QFormLayout()

        self.tts_enabled_checkbox = QCheckBox("启用语音合成")
        self.tts_enabled_checkbox.setChecked(self.config.get("tts_enabled", False))
        tts_layout.addRow("TTS 功能:", self.tts_enabled_checkbox)

        sovits_group = QGroupBox("GPT-SoVITS 设置")
        sovits_layout = QFormLayout()

        self.gpt_sovits_api_type_combo = QComboBox()
        self.gpt_sovits_api_type_combo.addItems(["gradio", "api_v2"])
        idx = self.gpt_sovits_api_type_combo.findText(self.config.get("gpt_sovits_api_type", "gradio"))
        if idx >= 0:
            self.gpt_sovits_api_type_combo.setCurrentIndex(idx)
        self.gpt_sovits_api_type_combo.currentTextChanged.connect(self._on_api_type_changed)
        sovits_layout.addRow("API 类型:", self.gpt_sovits_api_type_combo)

        self.gpt_sovits_api_url_edit = QLineEdit()
        self.gpt_sovits_api_url_edit.setText(self.config.get("gpt_sovits_api_url", "http://127.0.0.1:9880"))
        sovits_layout.addRow("API 地址:", self.gpt_sovits_api_url_edit)

        ref_row = QHBoxLayout()
        self.gpt_sovits_ref_audio_edit = QLineEdit()
        self.gpt_sovits_ref_audio_edit.setText(self.config.get("gpt_sovits_ref_audio", ""))
        self.gpt_sovits_ref_audio_edit.setPlaceholderText("选择参考音频文件")
        ref_btn = QPushButton("浏览...")
        ref_btn.clicked.connect(self._browse_ref_audio)
        ref_row.addWidget(self.gpt_sovits_ref_audio_edit)
        ref_row.addWidget(ref_btn)
        sovits_layout.addRow("参考音频:", ref_row)

        t2s_row = QHBoxLayout()
        self.gpt_sovits_t2s_weights_edit = QLineEdit()
        self.gpt_sovits_t2s_weights_edit.setText(self.config.get("gpt_sovits_t2s_weights", ""))
        self.gpt_sovits_t2s_weights_edit.setPlaceholderText("T2S 模型权重文件")
        t2s_btn = QPushButton("浏览...")
        t2s_btn.clicked.connect(self._browse_t2s_weights)
        t2s_row.addWidget(self.gpt_sovits_t2s_weights_edit)
        t2s_row.addWidget(t2s_btn)
        sovits_layout.addRow("T2S 权重:", t2s_row)

        vits_row = QHBoxLayout()
        self.gpt_sovits_vits_weights_edit = QLineEdit()
        self.gpt_sovits_vits_weights_edit.setText(self.config.get("gpt_sovits_vits_weights", ""))
        self.gpt_sovits_vits_weights_edit.setPlaceholderText("VITS 模型权重文件")
        vits_btn = QPushButton("浏览...")
        vits_btn.clicked.connect(self._browse_vits_weights)
        vits_row.addWidget(self.gpt_sovits_vits_weights_edit)
        vits_row.addWidget(vits_btn)
        sovits_layout.addRow("VITS 权重:", vits_row)

        apply_btn = QPushButton("应用模型权重")
        apply_btn.setStyleSheet("""
            QPushButton { background-color: #4CAF50; color: white; border: none;
                border-radius: 5px; padding: 6px 14px; font-weight: bold; }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:pressed { background-color: #3d8b40; }
        """)
        apply_btn.clicked.connect(self._apply_model_weights)
        sovits_layout.addRow("", apply_btn)

        sovits_group.setLayout(sovits_layout)
        tts_layout.addRow(sovits_group)
        tts_group.setLayout(tts_layout)
        layout.addWidget(tts_group)

        # ── 保存 / 取消 ───────────────────────────────────────────
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("保存设置")
        save_btn.clicked.connect(self._save_settings)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        layout.addStretch(1)

        content.setLayout(layout)
        scroll.setWidget(content)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)

    # ── 槽函数 ────────────────────────────────────────────────────

    def _on_transparency_changed(self, value):
        self.transparency_label.setText(f"{value}%")
        if self.transparency_callback:
            try:
                self.transparency_callback(value)
            except Exception:
                pass

    def _on_lock_model_changed(self, state):
        locked = (state == Qt.Checked)
        self.chat_model_combo.setEnabled(not locked)
        self.memory_model_combo.setEnabled(not locked)

    def _on_api_type_changed(self, api_type):
        if api_type == "gradio":
            self.gpt_sovits_api_url_edit.setText("http://127.0.0.1:9872")
        elif api_type == "api_v2":
            self.gpt_sovits_api_url_edit.setText("http://127.0.0.1:9880")

    def _browse_ref_audio(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择参考音频", "",
            "音频文件 (*.wav *.mp3 *.flac *.ogg);;All Files (*)")
        if path:
            self.gpt_sovits_ref_audio_edit.setText(path)

    def _browse_t2s_weights(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 T2S 权重", "", "权重文件 (*.ckpt);;All Files (*)")
        if path:
            self.gpt_sovits_t2s_weights_edit.setText(path)

    def _browse_vits_weights(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 VITS 权重", "", "权重文件 (*.pth);;All Files (*)")
        if path:
            self.gpt_sovits_vits_weights_edit.setText(path)

    def _save_settings(self):
        deepseek_key = self.deepseek_key_edit.text().strip()
        glm_key = self.glm_key_edit.text().strip()

        # 双向同步 .env
        _save_env({"DEEPSEEK_API_KEY": deepseek_key, "GLM4V_API_KEY": glm_key})

        # 同步 config
        self.config["deepseek_key"]          = deepseek_key
        self.config["glm4v_key"]             = glm_key
        self.config["selected_model"]        = self.chat_model_combo.currentText()
        self.config["thinking_mode"]         = self.thinking_mode_checkbox.isChecked()
        self.config["memory_summary_model"]  = self.memory_model_combo.currentText()
        self.config["lock_model"]            = self.lock_model_checkbox.isChecked()
        self.config["window_transparency"]   = self.transparency_slider.value()
        self.config["tts_enabled"]           = self.tts_enabled_checkbox.isChecked()
        self.config["tts_engine"]            = "gpt_sovits"
        self.config["gpt_sovits_api_type"]   = self.gpt_sovits_api_type_combo.currentText()
        self.config["gpt_sovits_api_url"]    = self.gpt_sovits_api_url_edit.text()
        self.config["gpt_sovits_ref_audio"]  = self.gpt_sovits_ref_audio_edit.text()
        self.config["gpt_sovits_t2s_weights"] = self.gpt_sovits_t2s_weights_edit.text()
        self.config["gpt_sovits_vits_weights"] = self.gpt_sovits_vits_weights_edit.text()

        save_config(self.config)
        QMessageBox.information(self, "设置", "设置已保存")
        self.accept()

    def _apply_model_weights(self):
        if self.gpt_sovits_api_type_combo.currentText() != "api_v2":
            QMessageBox.warning(self, "警告", "只有 api_v2 类型支持动态切换模型权重")
            return

        t2s = self.gpt_sovits_t2s_weights_edit.text()
        vits = self.gpt_sovits_vits_weights_edit.text()
        if not t2s and not vits:
            QMessageBox.warning(self, "警告", "请先设置模型权重路径")
            return

        parent = self.parent()
        while parent and not hasattr(parent, "agent"):
            parent = parent.parent()
        if not parent:
            QMessageBox.warning(self, "错误", "无法获取 AI Agent 实例")
            return

        try:
            parent.agent.config["gpt_sovits_t2s_weights"] = t2s
            parent.agent.config["gpt_sovits_vits_weights"] = vits
            result = parent.agent.apply_tts_model_weights()
            if result:
                QMessageBox.information(self, "成功", "模型权重应用成功")
            else:
                QMessageBox.warning(self, "失败", "模型权重应用失败，请查看控制台日志")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"应用模型权重时发生异常: {e}")

    # ── 拖拽支持 ──────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_pos:
            self.move(event.globalPos() - self.drag_pos)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = None
