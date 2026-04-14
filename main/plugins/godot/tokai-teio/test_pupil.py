"""
瞳孔/眼睛 blend shape 测试工具
← → 切换选项，↑ ↓ 调节数值，R 重置，Q 退出
"""

import sys
import socket
import json
import msvcrt

HOST = "127.0.0.1"
PORT = 9999

SHAPES = [
    "Eye_24_L(PupilA)[M_Face]",
    "Eye_24_R(PupilA)[M_Face]",
    "Eye_25_L(PupilB)[M_Face]",
    "Eye_25_R(PupilB)[M_Face]",
    "Eye_26_L(PupilC)[M_Face]",
    "Eye_26_R(PupilC)[M_Face]",
]

values = {s: 0.0 for s in SHAPES}
idx = 0
STEP = 0.1


def send(cmd: dict) -> None:
    try:
        with socket.create_connection((HOST, PORT), timeout=3) as s:
            s.sendall((json.dumps(cmd) + "\n").encode())
            s.recv(1024)
    except Exception as e:
        print(f"  ERROR: {e}")


def set_shape(name: str, value: float) -> None:
    value = round(max(0.0, min(1.0, value)), 2)
    values[name] = value
    send({"cmd": "blend_shape", "name": name, "value": value})


def reset_all() -> None:
    for s in SHAPES:
        values[s] = 0.0
        send({"cmd": "blend_shape", "name": s, "value": 0.0})


def print_state() -> None:
    print("\033[2J\033[H", end="")  # 清屏
    print("瞳孔测试  ← → 切换  ↑ ↓ 调值  R 重置  Q 退出\n")
    for i, s in enumerate(SHAPES):
        marker = "▶" if i == idx else " "
        bar = "█" * int(values[s] * 20)
        print(f"  {marker} {s:<40} {values[s]:.2f}  {bar}")


print_state()

while True:
    ch = msvcrt.getwch()
    if ch in ('\x00', '\xe0'):
        ch2 = msvcrt.getwch()
        if ch2 == 'M':    # 右
            idx = (idx + 1) % len(SHAPES)
        elif ch2 == 'K':  # 左
            idx = (idx - 1 + len(SHAPES)) % len(SHAPES)
        elif ch2 == 'H':  # 上
            set_shape(SHAPES[idx], values[SHAPES[idx]] + STEP)
        elif ch2 == 'P':  # 下
            set_shape(SHAPES[idx], values[SHAPES[idx]] - STEP)
    elif ch.lower() == 'r':
        reset_all()
    elif ch.lower() == 'q':
        print("\n退出。")
        break

    print_state()
