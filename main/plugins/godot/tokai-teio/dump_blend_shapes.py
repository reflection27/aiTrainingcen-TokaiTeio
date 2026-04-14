"""
从 .glb 文件直接解析所有 BlendShape（Morph Target）名字，无需打开 Godot。
用法：python dump_blend_shapes.py
"""

import json
import struct
import sys
from pathlib import Path

GLB_PATH = Path(__file__).parent / "titled.glb"


def read_glb_json(path: Path) -> dict:
    with open(path, "rb") as f:
        # GLB header: magic(4) version(4) length(4)
        magic, version, length = struct.unpack("<III", f.read(12))
        assert magic == 0x46546C67, "不是有效的 GLB 文件"

        # 第一个 chunk 必须是 JSON
        chunk_len, chunk_type = struct.unpack("<II", f.read(8))
        assert chunk_type == 0x4E4F534A, "第一个 chunk 不是 JSON"
        json_bytes = f.read(chunk_len)
        return json.loads(json_bytes.decode("utf-8"))


def main():
    if not GLB_PATH.exists():
        print(f"找不到文件: {GLB_PATH}")
        sys.exit(1)

    gltf = read_glb_json(GLB_PATH)
    meshes = gltf.get("meshes", [])

    all_names: list[str] = []
    for mesh in meshes:
        for prim in mesh.get("primitives", []):
            targets_names = prim.get("extras", {}).get("targetNames", [])
            # 部分导出器把名字放在 mesh.extras
            if not targets_names:
                targets_names = mesh.get("extras", {}).get("targetNames", [])
            all_names.extend(targets_names)

    # 去重保序
    seen = set()
    unique = [x for x in all_names if not (x in seen or seen.add(x))]

    print(f"===== BlendShape 完整列表（{len(unique)} 个）=====")
    for name in sorted(unique):
        print(name)

    print("\n--- 眼睛相关 ---")
    keywords = ["eye", "hikari", "hilight", "highlight", "pupil", "瞳", "高光"]
    for name in sorted(unique):
        if any(k in name.lower() for k in keywords):
            print(name)


if __name__ == "__main__":
    main()
