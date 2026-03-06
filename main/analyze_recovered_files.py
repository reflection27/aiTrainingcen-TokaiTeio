
import os
import sys

# 所有恢复的文件
recovered_dir = "recovered_files"
files = os.listdir(recovered_dir)

# 分析每个文件
for file_name in files:
    file_path = os.path.join(recovered_dir, file_name)
    file_size = os.path.getsize(file_path)

    # 读取文件的前几个字节来判断文件类型
    with open(file_path, 'rb') as f:
        header = f.read(16)

    # 判断文件类型
    if header.startswith(b'SQLite format 3'):
        file_type = "SQLite 数据库"
    elif header.startswith(b'\x00\x00\x00\x00'):
        file_type = "可能是 Python 编译文件 (.pyc)"
    elif header.startswith(b'\x00\x00\x00'):
        file_type = "可能是 Python 编译文件 (.pyc)"
    else:
        # 尝试解码为文本
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read(100)
            if content.startswith('# -*- coding: utf-8 -*-') or content.startswith('#'):
                file_type = "Python 源代码文件 (.py)"
            else:
                file_type = "文本文件"
        except UnicodeDecodeError:
            file_type = "二进制文件"

    print(f"文件: {file_name}")
    print(f"大小: {file_size / 1024 / 1024:.2f} MB")
    print(f"类型: {file_type}")
    print("-" * 50)

    # 确保输出立即显示
    sys.stdout.flush()
