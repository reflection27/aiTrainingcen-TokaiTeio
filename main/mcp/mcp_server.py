# -*- coding: utf-8 -*-
"""
MCP服务器
工具注册与调度框架，具体工具在 tools/ 目录中实现
"""

from typing import Any, Callable, Dict, List


class MCPServer:
    """MCP服务器 - 工具注册与调度"""

    def __init__(self):
        # {tool_name: {"fn": callable, "description": str, "params": list}}
        self._registry: Dict[str, Dict[str, Any]] = {}

    def register(self, name: str, fn: Callable, description: str = "", params: List[str] = None):
        """注册工具"""
        self._registry[name] = {
            "fn": fn,
            "description": description,
            "params": params or [],
        }

    def call_tool(self, tool_name: str, **kwargs) -> str:
        """调用已注册的工具"""
        if tool_name not in self._registry:
            return f"工具不存在: {tool_name}"
        try:
            return self._registry[tool_name]["fn"](**kwargs)
        except TypeError as e:
            return f"参数错误: {e}"
        except Exception as e:
            return f"工具调用失败: {e}"

    def list_tools(self) -> List[str]:
        """返回所有已注册工具名"""
        return list(self._registry.keys())

    def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """返回工具描述信息"""
        if tool_name not in self._registry:
            return {}
        entry = self._registry[tool_name]
        return {
            "name": tool_name,
            "description": entry["description"],
            "params": entry["params"],
        }

    def list_all_info(self) -> List[Dict[str, Any]]:
        """返回所有工具的描述信息"""
        return [self.get_tool_info(n) for n in self._registry]


def create_server() -> MCPServer:
    """创建并初始化服务器，加载所有工具"""
    from main.mcp.tools import register_all
    server = MCPServer()
    register_all(server)
    return server
