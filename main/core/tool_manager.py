
# -*- coding: utf-8 -*-
"""
工具管理模块
借鉴bopang2的插件化架构，实现模块化的工具管理
"""

from typing import Dict, Callable, Optional, List
from abc import ABC, abstractmethod
import asyncio
from functools import wraps

class BaseTool(ABC):
    """工具基类"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    async def execute(self, **kwargs) -> str:
        """执行工具"""
        pass

    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "name": self.name,
            "description": self.description
        }

class ToolManager:
    """工具管理器（借鉴bopang2的模块化架构）"""

    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        self.tool_categories: Dict[str, List[str]] = {
            "system": [],
            "search": [],
            "media": [],
            "file": [],
            "entertainment": []
        }

    def register_tool(self, tool: BaseTool, category: str = "system"):
        """注册工具"""
        self.tools[tool.name] = tool
        if category in self.tool_categories:
            self.tool_categories[category].append(tool.name)

    async def execute_tool(self, tool_name: str, **kwargs) -> str:
        """执行工具"""
        if tool_name not in self.tools:
            return f"未找到工具: {tool_name}"

        try:
            return await self.tools[tool_name].execute(**kwargs)
        except Exception as e:
            return f"工具执行失败: {str(e)}"

    def get_tools_by_category(self, category: str) -> List[Dict]:
        """获取指定类别的工具"""
        tool_names = self.tool_categories.get(category, [])
        return [self.tools[name].to_dict() for name in tool_names]

    def list_all_tools(self) -> Dict[str, List[Dict]]:
        """列出所有工具"""
        return {
            category: self.get_tools_by_category(category)
            for category in self.tool_categories
        }

# 示例工具实现
class WeatherTool(BaseTool):
    """天气查询工具"""

    def __init__(self):
        super().__init__(
            name="weather",
            description="查询天气信息"
        )

    async def execute(self, location: str = "北京") -> str:
        """查询天气"""
        # 这里可以调用实际的天气API
        await asyncio.sleep(0.5)  # 模拟API调用
        return f"今天{location}的天气是晴天，温度25°C"

class SearchTool(BaseTool):
    """搜索工具"""

    def __init__(self):
        super().__init__(
            name="search",
            description="网络搜索"
        )

    async def execute(self, query: str) -> str:
        """执行搜索"""
        # 这里可以调用实际的搜索API
        await asyncio.sleep(1.0)  # 模拟API调用
        return f"搜索结果: 关于'{query}'的相关信息..."

class MusicTool(BaseTool):
    """音乐工具"""

    def __init__(self):
        super().__init__(
            name="music",
            description="音乐推荐"
        )

    async def execute(self, genre: str = "流行") -> str:
        """推荐音乐"""
        await asyncio.sleep(0.3)  # 模拟处理
        return f"为您推荐{genre}风格的音乐: 《晴天》《稻香》《告白气球》"

# 工具装饰器
def tool(category: str = "system"):
    """工具注册装饰器"""
    def decorator(cls):
        original_init = cls.__init__

        @wraps(original_init)
        def new_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            # 自动注册到全局工具管理器
            if not hasattr(cls, "_manager"):
                cls._manager = ToolManager()
            cls._manager.register_tool(self, category)

        cls.__init__ = new_init
        return cls

    return decorator

# 使用示例
if __name__ == "__main__":
    async def main():
        # 创建工具管理器
        manager = ToolManager()

        # 注册工具
        manager.register_tool(WeatherTool(), "system")
        manager.register_tool(SearchTool(), "search")
        manager.register_tool(MusicTool(), "media")

        # 列出所有工具
        print("所有工具:", manager.list_all_tools())

        # 执行工具
        result = await manager.execute_tool("weather", location="上海")
        print("天气查询结果:", result)

    asyncio.run(main())
