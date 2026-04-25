# -*- coding: utf-8 -*-
"""
MCP客户端
通过 LocalMCPClient 直接调用本地 MCPServer
"""

from typing import Any, Dict, List


class LocalMCPClient:
    """本地MCP客户端，直接调用 MCPServer"""

    def __init__(self):
        from main.mcp.mcp_server import create_server
        self._server = create_server()

    async def call_tool(self, tool_name: str, **kwargs) -> str:
        """调用工具"""
        return self._server.call_tool(tool_name, **kwargs)

    async def list_tools(self) -> List[str]:
        """获取可用工具列表"""
        return self._server.list_tools()

    async def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """获取工具信息"""
        return self._server.get_tool_info(tool_name)

    async def list_all_info(self) -> List[Dict[str, Any]]:
        """获取所有工具信息"""
        return self._server.list_all_info()
