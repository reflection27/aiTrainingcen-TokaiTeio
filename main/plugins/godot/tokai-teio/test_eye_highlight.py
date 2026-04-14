"""
眼睛高光实时调节工具（UV 版）
← → 切换参数   ↑ ↓ 调节数值   R 重置   Q 退出并打印最终值
"""

import sys, socket, json, msvcrt

HOST, PORT = "127.0.0.1", 9999

# (参数名, 默认值, 最小, 最大, 步长)
PARAMS = [
    ("hl1_uv_x",    0.35, 0.0, 1.0, 0.02),
    ("hl1_uv_y",    0.30, 0.0, 1.0, 0.02),
    ("hl1_radius",  0.07, 0.01, 0.3, 0.01),
    ("hl1_strength",0.85, 0.0, 1.0, 0.05),
    ("hl2_uv_x",    0.65, 0.0, 1.0, 0.02),
    ("hl2_uv_y",    0.70, 0.0, 1.0, 0.02),
    ("hl2_radius",  0.035,0.01, 0.2, 0.005),
    ("hl2_strength",0.40, 0.0, 1.0, 0.05),
]

values  = {p[0]: p[1] for p in PARAMS}
default = {p[0]: p[1] for p in PARAMS}
mins    = {p[0]: p[2] for p in PARAMS}
maxs    = {p[0]: p[3] for p in PARAMS}
steps   = {p[0]: p[4] for p in PARAMS}
idx = 0


def send(param, value):
    try:
        with socket.create_connection((HOST, PORT), timeout=3) as s:
            s.sendall((json.dumps({"cmd": "eye_highlight", "param": param, "value": value}) + "\n").encode())
            s.recv(1024)
    except Exception as e:
        print(f"  ERROR: {e}")


def reset_all():
    for p in PARAMS:
        values[p[0]] = p[1]
        send(p[0], p[1])


def print_state():
    print("\033[2J\033[H", end="")
    print("高光调节(UV)  ← → 切换  ↑ ↓ 调值  R 重置  Q 退出\n")
    labels = {
        "hl1_uv_x":    "主高光 左←→右",
        "hl1_uv_y":    "主高光 上←→下",
        "hl1_radius":  "主高光 大小",
        "hl1_strength":"主高光 亮度",
        "hl2_uv_x":    "副高光 左←→右",
        "hl2_uv_y":    "副高光 上←→下",
        "hl2_radius":  "副高光 大小",
        "hl2_strength":"副高光 亮度",
    }
    for i, p in enumerate(PARAMS):
        name = p[0]
        v = values[name]
        marker = "▶" if i == idx else " "
        pct = (v - mins[name]) / (maxs[name] - mins[name])
        bar = "█" * int(pct * 24)
        print(f"  {marker} {labels[name]:<14} {v:.3f}  {bar}")


print_state()

while True:
    ch = msvcrt.getwch()
    if ch in ('\x00', '\xe0'):
        ch2 = msvcrt.getwch()
        name = PARAMS[idx][0]
        if ch2 == 'M':
            idx = (idx + 1) % len(PARAMS)
        elif ch2 == 'K':
            idx = (idx - 1 + len(PARAMS)) % len(PARAMS)
        elif ch2 == 'H':
            values[name] = round(min(maxs[name], values[name] + steps[name]), 4)
            send(name, values[name])
        elif ch2 == 'P':
            values[name] = round(max(mins[name], values[name] - steps[name]), 4)
            send(name, values[name])
    elif ch.lower() == 'r':
        reset_all()
    elif ch.lower() == 'q':
        print("\n\n最终参数：")
        for p in PARAMS:
            print(f"  {p[0]}: {values[p[0]]}")
        break
    print_state()
