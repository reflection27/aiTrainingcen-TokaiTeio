# -*- coding: utf-8 -*-
"""
本地MCP服务器
提供各种工具功能供东海帝王调用
"""

import json
import os
import sys
import subprocess
import platform
import datetime
from typing import Dict, List, Any, Optional


class LocalMCPServer:
    """本地MCP服务器 - 简化版本"""
    
    def __init__(self):
        self.tools = {
            "get_system_info": self.get_system_info,
            "list_files": self.list_files,
            "read_file": self.read_file,
            "write_file": self.write_file,
            "create_folder": self.create_folder,
            "get_process_list": self.get_process_list,
            "create_note": self.create_note,
            "list_notes": self.list_notes,
            "search_notes": self.search_notes,
            "calculate": self.calculate,
        }
        
    def get_system_info(self) -> str:
        """获取系统信息"""
        info = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "architecture": platform.architecture()[0],
            "processor": platform.processor(),
            "python_version": sys.version,
            "current_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return json.dumps(info, ensure_ascii=False, indent=2)
    
    def list_files(self, directory: str = ".") -> str:
        """列出指定目录的文件"""
        try:
            if not os.path.exists(directory):
                return f"目录不存在: {directory}"
            
            files = []
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                if os.path.isfile(item_path):
                    size = os.path.getsize(item_path)
                    files.append(f"文件: {item} ({size} bytes)")
                elif os.path.isdir(item_path):
                    files.append(f"目录: {item}/")
            
            return f"目录 {directory} 的内容:\n" + "\n".join(files)
        except Exception as e:
            return f"列出文件失败: {str(e)}"
    
    def read_file(self, file_path: str) -> str:
        """读取文件内容"""
        try:
            if not os.path.exists(file_path):
                return f"文件不存在: {file_path}"
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return f"文件 {file_path} 的内容:\n{content}"
        except Exception as e:
            return f"读取文件失败: {str(e)}"
    
    def write_file(self, file_path: str, content: str) -> str:
        """写入文件内容"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return f"文件 {file_path} 写入成功"
        except Exception as e:
            return f"写入文件失败: {str(e)}"
    
    def create_folder(self, folder_path: str) -> str:
        """创建文件夹"""
        try:
            # 检查文件夹是否已存在
            if os.path.exists(folder_path):
                if os.path.isdir(folder_path):
                    return f"文件夹 {folder_path} 已存在"
                else:
                    return f"路径 {folder_path} 已存在，但不是文件夹"
            
            # 创建文件夹（包括父目录）
            os.makedirs(folder_path, exist_ok=True)
            
            return f"文件夹 {folder_path} 创建成功"
        except Exception as e:
            return f"创建文件夹失败: {str(e)}"
    
    def get_process_list(self) -> str:
        """获取进程列表"""
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    "tasklist", 
                    capture_output=True, 
                    text=True
                )
            else:
                result = subprocess.run(
                    "ps aux", 
                    capture_output=True, 
                    text=True
                )
            
            return f"进程列表:\n{result.stdout}"
        except Exception as e:
            return f"获取进程列表失败: {str(e)}"
    
    def create_note(self, title: str, content: str, filename_format: str = "timestamp", location: str = None) -> str:
        """创建笔记"""
        try:
            # 确定保存位置
            if location:
                # 用户指定了位置
                if location.lower() in ["d盘", "d:", "d:/", "d:\\"]:
                    save_dir = "D:/"
                elif location.lower() in ["c盘", "c:", "c:/", "c:\\"]:
                    save_dir = "C:/"
                elif location.lower() in ["e盘", "e:", "e:/", "e:\\"]:
                    save_dir = "E:/"
                elif location.lower() in ["f盘", "f:", "f:/", "f:\\"]:
                    save_dir = "F:/"
                else:
                    # 尝试解析其他路径
                    save_dir = location
            else:
                # 默认保存到notes目录
                save_dir = "notes"
            
            # 确保目录存在
            os.makedirs(save_dir, exist_ok=True)
            
            # 根据文件名格式设置生成文件名
            if filename_format == "simple":
                # 简单格式：直接使用标题作为文件名
                filename = os.path.join(save_dir, f"{title}.txt")
                
                # 检查文件是否已存在，如果存在则添加数字后缀
                counter = 1
                original_filename = filename
                while os.path.exists(filename):
                    name_without_ext = original_filename[:-4]  # 移除.txt
                    filename = f"{name_without_ext}_{counter}.txt"
                    counter += 1
            else:
                # 时间戳格式：使用时间戳+标题
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = os.path.join(save_dir, f"{timestamp}_{title}.txt")
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"标题: {title}\n")
                f.write(f"创建时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"内容:\n{content}\n")
            
            return f"笔记已创建: {filename}"
        except Exception as e:
            return f"创建笔记失败: {str(e)}"
    
    def list_notes(self) -> str:
        """列出所有笔记"""
        try:
            notes_dir = "notes"
            if not os.path.exists(notes_dir):
                return "没有找到笔记目录"
            
            notes = []
            for file in os.listdir(notes_dir):
                if file.endswith('.txt'):
                    file_path = os.path.join(notes_dir, file)
                    stat = os.stat(file_path)
                    notes.append(f"{file} (大小: {stat.st_size} bytes, 修改时间: {datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')})")
            
            if notes:
                return "笔记列表:\n" + "\n".join(notes)
            else:
                return "没有找到笔记"
        except Exception as e:
            return f"列出笔记失败: {str(e)}"
    
    def search_notes(self, keyword: str) -> str:
        """搜索笔记内容"""
        try:
            notes_dir = "notes"
            if not os.path.exists(notes_dir):
                return "没有找到笔记目录"
            
            results = []
            for file in os.listdir(notes_dir):
                if file.endswith('.txt'):
                    file_path = os.path.join(notes_dir, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if keyword.lower() in content.lower():
                                results.append(f"找到关键词 '{keyword}' 在文件: {file}")
                    except:
                        continue
            
            if results:
                return "搜索结果:\n" + "\n".join(results)
            else:
                return f"没有找到包含关键词 '{keyword}' 的笔记"
        except Exception as e:
            return f"搜索笔记失败: {str(e)}"
    
    def calculate(self, expression: str) -> str:
        """计算数学表达式"""
        try:
            # 安全计算，只允许基本数学运算
            allowed_chars = set('0123456789+-*/(). ')
            if not all(c in allowed_chars for c in expression):
                return "表达式包含不允许的字符"
            
            result = eval(expression)
            return f"计算结果: {expression} = {result}"
        except Exception as e:
            return f"计算失败: {str(e)}"
    
    def call_tool(self, tool_name: str, **kwargs) -> str:
        """调用工具"""
        if tool_name in self.tools:
            try:
                return self.tools[tool_name](**kwargs)
            except Exception as e:
                return f"调用工具失败: {str(e)}"
        else:
            return f"工具不存在: {tool_name}"
    
    def list_tools(self) -> List[str]:
        """列出可用工具"""
        return list(self.tools.keys())
    
    def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """获取工具信息"""
        if tool_name in self.tools:
            return {
                "name": tool_name,
                "description": self.tools[tool_name].__doc__ or "无描述"
            }
        return {}
    

if __name__ == "__main__":
    server = LocalMCPServer()
    print("本地MCP服务器已启动")
    print("可用工具:", server.list_tools())
    print("\n测试工具调用:")
    print("系统信息:", server.call_tool("get_system_info"))
