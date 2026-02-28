# -*- coding: utf-8 -*-
"""
东海帝王AI担当 - 主程序入口
重构后的模块化版本
"""

import sys
import os
import threading
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont, QPalette, QColor
from PyQt5.QtCore import Qt, QObject, pyqtSignal

# 导入自定义模块
from config import load_config
from improved_ai_agent import ImprovedAIAgent
from main_window import AIAgentApp

# 全局变量，用于存储主窗口实例
main_window_instance = None

class TextInputRequestHandler(BaseHTTPRequestHandler):
    """文本输入请求处理器，用于接收STT程序发送的文本"""
    
    def _send_json_response(self, status_code, data):
        """发送JSON响应"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def _send_cors_headers(self):
        """发送CORS头"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    
    def do_OPTIONS(self):
        """处理OPTIONS请求"""
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()
    
    def do_GET(self):
        """处理GET请求"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/api/status':
            # 状态API
            self._send_json_response(200, {"status": "ready"})
        else:
            self._send_json_response(404, {"error": "Not found"})
    
    def do_POST(self):
        """处理POST请求"""
        global main_window_instance
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/api/text_input':
            # 文本输入API
            try:
                # 获取请求数据
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                
                # 解析JSON数据
                data = json.loads(post_data.decode('utf-8'))
                text = data.get("text", "")
                
                if text and text.strip():
                    print(f"📥 接收到文本: {text.strip()}")
                    # 将文本发送到主窗口
                    if main_window_instance:
                        # 使用QApplication.postEvent将事件发送到主线程
                        from PyQt5.QtCore import QEvent
                        class TextEvent(QEvent):
                            EVENT_TYPE = QEvent.User + 1
                            
                            def __init__(self, text):
                                super().__init__(TextEvent.EVENT_TYPE)
                                self.text = text
                        
                        # 将事件发送到主窗口
                        print(f"📤 发送事件到主窗口: {text.strip()}")
                        QApplication.postEvent(main_window_instance, TextEvent(text.strip()))
                        
                        self._send_json_response(200, {"status": "success", "message": "文本已接收"})
                    else:
                        self._send_json_response(500, {"error": "主窗口未初始化"})
                else:
                    self._send_json_response(400, {"error": "未提供有效文本"})
            except Exception as e:
                print(f"❌ 处理文本输入请求失败: {str(e)}")
                import traceback
                traceback.print_exc()
                self._send_json_response(500, {"error": f"处理请求失败: {str(e)}"})
        else:
            self._send_json_response(404, {"error": "Not found"})
    
    def log_message(self, format, *args):
        """重写日志方法，减少输出"""
        pass

def start_http_server(port=5000):
    """启动HTTP服务器"""
    global main_window_instance
    try:
        server = HTTPServer(('127.0.0.1', port), TextInputRequestHandler)
        print(f"✅ HTTP服务器已启动，监听地址: http://127.0.0.1:{port}")
        server.serve_forever()
    except Exception as e:
        print(f"❌ 启动HTTP服务器失败: {str(e)}")

def main():
    """主程序入口"""
    try:
        print("🚀 程序启动中...")

        # 创建Qt应用程序
        print("📱 创建Qt应用程序...")
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
        print("⚙️ 加载配置...")
        config = load_config()

        # 创建主窗口
        print("🖥️ 创建主窗口...")
        window = AIAgentApp(config)
        print("✅ 主窗口创建成功")
        window.show()
        print("✅ 主窗口已显示")
        
        # 保存主窗口实例
        global main_window_instance
        main_window_instance = window
        
        # 禁用麦克风按钮，因为现在通过HTTP接口接收STT文本
        if hasattr(window, 'record_btn'):
            window.record_btn.setEnabled(False)
            window.record_btn.setToolTip("语音识别已通过STT服务器处理")
            print("✅ 麦克风按钮已禁用，使用HTTP接口接收STT文本")
        
        # 重写主窗口的event方法，处理文本输入事件
        original_event = window.event
        
        def custom_event(event):
            # 处理自定义文本输入事件
            print(f"🔍 收到事件，类型: {event.type()}")
            if hasattr(event, 'EVENT_TYPE'):
                print(f"🔍 事件有EVENT_TYPE属性: {event.EVENT_TYPE}")
            if hasattr(event, 'text'):
                print(f"🔍 事件有text属性: {event.text}")
            if hasattr(event, 'EVENT_TYPE') and event.type() == event.EVENT_TYPE:
                print(f"📝 接收到自定义事件，文本: {event.text}")
                # 将文本设置到输入框
                window.input_edit.setText(event.text)
                print(f"✅ 文本已设置到输入框: {event.text}")
                print(f"📄 输入框当前文本: {window.input_edit.text()}")

                # 使用QTimer延迟调用send_message，以便文本能够显示在UI上
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(100, window.send_message)
                print(f"📤 已安排延迟调用send_message方法")
                return True
            # 其他事件交给原始event方法处理
            return original_event(event)
        
        window.event = custom_event

        # 启动HTTP服务器（在新线程中）
        print("🌐 启动HTTP服务器...")
        http_thread = threading.Thread(target=start_http_server, daemon=True)
        http_thread.start()

        # 运行应用程序
        print("🔄 启动事件循环...")
        sys.exit(app.exec_())
    except Exception as e:
        print(f"❌ 程序发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        input("按回车键退出...")

if __name__ == "__main__":
    main()
