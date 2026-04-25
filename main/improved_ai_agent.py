
# -*- coding: utf-8 -*-
"""
改进的AI Agent核心模块
整合异步处理和模块化架构，借鉴bopang2的快速响应机制
"""

import asyncio
from typing import Dict, Optional, List
from openai import AsyncOpenAI
from improved_memory import ImprovedMemorySystem
from tool_manager import ToolManager, BaseTool

class ImprovedAIAgent:
    """改进的AI Agent（整合异步处理和模块化架构）"""

    def __init__(self, config: Dict):
        self.config = config
        self.name = "东海帝王"
        self.role = "赛马娘世界观特雷森学园的一名学生赛马娘"

        # 初始化异步记忆系统
        self.memory = ImprovedMemorySystem()
        # 添加memory_lake属性以兼容现有代码
        self.memory_lake = self.memory

        # 初始化工具管理器
        self.tool_manager = ToolManager()
        self._register_default_tools()
        # 添加mcp_tools属性以兼容现有代码
        self.mcp_tools = self.tool_manager

        # 初始化异步OpenAI客户端
        api_key = config.get("deepseek_key", "")
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com/v1"
        )

        # 初始化TTS管理器
        self.tts_manager = None
        self.tts_engine = None
        self._init_tts_manager(config)

        # 响应缓存
        self.response_cache: Dict[str, str] = {}

        # 会话管理
        self.active_sessions: Dict[str, Dict] = {}
        # 添加developer_mode属性以兼容现有代码
        self.developer_mode = False
        # 添加app_count属性以兼容现有代码
        self.app_count = 0
        # 添加session_conversations属性以兼容现有代码
        self.session_conversations: List[Dict] = []

    def _init_tts_manager(self, config: Dict):
        """初始化TTS管理器"""
        try:
            tts_engine = config.get("tts_engine", "azure")  # 默认使用Azure TTS
            if tts_engine == "gpt_sovits":
                # 使用GPT-SoVITS TTS
                gpt_sovits_api_url = config.get("gpt_sovits_api_url", "http://127.0.0.1:9872")
                ref_audio_path = config.get("gpt_sovits_ref_audio", "")
                print(f"🔍 初始化GPT-SoVITS TTS管理器，API地址: {gpt_sovits_api_url}, 参考音频: {ref_audio_path}")
                from gpt_sovits_simple import SimpleGPTSoVITS
                self.tts_manager = SimpleGPTSoVITS(gpt_sovits_api_url, ref_audio_path)
                self.tts_engine = "gpt_sovits"
                print(f"✅ GPT-SoVITS TTS管理器初始化成功，可用性: {self.tts_manager.is_available()}")
            else:
                # 使用Azure TTS
                azure_key = config.get("azure_tts_key", "")
                azure_region = config.get("azure_region", "eastasia")
                if azure_key:
                    from tts_manager import TTSManager
                    self.tts_manager = TTSManager(azure_key, azure_region)
                    self.tts_engine = "azure"
                    print("✅ Azure TTS管理器初始化成功")
                else:
                    self.tts_manager = None
                    self.tts_engine = None
                    print("ℹ️ 未配置TTS密钥，TTS功能已禁用")
        except Exception as e:
            print(f"⚠️ TTS管理器初始化失败: {str(e)}")
            self.tts_manager = None
            self.tts_engine = None

    def _register_default_tools(self):
        """注册默认工具"""
        from tool_manager import WeatherTool, SearchTool, MusicTool

        self.tool_manager.register_tool(WeatherTool(), "system")
        self.tool_manager.register_tool(SearchTool(), "search")
        self.tool_manager.register_tool(MusicTool(), "media")

    async def process_command_async(
        self,
        user_input: str,
        user_id: str = "default",
        session_id: str = "default"
    ) -> str:
        """异步处理用户命令"""
        # 检查缓存
        cache_key = f"{session_id}:{user_input}"
        if cache_key in self.response_cache:
            return self.response_cache[cache_key]

        # 获取上下文
        context = await self.memory.get_context_async(session_id, user_input)

        # 构建完整的prompt
        full_prompt = self._build_prompt(user_input, context)

        # 调用AI
        response = await self._call_ai_async(full_prompt)

        # 保存对话
        await self.memory.save_conversation_async(
            user_input,
            response,
            user_id,
            session_id
        )

        # 缓存响应
        self.response_cache[cache_key] = response

        return response

    def _build_prompt(self, user_input: str, context: Dict) -> str:
        """构建完整的prompt"""
        prompt_parts = []

        # 添加系统提示
        prompt_parts.append(f"你是{self.name}，{self.role}。")

        # 添加知识库内容
        if context["knowledge"]:
            prompt_parts.append("\n[相关知识]")
            prompt_parts.extend(context["knowledge"])

        # 添加历史对话
        if context["history"]:
            prompt_parts.append("\n[历史对话]")
            for h in reversed(context["history"][-5:]):  # 只取最近5条
                prompt_parts.append(f"用户: {h['user']}")
                prompt_parts.append(f"助手: {h['assistant']}")

        # 添加当前输入
        prompt_parts.append(f"\n当前对话:\n用户: {user_input}\n助手:")

        return "\n".join(prompt_parts)

    async def _call_ai_async(self, prompt: str) -> str:
        """异步调用AI"""
        try:
            model = self.config.get("selected_model", "deepseek-chat")

            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2048,
                temperature=0.7
            )

            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"处理出错: {str(e)}"

    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return f"""你是{self.name}，{self.role}。
你活泼开朗、充满活力，热爱奔跑和比赛。
请以东海帝王的思考方式和说话习惯来交流！"""

    async def execute_tool_async(
        self,
        tool_name: str,
        **kwargs
    ) -> str:
        """异步执行工具"""
        return await self.tool_manager.execute_tool(tool_name, **kwargs)

    def clear_cache(self):
        """清除响应缓存"""
        self.response_cache.clear()

    async def get_session_context(self, session_id: str) -> Dict:
        """获取会话上下文"""
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = {
                "start_time": asyncio.get_event_loop().time(),
                "message_count": 0
            }

        self.active_sessions[session_id]["message_count"] += 1

        return self.active_sessions[session_id]

    async def add_knowledge_async(
        self,
        text: str,
        metadata: Optional[Dict] = None
    ):
        """异步添加知识"""
        await self.memory.add_knowledge_async(text, metadata)

    async def search_knowledge_async(
        self,
        query: str,
        k: int = 5
    ) -> List[str]:
        """异步搜索知识"""
        return await self.memory.search_knowledge_async(query, k)
    
    async def process_image_async(self, file_path: str) -> str:
        """异步处理图片分析"""
        # 这里可以集成图片分析功能
        # 暂时返回占位响应
        return f"已收到图片: {file_path}，图片分析功能正在开发中..."
    
    def update_tts_config(self, config: Dict):
        """更新TTS配置"""
        try:
            # 清理旧的TTS管理器
            if self.tts_manager:
                try:
                    self.tts_manager.cleanup()
                except:
                    pass

            # 重新初始化TTS管理器
            self._init_tts_manager(config)
            print("✅ TTS配置更新成功")
        except Exception as e:
            print(f"⚠️ TTS配置更新失败: {str(e)}")
