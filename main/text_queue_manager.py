
# -*- coding: utf-8 -*-
"""
流式文本队列管理器
用于处理流式文本，按标点符号切分，并按顺序发送到TTS合成
"""

import re
import queue
import threading
import time
from typing import Optional, Callable
from PyQt5.QtCore import QObject, pyqtSignal


class TextQueueManager(QObject):
    """流式文本队列管理器"""

    # 定义信号
    text_ready = pyqtSignal(str)  # 文本准备就绪，可以发送到TTS
    synthesis_complete = pyqtSignal()  # 语音合成完成

    def __init__(self, tts_manager=None):
        super().__init__()
        self.tts_manager = tts_manager
        self.text_queue = queue.Queue()  # 文本队列
        self.is_processing = False  # 是否正在处理
        self.stop_flag = False  # 停止标志
        self.buffer = ""  # 文本缓冲区
        self.worker_thread = None  # 工作线程
        self.lock = threading.Lock()  # 线程锁
        self.in_brackets = False  # 是否在括号内
        self.bracket_depth = 0  # 括号嵌套深度

    def add_streaming_text(self, text: str):
        """添加流式文本到队列"""
        with self.lock:
            # 检查文本是否以标点符号结尾
            # 如果以标点符号结尾，说明是一个完整的句子或短语，直接发送到 TTS
            # 注意：不检查括号（）和()，因为它们通常表示动作描述
            print(f"🔍 检查文本: {text}")
            print(f"🔍 当前缓冲区: {self.buffer}")
            if text:
                print(f"🔍 最后一个字符: {text[-1]}")
                print(f"🔍 最后一个字符的Unicode编码: {ord(text[-1])}")
            
            # 检查文本中是否包含标点符号
            # 这是为了避免当标点符号和括号同时出现时，标点符号滞留在缓冲区中
            if text and not self.in_brackets:
                # 检查文本中是否包含标点符号
                for char in text:
                    if char in '，。！？、；："''【】,.!?:;"''[]':
                        # 找到标点符号的位置
                        punct_pos = text.find(char)
                        # 将标点符号及其前面的文本添加到缓冲区
                        text_before_punct = text[:punct_pos+1]
                        self.buffer += text_before_punct
                        # 将缓冲区中的文本发送到TTS
                        full_text = self.buffer
                        print(f"✅ 检测到标点符号: {char}")
                        print(f"✅ 检测到标点符号，直接发送到 TTS: {full_text}")
                        # 检查句子是否已经在队列中（避免重复）
                        queue_contents = list(self.text_queue.queue)
                        if full_text not in queue_contents:
                            self.text_queue.put(full_text)
                            print(f"📤 添加句子到队列: {full_text}")
                            # 发射信号，通知有文本可以处理
                            self.text_ready.emit(full_text)
                        else:
                            print(f"⏭️ 句子已在队列中，跳过: {full_text}")
                        # 清空缓冲区
                        self.buffer = ""
                        # 更新文本，移除已处理的部分
                        text = text[punct_pos+1:]
                        # 只处理第一个标点符号，然后跳出循环
                        break

            # 检查文本中是否包含括号
            if text:

                # 再检查文本中是否包含反括号
                for char in text:
                    if char in '）)':
                        if self.in_brackets:
                            self.bracket_depth -= 1
                            print(f"🔍 检测到反括号: {char}, 深度: {self.bracket_depth}")
                            if self.bracket_depth == 0:
                                self.in_brackets = False
                                print(f"✅ 括号对匹配，删除括号及其内容")
                                # 删除缓冲区中的括号及其内容
                                # 找到第一个正括号的位置
                                start_pos = self.buffer.rfind('（')
                                if start_pos == -1:
                                    start_pos = self.buffer.rfind('(')
                                if start_pos != -1:
                                    self.buffer = self.buffer[:start_pos]
                                    print(f"📝 删除括号及其内容后，缓冲区: {self.buffer}")
                                # 从文本中移除反括号，避免它被添加到缓冲区
                                text = text.replace(char, '', 1)
                                print(f"📝 从文本中移除反括号: {text}")
                # 再检查文本中是否包含正括号
                for char in text:
                    if char in '（(':
                        if not self.in_brackets:
                            # 遇到正括号时，如果缓冲区内有文本，先发送并清空缓冲区
                            if self.buffer.strip():
                                # 检查缓冲区是否以标点符号结尾，如果是，则包含标点符号一起发送
                                buffer_to_send = self.buffer
                                if buffer_to_send and buffer_to_send[-1] in '，。！？、；："''【】,.!?:;"''[]':
                                    print(f"✅ 检测到正括号，缓冲区以标点符号结尾: {buffer_to_send[-1]}")
                                else:
                                    print(f"✅ 检测到正括号，发送缓冲区中的文本: {buffer_to_send}")
                                # 检查句子是否已经在队列中（避免重复）
                                queue_contents = list(self.text_queue.queue)
                                if buffer_to_send not in queue_contents:
                                    self.text_queue.put(buffer_to_send)
                                    print(f"📤 添加句子到队列: {buffer_to_send}")
                                    # 发射信号，通知有文本可以处理
                                    self.text_ready.emit(buffer_to_send)
                                else:
                                    print(f"⏭️ 句子已在队列中，跳过: {buffer_to_send}")
                                # 清空缓冲区
                                self.buffer = ""
                            self.in_brackets = True
                            self.bracket_depth = 1
                            print(f"🔍 检测到正括号: {char}")
                        else:
                            self.bracket_depth += 1
                            print(f"🔍 检测到嵌套正括号: {char}, 深度: {self.bracket_depth}")
            
            # 如果在括号内，不处理标点符号
            if self.in_brackets:
                print(f"⏳ 在括号内，不处理标点符号")
                # 检查文本中是否包含反括号
                if '）' in text or ')' in text:
                    # 如果包含反括号，只添加反括号之前的内容到缓冲区
                    punct_pos = text.find('）') if '）' in text else text.find(')')
                    text_before_punct = text[:punct_pos]
                    self.buffer += text_before_punct
                    print(f"📝 添加流式文本到缓冲区（反括号前）: {text_before_punct[:50]}...")
                    print(f"📝 当前缓冲区内容: {self.buffer[:100]}...")
                    # 反括号会在后续的括号处理逻辑中被处理
                else:
                    # 将新文本添加到缓冲区
                    self.buffer += text
                    print(f"📝 添加流式文本到缓冲区: {text[:50]}...")
                    print(f"📝 当前缓冲区内容: {self.buffer[:100]}...")
                return
            
            # 检查文本是否以标点符号结尾
            if text and text[-1] in '，。！？、；："''【】,.!?:;"\'\'[]':
                print(f"✅ 检测到标点符号结尾: {text[-1]}")
                # 确保标点符号总是与前面的文本一起发送到TTS
                # 将缓冲区中的文本和新文本组合在一起，确保标点符号包含在内
                # 不对text进行任何截断或修改，确保标点符号被包含
                # 确保text包含完整的标点符号，不进行任何截断
                full_text = self.buffer + text
                print(f"✅ 检测到标点符号结尾，直接发送到 TTS: {full_text}")
                # 检查句子是否已经在队列中（避免重复）
                queue_contents = list(self.text_queue.queue)
                if full_text not in queue_contents:
                    self.text_queue.put(full_text)
                    print(f"📤 添加句子到队列: {full_text}")
                    # 发射信号，通知有文本可以处理
                    self.text_ready.emit(full_text)
                else:
                    print(f"⏭️ 句子已在队列中，跳过: {full_text}")
                # 清空缓冲区
                self.buffer = ""
            else:
                # 将新文本添加到缓冲区
                self.buffer += text
                print(f"📝 添加流式文本到缓冲区: {text[:50]}...")
                print(f"📝 当前缓冲区内容: {self.buffer[:100]}...")
                # 确保添加到缓冲区的文本包含完整的标点符号，不进行任何截断

            # 支持英文标点：,.!?:;"'()[]




    def finalize_text(self):
        """完成文本输入，将缓冲区中剩余的文本添加到队列"""
        with self.lock:
            if self.buffer.strip():
                self.text_queue.put(self.buffer)
                print(f"📤 添加剩余文本到队列: {self.buffer}")
                self.text_ready.emit(self.buffer)
                self.buffer = ""

    def start_processing(self):
        """开始处理文本队列"""
        if self.is_processing:
            return

        self.is_processing = True
        self.stop_flag = False

        # 启动工作线程
        self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.worker_thread.start()
        print("✅ 文本队列处理已启动")

    def stop_processing(self):
        """停止处理文本队列"""
        self.stop_flag = True
        if self.worker_thread:
            self.worker_thread.join(timeout=1.0)
        self.is_processing = False
        print("⏸️ 文本队列处理已停止")

    def _process_queue(self):
        """处理文本队列的工作线程"""
        print(f"🔍 文本队列处理线程已启动, tts_manager={self.tts_manager is not None}")
        while not self.stop_flag:
            try:
                # 从队列中获取文本，设置超时以避免阻塞
                text = self.text_queue.get(timeout=0.1)
                print(f"🔍 从队列中获取文本: {text[:50] if text else None}...")

                if text and self.tts_manager:
                    # 发送到TTS合成
                    print(f"🎤 发送文本到TTS: {text[:50]}...")
                    self.tts_manager.speak_text(text)

                    # 不等待TTS完成，直接处理下一个文本
                    # 这样可以实现边显示文本边合成语音的效果
                elif text and not self.tts_manager:
                    print(f"⚠️ tts_manager为None，无法发送文本到TTS: {text[:50]}...")

            except queue.Empty:
                continue
            except Exception as e:
                print(f"❌ 处理文本队列失败: {e}")
                import traceback
                traceback.print_exc()

    def clear_queue(self):
        """清空文本队列"""
        with self.lock:
            while not self.text_queue.empty():
                try:
                    self.text_queue.get_nowait()
                except queue.Empty:
                    break
            self.buffer = ""
            print("🗑️ 文本队列已清空")

    def get_queue_size(self) -> int:
        """获取队列大小"""
        return self.text_queue.qsize()

    def is_queue_empty(self) -> bool:
        """检查队列是否为空"""
        return self.text_queue.empty()
