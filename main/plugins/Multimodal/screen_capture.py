"""
屏幕捕获模块
用于捕获屏幕内容并保存为图片
"""

import os
from datetime import datetime
from typing import Optional, Tuple, List
import pyautogui
from PIL import Image

try:
    import win32gui
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

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

    def list_windows(self) -> List[str]:
        """
        列出所有可见窗口标题（用于查找游戏窗口的实际标题）

        Returns:
            窗口标题列表
        """
        if not WIN32_AVAILABLE:
            raise RuntimeError("win32gui 未安装，请执行: pip install pywin32")

        windows = []

        def enum_callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    windows.append(title)

        win32gui.EnumWindows(enum_callback, None)
        return windows

    def _find_window_hwnd(self, title_keyword: str) -> Optional[int]:
        """
        按标题关键词查找窗口句柄（大小写不敏感，部分匹配）

        Args:
            title_keyword: 窗口标题关键词

        Returns:
            窗口句柄，找不到返回 None
        """
        if not WIN32_AVAILABLE:
            raise RuntimeError("win32gui 未安装，请执行: pip install pywin32")

        found = []

        def enum_callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title_keyword.lower() in title.lower():
                    found.append(hwnd)

        win32gui.EnumWindows(enum_callback, None)
        return found[0] if found else None

    def capture_window_by_title(
        self,
        title_keyword: str,
        save_path: Optional[str] = None
    ) -> str:
        """
        按窗口标题截图（部分匹配，大小写不敏感）

        Args:
            title_keyword: 窗口标题关键词，如 "ウマ娘"、"Minecraft"
            save_path: 保存路径，如果为 None 则自动生成

        Returns:
            截图保存路径

        Raises:
            ValueError: 找不到匹配窗口，或窗口区域无效
        """
        if save_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = os.path.join(self.save_dir, f"window_{timestamp}.png")

        hwnd = self._find_window_hwnd(title_keyword)
        if hwnd is None:
            raise ValueError(f"找不到标题包含 '{title_keyword}' 的窗口，"
                             f"可调用 list_windows() 查看当前所有窗口")

        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top

        if width <= 0 or height <= 0:
            raise ValueError(f"窗口区域无效: left={left}, top={top}, "
                             f"right={right}, bottom={bottom}")

        screenshot = pyautogui.screenshot(region=(left, top, width, height))
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
