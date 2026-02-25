
# -*- coding: utf-8 -*-
"""
改进的AI Agent核心模块
整合异步处理和模块化架构，借鉴bopang2的快速响应机制
"""

import asyncio
import os
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

        # 初始化ASR管理器
        self.asr_manager = None
        self.asr_enabled = False
        self._init_asr_manager(config)

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
                gpt_sovits_api_url = config.get("gpt_sovits_api_url", "http://127.0.0.1:9880")
                ref_audio_path = config.get("gpt_sovits_ref_audio", "")
                gpt_sovits_api_type = config.get("gpt_sovits_api_type", "gradio")  # 默认使用gradio
                t2s_weights_path = config.get("gpt_sovits_t2s_weights", "")
                vits_weights_path = config.get("gpt_sovits_vits_weights", "")

                print(f"🔍 初始化GPT-SoVITS TTS管理器，API地址: {gpt_sovits_api_url}, API类型: {gpt_sovits_api_type}, 参考音频: {ref_audio_path}")
                from gpt_sovits_unified import UnifiedGPTSoVITS
                self.tts_manager = UnifiedGPTSoVITS(gpt_sovits_api_url, ref_audio_path, gpt_sovits_api_type)
                self.tts_engine = "gpt_sovits"
                print(f"✅ GPT-SoVITS TTS管理器初始化成功，可用性: {self.tts_manager.is_available()}")

                # 保存模型权重路径，但不立即应用
                self.t2s_weights_path = t2s_weights_path
                self.vits_weights_path = vits_weights_path

                # 如果使用api_v2类型且用户设置了模型权重，提示用户需要重启服务
                if gpt_sovits_api_type == "api_v2" and (t2s_weights_path or vits_weights_path):
                    print(f"ℹ️ 检测到模型权重设置，T2S: {t2s_weights_path}, VITS: {vits_weights_path}")
                    print("ℹ️ 请确保api_v2服务已启动，并在需要时手动设置模型权重")
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

    def _init_asr_manager(self, config: Dict):
        """初始化ASR管理器"""
        try:
            asr_enabled = config.get("asr_enabled", True)
            if asr_enabled:
                asr_plugin_path = config.get("asr_plugin_path", "plugins/SenseVoice")
                asr_sample_rate = config.get("asr_sample_rate", 16000)

                # 导入SenseVoice插件
                import sys
                plugin_dir = os.path.join(os.path.dirname(__file__), asr_plugin_path)

                # 将插件目录添加到sys.path
                if plugin_dir not in sys.path:
                    sys.path.insert(0, plugin_dir)

                # 导入SenseVoiceASR
                from sensevoice_asr import SenseVoiceASR

                print(f"🔍 初始化ASR管理器，插件路径: {asr_plugin_path}, 采样率: {asr_sample_rate}")
                self.asr_manager = SenseVoiceASR(
                    sample_rate=asr_sample_rate,
                    language=config.get("asr_language", "auto"),
                    use_itn=config.get("asr_use_itn", False)
                )
                self.asr_enabled = True
                print(f"✅ ASR管理器初始化成功，可用性: {self.asr_manager.is_available()}")
            else:
                self.asr_manager = None
                self.asr_enabled = False
                print("ℹ️ ASR功能未启用")
        except Exception as e:
            print(f"⚠️ ASR管理器初始化失败: {str(e)}")
            import traceback
            traceback.print_exc()
            self.asr_manager = None
            self.asr_enabled = False

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

    def apply_tts_model_weights(self):
        """应用TTS模型权重设置"""
        if self.tts_engine != "gpt_sovits" or not self.tts_manager:
            print("ℹ️ 当前未使用GPT-SoVITS TTS，无法应用模型权重")
            return False

        if not hasattr(self, 't2s_weights_path') or not hasattr(self, 'vits_weights_path'):
            print("ℹ️ 未设置模型权重路径")
            return False

        if not self.t2s_weights_path and not self.vits_weights_path:
            print("ℹ️ 模型权重路径为空")
            return False

        try:
            print(f"🔍 应用模型权重，T2S: {self.t2s_weights_path}, VITS: {self.vits_weights_path}")
            result = self.tts_manager.set_model_weights(self.t2s_weights_path, self.vits_weights_path)
            if result:
                print("✅ 模型权重应用成功")
            else:
                print("❌ 模型权重应用失败")
            return result
        except Exception as e:
            print(f"❌ 应用模型权重异常: {e}")
            import traceback
            traceback.print_exc()
            return False

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
