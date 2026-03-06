
import os
import shutil

# 恢复文件映射
file_mappings = {
    "5642f418b261875ca6958fe1768f5b22e16d2a72.txt": "text_queue_manager.py",
    "7f70bc3a345892cf89bcdd82edd066bb0d0042dd.txt": "gpt_sovits_unified.py",
    "b88610611352612917ab7d366e41611602ad558b.txt": "improved_ai_agent.py",
    "7bba8485fc19af38a1fb44b81a0387a97280f31d.txt": "memory_lake.db",
}

# 恢复目录
recovered_dir = "recovered_files"

# 恢复每个文件
for recovered_file, target_file in file_mappings.items():
    recovered_path = os.path.join(recovered_dir, recovered_file)
    target_path = target_file

    # 检查恢复文件是否存在
    if not os.path.exists(recovered_path):
        print(f"警告: 恢复文件不存在: {recovered_path}")
        continue

    # 检查目标文件是否已存在
    if os.path.exists(target_path):
        # 创建备份
        backup_path = f"{target_path}.backup"
        shutil.copy2(target_path, backup_path)
        print(f"已创建备份: {backup_path}")

    # 复制恢复的文件到目标位置
    shutil.copy2(recovered_path, target_path)
    print(f"已恢复: {target_file}")

print("\n所有文件已恢复完成！")
