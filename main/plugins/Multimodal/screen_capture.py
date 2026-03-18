"""
屏幕捕获模块
用于捕获屏幕内容并保存为图片
"""

import os
from datetime import datetime
from typing import Optional, Tuple
import pyautogui
from PIL import Image

class ScreenCapture:
    """屏幕捕获类"""

    def __init__(self, save_dir: str = "temp_screenshots"):
        """
        初始化屏幕捕获类

        Args:
            save_dir: 截图保存目录
        """
        self.save_dir = save_dir
        self._ensure_save_dir()

    def _ensure_save_dir(self):
        """确保截图保存目录存在"""
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

    def capture_full_screen(self, save_path: Optional[str] = None) -> str:
        """
        捕获整个屏幕

        Args:
            save_path: 保存路径，如果为None则自动生成

        Returns:
            截图保存路径
        """
        if save_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = os.path.join(self.save_dir, f"screen_{timestamp}.png")

        # 使用pyautogui捕获屏幕
        screenshot = pyautogui.screenshot()
        screenshot.save(save_path)

        return save_path

    def capture_region(
        self,
        region: Tuple[int, int, int, int],
        save_path: Optional[str] = None
    ) -> str:
        """
        捕获屏幕指定区域

        Args:
            region: 区域坐标 (x, y, width, height)
            save_path: 保存路径，如果为None则自动生成

        Returns:
            截图保存路径
        """
        if save_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = os.path.join(self.save_dir, f"region_{timestamp}.png")

        # 使用pyautogui捕获指定区域
        screenshot = pyautogui.screenshot(region=region)
        screenshot.save(save_path)

        return save_path

    def capture_active_window(self, save_path: Optional[str] = None) -> str:
        """
        捕获当前活动窗口

        Args:
            save_path: 保存路径，如果为None则自动生成

        Returns:
            截图保存路径
        """
        if save_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = os.path.join(self.save_dir, f"window_{timestamp}.png")

        # 获取活动窗口
        active_window = pyautogui.getActiveWindow()

        # 捕获窗口区域
        region = (
            active_window.left,
            active_window.top,
            active_window.width,
            active_window.height
        )

        screenshot = pyautogui.screenshot(region=region)
        screenshot.save(save_path)

        return save_path

    def capture_and_resize(
        self,
        max_width: int = 1024,
        max_height: int = 1024,
        save_path: Optional[str] = None
    ) -> str:
        """
        捕获屏幕并调整大小

        Args:
            max_width: 最大宽度
            max_height: 最大高度
            save_path: 保存路径，如果为None则自动生成

        Returns:
            截图保存路径
        """
        if save_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = os.path.join(self.save_dir, f"resized_{timestamp}.png")

        # 捕获屏幕
        screenshot = pyautogui.screenshot()

        # 调整大小，保持宽高比
        width, height = screenshot.size
        ratio = min(max_width / width, max_height / height)
        new_size = (int(width * ratio), int(height * ratio))
        resized_screenshot = screenshot.resize(new_size, Image.LANCZOS)

        resized_screenshot.save(save_path)

        return save_path
