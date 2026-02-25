# -*- coding: utf-8 -*-
"""
东海帝王AI担当 - 主程序入口
重构后的模块化版本
"""

import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont, QPalette, QColor
from PyQt5.QtCore import Qt

# 导入自定义模块
from config import load_config
from improved_ai_agent import ImprovedAIAgent
from main_window import AIAgentApp

def main():
    """主程序入口"""
    # 创建Qt应用程序
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle("Fusion")
    
    # 创建调色板
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(245, 245, 245))  # 浅灰色背景
    palette.setColor(QPalette.WindowText, QColor(51, 51, 51))  # 深灰色文本
    palette.setColor(QPalette.Base, QColor(255, 255, 255))  # 白色基础色
    palette.setColor(QPalette.AlternateBase, QColor(245, 245, 245))  # 浅灰色交替基础色
    palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 220))  # 浅黄色工具提示基础色
    palette.setColor(QPalette.ToolTipText, QColor(0, 0, 0))  # 黑色工具提示文本
    palette.setColor(QPalette.Text, QColor(51, 51, 51))  # 文本颜色
    palette.setColor(QPalette.Button, QColor(240, 240, 240))  # 浅灰色按钮
    palette.setColor(QPalette.ButtonText, QColor(51, 51, 51))  # 深灰色按钮文本
    palette.setColor(QPalette.BrightText, QColor(255, 0, 0))  # 红色亮色文本
    palette.setColor(QPalette.Highlight, QColor(74, 144, 226))  # 蓝色高亮色
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))  # 白色高亮文本
    
    app.setPalette(palette)
    
    # 设置字体
    font = QFont("Microsoft YaHei UI", 10)
    app.setFont(font)
    
    # 加载配置
    config = load_config()
    
    # 创建主窗口
    window = AIAgentApp(config)
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

