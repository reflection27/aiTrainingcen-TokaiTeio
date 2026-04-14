"""
尾巴下垂角度调参工具
用法：python test_tail.py

上/下方向键：调整下垂角度（每次 ±5°）
Shift + 上/下：精细调整（±1°）
R：重置为 0°（rest pose）
Q：退出并打印当前角度（填入 action_happy.gd 的 DROOP_DEG）
"""

import sys
import socket
import json

HOST = "127.0.0.1"
PORT = 9999


def send(cmd: dict) -> str:
    try:
        with socket.create_connection((HOST, PORT), timeout=3) as s:
            s.sendall((json.dumps(cmd) + "\n").encode())
            return s.recv(1024).decode().strip()
    except Exception as e:
        return f"ERROR: {e}"


def apply(angle: float):
    resp = send({"cmd": "tail_droop", "angle": angle})
    print(f"\r角度: {angle:+.1f}°   {resp}    ", end="", flush=True)


def main():
    # 尝试 Windows 和 Unix 的键盘读取
    angle = 0.0
    apply(angle)

    try:
        import msvcrt  # Windows

        print("\n[Windows模式] 上/下=±5°  u/d=±1°  r=重置  q=退出")
        while True:
            ch = msvcrt.getch()
            if ch == b'\xe0':           # 方向键前缀
                ch2 = msvcrt.getch()
                if ch2 == b'H':         # 上
                    angle += 5.0
                elif ch2 == b'P':       # 下
                    angle -= 5.0
            elif ch in (b'u', b'U'):
                angle += 1.0
            elif ch in (b'd', b'D'):
                angle -= 1.0
            elif ch in (b'r', b'R'):
                angle = 0.0
            elif ch in (b'q', b'Q'):
                print(f"\n最终角度: {angle:+.1f}°")
                print(f"将 action_happy.gd 中 reset_bone_pose 后添加:")
                print(f"  const DROOP_DEG := {angle:.1f}")
                break
            else:
                continue
            apply(angle)

    except ImportError:
        import tty
        import termios

        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        print("\n[Unix模式] 上/下方向键=±5°  u/d=±1°  r=重置  q=退出")
        try:
            tty.setraw(fd)
            while True:
                ch = sys.stdin.read(1)
                if ch == '\x1b':
                    seq = sys.stdin.read(2)
                    if seq == '[A':     # 上
                        angle += 5.0
                    elif seq == '[B':   # 下
                        angle -= 5.0
                elif ch in ('u', 'U'):
                    angle += 1.0
                elif ch in ('d', 'D'):
                    angle -= 1.0
                elif ch in ('r', 'R'):
                    angle = 0.0
                elif ch in ('q', 'Q'):
                    print(f"\n最终角度: {angle:+.1f}°")
                    print(f"将 action_happy.gd 中 reset_bone_pose 后添加:")
                    print(f"  const DROOP_DEG := {angle:.1f}")
                    break
                else:
                    continue
                apply(angle)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


if __name__ == "__main__":
    main()
