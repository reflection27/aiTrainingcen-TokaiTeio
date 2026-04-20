"""
表情 + 动作 TCP 测试工具
用法：
  python test_expressions.py            # 交互模式（方向键切换）
  python test_expressions.py happy      # 直接发送一个表情
  python test_expressions.py --all      # 自动依次播放所有表情（每个停留3秒）
"""

import sys
import socket
import json
import time

HOST = "127.0.0.1"
PORT = 9999

PRESETS = ["normal", "happy", "smile", "angry",
           "sad", "surprised", "smug", "dere", "excited"]


def send(cmd: dict) -> str:
    try:
        with socket.create_connection((HOST, PORT), timeout=3) as s:
            s.sendall((json.dumps(cmd) + "\n").encode())
            resp = s.recv(1024).decode().strip()
            return resp
    except Exception as e:
        return f"ERROR: {e}"


def apply(preset: str) -> None:
    r1 = send({"cmd": "expression", "preset": preset})
    r2 = send({"cmd": "play_action",  "preset": preset})
    print(f"  expression → {r1}")
    print(f"  play_action → {r2}")


def run_all() -> None:
    for p in PRESETS:
        print(f"\n[{PRESETS.index(p)+1}/{len(PRESETS)}] {p}")
        apply(p)
        time.sleep(3)
    print("\n全部播完。")


def run_interactive() -> None:
    try:
        import msvcrt  # Windows
        def getch():
            ch = msvcrt.getwch()
            if ch in ('\x00', '\xe0'):   # 功能键前缀
                ch2 = msvcrt.getwch()
                return ch2
            return ch
    except ImportError:
        import tty, termios  # Unix
        def getch():
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                ch = sys.stdin.read(1)
                if ch == '\x1b':
                    sys.stdin.read(1)   # [
                    ch = sys.stdin.read(1)
                return ch
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)

    idx = 0
    rot_y = 0.0
    print("← → 切换表情  ↑ ↓ Y轴旋转/前后转身(±5°)  Space 重播动作  R 重置旋转  Q 退出")
    print(f"\n当前: [{idx+1}/{len(PRESETS)}] {PRESETS[idx]}  旋转: {rot_y:+.1f}°")
    apply(PRESETS[idx])

    while True:
        ch = getch()
        if ch in ('M', 'C'):    # 右箭头（Windows: M / Unix: C）
            idx = (idx + 1) % len(PRESETS)
            print(f"\n切换 → [{idx+1}/{len(PRESETS)}] {PRESETS[idx]}  旋转: {rot_y:+.1f}°")
            apply(PRESETS[idx])
        elif ch in ('K', 'D'):  # 左箭头（Windows: K / Unix: D）
            idx = (idx - 1 + len(PRESETS)) % len(PRESETS)
            print(f"\n切换 → [{idx+1}/{len(PRESETS)}] {PRESETS[idx]}  旋转: {rot_y:+.1f}°")
            apply(PRESETS[idx])
        elif ch in ('H', 'A'):  # 上箭头（Windows: H / Unix: A）
            rot_y += 5.0
            send({"cmd": "rotate_y", "angle": rot_y})
            print(f"\r旋转: {rot_y:+.1f}°   ", end="", flush=True)
        elif ch in ('P', 'B'):  # 下箭头（Windows: P / Unix: B）
            rot_y -= 5.0
            send({"cmd": "rotate_y", "angle": rot_y})
            print(f"\r旋转: {rot_y:+.1f}°   ", end="", flush=True)
        elif ch == ' ':
            print(f"\n重播动作: {PRESETS[idx]}")
            send({"cmd": "play_action", "preset": PRESETS[idx]})
        elif ch in ('r', 'R'):
            rot_y = 0.0
            send({"cmd": "rotate_y", "angle": 0.0})
            print(f"\r旋转重置: {rot_y:+.1f}°   ", end="", flush=True)
        elif ch.lower() == 'q':
            print("\n退出。")
            break


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args:
        run_interactive()
    elif args[0] == "--all":
        run_all()
    elif args[0] in PRESETS:
        print(f"发送: {args[0]}")
        apply(args[0])
    else:
        print(f"未知表情: {args[0]}")
        print(f"可用: {', '.join(PRESETS)}")
