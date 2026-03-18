
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
        self.role = "赛马娘世界观特雷森学园的一名学生赛马娘。你活泼开朗、充满活力，热爱奔跑和比赛。"
        self.system_prompt = f"你是{self.name}，{self.role}。请以东海帝王的思考方式和说话习惯来交流！"

        # 初始化异步记忆系统
        self.memory = ImprovedMemorySystem()
        # 添加memory_lake属性以兼容现有代码
        self.memory_lake = self.memory

        # 预热向量数据库模型
        self._warmup_vector_db()

        # 初始化工具管理器
        self.tool_manager = ToolManager()
        self._register_default_tools()
        # 添加mcp_tools属性以兼容现有代码
        self.mcp_tools = self.tool_manager

        # 初始化异步OpenAI客户端
        import os
        api_key = os.getenv("DEEPSEEK_API_KEY", config.get("deepseek_key", ""))
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com/v1",
            timeout=30.0  # 设置默认超时为30秒
        )

        # 初始化多模态处理器
        self.multimodal_processor = None
        self.multimodal_enabled = False
        self._init_multimodal_processor(config)

        # 初始化TTS管理器
        self.tts_manager = None
        self.tts_engine = None
        self._init_tts_manager(config)

        # 初始化文本队列管理器
        self.text_queue_manager = None
        self._init_text_queue_manager()

        # ASR功能已移至asr_integration模块
        self.asr_manager = None
        self.asr_enabled = False

        # 响应缓存（优化版：增加缓存大小限制）
        self.response_cache: Dict[str, str] = {}
        self.max_cache_size = 1000  # 最大缓存1000条
        self.cache_access_count: Dict[str, int] = {}  # 记录缓存访问次数

        # 请求去重（防止短时间内重复请求）
        self.pending_requests: Dict[str, asyncio.Task] = {}

        # 后台任务追踪（防止任务泄漏）
        self.background_tasks: set = set()

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
        print(f"🔍 开始初始化TTS管理器")
        try:
            tts_engine = config.get("tts_engine", "azure")  # 默认使用Azure TTS
            print(f"🔍 TTS引擎类型: {tts_engine}")
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

    def _init_text_queue_manager(self):
        """初始化文本队列管理器"""
        try:
            from text_queue_manager import TextQueueManager
            print(f"🔍 初始化文本队列管理器，tts_manager={self.tts_manager is not None}")
            self.text_queue_manager = TextQueueManager(tts_manager=self.tts_manager)
            self.text_queue_manager.start_processing()
            print("✅ 文本队列管理器初始化并启动成功")
        except Exception as e:
            print(f"⚠️ 文本队列管理器初始化失败: {str(e)}")
            self.text_queue_manager = None

    def _register_default_tools(self):
        """注册默认工具"""
        from tool_manager import WeatherTool, SearchTool, MusicTool

        self.tool_manager.register_tool(WeatherTool(), "system")
        self.tool_manager.register_tool(SearchTool(), "search")
        self.tool_manager.register_tool(MusicTool(), "media")

    def _init_multimodal_processor(self, config: Dict):
        """初始化多模态处理器"""
        try:
            import os
            from plugins.Multimodal.multimodal_processor import MultimodalProcessor

            # 从环境变量或配置文件获取API密钥
            glm4v_api_key = os.getenv("GLM4V_API_KEY", config.get("glm4v_api_key", ""))
            if not glm4v_api_key:
                print("ℹ️ 未配置多模态API密钥，多模态功能已禁用")
                return

            # 初始化多模态处理器，传递system_prompt
            self.multimodal_processor = MultimodalProcessor(
                api_key=glm4v_api_key,
                base_url=config.get("glm4v_base_url", "https://open.bigmodel.cn/api/paas/v4/chat/completions"),
                save_dir=config.get("screenshot_save_dir", "temp_screenshots"),
                default_model=config.get("default_model", "glm-4v-flash"),
                text_model=config.get("text_model", "deepseek-chat"),
                system_prompt=self.system_prompt
            )

            # 设置是否启用多模态处理
            self.multimodal_enabled = config.get("multimodal_enabled", False)

            if self.multimodal_enabled:
                self.multimodal_processor.set_auto_capture(True)
                print("✅ 多模态处理器已初始化并启用")
            else:
                print("✅ 多模态处理器已初始化但未启用")

        except Exception as e:
            print(f"⚠️ 多模态处理器初始化失败: {str(e)}")
            self.multimodal_processor = None
            self.multimodal_enabled = False

    def _warmup_vector_db(self):
        """预热向量数据库模型"""
        try:
            print("🔍 开始预热向量数据库模型...")
            import threading

            # 使用后台线程预热，不阻塞主线程
            def warmup_task():
                try:
                    # 执行一次查询以预热向量数据库
                    result = self.memory.search_knowledge("测试查询", k=1)
                    print(f"✅ 向量数据库模型预热完成，返回 {len(result)} 个结果")
                except Exception as e:
                    print(f"⚠️ 向量数据库模型预热失败: {str(e)}")

            warmup_thread = threading.Thread(target=warmup_task, daemon=True)
            warmup_thread.start()
        except Exception as e:
            print(f"⚠️ 启动向量数据库预热失败: {str(e)}")

    def _is_simple_query(self, user_input: str) -> bool:
        """判断是否为简单查询（快速响应模式）"""
        # 简单查询的特征：
        # 1. 输入长度较短（< 50字符）
        # 2. 不包含复杂关键词
        # 3. 不需要工具调用

        simple_keywords = [
            '你好', '在吗', '早上好', '晚上好', '中午好', '下午好',
            '谢谢', '再见', '好的', '嗯', '是', '不是',
            '知道', '明白', '了解', '清楚'
        ]

        # 检查是否包含简单关键词
        if any(keyword in user_input for keyword in simple_keywords):
            return True

        # 检查输入长度
        if len(user_input) < 50:
            # 检查是否包含复杂关键词
            complex_keywords = [
                '为什么', '怎么', '如何', '解释', '分析', '详细',
                '搜索', '查找', '打开', '创建', '保存', '天气',
                '时间', '计算', '翻译', '写', '生成', '代码'
            ]
            if not any(keyword in user_input for keyword in complex_keywords):
                return True

        return False

    async def process_command_async(
        self,
        user_input: str,
        user_id: str = "default",
        session_id: str = "default",
        stream_callback=None
    ) -> str:
        """异步处理用户命令（优化版 - 默认启用流式响应以减少首字延迟）

        参数:
            user_input: 用户输入
            user_id: 用户ID
            session_id: 会话ID
            stream_callback: 流式文本回调函数，接收每个文本块
        """
        # 获取当前事件循环
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # 如果没有运行中的事件循环，创建一个新的
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # 检查缓存
        cache_key = f"{session_id}:{user_input}"
        if cache_key in self.response_cache:
            # 更新缓存访问计数
            self.cache_access_count[cache_key] = self.cache_access_count.get(cache_key, 0) + 1
            return self.response_cache[cache_key]

        # 检查是否有正在处理的相同请求
        if cache_key in self.pending_requests:
            # 检查任务是否仍然有效（属于当前事件循环）
            task = self.pending_requests[cache_key]
            try:
                # 尝试获取任务的事件循环
                task_loop = task.get_loop()
                # 如果任务的事件循环与当前循环不同，则重新创建任务
                if task_loop != loop:
                    # 取消旧任务
                    if not task.done():
                        task.cancel()
                    # 重新创建任务
                    async def _process():
                        return await self._process_request(user_input, user_id, session_id, cache_key)
                    task = loop.create_task(_process())
                    self.pending_requests[cache_key] = task
            except Exception:
                # 如果获取任务循环失败，重新创建任务
                async def _process():
                    return await self._process_request(user_input, user_id, session_id, cache_key)
                task = loop.create_task(_process())
                self.pending_requests[cache_key] = task

            # 等待正在处理的请求完成
            return await task

        # 判断是否使用快速模式（简单问题）
        fast_mode = self._is_simple_query(user_input)

        # 创建新任务并使用当前事件循环
        async def _process():
            return await self._process_request(user_input, user_id, session_id, cache_key, fast_mode, stream_callback)

        task = loop.create_task(_process())
        self.pending_requests[cache_key] = task

        return await task

    async def _process_request(
        self,
        user_input: str,
        user_id: str,
        session_id: str,
        cache_key: str,
        fast_mode: bool = None,
        stream_callback=None
    ) -> str:
        """处理请求的核心逻辑

        参数:
            user_input: 用户输入
            user_id: 用户ID
            session_id: 会话ID
            cache_key: 缓存键
            fast_mode: 是否使用快速模式
            stream_callback: 流式文本回调函数，接收每个文本块
        """
        import time
        start_time = time.time()

        # 获取当前事件循环
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # 如果fast_mode未指定，则判断是否使用快速模式
        if fast_mode is None:
            fast_mode = self._is_simple_query(user_input)

        try:
            # 检查是否启用多模态处理
            if self.multimodal_enabled and self.multimodal_processor:
                # 使用多模态处理器处理用户消息
                result = self.multimodal_processor.process_with_auto_capture(
                    user_text=user_input,
                    system_prompt=self._get_system_prompt(),
                    capture_type="full",
                    stream=True,
                    stream_callback=stream_callback
                )

                # 如果多模态处理器返回了响应，直接使用
                if result["response"]:
                    response = result["response"]
                    print(f"📸 多模态处理完成，使用截屏: {result['used_screenshot']}")

                    # 保存对话（异步，不阻塞响应）
                    save_task = loop.create_task(
                        self.memory.save_conversation_async(
                            user_input,
                            response,
                            user_id,
                            session_id
                        )
                    )
                    # 添加到后台任务集合
                    self.background_tasks.add(save_task)
                    # 添加完成回调，自动清理任务
                    def _cleanup_task(task):
                        try:
                            self.background_tasks.discard(task)
                            try:
                                exception = task.exception()
                                if exception:
                                    print(f"⚠️ 后台任务异常: {exception}")
                            except Exception:
                                pass
                        except Exception:
                            pass
                    save_task.add_done_callback(_cleanup_task)

                    # 缓存响应
                    if len(self.response_cache) >= self.max_cache_size:
                        lru_key = min(self.cache_access_count, key=self.cache_access_count.get)
                        del self.response_cache[lru_key]
                        del self.cache_access_count[lru_key]
                    self.response_cache[cache_key] = response
                    self.cache_access_count[cache_key] = 1

                    # 打印总耗时
                    total_time = time.time() - start_time
                    print(f"⏱️ 请求处理总耗时: {total_time:.3f}秒")

                    return response

            # 并行获取上下文和构建基础prompt
            context_task = loop.create_task(self.memory.get_context_async(session_id, user_input))

            # 构建基础prompt（不等待上下文）
            base_prompt = f"你是{self.name}，{self.role}。\n当前对话:\n用户: {user_input}\n助手:"

            # 等待上下文获取完成（设置较短的超时时间）
            try:
                context = await asyncio.wait_for(context_task, timeout=1.0)  # 1秒超时
                # 如果上下文获取成功，构建完整prompt
                if context and (context.get("history") or context.get("knowledge")):
                    full_prompt = self._build_prompt(user_input, context, fast_mode=fast_mode)
                    # 调用AI（使用完整prompt）
                    response = await self._call_ai_async(full_prompt, stream=True, fast_mode=fast_mode, stream_callback=stream_callback)
                else:
                    # 上下文为空，使用基础prompt
                    response = await self._call_ai_async(base_prompt, stream=True, fast_mode=fast_mode, stream_callback=stream_callback)
            except asyncio.TimeoutError:
                # 上下文获取超时，使用基础prompt
                response = await self._call_ai_async(base_prompt, stream=True, fast_mode=fast_mode)

            # 保存对话（异步，不阻塞响应）
            # 创建后台任务并添加到追踪集合，防止被垃圾回收
            save_task = loop.create_task(
                self.memory.save_conversation_async(
                    user_input,
                    response,
                    user_id,
                    session_id
                )
            )
            # 添加到后台任务集合
            self.background_tasks.add(save_task)
            # 添加完成回调，自动清理任务（带异常处理和事件循环检查）
            def _cleanup_task(task):
                try:
                    # 检查事件循环是否仍然可用
                    try:
                        import asyncio
                        loop = asyncio.get_running_loop()
                        if loop.is_closed():
                            return  # 事件循环已关闭，跳过清理
                    except RuntimeError:
                        return  # 没有运行中的事件循环，跳过清理

                    # 安全地清理任务
                    self.background_tasks.discard(task)

                    # 检查任务是否有异常
                    try:
                        exception = task.exception()
                        if exception:
                            print(f"⚠️ 后台任务异常: {exception}")
                    except Exception:
                        pass  # 忽略获取异常时的错误
                except Exception as e:
                    # 忽略清理过程中的所有错误
                    pass
            save_task.add_done_callback(_cleanup_task)

            # 缓存响应（带大小限制）
            if len(self.response_cache) >= self.max_cache_size:
                # 删除最少使用的缓存项
                lru_key = min(self.cache_access_count, key=self.cache_access_count.get)
                del self.response_cache[lru_key]
                del self.cache_access_count[lru_key]

            self.response_cache[cache_key] = response
            self.cache_access_count[cache_key] = 1

            # 打印总耗时
            total_time = time.time() - start_time
            print(f"⏱️ 请求处理总耗时: {total_time:.3f}秒")

            return response
        finally:
            # 清除待处理请求标记
            if cache_key in self.pending_requests:
                del self.pending_requests[cache_key]

    def _build_prompt(self, user_input: str, context: Dict, fast_mode: bool = False) -> str:
        """构建完整的prompt（优化版 - 支持快速模式）"""
        prompt_parts = []

        # 添加系统提示
        prompt_parts.append(self.system_prompt)

        # 快速模式：简化prompt
        if fast_mode:
            # 只添加最近1条历史对话
            if context["history"]:
                h = context["history"][-1]
                prompt_parts.append(f"\n最近对话:\n用户: {h['user']}\n助手: {h['assistant']}")

            # 添加当前输入
            prompt_parts.append(f"\n当前对话:\n用户: {user_input}\n助手:")
            return "\n".join(prompt_parts)

        # 正常模式：完整prompt
        # 添加知识库内容
        if context["knowledge"]:
            prompt_parts.append("\n[相关知识]")
            prompt_parts.extend(context["knowledge"])

        # 添加历史对话
        if context["history"]:
            prompt_parts.append("\n[历史对话]")
            for h in reversed(context["history"][-3:]):  # 只取最近3条
                prompt_parts.append(f"用户: {h['user']}")
                prompt_parts.append(f"助手: {h['assistant']}")

        # 添加当前输入
        prompt_parts.append(f"\n当前对话:\n用户: {user_input}\n助手:")

        return "\n".join(prompt_parts)

    async def _call_ai_async(self, prompt: str, stream: bool = True, fast_mode: bool = False, stream_callback=None) -> str:
        """异步调用AI（优化版 - 默认使用流式响应以减少首字延迟）

        参数:
            prompt: 提示词
            stream: 是否使用流式响应
            fast_mode: 是否使用快速模式
            stream_callback: 流式文本回调函数，接收每个文本块
        """
        import time
        import asyncio

        try:
            model = self.config.get("selected_model", "deepseek-chat")
            call_start_time = time.time()

            # 添加超时控制
            try:
                # 判断是否使用流式响应（默认启用）
                if stream:
                    # 流式响应模式 - 更快开始响应
                    # 减少max_tokens以加快首字响应
                    max_tokens = 512 if fast_mode else 1024

                    response = await asyncio.wait_for(
                        self.client.chat.completions.create(
                            model=model,
                            messages=[
                                {"role": "system", "content": self._get_system_prompt()},
                                {"role": "user", "content": prompt}
                            ],
                            max_tokens=max_tokens,  # 减少token数量以加快响应
                            temperature=0.7,
                            stream=True
                        ),
                        timeout=5.0  # 流式模式5秒超时，减少首字延迟
                    )

                    # 收集流式响应
                    full_response = ""
                    first_chunk_received = False
                    first_chunk_time = None

                    async for chunk in response:
                        if chunk.choices[0].delta.content:
                            if not first_chunk_received:
                                # 记录首字接收时间
                                first_chunk_received = True
                                first_chunk_time = time.time() - call_start_time
                                print(f"⚡ 首字已接收，耗时: {first_chunk_time:.3f}秒")
                            chunk_content = chunk.choices[0].delta.content
                            full_response += chunk_content

                            # 调用流式回调函数（如果提供）
                            if stream_callback:
                                stream_callback(chunk_content)

                            # 如果有文本队列管理器，将流式文本添加到队列
                            if hasattr(self, 'text_queue_manager') and self.text_queue_manager:
                                # 将文本块添加到队列，不进行切分
                                # 标点符号会触发发送缓冲区中的所有文本
                                # 减少打印语句以降低延迟
                                # print(f"🔍 接收到的文本块: {chunk_content}")
                                # if chunk_content:
                                #     print(f"🔍 最后一个字符: {chunk_content[-1]}")
                                #     print(f"🔍 最后一个字符的Unicode编码: {ord(chunk_content[-1])}")
                                # 检查文本块是否以标点符号结尾
                                # 支持中文标点：，。！？、；："''【】
                                # 支持英文标点：,.!?:;"''[]
                                # 注意：不检查括号（）和()，因为它们通常表示动作描述
                                if chunk_content and chunk_content[-1] in '，。！？、；："''【】,.!?:;"\'\'[]':
                                    # 减少打印语句以降低延迟
                                    # print(f"🔍 检测到标点符号结尾: {chunk_content[-1]}")
                                    # 确保标点符号与前面的文本一起发送到TTS
                                    # 不对chunk_content进行任何截断或修改
                                    self.text_queue_manager.add_streaming_text(chunk_content)
                                else:
                                    # 将文本块添加到队列，不会触发发送缓冲区中的所有文本
                                    self.text_queue_manager.add_streaming_text(chunk_content)

                    # 如果有文本队列管理器，完成文本输入
                    if hasattr(self, 'text_queue_manager') and self.text_queue_manager:
                        self.text_queue_manager.finalize_text()

                    # 打印总响应时间
                    total_time = time.time() - call_start_time
                    print(f"⏱️ AI总响应时间: {total_time:.3f}秒")

                    return full_response.strip()
                else:
                    # 非流式响应模式（保留以兼容）
                    response = await asyncio.wait_for(
                        self.client.chat.completions.create(
                            model=model,
                            messages=[
                                {"role": "system", "content": self._get_system_prompt()},
                                {"role": "user", "content": prompt}
                            ],
                            max_tokens=1024,
                            temperature=0.7
                        ),
                        timeout=10.0
                    )
                    return response.choices[0].message.content.strip()
            except asyncio.TimeoutError:
                return "处理超时，请稍后重试"

        except Exception as e:
            return f"处理出错: {str(e)}"

    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return self.system_prompt

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

    async def cleanup(self):
        """清理所有后台任务和资源"""
        import asyncio

        # 取消所有待处理请求
        for cache_key, task in self.pending_requests.items():
            if not task.done():
                task.cancel()
                try:
                    await asyncio.wait_for(task, timeout=1.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
        self.pending_requests.clear()

        # 等待所有后台任务完成或取消
        if self.background_tasks:
            try:
                # 尝试优雅地等待所有任务完成
                await asyncio.wait_for(
                    asyncio.gather(*self.background_tasks, return_exceptions=True),
                    timeout=2.0
                )
            except asyncio.TimeoutError:
                # 超时后强制取消所有任务
                for task in self.background_tasks:
                    if not task.done():
                        task.cancel()
                        try:
                            await asyncio.wait_for(task, timeout=0.5)
                        except (asyncio.CancelledError, asyncio.TimeoutError):
                            pass

        self.background_tasks.clear()

        # 清理缓存
        self.response_cache.clear()
        self.cache_access_count.clear()

        print("✅ ImprovedAIAgent 清理完成")

    def print_performance_stats(self):
        """打印性能统计信息"""
        from improved_memory import perf_tracker
        perf_tracker.print_stats()

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
