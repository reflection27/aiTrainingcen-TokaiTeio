"""
与 Godot 桌宠通信的 TCP 客户端
在 improved_ai_agent.py 中 import 并使用 GodotPetClient 单例
"""

import json
import socket
import threading
import logging

logger = logging.getLogger(__name__)


class GodotPetClient:
    HOST = "127.0.0.1"
    PORT = 9999

    def __init__(self):
        self._sock: socket.socket | None = None
        self._lock = threading.Lock()
        self._connected = False

    def connect(self) -> bool:
        with self._lock:
            if self._connected:
                return True
            try:
                self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._sock.settimeout(2.0)
                self._sock.connect((self.HOST, self.PORT))
                self._sock.settimeout(None)
                self._connected = True
                logger.info("GodotPetClient: 已连接桌宠 %s:%d", self.HOST, self.PORT)
                return True
            except (ConnectionRefusedError, TimeoutError, OSError) as e:
                logger.debug("GodotPetClient: 桌宠未运行 — %s", e)
                self._sock = None
                self._connected = False
                return False

    def disconnect(self) -> None:
        with self._lock:
            if self._sock:
                try:
                    self._sock.close()
                except OSError:
                    pass
            self._sock = None
            self._connected = False

    def send(self, cmd: dict) -> bool:
        """发送命令，自动重连一次"""
        if not self._connected:
            self.connect()
        with self._lock:
            if not self._connected or self._sock is None:
                return False
            try:
                msg = (json.dumps(cmd, ensure_ascii=False) + "\n").encode("utf-8")
                self._sock.sendall(msg)
                return True
            except (BrokenPipeError, ConnectionResetError, OSError):
                self._sock = None
                self._connected = False
                logger.warning("GodotPetClient: 连接断开")
                return False

    # --- 便捷方法 ---

    def idle(self) -> None:
        self.send({"cmd": "idle"})

    def talking(self) -> None:
        self.send({"cmd": "talking"})

    def wave(self) -> None:
        self.send({"cmd": "wave"})

    def expression(self, preset: str, duration: float = 0.3) -> None:
        """preset: normal/happy/smile/angry/sad/surprised/smug/dere/excited"""
        self.send({"cmd": "expression", "preset": preset, "duration": duration})
        self.send({"cmd": "play_action", "action": preset})

    def move(self, x: int, y: int) -> None:
        self.send({"cmd": "move", "x": x, "y": y})

    def hide(self) -> None:
        self.send({"cmd": "hide"})

    def show(self) -> None:
        self.send({"cmd": "show"})


# 全局单例
pet = GodotPetClient()
