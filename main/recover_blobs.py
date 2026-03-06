
import os
import subprocess
import sys

# 所有 dangling blob 的哈希值
blobs = [
    "3848455bdccc8a25a4848a1facba790c4d9c6e14",
    "7f70bc3a345892cf89bcdd82edd066bb0d0042dd",
    "c341e66ec6000ae3a25c93b6fe1c4d49246abe4d",
    "5642f418b261875ca6958fe1768f5b22e16d2a72",
    "7bba8485fc19af38a1fb44b81a0387a97280f31d",
    "6cd430e29c0b9d2f0f1dea62ed40af7ac3d65164",
    "ba2463ec827758abb34ef9185b74ec497ae45898",
    "80e52c2928c0b184f768a4bc8cae1c12c7a31e7e",
    "198e878ca54c00bb02d7e09b57fcf37634c359e4",
    "b88610611352612917ab7d366e41611602ad558b"
]

# 创建恢复目录
recovery_dir = "recovered_files"
if not os.path.exists(recovery_dir):
    os.makedirs(recovery_dir)

# 恢复每个 blob
for blob in blobs:
    try:
        # 获取 blob 内容（二进制模式）
        result = subprocess.run(
            ["git", "show", blob],
            capture_output=True,
            check=True
        )

        if result.stdout is None:
            print(f"警告: {blob} 的内容为空")
            continue

        # 尝试检测编码并解码
        try:
            content = result.stdout.decode('utf-8')
        except UnicodeDecodeError:
            try:
                content = result.stdout.decode('gbk')
            except UnicodeDecodeError:
                # 如果都失败，使用latin-1（不会失败，但可能不是最佳编码）
                content = result.stdout.decode('latin-1')

        # 将内容写入文件
        output_file = os.path.join(recovery_dir, f"{blob}.txt")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"已恢复: {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"恢复 {blob} 失败: {e}")
    except Exception as e:
        print(f"恢复 {blob} 时发生错误: {e}")

print("\n所有 blob 已恢复到 recovered_files 目录")
