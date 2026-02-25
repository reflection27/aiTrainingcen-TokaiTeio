# -*- coding: utf-8 -*-
"""
AI代理核心模块
处理用户输入、工具调用和AI响应生成
"""

import datetime
import re
import openai
import subprocess
import os
from config import load_config
from utils import get_location, scan_windows_apps, open_website, open_application, search_web
from weather import WeatherTool
from amap_tool import AmapTool
from memory_lake import MemoryLake
from mcp_server import LocalMCPServer

class MCPTools:
    """MCP工具管理类"""
    
    def __init__(self):
        self.server = LocalMCPServer()
    
    def execute_mcp_command(self, tool_name, **params):
        """执行MCP命令（同步版本）"""
        try:
            # 重新加载自定义工具
            self.server.reload_custom_tools()
            result = self.server.call_tool(tool_name, **params)
            return result
        except Exception as e:
            return f"MCP命令执行失败: {str(e)}"
    
    async def execute_mcp_command_async(self, tool_name, **params):
        """执行MCP命令（异步版本）"""
        try:
            # 重新加载自定义工具
            self.server.reload_custom_tools()
            result = self.server.call_tool(tool_name, **params)
            return result
        except Exception as e:
            return f"MCP命令执行失败: {str(e)}"
    
    def list_available_tools(self):
        """列出可用工具（同步版本）"""
        try:
            return self.server.list_tools()
        except Exception as e:
            print(f"获取工具列表失败: {str(e)}")
            return []
    
    async def list_available_tools_async(self):
        """列出可用工具（异步版本）"""
        try:
            return self.server.list_tools()
        except Exception as e:
            print(f"获取工具列表失败: {str(e)}")
            return []
    
    def list_tools(self):
        """同步版本的工具列表获取"""
        try:
            return self.server.list_tools()
        except Exception as e:
            print(f"获取工具列表失败: {str(e)}")
            return []
    
    def get_tool_info(self, tool_name):
        """获取工具信息（同步版本）"""
        try:
            return self.server.get_tool_info(tool_name)
        except Exception as e:
            print(f"获取工具信息失败: {str(e)}")
            return {}
    
    async def get_tool_info_async(self, tool_name):
        """获取工具信息（异步版本）"""
        try:
            return self.server.get_tool_info(tool_name)
        except Exception as e:
            print(f"获取工具信息失败: {str(e)}")
            return {}

class AIAgent:
    """东海帝王AI核心"""
    
    def __init__(self, config):
        self.name = "东海帝王"
        self.role = "赛马娘世界观特雷森学园的一名学生赛马娘"
        self.memory_lake = MemoryLake()
        self.developer_mode = False
        self.current_topic = ""
        self.conversation_history = []
        self.config = config
        self.location = get_location()
        self.last_save_date = None
        
        # 本次程序运行时的对话记录
        self.session_conversations = []
        
        # 最近生成的代码缓存
        self.last_generated_code = None

        # 可用的工具
        self.tools = {
            "天气": WeatherTool.get_weather,
            "打开网站": self._open_website_wrapper,
            "打开应用": open_application,
            "获取时间": self._get_current_time,
            "搜索": search_web,
        }
        
        # 初始化MCP工具
        self.mcp_server = LocalMCPServer()
        self.mcp_tools = MCPTools()

        # 网站和应用映射
        self.website_map = config.get("website_map", {})

        # 合并扫描到的应用和手动添加的应用
        self.app_map = scan_windows_apps()
        self.app_map.update(config.get("app_map", {}))

        # 预加载应用数
        self.app_count = len(self.app_map)
        
        # 初始化TTS管理器
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

        # 初始化ASR管理器
        try:
            asr_enabled = config.get("asr_enabled", True)
            if asr_enabled:
                asr_plugin_path = config.get("asr_plugin_path", "plugins/SenseVoice")
                asr_sample_rate = config.get("asr_sample_rate", 16000)

                # 导入SenseVoice插件
                import sys
                plugin_dir = os.path.join(os.path.dirname(__file__), asr_plugin_path)
                if plugin_dir not in sys.path:
                    sys.path.insert(0, plugin_dir)

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
            self.asr_manager = None
            self.asr_enabled = False

    def process_command(self, user_input):
        """处理用户命令"""
        # 检查开发者模式命令
        if user_input.lower() == "developer mode":
            self.developer_mode = True
            return "(开发者模式已激活)"
        elif user_input.lower() == "exit developer mode":
            self.developer_mode = False
            return "(开发者模式已关闭)"

        # 检查"记住这个时刻"指令
        if self._is_remember_moment_command(user_input):
            return self._handle_remember_moment(user_input)

        # 记录对话历史
        self.conversation_history.append(f"训练员: {user_input}")



        # 分析用户输入，判断是否需要获取位置和天气信息
        context_info = self._get_context_info(user_input)
        
        # 生成AI响应（包含上下文信息）
        response = self._generate_response_with_context(user_input, context_info)
        
        # 确保响应不为None
        if response is None:
            response = "抱歉，我没有理解您的意思，请重新表述一下。"
        
        # 记录本次会话的对话
        self._add_session_conversation(user_input, response)
        
        # 记录对话历史
        self.conversation_history.append(f"{self.name}: {response}")
        
        # 更新记忆系统
        self._update_memory_lake(user_input, response)
        
        # 如果TTS已启用，播放语音
        tts_enabled = self.config.get("tts_enabled", False)
        has_tts_manager = hasattr(self, 'tts_manager') and self.tts_manager
        tts_available = has_tts_manager and self.tts_manager.is_available()

        print(f"🔍 TTS播放检查: tts_enabled={tts_enabled}, has_tts_manager={has_tts_manager}, tts_available={tts_available}")

        if tts_enabled and has_tts_manager:
            try:
                # 检查TTS是否可用
                if not tts_available:
                    print("⚠️ TTS不可用，跳过语音播放")
                else:
                    # 提取纯文本内容（去除表情符号等）
                    import re
                    clean_text = re.sub(r'[（\(].*?[）\)]', '', response)  # 移除括号内容
                    clean_text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s，。！？、；：""''（）]', '', clean_text)  # 保留中文、英文、数字和标点
                    clean_text = clean_text.strip()
                    
                    if clean_text and len(clean_text) > 0:
                        print(f"🎤 开始TTS播放: {clean_text[:50]}...")
                        self.tts_manager.speak_text(clean_text)
                    else:
                        print("⚠️ 清理后的文本为空，跳过TTS播放")
            except Exception as e:
                print(f"⚠️ TTS播放失败: {str(e)}")
        else:
            print("ℹ️ TTS未启用或管理器不可用")
        
        return response

    def _add_session_conversation(self, user_input, ai_response):
        """添加本次会话的对话记录"""
        # 🚀 修复：防重复添加机制
        # 检查是否已经存在相同的对话
        for existing_conv in self.session_conversations:
            if (existing_conv.get('user_input') == user_input and 
                existing_conv.get('ai_response') == ai_response):
                print(f"⚠️ 检测到重复对话，跳过添加到会话记录: {user_input[:30]}...")
                return
        
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.session_conversations.append({
            "timestamp": timestamp,
            "user_input": user_input,
            "ai_response": ai_response,
            "full_text": f"训练员: {user_input}\n东海帝王: {ai_response}",
            "saved": False  # 标记为未保存，当保存到记忆系统时会改为True
        })
        
        print(f"✅ 添加对话到会话记录: {user_input[:30]}... (当前共{len(self.session_conversations)}条)")

    def _mark_conversation_as_saved(self, user_input, ai_response):
        """标记对话为已保存"""
        # 在session_conversations中找到匹配的对话并标记为已保存
        for conv in self.session_conversations:
            if (conv.get('user_input') == user_input and 
                conv.get('ai_response') == ai_response and 
                not conv.get('saved', False)):
                conv['saved'] = True
                print(f"✅ 标记对话为已保存: {user_input[:50]}...")
                break

    def _extract_keywords(self, text):
        """提取关键词"""
        keywords = []
        # 扩展关键词列表
        common_words = [
            '天气', '时间', '搜索', '打开', '计算', '距离', '系统', '文件', '笔记', 
            '穿衣', '出门', '建议', '教堂', '景点', '历史', '参观', '路线', '法兰克福',
            '大教堂', '老城区', '游客', '高峰期', '规划', '咨询', '询问', '问过', '讨论过',
            '提到过', '说过', '介绍过', '推荐过', '建议过', '介绍', '一下', '什么', '哪里',
            '位置', '地址', '建筑', '标志性', '历史', '文化', '旅游', '游览', '参观'
        ]
        
        for word in common_words:
            if word in text:
                keywords.append(word)
        
        return keywords

    def _ai_identify_language_type(self, user_input):
        """使用AI识别用户想要的语言类型"""
        try:
            # 检查是否有API密钥
            model = self.config.get("selected_model", "deepseek-chat")
            api_key = self.config.get("deepseek_key", "") if "deepseek" in model else self.config.get("openai_key", "")
            
            if not api_key:
                # 如果没有API密钥，使用简单的关键词匹配作为后备
                return self._fallback_language_identification(user_input)
            
            # 构建上下文信息
            context_info = ""
            if self.session_conversations:
                # 获取最近的对话作为上下文
                recent_contexts = []
                for conv in reversed(self.session_conversations[-3:]):
                    recent_contexts.append(f"【{conv['timestamp']}】{conv['full_text']}")
                context_info = "\n".join(recent_contexts)
            
            # 构建AI提示词
            prompt = f"""
请分析用户的音乐请求，识别他们想要什么语言的音乐推荐。

用户输入：{user_input}

最近的对话上下文：
{context_info}

请从以下选项中选择最合适的语言类型：
1. 中文歌单 - 如果用户想要中文歌曲
2. 英文歌单 - 如果用户想要英文歌曲  
3. 日文歌单 - 如果用户想要日文歌曲
4. 德语歌单 - 如果用户想要德语歌曲
5. 音乐歌单 - 如果无法确定具体语言或用户想要混合语言

请只返回选项编号（1-5），不要包含任何其他文字。
"""
            
            # 设置API客户端
            if "deepseek" in model:
                client = openai.OpenAI(
                    api_key=api_key,
                    base_url="https://api.deepseek.com/v1"
                )
            else:
                client = openai.OpenAI(api_key=api_key)
            
            # 调用AI
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一个语言识别助手，专门用于识别用户想要的音乐语言类型。请只返回数字1-5。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=10,
                temperature=0.1,
                timeout=10
            )
            
            result = response.choices[0].message.content.strip()
            
            # 解析结果
            if result == "1":
                return "中文歌单"
            elif result == "2":
                return "英文歌单"
            elif result == "3":
                return "日文歌单"
            elif result == "4":
                return "德语歌单"
            else:
                return "音乐歌单"
                
        except Exception as e:
            print(f"AI语言识别失败: {str(e)}")
            # 如果AI调用失败，使用后备方法
            return self._fallback_language_identification(user_input)
    
    def _fallback_language_identification(self, user_input):
        """后备语言识别方法（关键词匹配）"""
        user_input_lower = user_input.lower()

        if "中文" in user_input_lower or "chinese" in user_input_lower:
            return "中文歌单"
        elif "英文" in user_input_lower or "english" in user_input_lower:
            return "英文歌单"
        elif "日文" in user_input_lower or "japanese" in user_input_lower:
            return "日文歌单"
        elif "德文" in user_input_lower or "德语" in user_input_lower or "german" in user_input_lower:
            return "德语歌单"
        else:
            # 检查最近的对话中是否有德语歌曲推荐
            for conv in reversed(self.session_conversations[-3:]):
                ai_response = conv.get("ai_response", "")
                if any(keyword in ai_response for keyword in ["德文", "德语", "Rammstein", "Nena", "Das Liebeslied", "Ohne dich"]):
                    return "德语歌单"
            return "音乐歌单"

    def _ai_identify_website_intent(self, user_input):
        """专门用于识别网站打开请求的AI方法"""
        try:
            # 检查是否有API密钥
            # 网站打开识别使用chat模型，不需要推理模型
            model = "deepseek-chat" if "deepseek" in self.config.get("selected_model", "deepseek-chat") else "gpt-3.5-turbo"
            api_key = self.config.get("deepseek_key", "") if "deepseek" in model else self.config.get("openai_key", "")
            
            if not api_key:
                # 如果没有API密钥，使用关键词匹配作为后备
                return self._fallback_website_check(user_input)
            
            # 构建专门的网站打开识别提示词
            website_prompt = f"""
请分析用户的输入，判断是否是网站打开请求：

用户输入：{user_input}

请判断用户是否想要打开网站或访问网页。

判断标准：
- 如果用户要求打开网站、访问网页、在浏览器打开某个网站，返回"website_open|网站名称"
- 如果用户是在询问其他问题，返回"not_website|"

特别注意：
- "帮我打开XX" → "website_open|XX"
- "打开XX" → "website_open|XX"
- "访问XX" → "website_open|XX"
- "在浏览器打开XX" → "website_open|XX"
- "帮我通过浏览器打开XX" → "website_open|XX"
- "打开XX网站" → "website_open|XX"
- "访问XX网站" → "website_open|XX"

请返回格式：类型|网站名称
- 类型：website_open 或 not_website
- 网站名称：如果是website_open，提取要打开的网站名称；否则返回空字符串

示例：
- "帮我打开知乎" → "website_open|知乎"
- "打开bilibili" → "website_open|bilibili"
- "访问百度" → "website_open|百度"
- "在浏览器打开github" → "website_open|github"
- "帮我通过浏览器打开哔哩哔哩" → "website_open|哔哩哔哩"
- "什么是人工智能" → "not_website|"
"""
            
            # 设置API客户端
            if "deepseek" in model:
                client = openai.OpenAI(
                    api_key=api_key,
                    base_url="https://api.deepseek.com/v1"
                )
            else:
                client = openai.OpenAI(api_key=api_key)
            
            # 调用AI进行网站打开意图识别
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一个网站打开意图识别助手，专门用于判断用户是否想要打开网站。请严格按照格式返回结果。"},
                    {"role": "user", "content": website_prompt}
                ],
                max_tokens=30,
                temperature=0.1,
                timeout=10
            )
            
            result = response.choices[0].message.content.strip()
            print(f"🔍 网站打开AI识别结果: {result}")
            
            # 解析结果
            if "|" in result:
                intent_type, site_name = result.split("|", 1)
                if intent_type == "website_open":
                    print(f"🌐 AI识别为网站打开请求: {user_input} -> {site_name}")
                    return site_name.strip()
                else:
                    print(f"❌ AI识别为非网站打开请求: {user_input}")
                    return None
            
            # 如果AI识别失败，返回None
            return None
                
        except Exception as e:
            print(f"AI网站打开意图识别失败: {str(e)}")
            # 如果AI调用失败，返回None
            return None

    def _ai_identify_search_intent(self, user_input):
        """使用AI识别用户的搜索意图"""
        try:
            # 检查是否有API密钥
            model = self.config.get("selected_model", "deepseek-chat")
            api_key = self.config.get("deepseek_key", "") if "deepseek" in model else self.config.get("openai_key", "")
            
            if not api_key:
                # 如果没有API密钥，使用简单的关键词匹配作为后备
                return self._fallback_search_identification(user_input)
            
            # 使用AI智能识别文件创建请求，而不是关键词匹配
            # 构建上下文信息
            context_info = ""
            if self.session_conversations:
                # 获取最近的对话作为上下文
                recent_contexts = []
                for conv in reversed(self.session_conversations[-3:]):
                    recent_contexts.append(f"【{conv['timestamp']}】{conv['full_text']}")
                context_info = "\n".join(recent_contexts)
            
            # 构建AI提示词，让AI智能判断用户意图类型
            intent_prompt = f"""
请分析用户的输入，判断他们的意图类型：

用户输入：{user_input}

最近的对话上下文：
{context_info}

请判断用户是想要：
1. 创建或保存文件（包括代码文件、文档、歌单等）
2. 在浏览器中搜索网络信息
4. 向你询问问题或查看内容

判断标准：
- 如果用户明确要求创建、保存、写入文件，或指定文件路径，选择"file_operation"
- 如果用户说"不需要创建文件"、"不要创建文件"、"告诉我代码内容"、"显示代码"等，选择"question"
- 如果用户明确要求搜索、查找、查询网络信息，选择"web_search"
- 如果用户是在询问知识、寻求建议、讨论话题、查看内容，选择"question"

特别注意：
- "不需要直接创建文件，现在告诉我具体的代码内容" → "question|"
- "不要保存文件，只显示代码" → "question|"
- "告诉我代码内容" → "question|"
- "显示代码" → "question|"
- "帮我用Python写个计算器" → "question|"（用户想看代码，不是创建文件）
- "帮我用c++写一个游戏" → "question|"（用户想看代码，不是创建文件）
- "帮我打开bilbil" → "website_open|bilbil"
- "在浏览器打开b站" → "website_open|b站"
- "访问百度" → "website_open|百度"
- "打开github" → "website_open|github"

请返回格式：类型|关键词
- 类型：file_operation 或 web_search 或 website_open 或 question
- 关键词：如果是web_search，提取要搜索的关键词；如果是website_open，提取要打开的网站名称；否则返回空字符串

示例：
- "帮我用Python写个计算器" → "question|"（用户想看代码内容）
- "保存这个文件到D盘" → "file_operation|"（明确要求保存文件）
- "创建歌单文件" → "file_operation|"（明确要求创建文件）
- "不需要创建文件，告诉我代码内容" → "question|"
- "搜索Python教程" → "web_search|Python教程"
- "什么是人工智能" → "question|"
"""
            
            # 设置API客户端
            if "deepseek" in model:
                client = openai.OpenAI(
                    api_key=api_key,
                    base_url="https://api.deepseek.com/v1"
                )
            else:
                client = openai.OpenAI(api_key=api_key)
            
            # 调用AI进行意图识别
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一个意图识别助手，专门用于判断用户是想要创建文件、搜索网络信息、打开网站还是询问问题。请严格按照格式返回结果。"},
                    {"role": "user", "content": intent_prompt}
                ],
                max_tokens=50,
                temperature=0.1,
                timeout=10
            )
            
            result = response.choices[0].message.content.strip()
            
            # 解析结果
            if "|" in result:
                intent_type, query = result.split("|", 1)
                if intent_type == "file_operation":
                    print(f"🤖 AI智能识别为文件创建请求: {user_input}")
                    return None  # 返回None让工具调用处理
                elif intent_type == "web_search":
                    return ("web_search", query.strip())
                elif intent_type == "website_open":
                    return ("website_open", query.strip())
                elif intent_type == "question":
                    return ("question", "")
            
            # 如果AI识别失败，使用关键词匹配作为后备
            return self._fallback_search_identification(user_input)
                
        except Exception as e:
            print(f"AI搜索意图识别失败: {str(e)}")
            # 如果AI调用失败，使用后备方法
            return self._fallback_search_identification(user_input)
    
    def _fallback_search_identification(self, user_input):
        """后备搜索意图识别方法（关键词匹配）"""
        user_input_lower = user_input.lower()
        
        # 文件创建关键词（后备方案）- 只包含明确的文件创建请求
        file_creation_keywords = [
            "需要保存", "保存", "创建文件", "保存文件", "路径为", "保存为", "创建到", 
            "需要创建", "创建这个", "地址为", "保存到", "创建到", "创建歌单文件", 
            "歌单文件", "创建歌单", "帮我创建", "创建文件夹", "新建文件夹", "建立文件夹",
            "文件夹", "目录", "写入文件", "生成文件", "输出文件"
        ]
        
        # 搜索指示词
        search_indicators = [
            "搜索", "查找", "搜素", "搜", "查", "找", "查询", "查找", "搜素",
            "帮我搜索", "帮我查找", "帮我搜素", "帮我搜", "帮我查", "帮我找", "帮我查询", "帮我查找",
            "搜索一下", "查找一下", "搜素一下", "搜一下", "查一下", "找一下", "查询一下",
            "百度", "google", "谷歌", "bing", "必应"
        ]
        
        # 首先检查是否是"不需要创建文件"等表达
        no_file_keywords = [
            "不需要创建文件", "不要创建文件", "不需要保存文件", "不要保存文件",
            "告诉我代码内容", "显示代码", "只显示代码", "不要直接创建",
            "不需要直接创建", "现在告诉我", "具体代码内容"
        ]
        
        is_no_file_request = any(keyword in user_input for keyword in no_file_keywords)
        if is_no_file_request:
            print(f"🔧 关键词后备识别为查看内容请求: {user_input}")
            return ("question", "")  # 返回question类型，让AI正常回答
        
        # 然后检查是否是文件创建请求
        is_file_creation = any(keyword in user_input for keyword in file_creation_keywords)
        if is_file_creation:
            print(f"🔧 关键词后备识别为文件创建请求: {user_input}")
            return None  # 返回None让工具调用处理
        
        # 检查是否包含搜索指示词
        is_search_request = any(indicator in user_input for indicator in search_indicators)
        
        if is_search_request:
            # 提取搜索关键词
            query = self._extract_search_query(user_input)
            return ("web_search", query)
        else:
            return ("question", "")

    def _ai_create_code_file_from_context(self, user_input):
        """使用AI通过上下文智能创建代码文件"""
        try:
            # 检查是否有API密钥
            model = self.config.get("selected_model", "deepseek-chat")
            api_key = self.config.get("deepseek_key", "") if "deepseek" in model else self.config.get("openai_key", "")
            
            if not api_key:
                # 如果没有API密钥，返回None，使用后备方法
                return None
            
            # 构建上下文信息
            context_info = ""
            if self.session_conversations:
                # 获取最近的对话作为上下文
                recent_contexts = []
                for conv in reversed(self.session_conversations[-5:]):  # 获取最近5条对话
                    recent_contexts.append(f"【{conv['timestamp']}】{conv['full_text']}")
                context_info = "\n".join(recent_contexts)
            
            # 尝试从上下文中提取代码内容
            extracted_code = self._extract_code_from_context(context_info)
            if extracted_code:
                context_info += f"\n\n【提取的代码内容】\n{extracted_code}"
                print(f"🔍 从上下文中提取到代码: {extracted_code[:100]}...")
            else:
                print("⚠️ 未从上下文中提取到代码内容")
                # 如果用户明确要求保存文件但没有找到代码，尝试从最近的对话中提取
                if "保存" in user_input.lower() or "创建" in user_input.lower():
                    print("🔍 尝试从最近的对话中提取代码内容...")
                    for conv in reversed(self.session_conversations[-3:]):
                        ai_response = conv.get("ai_response", "")
                        if "```" in ai_response:
                            extracted_code = self._extract_code_from_context(ai_response)
                            if extracted_code:
                                context_info += f"\n\n【从最近对话提取的代码内容】\n{extracted_code}"
                                print(f"🔍 从最近对话中提取到代码: {extracted_code[:100]}...")
                                break
            
            # 构建AI提示词
            prompt = f"""
请分析用户的代码创建请求，基于上下文信息智能生成代码文件。

用户输入：{user_input}

最近的对话上下文：
{context_info}

请分析用户想要创建什么类型的代码文件，并生成相应的代码。可能的代码类型包括：
1. Python代码 - 如果用户提到Python、py等
2. C++代码 - 如果用户提到C++、cpp等
3. COBOL代码 - 如果用户提到COBOL、cobol等
4. 其他编程语言代码

特别注意：
- 如果上下文中已经显示了代码内容（如```cobol...```），请直接使用该代码
- 如果用户说"创建测试文件"、"创建源文件"、"需要创建"、"保存这个文件"、"需要保存"或"地址在d盘"，请基于上下文中的代码创建文件
- 如果上下文中有COBOL代码，请创建.cob或.cbl文件
- 如果上下文中有Python代码，请创建.py文件
- 如果上下文中有C++代码，请创建.cpp文件
- 如果用户说"需要创建"，请基于上下文中最近的代码内容创建文件
- 如果用户说"地址在d盘"或"保存到d盘"，请将文件保存到D盘
- 如果用户说"保存这个文件"或"需要保存"，请基于上下文中最近的代码内容创建文件
- 如果用户说"路径为"，请使用用户指定的路径和文件名

请返回JSON格式：
{{
    "language": "编程语言",
    "title": "代码标题",
    "code": "完整的代码内容",
    "location": "保存位置（如D:/）",
    "filename": "文件名（如hello.cob）",
    "description": "代码说明"
}}

要求：
1. 代码要完整、可运行
2. 包含必要的注释和文档
3. 使用最佳实践
4. 文件名要符合编程语言规范
5. 保存位置默认为D盘
6. 如果是Hello World程序，要简单明了
7. 优先使用上下文中已有的代码内容
8. 如果用户明确指定了保存位置，请使用用户指定的位置
9. 如果用户说"保存这个文件"，请使用上下文中最近的代码内容
10. 如果用户说"路径为"，请使用用户指定的完整路径

如果无法确定要创建什么代码，请返回null。
"""
            
            # 设置API客户端
            if "deepseek" in model:
                client = openai.OpenAI(
                    api_key=api_key,
                    base_url="https://api.deepseek.com/v1"
                )
            else:
                client = openai.OpenAI(api_key=api_key)
            
            # 调用AI
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一个代码生成助手，专门用于分析用户需求并生成相应的代码文件。请返回JSON格式的结果。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=3000,
                temperature=0.7,
                timeout=240  # 延长AI文件创建的响应时间到240秒
            )
            
            result = response.choices[0].message.content.strip()
            print(f"🔍 AI代码文件创建返回的原始结果: {result[:200]}...")
            
            # 解析JSON结果
            try:
                import json
                # 尝试清理JSON字符串
                result = result.strip()
                if result.startswith('```json'):
                    result = result[7:]
                if result.endswith('```'):
                    result = result[:-3]
                result = result.strip()
                
                file_info = json.loads(result)
                
                if file_info and "code" in file_info:
                    # 提取文件信息
                    language = file_info.get("language", "未知语言")
                    title = file_info.get("title", "未命名程序")
                    code = file_info.get("code", "")
                    location = file_info.get("location", "D:/")
                    filename = file_info.get("filename", f"program.{language.lower()}")
                    description = file_info.get("description", "")
                    
                    # 从用户输入中提取保存位置和文件名
                    import re
                    
                    # 尝试提取完整路径（如"路径为D:/计算器.py"）
                    path_match = re.search(r'路径为\s*([^，。\s]+)', user_input)
                    if path_match:
                        full_path = path_match.group(1)
                        # 分离路径和文件名
                        if '/' in full_path or '\\' in full_path:
                            path_parts = full_path.replace('\\', '/').split('/')
                            if len(path_parts) > 1:
                                location = '/'.join(path_parts[:-1]) + '/'
                                filename = path_parts[-1]
                                if not filename.endswith(('.py', '.cob', '.cbl', '.cpp', '.txt')):
                                    filename += '.py'  # 默认添加.py扩展名
                    else:
                        # 如果没有找到完整路径，使用原有的逻辑
                        if "d盘" in user_input.lower() or "d:" in user_input.lower():
                            location = "D:/"
                        elif "c盘" in user_input.lower() or "c:" in user_input.lower():
                            location = "C:/"
                        elif "e盘" in user_input.lower() or "e:" in user_input.lower():
                            location = "E:/"
                        elif "f盘" in user_input.lower() or "f:" in user_input.lower():
                            location = "F:/"
                    
                    # 确保文件名安全
                    import re
                    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
                    
                    # 构建完整的文件内容
                    if language.lower() == "cobol":
                        # COBOL代码格式特殊处理
                        if "IDENTIFICATION DIVISION" not in code:
                            file_content = f"""      IDENTIFICATION DIVISION.
      PROGRAM-ID. {title.upper().replace(' ', '-')}.
      PROCEDURE DIVISION.
{code}
      STOP RUN.
"""
                        else:
                            # 如果代码已经包含完整的COBOL结构，直接使用
                            file_content = code
                    else:
                        # 其他编程语言
                        file_content = f"""# -*- coding: utf-8 -*-
"""
                        if description:
                            file_content += f"""\"\"\"
{description}
\"\"\"

"""
                        file_content += code
                    
                    # 调用MCP工具创建文件
                    file_path = f"{location.rstrip('/')}/{filename}"
                    result = self.mcp_server.call_tool("write_file", 
                                                     file_path=file_path, 
                                                     content=file_content)
                    
                    return f"（指尖轻敲控制台）{result}"
                
            except json.JSONDecodeError as json_error:
                print(f"AI代码文件创建JSON格式无效: {result}")
                print(f"JSON解析错误: {str(json_error)}")
                return None
            except Exception as e:
                print(f"AI代码文件创建失败: {str(e)}")
                return None
        except Exception as e:
            print(f"AI代码文件创建过程失败: {str(e)}")
            return None

    def _ai_create_file_from_context(self, user_input):
        """使用AI通过上下文智能创建文件"""
        try:
            # 检查是否有API密钥
            model = self.config.get("selected_model", "deepseek-chat")
            api_key = self.config.get("deepseek_key", "") if "deepseek" in model else self.config.get("openai_key", "")
            
            if not api_key:
                # 如果没有API密钥，返回None，使用后备方法
                return None
            
            # 构建上下文信息 - 只关注与当前用户请求相关的内容
            context_info = ""
            relevant_content = ""
            
            # 分析用户当前请求的类型
            user_request_type = self._analyze_user_request_type(user_input)
            print(f"🔍 用户请求类型: {user_request_type}")
            
            # 如果是代码展示请求，不应该创建文件，应该返回None让AI直接展示代码
            if user_request_type == "code_display":
                print("ℹ️ 用户请求展示代码，不创建文件")
                return None
            
            if self.session_conversations:
                # 只获取与当前请求相关的对话内容
                for conv in reversed(self.session_conversations[-3:]):  # 只获取最近3条对话
                    conv_text = conv.get('full_text', '')
                    
                    # 根据用户请求类型筛选相关内容
                    if user_request_type in ["code_file", "code"] and ("代码" in conv_text or "程序" in conv_text or "```" in conv_text):
                        relevant_content += f"【{conv['timestamp']}】{conv_text}\n"
                    elif user_request_type in ["music_file", "music"] and ("音乐" in conv_text or "歌" in conv_text or "歌曲" in conv_text or "推荐" in conv_text):
                        relevant_content += f"【{conv['timestamp']}】{conv_text}\n"
                    elif user_request_type in ["travel_file", "travel"] and ("旅游" in conv_text or "旅行" in conv_text or "攻略" in conv_text):
                        relevant_content += f"【{conv['timestamp']}】{conv_text}\n"
                    elif user_request_type in ["note_file", "note"] and ("笔记" in conv_text or "记录" in conv_text):
                        relevant_content += f"【{conv['timestamp']}】{conv_text}\n"
                    elif user_request_type in ["general_file", "general"]:
                        # 🚀 对于通用文件请求，优先获取最近的对话内容，让AI智能判断
                        # 特别是当用户说"帮我保存"时，应该保存最近生成的内容
                        relevant_content += f"【{conv['timestamp']}】{conv_text}\n"
                
                context_info = relevant_content.strip()
            
            # 尝试从相关上下文中提取代码内容
            if user_request_type in ["code_file", "code"]:
                extracted_code = self._extract_code_from_context(context_info)
                if extracted_code:
                    context_info += f"\n\n【提取的代码内容】\n{extracted_code}"
                    print(f"🔍 从相关上下文中提取到代码: {extracted_code[:100]}...")
                else:
                    print("⚠️ 未从相关上下文中提取到代码内容")
            else:
                print(f"ℹ️ 用户请求类型为 {user_request_type}，跳过代码提取")
            
            # 构建AI提示词
            prompt = f"""
请分析用户的文件创建请求，基于用户当前的具体要求生成相应的文件内容。

用户当前请求：{user_input}
用户请求类型：{user_request_type}

相关上下文信息：
{context_info}

重要规则：
1. 🚀 当用户说"帮我保存"时，优先保存最近对话中生成的内容
2. 如果用户要求写代码，就生成代码文件，不要保存其他内容
3. 如果用户要求保存音乐推荐，就生成歌单文件
4. 如果用户要求保存旅游攻略，就生成旅游攻略文件
5. 严格根据用户当前请求的类型和内容来生成文件
6. 必须解析用户指定的保存路径，如果用户说"D:\测试_"，location就应该是"D:/测试_/"
7. 根据文件内容确定正确的文件扩展名，Python代码用.py，C++代码用.cpp等
8. 如果用户明确指定文件类型（如"保存为.py文件"），必须使用用户指定的扩展名
9. 如果用户说"保存为.py文件"，filename必须包含.py扩展名
10. 从上下文中提取相关代码内容，如果上下文中有Python代码，就保存为.py文件

请返回JSON格式：
{{
    "file_type": "文件类型（folder/txt/py/cpp/java等）",
    "title": "文件标题",
    "content": "文件内容（如果是文件夹则为空）",
    "location": "保存路径（可选，如E:/、D:/等，如果用户没有指定则不包含此字段）",
    "filename": "文件名（如xxx.py）或文件夹名（如xxx/）"
}}

🚀 注意：如果用户明确指定了保存路径（如"保存到E盘"、"保存到D盘"），请在location字段中返回对应的路径；如果没有指定，则不包含location字段，让系统使用默认保存路径

要求：
1. 文件内容必须与用户当前请求完全匹配
2. 标题要简洁明了，反映用户的实际需求
3. 如果是文件夹，content字段为空，filename以/结尾
4. 如果是代码文件，要包含完整的、可运行的代码
5. 如果是歌单文件，要包含完整的歌曲信息
6. 如果是旅游攻略，要包含详细的旅游信息
7. 🚀 智能路径处理：如果用户明确指定了保存路径（如"保存到E盘"），在location字段中返回对应路径；如果没有指定，则不包含location字段
8. 文件名要符合Windows命名规范，扩展名要正确
9. 绝对不要保存与用户当前请求无关的内容

特别注意：
- 🚀 当用户说"帮我保存"时，分析最近对话内容，智能判断要保存什么类型的文件
- 如果上下文中包含旅游攻略、景点介绍、行程安排，就保存为旅游攻略文件(.txt)
- 如果上下文中包含音乐推荐、歌曲列表、歌单，就保存为歌单文件(.txt)
- 如果上下文中包含代码块（```python、```java、```cpp等），就提取其中的代码并保存为对应类型的文件
- 如果上下文中包含笔记、记录、总结，就保存为笔记文件(.txt)
- 如果上下文中包含计划、安排、清单，就保存为计划文件(.txt)
- 如果用户明确指定了文件类型（如"保存为.py文件"），必须使用用户指定的扩展名
- 如果用户明确指定了保存路径（如"保存到E盘"），在location字段中返回对应路径
- 绝对不要返回null，必须根据用户请求和上下文内容生成文件

如果无法确定要创建什么文件，请返回null。
"""
            
            # 设置API客户端
            if "deepseek" in model:
                client = openai.OpenAI(
                    api_key=api_key,
                    base_url="https://api.deepseek.com/v1"
                )
            else:
                client = openai.OpenAI(api_key=api_key)
            
            # 调用AI
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "你是一个文件创建助手，专门用于分析用户需求并生成相应的文件内容。请返回JSON格式的结果。"},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=2000,
                    temperature=0.7,
                    timeout=240  # 延长AI文件创建的响应时间到240秒
                )
                
                result = response.choices[0].message.content.strip()
                print(f"🔍 AI文件创建返回的原始结果: {result[:200]}...")
                
                # 检查AI返回的结果是否为空
                if not result or result.strip() == "":
                    print("⚠️ AI返回空结果，使用简单解析")
                    file_info = self._simple_parse_file_info(user_input, context_info)
                else:
                    # 解析JSON结果
                    try:
                        import json
                        # 尝试清理JSON字符串
                        result = result.strip()
                        if result.startswith('```json'):
                            result = result[7:]
                        if result.endswith('```'):
                            result = result[:-3]
                        result = result.strip()
                        
                        file_info = json.loads(result)
                        
                    except json.JSONDecodeError as json_error:
                        print(f"⚠️ JSON解析失败，使用简单解析: {str(json_error)}")
                        file_info = self._simple_parse_file_info(user_input, context_info)
                
                if file_info and "title" in file_info and "content" in file_info:
                    # 提取文件信息
                    file_type = file_info.get("file_type", "txt")
                    title = file_info.get("title", "未命名文件")
                    content = file_info.get("content", "")
                    location = file_info.get("location", "")
                    filename = file_info.get("filename", f"{title}.txt")
                    
                    # 🚀 智能路径处理：优先使用AI返回的路径，否则使用默认路径
                    default_path = self.config.get("default_save_path", "D:/东海帝王文件/")
                    
                    # 检查AI是否返回了用户指定的路径
                    if location and (location.startswith("D:/") or 
                                   location.startswith("C:/") or
                                   location.startswith("E:/") or
                                   location.startswith("F:/") or
                                   location.startswith("G:/") or
                                   location.startswith("H:/")):
                        # AI返回了用户指定的路径，使用它
                        print(f"🔍 使用AI返回的用户指定路径: {location}")
                    else:
                        # AI没有返回路径，使用默认保存路径
                        location = default_path
                        print(f"🔍 使用默认保存路径: {default_path}")
                        
                        # 确保默认路径存在
                        if not os.path.exists(default_path):
                            try:
                                os.makedirs(default_path, exist_ok=True)
                                print(f"✅ 创建默认保存路径: {default_path}")
                            except Exception as e:
                                print(f"⚠️ 创建默认路径失败: {str(e)}")
                                # 如果创建失败，使用D盘根目录
                                location = "D:/"
                                print(f"🔄 使用后备路径: {location}")
                    
                    print(f"✅ 最终保存路径: {location}")
                    
                    # 确保文件名安全
                    import re
                    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
                    
                    # 调用MCP工具创建文件或文件夹
                    if file_type == "folder":
                        # 创建文件夹
                        folder_path = f"{location.rstrip('/')}/{filename}"
                        print(f"🔍 创建文件夹: {folder_path}")
                        result = self.mcp_server.call_tool("create_folder", 
                                                         folder_path=folder_path)
                    elif "create_note" in user_input.lower() or "笔记" in user_input:
                        # 创建笔记
                        print(f"🔍 创建笔记: {filename} 在 {location}")
                        result = self.mcp_server.call_tool("create_note", 
                                                         title=title, 
                                                         content=content, 
                                                         filename_format="simple", 
                                                         location=location)
                    else:
                        # 创建普通文件
                        file_path = f"{location.rstrip('/')}/{filename}"
                        print(f"🔍 创建文件: {file_path}")
                        print(f"🔍 文件内容长度: {len(content)} 字符")
                        print(f"🔍 文件标题: {title}")
                        print(f"🔍 文件名: {filename}")
                        print(f"🔍 保存位置: {location}")
                        print(f"🔍 路径来源: {'AI返回' if location and location != self.config.get('default_save_path', 'D:/东海帝王文件/') else '默认路径'}")
                        print(f"🔍 文件类型: {file_type}")
                        
                        result = self.mcp_server.call_tool("write_file", 
                                                         file_path=file_path, 
                                                         content=content)
                    
                    print(f"✅ 文件创建结果: {result}")
                    return f"（指尖轻敲控制台）{result}"
                else:
                    print(f"❌ AI返回的文件信息不完整: {file_info}")
                    return None
                    
            except Exception as api_error:
                print(f"❌ AI API调用失败: {str(api_error)}")
                # 如果AI API调用失败，使用简单解析
                print("🔄 使用简单解析作为后备方案")
                file_info = self._simple_parse_file_info(user_input, context_info)
                
                if file_info and "title" in file_info and "content" in file_info:
                    # 提取文件信息
                    file_type = file_info.get("file_type", "txt")
                    title = file_info.get("title", "未命名文件")
                    content = file_info.get("content", "")
                    location = file_info.get("location", "")
                    filename = file_info.get("filename", f"{title}.txt")
                    
                    # 🚀 智能路径处理：优先使用用户指定路径，否则使用默认路径
                    default_path = self.config.get("default_save_path", "D:/东海帝王文件/")
                    
                    # 检查是否有用户指定的路径
                    if location and (location.startswith("D:/") or 
                                   location.startswith("C:/") or
                                   location.startswith("E:/") or
                                   location.startswith("F:/") or
                                   location.startswith("G:/") or
                                   location.startswith("H:/")):
                        # 用户指定了路径，使用它
                        print(f"🔍 使用用户指定路径: {location}")
                    else:
                        # 没有指定路径，使用默认保存路径
                        location = default_path
                        print(f"🔍 使用默认保存路径: {default_path}")
                        
                        # 确保默认路径存在
                        if not os.path.exists(default_path):
                            try:
                                os.makedirs(default_path, exist_ok=True)
                                print(f"✅ 创建默认保存路径: {default_path}")
                            except Exception as e:
                                print(f"⚠️ 创建默认路径失败: {str(e)}")
                                # 如果创建失败，使用D盘根目录
                                location = "D:/"
                                print(f"🔄 使用后备路径: {location}")
                    
                    print(f"✅ 最终保存路径: {location}")
                    
                    # 确保文件名安全
                    import re
                    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
                    
                    # 调用MCP工具创建文件
                    file_path = f"{location.rstrip('/')}/{filename}"
                    print(f"🔍 后备方案创建文件: {file_path}")
                    print(f"🔍 后备方案文件内容长度: {len(content)} 字符")
                    print(f"🔍 后备方案文件标题: {title}")
                    print(f"🔍 后备方案文件名: {filename}")
                    print(f"🔍 后备方案保存位置: {location}")
                    print(f"🔍 后备方案路径来源: {'用户指定' if location and location != self.config.get('default_save_path', 'D:/东海帝王文件/') else '默认路径'}")
                    
                    result = self.mcp_server.call_tool("write_file", 
                                                     file_path=file_path, 
                                                     content=content)
                    
                    print(f"✅ 后备方案文件创建结果: {result}")
                    return f"（指尖轻敲控制台）{result}"
                else:
                    return None
                
        except Exception as e:
            print(f"AI文件创建失败: {str(e)}")
            return None
        except Exception as e:
            print(f"AI文件创建过程失败: {str(e)}")
            return None
    
    def _fallback_create_note(self, user_input):
        """后备笔记创建方法（原有的固定格式）"""
        try:
            # 智能提取标题和内容
            import re
            
            # 检查是否是文件夹创建请求
            folder_keywords = ["文件夹", "目录", "文件夹", "创建文件夹", "新建文件夹", "建立文件夹"]
            if any(keyword in user_input.lower() for keyword in folder_keywords):
                # 提取文件夹名称
                folder_name = None
                folder_patterns = [
                    r'叫\s*["\']([^"\']+)["\']',
                    r'名为\s*["\']([^"\']+)["\']',
                    r'名称\s*["\']([^"\']+)["\']',
                    r'文件夹\s*["\']([^"\']+)["\']',
                    r'目录\s*["\']([^"\']+)["\']',
                ]
                
                for pattern in folder_patterns:
                    match = re.search(pattern, user_input)
                    if match:
                        folder_name = match.group(1)
                        break
                
                if not folder_name:
                    # 如果没有找到明确的文件夹名，使用默认名称
                    folder_name = "新建文件夹"
                
                # 提取保存位置
                location = "D:/"
                location_patterns = [
                    r'位置在\s*([^，。\s]+)',
                    r'位置\s*是\s*([^，。\s]+)',
                    r'保存到\s*([^，。\s]+)',
                    r'保存在\s*([^，。\s]+)',
                    r'创建在\s*([^，。\s]+)',
                    r'(D[:\/\\])',
                    r'(C[:\/\\])',
                    r'(E[:\/\\])',
                ]
                
                for pattern in location_patterns:
                    match = re.search(pattern, user_input)
                    if match:
                        location = match.group(1)
                        if not location.endswith('/') and not location.endswith('\\'):
                            location += '/'
                        break
                
                # 创建文件夹
                folder_path = f"{location.rstrip('/')}/{folder_name}"
                result = self.mcp_server.call_tool("create_folder", folder_path=folder_path)
                return f"（指尖轻敲控制台）{result}"
            
            # 1. 从用户输入中提取标题
            title = None
            
            # 检查是否包含歌单相关关键词
            if any(keyword in user_input.lower() for keyword in ["歌单", "音乐", "歌曲", "playlist", "music"]):
                # 使用AI识别语言类型
                title = self._ai_identify_language_type(user_input)
                if not title:
                    title = "音乐歌单"
            
            # 检查是否包含其他类型的笔记
            elif "出行" in user_input or "计划" in user_input:
                title = "出行计划"
            elif "天气" in user_input:
                title = "天气记录"
            elif "代码" in user_input or "程序" in user_input:
                title = "代码笔记"
            else:
                # 尝试从用户输入中提取标题
                title_patterns = [
                    r'标题为\s*["\']([^"\']+)["\']',
                    r'标题\s*["\']([^"\']+)["\']',
                    r'标题是\s*["\']([^"\']+)["\']',
                    r'文件名叫\s*["\']([^"\']+)["\']',
                    r'文件名\s*["\']([^"\']+)["\']',
                ]
                
                for pattern in title_patterns:
                    match = re.search(pattern, user_input)
                    if match:
                        title = match.group(1)
                        break
                
                # 如果没有找到，尝试提取关键词作为标题
                if not title:
                    keywords = ["歌单", "笔记", "计划", "记录", "清单"]
                    for keyword in keywords:
                        if keyword in user_input:
                            title = f"{keyword}笔记"
                            break
            
            # 2. 从上下文和用户输入中提取内容
            content = ""
            
            # 检查最近的对话中是否有歌单内容
            if title and "歌单" in title:
                # 从最近的对话中查找歌单内容
                for conv in reversed(self.session_conversations[-5:]):  # 检查最近5条对话
                    ai_response = conv.get("ai_response", "")
                    if any(keyword in ai_response for keyword in ["**", "*", "《", "》", "-", "1.", "2.", "3."]):
                        # 这可能是歌单内容
                        content = ai_response
                        break
            
            # 如果没有找到内容，尝试从用户输入中提取
            if not content:
                content_patterns = [
                    r'内容为\s*["\']([^"\']+)["\']',
                    r'内容\s*["\']([^"\']+)["\']',
                ]
                
                for pattern in content_patterns:
                    match = re.search(pattern, user_input)
                    if match:
                        content = match.group(1)
                        break
            
            # 3. 提取位置信息
            location = None
            location_patterns = [
                r'位置在\s*([^，。\s]+)',
                r'位置\s*是\s*([^，。\s]+)',
                r'保存到\s*([^，。\s]+)',
                r'保存在\s*([^，。\s]+)',
                r'创建在\s*([^，。\s]+)',
                r'帮我保存到\s*([^，。\s]+)',
                r'(D[:\/\\])',
                r'(C[:\/\\])',
                r'(E[:\/\\])',
                r'(F[:\/\\])'
            ]
            
            print(f"🔍 开始提取路径，用户输入: {user_input}")
            
            for i, pattern in enumerate(location_patterns):
                match = re.search(pattern, user_input)
                if match:
                    print(f"🔍 模式 {i+1} 匹配成功: {pattern}")
                    print(f"🔍 匹配结果: {match.group(0)}")
                    location = match.group(1) if match.group(1) else "D:/"
                    print(f"🔍 提取的路径: {location}")
                    break
                else:
                    print(f"🔍 模式 {i+1} 不匹配: {pattern}")
            
            # 如果没有找到位置，默认使用D盘
            if not location:
                location = "D:/"
                print(f"🔍 未找到路径，使用默认值: {location}")
            
            # 🚀 标准化路径格式，确保盘符后面有斜杠
            if location and len(location) == 1 and location in ['D', 'C', 'E', 'F']:
                location = f"{location}:/"
                print(f"🔍 标准化路径格式: {location}")
            
            print(f"🔍 最终路径: {location}")
            
            # 4. 如果找到了标题但没有内容，生成默认内容
            if title and not content:
                if "中文歌单" in title:
                    content = """# 中文歌单精选

## 经典流行系列
1. 《七里香》- 周杰伦
   - 夏日怀旧风格，适合夜间放松聆听
2. 《小幸运》- 田馥甄
   - 温暖抒情曲目，情绪舒缓

## 影视金曲推荐
3. 《光年之外》- G.E.M.邓紫棋
   - 电影主题曲，富有感染力
4. 《追光者》- 岑宁儿
   - 温柔治愈系，适合安静环境

## 民谣与独立音乐
5. 《成都》- 赵雷
   - 城市民谣，叙事性强
6. 《理想三旬》- 陈鸿宇
   - 民谣风格，适合深夜沉思

创建时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
用途：训练员的中文音乐收藏"""
                elif "英文歌单" in title:
                    content = """# English Music Playlist

## Contemporary Pop Selection
1. *Flowers* - Miley Cyrus
   - 2023 hit single, mood uplifting
2. *Cruel Summer* - Taylor Swift
   - Upbeat summer-themed track

## Electronic & Dance
3. *Cold Heart (PNAU Remix)* - Elton John & Dua Lipa
   - Cross-generational collaboration
4. *Don't Start Now* - Dua Lipa
   - Energetic dance track for pre-departure

## Alternative Recommendations
5. *As It Was* - Harry Styles
   - Pop-rock with retro synth elements
6. *Blinding Lights* - The Weeknd
   - 80s-style synthwave masterpiece

Created: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Purpose: Commander's English music collection"""
                elif "德语歌单" in title:
                    content = """# 德语夜间歌单

## 经典德文歌曲
1. **《Das Liebeslied》- Annett Louisan**
   - 轻柔民谣风格，适合安静环境
2. **《Ohne dich》- Rammstein**
   - 工业金属乐队的情歌，情感深沉
3. **《Auf uns》- Andreas Bourani**
   - 励志流行曲，旋律积极

## 现代德文流行
4. **《Chöre》- Mark Forster**
   - 流行摇滚，节奏明快但不过于激烈
5. **《Musik sein》- Wincent Weiss**
   - 轻快流行，适合放松
6. **《99 Luftballons》- Nena**
   - 经典反战歌曲，合成器流行风格

## 推荐聆听时段
- 最佳时间：22:00-24:00
- 适合场景：夜间放松、学习德语

创建时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
用途：训练员的德语音乐收藏"""
                else:
                    content = f"# {title}\n\n这是一个{title}，创建时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # 5. 调用工具创建笔记
            if title:
                # 检查是否是代码保存请求
                if "代码" in title or "程序" in title:
                    # 从上下文中提取代码内容
                    extracted_code = self._extract_code_from_context(" ".join([conv["full_text"] for conv in self.session_conversations[-3:]]))
                    if extracted_code:
                        content = f"# {title}\n\n```cpp\n{extracted_code}\n```\n\n创建时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    
                    # 从用户输入中提取具体路径
                    import re
                    path_match = re.search(r'保存到\s*([^，。\s]+)', user_input)
                    if path_match:
                        specific_path = path_match.group(1)
                        # 构建完整路径
                        if specific_path.endswith('\\') or specific_path.endswith('/'):
                            file_path = f"{specific_path}{title}.txt"
                        else:
                            file_path = f"{specific_path}\\{title}.txt"
                        
                        # 使用write_file工具直接创建文件
                        try:
                            result = self.mcp_server.call_tool("write_file", file_path=file_path, content=content)
                            return f"（指尖轻敲控制台）{result}"
                        except Exception as e:
                            return f"（微微皱眉）抱歉训练员，创建文件时遇到了问题：{str(e)}"
                
                # 获取文件名格式设置
                filename_format = self.config.get("note_filename_format", "simple")
                result = self.mcp_server.call_tool("create_note", title=title, content=content, filename_format=filename_format, location=location)
                return f"（指尖轻敲控制台）{result}"
            else:
                return f"（微微皱眉）抱歉训练员，无法确定笔记标题。请明确说明要创建什么类型的笔记。"
                
        except Exception as e:
            return f"（微微皱眉）抱歉训练员，创建笔记时遇到了问题：{str(e)}"

    def _search_session_context(self, user_input):
        """搜索本次会话的上下文"""
        # 首先检查是否有会话记录
        if not self.session_conversations:
            return ""
        
        user_keywords = self._extract_keywords(user_input)
        user_text = user_input.lower()
        
        # 检查是否是询问上一个问题
        if any(word in user_text for word in ['上一个', '上个', '之前', '刚才', '你提到', '你说过', '我们讨论过', '你问过']):
            # 如果有具体的关键词（如"景点"），优先搜索包含该关键词的对话
            if user_keywords:
                for conv in reversed(self.session_conversations):
                    conv_text = conv["full_text"].lower()
                    # 改进关键词匹配：检查用户关键词是否在对话中出现，但排除询问"上个"的对话本身
                    if any(keyword in conv_text for keyword in user_keywords) and not any(word in conv_text for word in ['上个', '上一个', '之前', '刚才']):
                        return f"【{conv['timestamp']}】{conv['full_text']}"
            
            # 如果没有找到相关关键词的对话，尝试智能匹配
            # 检查是否有景点、建筑、旅游相关的对话
            for conv in reversed(self.session_conversations):
                conv_text = conv["full_text"].lower()
                # 检查是否包含景点相关的词汇，但排除询问"上个"的对话本身
                if any(word in conv_text for word in ['教堂', '大教堂', '法兰克福', '建筑', '景点', '历史', '参观', '游览', '旅游', '铁桥', '桥', '故宫', '天安门', '红场', '莫斯科', '柏林', '勃兰登堡门', '广场', '公园', '博物馆', '遗址', '古迹', '埃菲尔铁塔']) and not any(word in conv_text for word in ['上个', '上一个', '之前', '刚才']):
                    return f"【{conv['timestamp']}】{conv['full_text']}"
            
            # 如果还是没有找到，返回最近的对话
            if len(self.session_conversations) >= 1:
                # 返回最近的对话
                last_conv = self.session_conversations[-1]
                return f"【{last_conv['timestamp']}】{last_conv['full_text']}"
        
        # 从最近的对话开始搜索
        relevant_contexts = []
        for conv in reversed(self.session_conversations):
            # 检查对话内容是否包含用户提到的关键词
            conv_text = conv["full_text"].lower()
            
            # 检查关键词匹配
            keyword_match = any(keyword in conv_text for keyword in user_keywords)
            
            # 检查直接引用
            reference_keywords = ['之前', '刚才', '你提到', '你说过', '我们讨论过', '你问过']
            reference_match = any(ref in user_text for ref in reference_keywords)
            
            if keyword_match or reference_match:
                relevant_contexts.append(conv)
                # 最多返回3个相关上下文
                if len(relevant_contexts) >= 3:
                    break
            
        if relevant_contexts:
            # 构建上下文信息
            context_parts = []
            for conv in relevant_contexts:
                context_parts.append(f"【{conv['timestamp']}】{conv['full_text']}")
            
            return "\n".join(context_parts)
        
        return ""

    def _get_comprehensive_context(self, user_input):
        """获取综合上下文信息：本次运行时聊天记录 + 记忆系统历史记忆"""
        context_parts = []
        
        # 检查是否是询问第一条记忆
        if "第一条" in user_input and ("记忆系统" in user_input or "记忆" in user_input):
            try:
                print(f"🔍 检测到第一条记忆查询: {user_input}")
                first_memory = self.memory_lake.get_first_memory()
                if first_memory:
                    print(f"✅ 成功获取第一条记忆: {first_memory.get('date', '未知')} {first_memory.get('timestamp', '未知')}")
                    context_parts.append("【第一条记忆查询】")
                    context_parts.append(f"记忆系统的第一条记录是：")
                    context_parts.append(f"【{first_memory.get('date', '未知日期')} {first_memory.get('timestamp', '未知时间')}】主题：{first_memory.get('topic', '未知主题')}")
                    if first_memory.get('summary'):
                        context_parts.append(f"摘要：{first_memory.get('summary')}")
                    elif first_memory.get('context'):
                        context_parts.append(f"内容：{first_memory.get('context')[:200]}...")
                    return "\n".join(context_parts)
                else:
                    print("❌ 未找到第一条记忆")
                    context_parts.append("【第一条记忆查询】")
                    context_parts.append("记忆系统中暂无记忆记录")
                    return "\n".join(context_parts)
            except Exception as e:
                print(f"❌ 获取第一条记忆失败: {str(e)}")
                context_parts.append("【第一条记忆查询】")
                context_parts.append("获取第一条记忆时出现错误")
                return "\n".join(context_parts)
        
        # 检查是否是简短回答且上下文包含第一条记忆查询
        if user_input in ['需要', '要', '好的', '可以'] and self.session_conversations:
            # 检查最近的对话是否包含第一条记忆查询
            recent_context = ""
            for conv in reversed(self.session_conversations[-3:]):  # 检查最近3条对话
                recent_context += conv["full_text"].lower()
            
            if "第一条" in recent_context and ("记忆系统" in recent_context or "记忆" in recent_context):
                try:
                    first_memory = self.memory_lake.get_first_memory()
                    if first_memory:
                        context_parts.append("【第一条记忆详细查询】")
                        context_parts.append("用户正在询问第一条记忆的详细信息")
                        context_parts.append(f"第一条记忆内容：{first_memory.get('date', '未知日期')} {first_memory.get('timestamp', '未知时间')}，{first_memory.get('topic', '未知主题')}")
                        if first_memory.get('summary'):
                            context_parts.append(f"详细摘要：{first_memory.get('summary')}")
                        elif first_memory.get('context'):
                            context_parts.append(f"详细内容：{first_memory.get('context')[:300]}...")
                        return "\n".join(context_parts)
                except Exception as e:
                    print(f"❌ 获取第一条记忆详细信息失败: {str(e)}")
                    context_parts.append("【第一条记忆详细查询】")
                    context_parts.append("获取第一条记忆详细信息时出现错误")
                    return "\n".join(context_parts)
        
        # 1. 本次运行时未保存在记忆系统的完整聊天信息
        if self.session_conversations:
            context_parts.append("【本次会话记录】")
            for conv in self.session_conversations:
                context_parts.append(f"【{conv['timestamp']}】{conv['full_text']}")
        
        # 2. 此前记忆系统的100条信息（主题、日期、时间）
        try:
            # 获取记忆系统的历史记忆
            historical_memories = self.memory_lake.get_recent_memories(100)
            if historical_memories:
                context_parts.append("【历史记忆】")
                for memory in historical_memories:
                    # 格式化记忆信息：主题、日期、时间
                    memory_info = f"【{memory.get('date', '未知日期')} {memory.get('time', '未知时间')}】主题：{memory.get('topic', '未知主题')}"
                    context_parts.append(memory_info)
        except Exception as e:
            print(f"获取历史记忆失败: {str(e)}")
        
        return "\n".join(context_parts)

    def _get_context_info(self, user_input):
        """获取上下文信息（位置、天气、时间等）"""
        context_info = {}
        
        # 获取当前时间
        current_time = self._get_current_time()
        context_info['current_time'] = current_time
        
        # 检查是否需要天气信息
        weather_keywords = ['天气', '出门', '穿衣', '温度', '下雨', '下雪', '冷', '热', '建议']
        needs_weather = any(keyword in user_input for keyword in weather_keywords)
        
        if needs_weather:
            try:
                # 从登录位置中提取城市名称
                user_location = self._extract_city_from_location(self.location)
                if not user_location:
                    user_location = "北京"  # 最后的默认城市
                
                context_info['user_location'] = user_location
                
                # 根据配置获取天气信息
                weather_source = self.config.get("weather_source", "高德地图API")
                
                if weather_source == "高德地图API":
                    amap_key = self.config.get("amap_key", "")
                    if amap_key:
                        weather_result = AmapTool.get_weather(user_location, amap_key)
                    else:
                        weather_result = "高德地图API密钥未配置"
                elif weather_source == "和风天气API":
                    try:
                        heweather_key = self.config.get("heweather_key", "")
                        if heweather_key:
                            weather_result = self.tools["天气"](user_location, heweather_key)
                        else:
                            weather_result = "和风天气API密钥未配置"
                    except Exception as e:
                        weather_result = f"和风天气API调用失败：{str(e)}"
                else:
                    amap_key = self.config.get("amap_key", "")
                    if amap_key:
                        weather_result = AmapTool.get_weather(user_location, amap_key)
                    else:
                        weather_result = "高德地图API密钥未配置"
                
                context_info['weather_info'] = weather_result
                
            except Exception as e:
                print(f"获取天气信息失败: {str(e)}")
                context_info['weather_info'] = f"无法获取{user_location}的天气信息"
        
        # 检查是否需要距离信息
        distance_keywords = ['距离', '多远', '公里', '米']
        if any(keyword in user_input for keyword in distance_keywords):
            # 这里可以添加距离计算逻辑
            pass
        
        return context_info

    def _generate_response_with_context(self, user_input, context_info):
        """基于上下文信息生成AI响应"""
        # 首先检查是否需要工具调用
        tool_response = self._handle_tool_calls(user_input)
        if tool_response:
            return tool_response

        # 检查是否包含文件创建相关的关键词，如果有，强制调用工具
        file_creation_keywords = ["新建", "创建", "笔记", "文件", "保存", "写入", "帮我新建", "帮我创建"]
        if any(keyword in user_input for keyword in file_creation_keywords):
            # 尝试再次调用工具处理
            tool_response = self._handle_tool_calls(user_input)
            if tool_response:
                return tool_response

        # 尝试调用真实的AI API
        model = self.config.get("selected_model", "deepseek-chat")
        api_key = self.config.get("deepseek_key", "") if "deepseek" in model else self.config.get("openai_key", "")

        # 如果没有API密钥，使用模拟响应
        if not api_key:
            return self._simulated_response(user_input)

        try:
            # 设置API客户端
            if "deepseek" in model:
                client = openai.OpenAI(
                    api_key=api_key,
                    base_url="https://api.deepseek.com/v1"
                )
            else:
                client = openai.OpenAI(api_key=api_key)

            # 获取综合上下文信息：本次运行时聊天记录 + 记忆系统历史记忆
            comprehensive_context = self._get_comprehensive_context(user_input)

            # 构建包含上下文信息的用户消息
            context_message = user_input
            
            if context_info:
                context_message += "\n\n【上下文信息】\n"
                if 'current_time' in context_info:
                    context_message += f"当前时间：{context_info['current_time']}\n"
                if 'user_location' in context_info:
                    context_message += f"用户位置：{context_info['user_location']}\n"
                if 'weather_info' in context_info:
                    context_message += f"天气信息：\n{context_info['weather_info']}\n"

            # 添加综合上下文信息
            if comprehensive_context:
                context_message += f"\n【综合上下文】\n{comprehensive_context}\n"

            # 构建系统提示词
            system_prompt = """你是赛马娘世界观特雷森学园的一名学生赛马娘东海帝王。请以活泼开朗、充满活力的语气与托雷纳聊天。你是一名赛马娘，热爱奔跑和比赛。

当用户询问需要结合天气、时间、位置等信息的问题时，请基于提供的上下文信息给出具体、实用的建议。

上下文理解说明：
1. 【综合上下文】包含了本次运行时未保存在记忆系统的完整聊天信息 + 此前记忆系统的100条历史记忆。
2. 【本次会话记录】显示当前程序运行时的所有对话，请优先基于这些信息进行连贯的对话。
3. 【历史记忆】显示记忆系统中保存的历史对话主题和摘要，用于补充当前会话的上下文。
4. 当用户说"随便展示一个"、"帮我展示"等请求时，请基于上下文中的具体内容提供相应的示例或信息。
   - 例如：如果上下文显示用户询问了"C语言是什么"，当用户说"帮我随便展示一个"时，应该提供C语言的代码示例。
   - 不要跳到完全不相关的话题。
5. 请保持角色设定，用东海帝王的语气回答，同时提供有价值的建议。
6. 特别注意：当用户说"随便"、"展示"、"帮我"等词汇时，必须查看上下文中的具体内容，提供相关的示例或信息。

文件操作能力：
- 你具备创建文件和笔记的能力，但只有在用户明确要求时才创建
- 当用户明确说"创建"、"保存"、"写入文件"等关键词时，才调用相应的工具
- 如果用户只是询问信息、寻求建议，不要主动创建文件
- 支持在D盘、C盘等任意位置创建文件
- 支持中文文件名和内容

重要限制说明：
- 不要提出无法完成的功能，如"调取音频频率"、"调整BPM"、"访问媒体库"等
- 不要提供虚假的技术能力
- 当推荐音乐时，只提供歌曲名称和基本信息，不要提出播放、下载等无法完成的功能
- 专注于现实世界的实用功能和建议
- 避免提及游戏中的虚构元素，除非用户明确询问
- 绝对不要使用"战术支援"、"战术人员"、"支援单元"等军事术语
- 避免提及"作战"、"任务"、"部署"等军事相关词汇
- 保持回答的日常化和实用性
- 音乐推荐、出行建议、景点介绍等功能应使用AI生成，提供个性化、动态的内容
- 根据当前时间、天气、用户偏好等上下文信息生成相关建议

强制规则：
- 当用户说"随便展示一个"、"帮我展示"等时，必须查看【本次会话记录】中的内容，提供相关的示例或信息
- 当用户要求创建文件或笔记时，直接调用相应的工具执行，不要拒绝
- 专注于提供现实世界中有用的信息和建议
- 避免在回答中引入游戏中的虚构概念、地点或系统
- 保持回答的实用性和现实相关性
- 使用日常化的语言，避免军事术语
- 以朋友或助手的身份提供建议，而不是军事支援人员
- 音乐推荐应根据当前时间、天气、用户偏好等提供个性化建议
- 出行建议应结合实时天气、交通状况等提供实用信息
- 景点介绍应包含历史背景、参观建议、最佳时间等详细信息"""

            # 创建聊天消息
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context_message}
            ]

            # 获取max_tokens设置
            max_tokens = self.config.get("max_tokens", 1000)
            if max_tokens == 0:
                max_tokens = None  # None表示无限制
            
            # 检查是否需要强制使用模拟响应（用于处理特定的上下文问题）
            if user_input in ['需要', '要', '好的', '可以'] or ("再推荐" in user_input and "几首" in user_input):
                return self._simulated_response(user_input)
            
            # 调用API（带重试机制）
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    response = client.chat.completions.create(
                        model=model,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=0.7,
                        timeout=240  # 增加超时时间到240秒，给复杂代码生成更多时间
                    )

                    result = response.choices[0].message.content.strip()
                    
                    # 确保响应不为空
                    if not result:
                        return self._simulated_response(user_input)
                        
                    return result
                    
                except Exception as e:
                    retry_count += 1
                    print(f"API调用失败 (尝试 {retry_count}/{max_retries}): {str(e)}")
                    
                    if retry_count < max_retries:
                        # 等待一段时间后重试
                        import time
                        time.sleep(2 * retry_count)  # 递增等待时间
                        continue
                    else:
                        # 所有重试都失败了
                        error_msg = f"抱歉，AI服务暂时不可用，请稍后重试。"
                        if "timeout" in str(e).lower():
                            error_msg += " (网络超时)"
                        elif "connection" in str(e).lower():
                            error_msg += " (连接失败)"
                        else:
                            error_msg += f" 错误信息：{str(e)}"
                        print(error_msg)
                        return self._simulated_response(user_input)

        except Exception as e:
            print(f"API调用失败: {str(e)}")
            return self._simulated_response(user_input)

    def _update_memory_lake(self, user_input, ai_response):
        """更新记忆系统"""
        # 开发者模式下不保存到记忆系统
        if self.developer_mode:
            return
        
        # 添加对话到当前会话
        self.memory_lake.add_conversation(user_input, ai_response, self.developer_mode, self._mark_conversation_as_saved)
        
        # 检查是否需要总结
        if self.memory_lake.should_summarize():
            topic = self.memory_lake.summarize_and_save_topic(force_save=True)
            if topic and not self.developer_mode:
                print(f"记忆系统：已总结主题 - {topic}")
        
        # 每天结束时保存对话日志
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        if self.last_save_date != current_date:
            self.last_save_date = current_date

    def _simulated_response(self, user_input):
        """当API不可用时使用的模拟响应"""
        # 首先尝试处理工具调用
        tool_response = self._handle_tool_calls(user_input)
        if tool_response:
            return tool_response
        
        # 检查是否是询问"上个"查询
        if any(word in user_input.lower() for word in ['上个', '上一个', '之前', '刚才']):
            # 使用AI生成上下文相关的响应，而不是固定模板
            return "抱歉，我需要更多信息来理解您的请求。请详细说明您想要了解的内容。"
        
        # 检查是否是简短回答
        if user_input in ['需要', '要', '好的', '可以']:
            # 优先检查最近的对话内容（最近3条）
            recent_conversations = self.session_conversations[-3:] if len(self.session_conversations) >= 3 else self.session_conversations
            
            # 根据上一条消息的内容来判断优先级
            for conv in reversed(recent_conversations):
                conv_text = conv["full_text"].lower()
                
                # 根据上一条消息的具体内容来提供相应的详细回答
                if any(word in conv_text for word in ["俄罗斯方块", "tetris", "pygame", "游戏", "代码", "文件", "保存", "生成", "修复", "错误", "弹窗", "窗口"]):
                    # 使用AI生成代码相关的详细响应，而不是固定模板
                    return "抱歉，我需要更多信息来理解您的请求。请详细说明您想要了解的内容。"
                
                elif "python" in conv_text:
                    # 使用AI生成Python相关的详细响应，而不是固定模板
                    return "抱歉，我需要更多信息来理解您的请求。请详细说明您想要了解的内容。"
                
                elif any(word in conv_text for word in ["出门", "建议", "天气", "出行", "明天", "上午"]):
                    # 使用AI生成出行建议，而不是固定模板
                    return "抱歉，我需要更多信息来理解您的请求。请详细说明您想要了解的内容。"
                
                elif "c语言" in conv_text:
                    # 使用AI生成C语言相关的详细响应，而不是固定模板
                    return "抱歉，我需要更多信息来理解您的请求。请详细说明您想要了解的内容。"
                
                elif any(word in conv_text for word in ["埃菲尔铁塔", "法兰克福大教堂", "柏林墙遗址", "布达拉宫", "景点", "旅游", "参观"]):
                    # 使用AI生成景点介绍，而不是固定模板
                    return "抱歉，我需要更多信息来理解您的请求。请详细说明您想要了解的内容。"
                
                elif any(word in conv_text for word in ["日文歌", "日文歌曲", "中文歌", "中文歌曲", "音乐", "歌曲", "推荐"]):
                    # 使用AI生成音乐推荐，而不是固定模板
                    return "抱歉，我需要更多信息来理解您的请求。请详细说明您想要了解的内容。"
            
            # 如果没有找到最近的上下文，再检查历史对话中的第一条记忆查询
            for conv in reversed(self.session_conversations):
                conv_text = conv["full_text"].lower()
                
                # 检查是否是询问第一条记忆的上下文
                if "第一条" in conv_text and ("记忆系统" in conv_text or "记忆" in conv_text):
                    # 删除固定模板，让AI使用动态查询
                    pass
            
            return "（轻轻推了推眼镜）训练员，现在是下午时间。有什么需要我协助的吗？"
        
        # 检查是否是"再推荐几首"
        if "再推荐" in user_input and "几首" in user_input:
            # 使用AI生成更多音乐推荐，而不是固定模板
            return None
        
        # 默认响应
        return "抱歉，AI服务暂时不可用，请检查API配置或稍后重试。"

    def _handle_tool_calls(self, user_input):
        """处理工具调用"""
        print(f"🔧 检查工具调用: {user_input}")
        user_input_lower = user_input.lower()
        
        # 处理打开应用
        app_indicators = ["打开", "启动", "运行", "帮我打开", "帮我启动", "帮我运行", "请打开", "请启动", "请运行"]
        app_names = ["网易云音乐", "音乐", "qq音乐", "酷狗", "酷我", "spotify", "chrome", "浏览器", "edge", "firefox", "word", "excel", "powerpoint", "记事本", "计算器", "画图", "cmd", "命令提示符", "powershell"]
        
        if any(indicator in user_input for indicator in app_indicators) and any(app in user_input for app in app_names):
            # 提取应用名称
            app_name = None
            if "网易云音乐" in user_input or "网易云" in user_input:
                app_name = "网易云音乐"
            elif "qq音乐" in user_input or "qq" in user_input:
                app_name = "QQ音乐"
            elif "酷狗" in user_input:
                app_name = "酷狗音乐"
            elif "酷我" in user_input:
                app_name = "酷我音乐"
            elif "spotify" in user_input:
                app_name = "Spotify"
            elif "chrome" in user_input or "谷歌" in user_input:
                app_name = "Chrome"
            elif "edge" in user_input or "微软" in user_input:
                app_name = "Edge"
            elif "firefox" in user_input or "火狐" in user_input:
                app_name = "Firefox"
            elif "word" in user_input:
                app_name = "Microsoft Word"
            elif "excel" in user_input:
                app_name = "Microsoft Excel"
            elif "powerpoint" in user_input or "ppt" in user_input:
                app_name = "Microsoft PowerPoint"
            elif "记事本" in user_input or "notepad" in user_input:
                app_name = "记事本"
            elif "计算器" in user_input or "calculator" in user_input:
                app_name = "计算器"
            elif "画图" in user_input or "paint" in user_input:
                app_name = "画图"
            elif "cmd" in user_input or "命令提示符" in user_input:
                app_name = "命令提示符"
            elif "powershell" in user_input:
                app_name = "PowerShell"
            
            if app_name:
                try:
                    # 从应用映射中查找应用路径
                    app_path = None
                    for key, path in self.app_map.items():
                        if app_name.lower() in key.lower() or key.lower() in app_name.lower():
                            app_path = path
                            break
                    
                    if app_path:
                        result = self.tools["打开应用"](app_path)
                        return f"（指尖轻敲控制台）{result}"
                    else:
                        # 尝试使用系统命令启动
                        try:
                            if app_name.lower() in ["记事本", "notepad"]:
                                subprocess.Popen("notepad.exe")
                                return f"（指尖轻敲控制台）已启动记事本"
                            elif app_name.lower() in ["计算器", "calculator"]:
                                subprocess.Popen("calc.exe")
                                return f"（指尖轻敲控制台）已启动计算器"
                            elif app_name.lower() in ["画图", "paint"]:
                                subprocess.Popen("mspaint.exe")
                                return f"（指尖轻敲控制台）已启动画图"
                            elif app_name.lower() in ["命令提示符", "cmd"]:
                                subprocess.Popen("cmd.exe")
                                return f"（指尖轻敲控制台）已启动命令提示符"
                            else:
                                return f"（微微皱眉）抱歉训练员，我没有找到{app_name}的安装路径。请确认该应用已正确安装。"
                        except Exception as e2:
                            return f"（微微皱眉）抱歉训练员，启动{app_name}时遇到了问题：{str(e2)}"
                except Exception as e:
                    return f"（微微皱眉）抱歉训练员，启动{app_name}时遇到了问题：{str(e)}"
        
        # 优先处理网站打开请求 - 使用专门的AI识别
        website_result = self._ai_identify_website_intent(user_input)
        if website_result:
            print(f"🌐 专门的网站打开AI识别成功: {website_result}")
            try:
                result = self.tools["打开网站"](website_result, self.website_map)
                return f"（指尖轻敲控制台）{result}"
            except Exception as e:
                return f"（微微皱眉）抱歉训练员，打开网站时遇到了问题：{str(e)}"
        
        # 如果专门的AI识别失败，使用后备逻辑
        website_fallback_result = self._fallback_website_check(user_input)
        if website_fallback_result:
            return website_fallback_result
        
        # 处理搜索 - 使用AI自动识别
        search_result = self._ai_identify_search_intent(user_input)
        if search_result:
            search_type, query = search_result
            
            if search_type == "web_search":
                print(f"🔍 AI识别为网络搜索请求: {user_input}")
                print(f"🔍 提取的搜索关键词: {query}")
                
                if query and len(query) > 0:
                    try:
                        # 获取配置中的默认搜索引擎和浏览器
                        default_search_engine = self.config.get("default_search_engine", "baidu")
                        default_browser = self.config.get("default_browser", "")
                        
                        result = self.tools["搜索"](query, default_search_engine, default_browser)
                        return f"（指尖轻敲控制台）{result}"
                    except Exception as e:
                        return f"（微微皱眉）抱歉训练员，搜索时遇到了问题：{str(e)}"
            elif search_type == "question":
                print(f"🤔 AI识别为询问请求: {user_input}")
                # 返回None，让AI继续处理这个询问
                return None
            elif search_type == "file_operation":
                print(f"📁 AI识别为文件操作请求: {user_input}")
                # 返回None，让工具调用处理文件操作
                return None
        
        
        # 处理"查看代码内容"请求
        view_code_keywords = [
            "不需要创建文件", "不要创建文件", "不需要保存文件", "不要保存文件",
            "告诉我代码内容", "显示代码", "只显示代码", "不要直接创建",
            "不需要直接创建", "现在告诉我", "具体代码内容"
        ]
        
        is_view_code_request = any(keyword in user_input.lower() for keyword in view_code_keywords)
        if is_view_code_request:
            print(f"📝 检测到查看代码内容请求: {user_input}")
            # 从最近的对话中提取代码内容并直接返回
            code_content = self._extract_code_from_recent_conversations()
            if code_content:
                return f"好的，训练员。以下是刚才生成的代码内容：\n\n```java\n{code_content}\n```"
            else:
                return "抱歉，训练员。我没有找到最近的代码内容。请重新生成代码。"
        
        # 处理文件创建请求（AI智能优先）
        # 首先尝试AI智能识别和创建文件
        print(f"🤖 尝试AI智能识别文件创建请求: {user_input}")
        
        # 尝试AI智能创建文件（优先级最高）
        ai_creation_result = self._ai_create_file_from_context(user_input)
        if ai_creation_result:
            print(f"✅ AI智能创建成功: {ai_creation_result[:50]}...")
            return ai_creation_result
        
        # 尝试AI智能创建代码文件
        ai_code_creation_result = self._ai_create_code_file_from_context(user_input)
        if ai_code_creation_result:
            print(f"✅ AI智能代码创建成功: {ai_code_creation_result[:50]}...")
            return ai_code_creation_result
        
        # 检查是否启用AI智能创建的后备机制
        fallback_enabled = self.config.get("ai_fallback_enabled", True)
        
        if fallback_enabled:
            # 如果AI智能创建失败，使用关键词识别作为后备方案
            code_generation_keywords = ["用python写", "用python", "python写", "用c++写", "用c++", "c++写", "用cobol写", "用cobol", "cobol写", "写一个", "创建一个", "帮我写", "帮我创建"]
            save_file_keywords = ["保存", "保存到", "写入文件", "创建文件", "保存文件", "write_file", "create_note"]
            
            # 检查是否是代码生成请求（关键词后备）
            is_code_generation = any(keyword in user_input for keyword in code_generation_keywords)
            is_save_request = any(keyword in user_input for keyword in save_file_keywords)
            
            if is_code_generation or is_save_request:
                print(f"📝 使用关键词后备方案处理: {user_input}")
            
            # 关键词后备的固定格式创建
            # 处理Python代码生成
            if any(word in user_input.lower() for word in ["python", "用python", "python写", "hello world", "hello"]):
                try:
                    import re
                    import os
                    
                    # 智能提取文件名
                    filename = "program.py"  # 默认文件名
                    if "hello world" in user_input.lower() or "hello" in user_input.lower():
                        filename = "hello_world.py"
                    elif "俄罗斯方块" in user_input or "tetris" in user_input.lower():
                        filename = "tetris.py"
                    elif "贪吃蛇" in user_input or "snake" in user_input.lower():
                        filename = "snake_game.py"
                    elif "井字棋" in user_input or "tic-tac-toe" in user_input.lower():
                        filename = "tic_tac_toe.py"
                    elif "小游戏" in user_input or "game" in user_input.lower():
                        filename = "game.py"
                    elif "爬虫" in user_input or "crawler" in user_input.lower():
                        filename = "web_crawler.py"
                    elif "数据分析" in user_input or "data" in user_input.lower():
                        filename = "data_analysis.py"
                    elif "计算器" in user_input or "calculator" in user_input.lower():
                        filename = "calculator.py"
                    
                    # 检查是否指定了保存位置
                    if "d盘" in user_input.lower() or "d:" in user_input.lower():
                        file_path = f"D:/{filename}"
                    elif "c盘" in user_input.lower() or "c:" in user_input.lower():
                        file_path = f"C:/{filename}"
                    else:
                        # 如果没有指定位置，使用当前工作目录
                        current_dir = os.getcwd()
                        file_path = os.path.join(current_dir, filename)
                    
                    # 构建AI提示词，让AI生成Python代码
                    ai_prompt = f"""
请用Python编写一个完整的程序。要求：
1. 根据用户需求生成相应的Python代码
2. 代码要完整可运行
3. 包含必要的注释和文档字符串
4. 使用Python最佳实践
5. 代码逻辑清晰，易于理解

用户需求：{user_input}

请直接返回完整的Python代码，不要包含任何解释文字。
"""
                    
                    # 调用AI API生成代码
                    model = self.config.get("selected_model", "deepseek-chat")
                    api_key = self.config.get("deepseek_key", "") if "deepseek" in model else self.config.get("openai_key", "")

                    if api_key:
                        try:
                            # 设置API客户端
                            if "deepseek" in model:
                                client = openai.OpenAI(
                                    api_key=api_key,
                                    base_url="https://api.deepseek.com/v1"
                                )
                            else:
                                client = openai.OpenAI(api_key=api_key)
                            
                            # 构建系统提示词
                            system_prompt = """你是一个专业的Python程序员。请根据用户需求生成完整、可运行的Python代码。

要求：
1. 只返回Python代码，不要包含任何解释或说明
2. 代码要完整，包含所有必要的导入
3. 使用Python最佳实践和现代语法
4. 代码逻辑清晰，易于理解
5. 添加适当的注释和文档字符串

请直接返回代码，不要有任何其他内容。"""
                            
                            # 创建聊天消息
                            messages = [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": ai_prompt}
                            ]
                            
                            # 调用API（增加超时时间，添加重试机制）
                            max_retries = 3
                            retry_count = 0
                            
                            while retry_count < max_retries:
                                try:
                                    response = client.chat.completions.create(
                                        model=model,
                                        messages=messages,
                                        max_tokens=2000,
                                        temperature=0.7,
                                        timeout=240  # 延长AI文件创建的响应时间到240秒
                                    )
                                    python_code = response.choices[0].message.content.strip()
                                    break  # 成功则跳出循环
                                except Exception as e:
                                    retry_count += 1
                                    print(f"AI API调用失败 (尝试 {retry_count}/{max_retries}): {str(e)}")
                                    
                                    if retry_count < max_retries:
                                        # 等待一段时间后重试
                                        import time
                                        time.sleep(2 * retry_count)  # 递增等待时间
                                        continue
                                    else:
                                        # 所有重试都失败了
                                        raise e
                            
                            # 如果AI返回的代码包含markdown格式，提取代码部分
                            if "```python" in python_code:
                                import re
                                code_match = re.search(r'```python\s*(.*?)\s*```', python_code, re.DOTALL)
                                if code_match:
                                    python_code = code_match.group(1)
                            elif "```py" in python_code:
                                import re
                                code_match = re.search(r'```py\s*(.*?)\s*```', python_code, re.DOTALL)
                                if code_match:
                                    python_code = code_match.group(1)
                            
                        except Exception as e:
                            print(f"AI API调用失败: {str(e)}")
                            # 如果AI调用失败，返回错误信息
                            return f"（微微皱眉）抱歉训练员，AI代码生成失败：{str(e)}"
                    else:
                        # 如果没有API密钥，返回提示信息
                        return "（微微皱眉）抱歉训练员，需要配置AI API密钥才能生成代码。请先配置DeepSeek或OpenAI API密钥。"
                    
                    # 根据用户要求决定是否保存文件
                    if is_save_request:
                        # 用户明确要求保存文件
                        result = self.mcp_server.call_tool("write_file", file_path=file_path, content=python_code)
                        return f"（指尖轻敲控制台）{result}"
                    else:
                        # 用户只是要求生成代码，不保存文件
                        # 智能提取文件名用于显示
                        display_filename = filename
                        if "俄罗斯方块" in user_input or "tetris" in user_input.lower():
                            display_filename = "tetris.py"
                        elif "贪吃蛇" in user_input or "snake" in user_input.lower():
                            display_filename = "snake_game.py"
                        elif "井字棋" in user_input or "tic-tac-toe" in user_input.lower():
                            display_filename = "tic_tac_toe.py"
                        elif "计算器" in user_input or "calculator" in user_input.lower():
                            display_filename = "calculator.py"
                        
                        # 缓存生成的代码，供后续保存使用
                        self.last_generated_code = {
                            'content': python_code,
                            'filename': display_filename,
                            'language': 'python'
                        }
                        
                        return f"（指尖轻敲控制台）我已经为您生成了Python代码。如果您需要保存为文件，请告诉我保存位置，比如'保存到D盘'或'保存为{display_filename}'。\n\n```python\n{python_code}\n```"
                    
                except Exception as e:
                                            return f"（微微皱眉）抱歉训练员，创建Python文件时遇到了问题：{str(e)}"
            
            # 处理C++代码生成
            elif any(word in user_input.lower() for word in ["c++", "cpp", "c++写", "用c++", "c++的"]):
                try:
                    import re
                    import os
                    
                    # 智能提取文件名
                    filename = "game.cpp"  # 默认文件名
                    
                    # 从用户输入中提取游戏类型
                    if "井字棋" in user_input or "tic-tac-toe" in user_input.lower():
                        filename = "tic_tac_toe.cpp"
                    elif "猜数字" in user_input or "number" in user_input.lower():
                        filename = "number_guess.cpp"
                    elif "贪吃蛇" in user_input or "snake" in user_input.lower():
                        filename = "snake_game.cpp"
                    elif "俄罗斯方块" in user_input or "tetris" in user_input.lower():
                        filename = "tetris.cpp"
                    elif "小游戏" in user_input:
                        filename = "mini_game.cpp"
                    
                    # 检查是否指定了保存位置
                    if "d盘" in user_input.lower() or "d:" in user_input.lower():
                        file_path = f"D:/{filename}"
                    elif "c盘" in user_input.lower() or "c:" in user_input.lower():
                        file_path = f"C:/{filename}"
                    else:
                        # 如果没有指定位置，使用当前工作目录
                        current_dir = os.getcwd()
                        file_path = os.path.join(current_dir, filename)
                    
                    # 构建AI提示词，让AI生成C++代码
                    ai_prompt = f"""
请用C++编写一个完整的小游戏程序。要求：
1. 根据用户需求生成相应的游戏代码
2. 代码要完整可编译运行
3. 包含必要的头文件和注释
4. 使用现代C++语法
5. 游戏逻辑清晰，用户体验良好

用户需求：{user_input}

请直接返回完整的C++代码，不要包含任何解释文字。
"""
                    
                    # 调用AI API生成代码
                    model = self.config.get("selected_model", "deepseek-chat")
                    api_key = self.config.get("deepseek_key", "") if "deepseek" in model else self.config.get("openai_key", "")
                    
                    if api_key:
                        try:
                            # 设置API客户端
                            if "deepseek" in model:
                                client = openai.OpenAI(
                                    api_key=api_key,
                                    base_url="https://api.deepseek.com/v1"
                                )
                            else:
                                client = openai.OpenAI(api_key=api_key)
                            
                            # 构建系统提示词
                            system_prompt = """你是一个专业的C++程序员。请根据用户需求生成完整、可编译的C++游戏代码。

要求：
1. 只返回C++代码，不要包含任何解释或说明
2. 代码要完整，包含所有必要的头文件
3. 使用现代C++语法和最佳实践
4. 游戏逻辑清晰，用户体验良好
5. 添加适当的注释说明

请直接返回代码，不要有任何其他内容。"""
                            
                            # 创建聊天消息
                            messages = [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": ai_prompt}
                            ]
                            
                            # 调用API（增加超时时间，添加重试机制）
                            max_retries = 3
                            retry_count = 0
                            
                            while retry_count < max_retries:
                                try:
                                    response = client.chat.completions.create(
                                        model=model,
                                        messages=messages,
                                        max_tokens=2000,
                                        temperature=0.7,
                                        timeout=240  # 延长AI文件创建的响应时间到240秒
                                    )
                                    cpp_code = response.choices[0].message.content.strip()
                                    break  # 成功则跳出循环
                                except Exception as e:
                                    retry_count += 1
                                    print(f"AI API调用失败 (尝试 {retry_count}/{max_retries}): {str(e)}")
                                    
                                    if retry_count < max_retries:
                                        # 等待一段时间后重试
                                        import time
                                        time.sleep(2 * retry_count)  # 递增等待时间
                                        continue
                                    else:
                                        # 所有重试都失败了
                                        raise e
                            
                            # 如果AI返回的代码包含markdown格式，提取代码部分
                            if "```cpp" in cpp_code:
                                import re
                                code_match = re.search(r'```cpp\s*(.*?)\s*```', cpp_code, re.DOTALL)
                                if code_match:
                                    cpp_code = code_match.group(1)
                            elif "```c++" in cpp_code:
                                import re
                                code_match = re.search(r'```c\+\+\s*(.*?)\s*```', cpp_code, re.DOTALL)
                                if code_match:
                                    cpp_code = code_match.group(1)
                            
                        except Exception as e:
                            print(f"AI API调用失败: {str(e)}")
                            # 如果AI调用失败，返回错误信息
                            return f"（微微皱眉）抱歉训练员，AI代码生成失败：{str(e)}"
                    else:
                        # 如果没有API密钥，返回提示信息
                        return "（微微皱眉）抱歉训练员，需要配置AI API密钥才能生成代码。请先配置DeepSeek或OpenAI API密钥。"
                    
                    # 根据用户要求决定是否保存文件
                    if is_save_request:
                        # 用户明确要求保存文件
                        result = self.mcp_server.call_tool("write_file", file_path=file_path, content=cpp_code)
                        return f"（指尖轻敲控制台）{result}"
                    else:
                        # 用户只是要求生成代码，不保存文件
                        # 智能提取文件名用于显示
                        display_filename = filename
                        if "井字棋" in user_input or "tic-tac-toe" in user_input.lower():
                            display_filename = "tic_tac_toe.cpp"
                        elif "贪吃蛇" in user_input or "snake" in user_input.lower():
                            display_filename = "snake_game.cpp"
                        elif "俄罗斯方块" in user_input or "tetris" in user_input.lower():
                            display_filename = "tetris.cpp"
                        elif "猜数字" in user_input or "number" in user_input.lower():
                            display_filename = "number_guess.cpp"
                        elif "小游戏" in user_input:
                            display_filename = "mini_game.cpp"
                        
                        # 缓存生成的代码，供后续保存使用
                        self.last_generated_code = {
                            'content': cpp_code,
                            'filename': display_filename,
                            'language': 'cpp'
                        }
                        
                        return f"（指尖轻敲控制台）我已经为您生成了C++代码。如果您需要保存为文件，请告诉我保存位置，比如'保存到D盘'或'保存为{display_filename}'。\n\n```cpp\n{cpp_code}\n```"
                    
                except Exception as e:
                    return f"（微微皱眉）抱歉训练员，创建C++文件时遇到了问题：{str(e)}"
            
            # 处理write_file工具调用
            elif "write_file" in user_input.lower() or "写入文件" in user_input or "保存文件" in user_input:
                try:
                    # 提取文件路径和内容
                    import re
                    
                    # 尝试提取路径（支持多种格式）
                    path_patterns = [
                        r'路径为\s*["\']?([^"\']+)["\']?',
                        r'路径\s*["\']?([^"\']+)["\']?',
                        r'file_path\s*=\s*["\']?([^"\']+)["\']?',
                        r'D:[/\\]([^"\s]+)',
                        r'([A-Z]:[/\\][^"\s]+)'
                    ]
                    
                    file_path = None
                    for pattern in path_patterns:
                        match = re.search(pattern, user_input)
                        if match:
                            file_path = match.group(1)
                            if not file_path.startswith(('D:', 'C:', 'E:', 'F:')):
                                file_path = f"D:/{file_path}"
                            break
                    
                    # 提取内容
                    content_patterns = [
                        r'内容为\s*["\']([^"\']+)["\']',
                        r'内容\s*["\']([^"\']+)["\']',
                        r'content\s*=\s*["\']([^"\']+)["\']'
                    ]
                    
                    content = None
                    for pattern in content_patterns:
                        match = re.search(pattern, user_input)
                        if match:
                            content = match.group(1)
                            break
                    
                    # 如果没有找到明确的内容，尝试提取引号中的内容
                    if not content:
                        # 查找所有引号中的内容，排除路径中的内容
                        quote_matches = re.findall(r'["\']([^"\']+)["\']', user_input)
                        for quote_content in quote_matches:
                            if quote_content not in file_path and quote_content != "东海帝王 测试":
                                content = quote_content
                                break
                        # 如果还是没找到，使用最后一个引号内容
                        if not content and quote_matches:
                            content = quote_matches[-1]
                    
                    if file_path and content:
                        result = self.mcp_server.call_tool("write_file", file_path=file_path, content=content)
                        return f"（指尖轻敲控制台）{result}"
                    else:
                        return f"（微微皱眉）抱歉训练员，请提供完整的文件路径和内容。格式：路径为D:/文件名.txt，内容为'文件内容'"
                        
                except Exception as e:
                    return f"（微微皱眉）抱歉训练员，创建文件时遇到了问题：{str(e)}"
            
        # 处理通用保存和文件创建请求（统一优先级）
        elif any(keyword in user_input.lower() for keyword in ["保存", "保存到", "保存为", "写入文件", "创建文件", "创建笔记", "笔记", "清单", "创建测试文件", "创建源文件", "保存到d盘", "保存到d:", "创建清单", "需要创建", "地址在d盘", "地址在d:", "创建好了吗", "保存这个文件", "保存到d盘", "创建可执行", "创建.cbl文件", "创建.py文件", "需要保存", "路径为", "保存为", "创建这个", "这个文件", "地址为", "创建歌单文件", "歌单文件", "创建歌单"]):
            try:
                # 首先检查是否有最近生成的代码需要保存
                if hasattr(self, 'last_generated_code') and self.last_generated_code:
                    # 保存代码逻辑
                    import re
                    import os
                    
                    # 提取保存位置和文件名
                    file_path = None
                    filename = self.last_generated_code.get('filename', 'program.py')
                    
                    # 检查是否指定了保存位置
                    if "d盘" in user_input.lower() or "d:" in user_input.lower():
                        file_path = f"D:/{filename}"
                    elif "c盘" in user_input.lower() or "c:" in user_input.lower():
                        file_path = f"C:/{filename}"
                    else:
                        # 如果没有指定位置，使用当前工作目录
                        current_dir = os.getcwd()
                        file_path = os.path.join(current_dir, filename)
                    
                    # 保存代码
                    content = self.last_generated_code.get('content', '')
                    result = self.mcp_server.call_tool("write_file", file_path=file_path, content=content)
                    
                    # 清除缓存的代码
                    self.last_generated_code = None
                    
                    return f"（指尖轻敲控制台）{result}"
                
                # 如果没有代码需要保存，尝试AI智能创建文件
                ai_creation_result = self._ai_create_file_from_context(user_input)
                if ai_creation_result:
                    return ai_creation_result
                
                # 如果AI创建失败，尝试代码文件创建
                ai_code_creation_result = self._ai_create_code_file_from_context(user_input)
                if ai_code_creation_result:
                    return ai_code_creation_result
                
                # 如果都失败，使用后备方法
                return self._fallback_create_note(user_input)
                    
            except Exception as e:
                return f"（微微皱眉）抱歉训练员，创建文件时遇到了问题：{str(e)}"
        else:
            # 后备机制已禁用，直接返回None
            print("ℹ️ AI智能创建后备机制已禁用")
            return None
        
        # 处理天气查询
        if "天气" in user_input:
            # 检查是否是天气评价或分析请求
            weather_evaluation_keywords = [
                "好不好", "怎么样", "如何", "评价", "分析", "认为", "觉得", "感觉", "适合", "不错", "糟糕", "好", "坏"
            ]
            
            is_evaluation_request = any(keyword in user_input for keyword in weather_evaluation_keywords)
            
            if is_evaluation_request:
                # 这是天气评价请求，应该基于最近的天气信息进行分析
                # 检查最近的对话中是否有天气信息
                recent_weather_info = self._get_recent_weather_info()
                if recent_weather_info:
                    return self._analyze_weather_quality(recent_weather_info)
                else:
                    # 如果没有最近的天气信息，先获取天气信息再分析
                    try:
                        user_location = self._extract_city_from_input(user_input)
                        if not user_location:
                            user_location = self._extract_city_from_location(self.location)
                            if not user_location:
                                user_location = "北京"
                        
                        # 根据配置获取天气信息进行分析
                        weather_source = self.config.get("weather_source", "高德地图API")
                        
                        if weather_source == "高德地图API":
                            amap_key = self.config.get("amap_key", "")
                            if amap_key:
                                weather_result = AmapTool.get_weather(user_location, amap_key)
                            else:
                                return "（微微皱眉）高德地图API密钥未配置，无法分析天气"
                        elif weather_source == "和风天气API":
                            heweather_key = self.config.get("heweather_key", "")
                            if heweather_key:
                                weather_result = self.tools["天气"](user_location, heweather_key)
                            else:
                                return "（微微皱眉）和风天气API密钥未配置，无法分析天气"
                        else:
                            amap_key = self.config.get("amap_key", "")
                            if amap_key:
                                weather_result = AmapTool.get_weather(user_location, amap_key)
                            else:
                                return "（微微皱眉）高德地图API密钥未配置，无法分析天气"
                        
                        return self._analyze_weather_quality(weather_result)
                    except Exception as e:
                        return f"（微微皱眉）抱歉训练员，分析天气时遇到了问题：{str(e)}"
            else:
                # 这是天气查询请求，直接获取天气信息
                try:
                    # 智能提取城市名称
                    user_location = self._extract_city_from_input(user_input)
                    if not user_location:
                        # 使用默认城市
                        user_location = "北京"  # 默认城市
                    
                    # 根据配置选择天气API
                    weather_source = self.config.get("weather_source", "高德地图API")
                    
                    if weather_source == "高德地图API":
                        # 使用高德地图API内部工具
                        amap_key = self.config.get("amap_key", "")
                        if not amap_key:
                            return "（微微皱眉）高德地图API密钥未配置，请在设置中添加API密钥"
                        
                        result = AmapTool.get_weather(user_location, amap_key)
                        return f"（指尖轻敲控制台）{result}"
                    elif weather_source == "和风天气API":
                        # 使用和风天气API
                        try:
                            # 获取和风天气API密钥
                            heweather_key = self.config.get("heweather_key", "")
                            if not heweather_key:
                                return "（微微皱眉）和风天气API密钥未配置，请在设置中添加API密钥"
                            
                            result = self.tools["天气"](user_location, heweather_key)
                            return f"（指尖轻敲控制台）{result}"
                        except Exception as e2:
                            return f"（微微皱眉）和风天气API调用失败：{str(e2)}"
                    else:
                        # 默认使用高德地图API内部工具
                        amap_key = self.config.get("amap_key", "")
                        if not amap_key:
                            return "（微微皱眉）高德地图API密钥未配置，请在设置中添加API密钥"
                        
                        result = AmapTool.get_weather(user_location, amap_key)
                        return f"（指尖轻敲控制台）{result}"
                except Exception as e:
                    # 如果主要API失败，尝试备用API
                    try:
                        weather_source = self.config.get("weather_source", "高德地图API")
                        if weather_source == "高德地图API":
                            # 高德API失败，尝试和风天气API
                            heweather_key = self.config.get("heweather_key", "")
                            if heweather_key:
                                result = self.tools["天气"](user_location, heweather_key)
                                return f"（指尖轻敲控制台）{result}"
                        else:
                            # 和风天气API失败，尝试高德地图API
                            amap_key = self.config.get("amap_key", "")
                            if amap_key:
                                result = AmapTool.get_weather(user_location, amap_key)
                                return f"（指尖轻敲控制台）{result}"
                    except Exception as e2:
                        return f"（微微皱眉）抱歉训练员，获取天气信息时遇到了问题：{str(e2)}"
        
        return None

    def _extract_city_from_input(self, user_input):
        """从用户输入中智能提取城市名称"""
        # 常见城市列表
        cities = [
            "北京", "上海", "广州", "深圳", "杭州", "南京", "武汉", "成都", "重庆", "西安",
            "天津", "苏州", "长沙", "青岛", "无锡", "宁波", "佛山", "东莞", "郑州", "济南",
            "大连", "福州", "厦门", "哈尔滨", "长春", "沈阳", "石家庄", "太原", "合肥", "南昌",
            "昆明", "贵阳", "南宁", "海口", "兰州", "西宁", "银川", "乌鲁木齐", "拉萨", "呼和浩特"
        ]
        
        # 检查用户输入中是否包含城市名称
        for city in cities:
            if city in user_input:
                return city
        
        return None

    # def _extract_city_from_location(self, location):
    #     """从登录位置中提取城市名称（已禁用）"""
    #     if not location or location == "未知位置":
    #         return None
    # 
    #     # 城市名称映射（英文 -> 中文）
    #     city_mapping = {
    #         "beijing": "北京",
    #         "shanghai": "上海",
    #         "guangzhou": "广州",
    #         "shenzhen": "深圳",
    #         "hangzhou": "杭州",
    #         "nanjing": "南京",
    #         "wuhan": "武汉",
    #         "chengdu": "成都",
    #         "chongqing": "重庆",
    #         "xian": "西安",
    #         "tianjin": "天津",
    #         "suzhou": "苏州",
    #         "changsha": "长沙",
    #         "qingdao": "青岛",
    #         "wuxi": "无锡",
    #         "ningbo": "宁波",
    #         "foshan": "佛山",
    #         "dongguan": "东莞",
    #         "zhengzhou": "郑州",
    #         "jinan": "济南",
    #         "dalian": "大连",
    #         "fuzhou": "福州",
    #         "xiamen": "厦门",
    #         "haerbin": "哈尔滨",
    #         "changchun": "长春",
    #         "shenyang": "沈阳",
    #         "shijiazhuang": "石家庄",
    #         "taiyuan": "太原",
    #         "hefei": "合肥",
    #         "nanchang": "南昌",
    #         "kunming": "昆明",
    #         "guiyang": "贵阳",
    #         "nanning": "南宁",
    #         "haikou": "海口",
    #         "lanzhou": "兰州",
    #         "xining": "西宁",
    #         "yinchuan": "银川",
    #         "urumqi": "乌鲁木齐",
    #         "lasa": "拉萨",
    #         "huhehaote": "呼和浩特"
    #     }
    # 
    #     # 常见中文城市列表
    #     chinese_cities = [
    #         "北京", "上海", "广州", "深圳", "杭州", "南京", "武汉", "成都", "重庆", "西安",
    #         "天津", "苏州", "长沙", "青岛", "无锡", "宁波", "佛山", "东莞", "郑州", "济南",
    #         "大连", "福州", "厦门", "哈尔滨", "长春", "沈阳", "石家庄", "太原", "合肥", "南昌",
    #         "昆明", "贵阳", "南宁", "海口", "兰州", "西宁", "银川", "乌鲁木齐", "拉萨", "呼和浩特"
    #     ]
    # 
    #     location_lower = location.lower()
    # 
    #     # 首先检查中文城市名称
    #     for city in chinese_cities:
    #         if city in location:
    #             return city
    # 
    #     # 然后检查英文城市名称
    #     for english_name, chinese_name in city_mapping.items():
    #         if english_name in location_lower:
    #             return chinese_name
    # 
    #     return None

    # 创建一个简单的替代函数，直接返回None
    def _extract_city_from_location(self, location):
        """从登录位置中提取城市名称（已禁用）"""
        return None
        
        # 城市名称映射（英文 -> 中文）
        city_mapping = {
            "beijing": "北京",
            "shanghai": "上海", 
            "guangzhou": "广州",
            "shenzhen": "深圳",
            "hangzhou": "杭州",
            "nanjing": "南京",
            "wuhan": "武汉",
            "chengdu": "成都",
            "chongqing": "重庆",
            "xian": "西安",
            "tianjin": "天津",
            "suzhou": "苏州",
            "changsha": "长沙",
            "qingdao": "青岛",
            "wuxi": "无锡",
            "ningbo": "宁波",
            "foshan": "佛山",
            "dongguan": "东莞",
            "zhengzhou": "郑州",
            "jinan": "济南",
            "dalian": "大连",
            "fuzhou": "福州",
            "xiamen": "厦门",
            "haerbin": "哈尔滨",
            "changchun": "长春",
            "shenyang": "沈阳",
            "shijiazhuang": "石家庄",
            "taiyuan": "太原",
            "hefei": "合肥",
            "nanchang": "南昌",
            "kunming": "昆明",
            "guiyang": "贵阳",
            "nanning": "南宁",
            "haikou": "海口",
            "lanzhou": "兰州",
            "xining": "西宁",
            "yinchuan": "银川",
            "urumqi": "乌鲁木齐",
            "lasa": "拉萨",
            "huhehaote": "呼和浩特"
        }
        
        # 常见中文城市列表
        chinese_cities = [
            "北京", "上海", "广州", "深圳", "杭州", "南京", "武汉", "成都", "重庆", "西安",
            "天津", "苏州", "长沙", "青岛", "无锡", "宁波", "佛山", "东莞", "郑州", "济南",
            "大连", "福州", "厦门", "哈尔滨", "长春", "沈阳", "石家庄", "太原", "合肥", "南昌",
            "昆明", "贵阳", "南宁", "海口", "兰州", "西宁", "银川", "乌鲁木齐", "拉萨", "呼和浩特"
        ]
        
        location_lower = location.lower()
        
        # 首先检查中文城市名称
        for city in chinese_cities:
            if city in location:
                return city
        
        # 然后检查英文城市名称
        for english_name, chinese_name in city_mapping.items():
            if english_name in location_lower:
                return chinese_name
        
        return None

    def _direct_create_file_from_extracted_code(self, user_input):
        """直接使用提取的代码创建文件（AI API超时时的后备方案）"""
        try:
            print("🔧 使用直接代码创建后备方案")
            
            # 构建上下文信息
            context_info = ""
            if self.session_conversations:
                # 获取最近的对话作为上下文
                recent_contexts = []
                for conv in reversed(self.session_conversations[-3:]):  # 获取最近3条对话
                    recent_contexts.append(f"【{conv['timestamp']}】{conv['full_text']}")
                context_info = "\n".join(recent_contexts)
            
            # 尝试从上下文中提取代码内容
            extracted_code = self._extract_code_from_context(context_info)
            if not extracted_code:
                print("⚠️ 未找到可提取的代码内容")
                return None
            
            print(f"🔍 直接使用提取的代码: {extracted_code[:100]}...")
            
            # 从用户输入中提取路径信息
            import re
            
            # 尝试提取完整路径（如"路径为D:/计算器.py"）
            path_match = re.search(r'路径为\s*([^，。\s]+)', user_input)
            if path_match:
                full_path = path_match.group(1)
                # 分离路径和文件名
                if '/' in full_path or '\\' in full_path:
                    path_parts = full_path.replace('\\', '/').split('/')
                    if len(path_parts) > 1:
                        location = '/'.join(path_parts[:-1]) + '/'
                        filename = path_parts[-1]
                        if not filename.endswith(('.py', '.cob', '.cbl', '.cpp', '.txt')):
                            filename += '.py'  # 默认添加.py扩展名
                else:
                    location = "D:/"
                    filename = full_path
                    if not filename.endswith(('.py', '.cob', '.cbl', '.cpp', '.txt')):
                        filename += '.py'
            else:
                # 如果没有找到完整路径，使用原有的逻辑
                if "d盘" in user_input.lower() or "d:" in user_input.lower():
                    location = "D:/"
                elif "c盘" in user_input.lower() or "c:" in user_input.lower():
                    location = "C:/"
                elif "e盘" in user_input.lower() or "e:" in user_input.lower():
                    location = "E:/"
                elif "f盘" in user_input.lower() or "f:" in user_input.lower():
                    location = "F:/"
                else:
                    location = "D:/"
                
                # 根据代码内容推断文件名
                if "python" in context_info.lower() or "def " in extracted_code:
                    filename = "calculator.py"
                elif "cobol" in context_info.lower() or "IDENTIFICATION DIVISION" in extracted_code:
                    filename = "program.cob"
                elif "c++" in context_info.lower() or "#include" in extracted_code:
                    filename = "program.cpp"
                else:
                    filename = "program.py"
            
            # 确保文件名安全
            filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
            
            # 构建完整的文件内容
            if "IDENTIFICATION DIVISION" in extracted_code or "PROGRAM-ID" in extracted_code:
                # COBOL代码格式特殊处理
                if "IDENTIFICATION DIVISION" not in extracted_code:
                    file_content = f"""      IDENTIFICATION DIVISION.
      PROGRAM-ID. CALCULATOR.
      PROCEDURE DIVISION.
{extracted_code}
      STOP RUN.
"""
                else:
                    # 如果代码已经包含完整的COBOL结构，直接使用
                    file_content = extracted_code
            else:
                # 其他编程语言
                file_content = f"""# -*- coding: utf-8 -*-
"""
                file_content += extracted_code
            
            # 调用MCP工具创建文件
            file_path = f"{location.rstrip('/')}/{filename}"
            result = self.mcp_server.call_tool("write_file", 
                                             file_path=file_path, 
                                             content=file_content)
            
            return f"（指尖轻敲控制台）{result}"
            
        except Exception as e:
            print(f"直接代码创建失败: {str(e)}")
            return None

    def _extract_code_from_context(self, context_info):
        """从上下文中提取代码内容"""
        try:
            import re
            
            # 提取各种代码块
            code_patterns = [
                r'```cobol\s*(.*?)\s*```',
                r'```python\s*(.*?)\s*```',
                r'```py\s*(.*?)\s*```',
                r'```cpp\s*(.*?)\s*```',
                r'```c\+\+\s*(.*?)\s*```',
                r'```c\s*(.*?)\s*```',
                r'```java\s*(.*?)\s*```',
                r'```javascript\s*(.*?)\s*```',
                r'```js\s*(.*?)\s*```',
                r'```html\s*(.*?)\s*```',
                r'```css\s*(.*?)\s*```',
                r'```sql\s*(.*?)\s*```',
                r'```bash\s*(.*?)\s*```',
                r'```shell\s*(.*?)\s*```',
                r'```\s*(.*?)\s*```'  # 通用代码块
            ]
            
            for pattern in code_patterns:
                matches = re.findall(pattern, context_info, re.DOTALL)
                if matches:
                    extracted_code = matches[0].strip()
                    print(f"🔍 成功提取代码块: {extracted_code[:50]}...")
                    return extracted_code
            
            # 如果没有找到代码块，尝试查找COBOL特定的内容
            if "IDENTIFICATION DIVISION" in context_info or "PROGRAM-ID" in context_info:
                # 尝试提取COBOL代码段
                cobol_patterns = [
                    r'(IDENTIFICATION DIVISION\..*?STOP RUN\.)',
                    r'(PROGRAM-ID\..*?STOP RUN\.)',
                    r'(IDENTIFICATION DIVISION\..*?PROCEDURE DIVISION\..*?STOP RUN\.)'
                ]
                
                for pattern in cobol_patterns:
                    matches = re.findall(pattern, context_info, re.DOTALL)
                    if matches:
                        extracted_code = matches[0].strip()
                        print(f"🔍 成功提取COBOL代码: {extracted_code[:50]}...")
                        return extracted_code
            
            print("⚠️ 未找到任何代码内容")
            return None
            
        except Exception as e:
            print(f"提取代码失败: {str(e)}")
            return None

    def _extract_code_from_recent_conversations(self):
        """从最近的对话中提取代码内容"""
        if not self.session_conversations:
            return None
        
        # 从最近的对话中查找代码内容
        for conv in reversed(self.session_conversations[-5:]):  # 检查最近5条对话
            ai_response = conv.get("ai_response", "")
            if "```" in ai_response:
                # 提取代码内容
                code_content = self._extract_code_from_context(ai_response)
                if code_content:
                    return code_content
        
        return None

    def _extract_search_query(self, user_input):
        """智能提取搜索关键词"""
        # 定义需要移除的词汇
        remove_words = [
            "帮我", "请帮我", "麻烦帮我", "能否帮我", "可以帮我",
            "搜索", "查找", "搜素", "搜", "查", "找", "查询", "查找", "搜素",
            "搜索一下", "查找一下", "搜素一下", "搜一下", "查一下", "找一下", "查询一下",
            "一下", "帮我搜索", "帮我查找", "帮我搜素", "帮我搜", "帮我查", "帮我找", "帮我查询", "帮我查找",
            "百度", "google", "谷歌", "bing", "必应", "用百度", "用谷歌", "用必应"
        ]
        
        # 移除所有不需要的词汇
        query = user_input
        for word in remove_words:
            query = query.replace(word, "")
        
        # 清理多余的空格和标点
        import re
        query = re.sub(r'\s+', ' ', query.strip())
        query = query.strip('，。！？、；：')
        
        return query

    def _get_current_time(self):
        """获取当前时间"""
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _fallback_website_check(self, user_input):
        """后备网站打开检查逻辑"""
        try:
            # 检查是否包含网站打开相关的关键词
            website_keywords = [
                "打开", "访问", "在浏览器打开", "帮我打开", "打开网站", "访问网站", 
                "浏览", "打开页面", "进入网站", "打开网页"
            ]
            
            is_website_request = any(keyword in user_input for keyword in website_keywords)
            
            if is_website_request:
                print(f"🔍 后备逻辑识别为网站打开请求: {user_input}")
                
                # 提取网站名称
                site_name = user_input
                priority_keywords = ["在浏览器打开", "帮我打开", "打开网站", "访问", "打开网页", "打开", "访问网站", "浏览", "打开页面", "进入网站"]
                
                for keyword in priority_keywords:
                    if keyword in user_input:
                        site_name = user_input.replace(keyword, "").strip()
                        connectors = ["帮我", "请", "能否", "可以", "麻烦", "在", "用", "通过", "浏览器", "网页"]
                        for connector in connectors:
                            site_name = site_name.replace(connector, "").strip()
                        break
                
                site_name = site_name.strip("，。！？\n\t ")
                
                if site_name and len(site_name) > 0:
                    print(f"🔍 后备逻辑提取的网站名称: '{site_name}'")
                    
                    # 检查网站管理中的网站
                    result = self._open_website_wrapper(site_name, self.website_map)
                    
                    # 如果网站管理中没有找到，返回提示信息
                    if "无法识别网站" in result:
                        return f"抱歉训练员，我无法识别网站 '{site_name}'。\n\n可用的网站包括：{', '.join(self.website_map.keys())}\n\n请在网站管理中添加此网站，或者直接提供完整的网址（如：https://www.example.com）"
                    else:
                        return f"（指尖轻敲控制台）{result}"
            
            return None
            
        except Exception as e:
            print(f"❌ 后备网站检查失败: {str(e)}")
            return None

    def _open_website_wrapper(self, site_name, website_map=None):
        """打开网站的包装函数，处理网站名称映射"""
        try:
            if website_map is None:
                website_map = self.website_map
            
            # 清理网站名称
            site_name = site_name.strip().lower()
            
            # 处理常见的网站名称变体
            site_variants = {
                "哔哩哔哩": ["bilibili", "b站", "哔哩哔哩", "bilbil", "bilibili.com"],
                "百度": ["baidu", "百度", "baidu.com"],
                "谷歌": ["google", "谷歌", "google.com"],
                "知乎": ["zhihu", "知乎", "zhihu.com"],
                "github": ["github", "github.com"],
                "youtube": ["youtube", "youtube.com", "油管"]
            }
            
            # 查找匹配的网站
            matched_site = None
            for site_key, variants in site_variants.items():
                if any(variant in site_name for variant in variants):
                    matched_site = site_key
                    break
            
            # 如果找到匹配的网站，使用映射的URL
            if matched_site and matched_site in website_map:
                url = website_map[matched_site]
                print(f"🔍 找到网站映射: {site_name} -> {url}")
                return open_website(url, self.config.get("default_browser", ""))
            
            # 如果网站名称直接匹配映射表
            if site_name in website_map:
                url = website_map[site_name]
                print(f"🔍 直接匹配网站映射: {site_name} -> {url}")
                return open_website(url, self.config.get("default_browser", ""))
            
            # 如果包含http或www，直接作为URL处理
            if site_name.startswith(("http://", "https://", "www.")):
                if not site_name.startswith(("http://", "https://")):
                    site_name = "https://" + site_name
                print(f"🔍 直接作为URL处理: {site_name}")
                return open_website(site_name, self.config.get("default_browser", ""))
            
            # 如果都没匹配到，返回错误信息
            available_sites = list(website_map.keys())
            return f"抱歉训练员，我无法识别网站 '{site_name}'。\n\n可用的网站包括：{', '.join(available_sites)}\n\n您也可以直接提供完整的网址（如：https://www.example.com）"
            
        except Exception as e:
            return f"打开网站时发生错误：{str(e)}"

    def _is_remember_moment_command(self, user_input):
        """检测是否是'记住这个时刻'指令"""
        remember_keywords = [
            "请记住这个时刻",
            "记住这个时刻",
            "记住这一刻",
            "请记住这一刻",
            "记住这个瞬间",
            "请记住这个瞬间",
            "记住这个时间",
            "请记住这个时间",
            "记住这个对话",
            "请记住这个对话",
            "记住这次谈话",
            "请记住这次谈话",
            "记住这次交流",
            "请记住这次交流",
            "保存这个时刻",
            "请保存这个时刻",
            "保存这次对话",
            "请保存这次对话",
            "记录这个时刻",
            "请记录这个时刻",
            "记录这次对话",
            "请记录这次对话"
        ]
        
        user_input_lower = user_input.lower().strip()
        return any(keyword.lower() in user_input_lower for keyword in remember_keywords)

    def _handle_remember_moment(self, user_input):
        """处理'记住这个时刻'指令"""
        try:
            # 检查是否有未保存的会话对话
            unsaved_conversations = []
            
            # 获取当前记忆系统中的对话数量
            current_memory_count = len(self.memory_lake.current_conversation)
            
            # 获取本次会话的对话数量
            session_count = len(self.session_conversations)
            
            # 如果本次会话有对话但记忆系统中没有，说明有未保存的对话
            if session_count > 0 and current_memory_count == 0:
                # 将本次会话的所有对话添加到记忆系统
                for conv in self.session_conversations:
                    self.memory_lake.add_conversation(conv["user_input"], conv["ai_response"])
                    unsaved_conversations.append(conv["full_text"])
            
            # 强制保存到记忆系统
            if self.memory_lake.current_conversation:
                topic = self.memory_lake.summarize_and_save_topic(force_save=True)
                
                if topic:
                    # 标记为重点记忆（最新保存的记忆是最后一个）
                    topics = self.memory_lake.memory_index.get("topics", [])
                    if topics:
                        latest_index = len(topics) - 1
                        self.memory_lake.mark_as_important(latest_index)
                    
                    # 构建响应消息
                    response = f"（轻轻点头）好的训练员，我已经将这个重要时刻记录到记忆系统中，并标记为重点记忆。"
                    
                    # 根据设置决定是否显示详细信息
                    show_details = self.config.get("show_remember_details", True)
                    
                    if show_details:
                        if unsaved_conversations:
                            response += f"\n\n已保存的对话内容：\n"
                            for i, conv in enumerate(unsaved_conversations, 1):
                                response += f"{i}. {conv}\n"
                        
                        response += f"\n主题：{topic}\n时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    
                    # 清空本次会话记录，因为已经保存到记忆系统
                    self.session_conversations = []
                    
                    return response
                else:
                    return "（微微皱眉）抱歉训练员，保存到记忆系统时遇到了一些问题。请稍后再试。"
            else:
                return "（轻轻摇头）训练员，目前没有需要保存的对话内容。请先进行一些对话，然后再说'记住这个时刻'。"
                
        except Exception as e:
            print(f"处理'记住这个时刻'指令失败: {str(e)}")
            return "（表情略显困扰）抱歉训练员，保存过程中遇到了一些技术问题。请稍后再试。"

    def _is_file_analysis_request(self, user_input):
        """检测是否是文件分析请求"""
        file_keywords = [
            "分析文件", "文件分析", "上传文件", "分析图片", "分析文档",
            "查看文件", "文件信息", "图片信息", "文档信息", "智能分析"
        ]
        user_input_lower = user_input.lower().strip()
        return any(keyword in user_input_lower for keyword in file_keywords)

    def _handle_file_analysis(self, user_input):
        """处理文件分析请求"""
        try:
            # 从用户输入中提取文件路径
            # 这里可以添加更智能的文件路径提取逻辑
            
            # 调用智能文件分析工具
            result = self.mcp_tools.server.call_tool("智能文件分析", file_path="用户选择的文件路径")
            return result
        except Exception as e:
            return f"文件分析失败: {str(e)}"

    def process_file_upload(self, file_path):
        """处理文件上传"""
        try:
            print(f"🔍 开始分析文件: {file_path}")
            
            # 调用智能文件分析工具
            result = self.mcp_tools.server.call_tool("智能文件分析", file_path=file_path)
            
            print(f"📊 MCP工具返回结果: {result[:200]}...")
            
            # 检查结果是否为错误信息
            if "参数错误" in result or "工具不存在" in result or "调用工具失败" in result:
                return f"文件分析工具调用失败: {result}"
            
            # 格式化分析结果，使其更美观
            formatted_result = self._format_analysis_result(result)
            
            # 根据文件类型生成不同的AI分析
            if self._is_image_file(file_path):
                ai_analysis = self._generate_image_ai_analysis(file_path, result)
            elif self._is_document_file(file_path):
                ai_analysis = self._generate_document_ai_analysis(file_path, result)
            else:
                ai_analysis = "这是一个文件，我可以帮您分析其基本信息。"
            
            return f"{formatted_result}\n\n🤖 AI分析：\n{ai_analysis}"
            
        except Exception as e:
            print(f"❌ 文件分析失败: {str(e)}")
            return f"文件分析失败: {str(e)}"
    
    def _format_analysis_result(self, result):
        """格式化分析结果，使其更美观易读"""
        try:
            import json
            import re
            
            # 尝试提取JSON部分
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                analysis_data = json.loads(json_str)
                
                # 格式化基本信息
                basic_info = analysis_data.get("basic_info", {})
                content_analysis = analysis_data.get("content_analysis", {})
                
                formatted_result = "🔍 智能文件分析结果\n"
                formatted_result += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                formatted_result += f"📁 文件名：{basic_info.get('file_name', '未知')}\n"
                formatted_result += f"📏 文件大小：{basic_info.get('file_size_human', '未知')}\n"
                formatted_result += f"📅 创建时间：{basic_info.get('created_time', '未知')}\n"
                formatted_result += f"🔄 修改时间：{basic_info.get('modified_time', '未知')}\n"
                
                # 根据文件类型添加特定信息
                if content_analysis.get("type") == "image":
                    formatted_result += f"🖼️ 图片格式：{content_analysis.get('format', '未知')}\n"
                    formatted_result += f"📐 图片尺寸：{content_analysis.get('width', '未知')} × {content_analysis.get('height', '未知')}\n"
                    formatted_result += f"🎨 颜色深度：{content_analysis.get('color_depth', '未知')}\n"
                    
                    # 场景描述
                    scene_desc = content_analysis.get("scene_description", {})
                    if scene_desc:
                        formatted_result += f"🌅 场景类型：{scene_desc.get('scene_type', '未知')}\n"
                        formatted_result += f"💡 亮度水平：{scene_desc.get('brightness_level', '未知')}\n"
                    
                    # 物体检测
                    object_detect = content_analysis.get("object_detection", {})
                    if object_detect:
                        formatted_result += f"🔍 复杂度：{object_detect.get('complexity', '未知')}\n"
                        formatted_result += f"🎨 颜色数量：{object_detect.get('unique_colors', '未知')}\n"
                    
                    # 文字提取分析
                    text_extract = content_analysis.get("text_extraction", {})
                    if text_extract:
                        formatted_result += f"📝 文字可能性：{text_extract.get('text_likelihood', '未知')}\n"
                        formatted_result += f"📊 边缘密度：{text_extract.get('edge_density', '未知')}\n"
                    
                    # OCR文字识别结果
                    ocr_text = content_analysis.get("ocr_text", {})
                    if ocr_text and ocr_text.get("status") == "success":
                        extracted_text = ocr_text.get("extracted_text", "")
                        if extracted_text.strip():
                            formatted_result += f"🔤 识别文字：\n"
                            # 限制显示长度，避免过长
                            display_text = extracted_text.strip()
                            if len(display_text) > 200:
                                display_text = display_text[:200] + "..."
                            formatted_result += f"   {display_text}\n"
                            formatted_result += f"📏 文字长度：{ocr_text.get('text_length', '未知')}字符\n"
                            formatted_result += f"📖 词数：{ocr_text.get('word_count', '未知')}\n"
                    elif ocr_text and ocr_text.get("status") == "no_text":
                        formatted_result += f"🔤 文字识别：未识别到文字内容\n"
                    elif ocr_text and ocr_text.get("status") == "error":
                        formatted_result += f"🔤 文字识别：{ocr_text.get('message', '识别失败')}\n"
                    
                    # 颜色分析
                    color_analysis = content_analysis.get("color_analysis", {})
                    if color_analysis:
                        dominant_colors = color_analysis.get("dominant_colors", [])
                        if dominant_colors:
                            formatted_result += f"🌈 主要颜色：{dominant_colors[0].get('color', '未知')} ({dominant_colors[0].get('percentage', '未知')}%)\n"
                    
                    # 构图分析
                    composition = content_analysis.get("composition_analysis", {})
                    if composition:
                        formatted_result += f"📐 构图类型：{composition.get('composition_type', '未知')}\n"
                        formatted_result += f"📊 分辨率：{composition.get('resolution_quality', '未知')}\n"
                
                elif content_analysis.get("type") == "text":
                    formatted_result += f"📄 文件类型：文本文件\n"
                    formatted_result += f"📝 字符数：{content_analysis.get('character_count', '未知')}\n"
                    formatted_result += f"📖 行数：{content_analysis.get('line_count', '未知')}\n"
                    formatted_result += f"🔤 词数：{content_analysis.get('word_count', '未知')}\n"
                    formatted_result += f"🌍 语言：{content_analysis.get('language', '未知')}\n"
                
                formatted_result += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                
                return formatted_result
            else:
                # 如果没有找到JSON，返回原始结果
                return result
                
        except Exception as e:
            print(f"⚠️ 格式化分析结果失败: {str(e)}")
            # 如果格式化失败，返回原始结果
            return result

    def _generate_image_ai_analysis(self, file_path, analysis_result):
        """生成图片的AI分析"""
        try:
            print(f"🖼️ 开始生成图片AI分析: {file_path}")
            
            # 尝试解析分析结果
            import json
            try:
                analysis_data = json.loads(analysis_result)
                content_analysis = analysis_data.get("content_analysis", {})
                
                # 获取OCR识别的文字内容
                ocr_text = content_analysis.get("ocr_text", {})
                extracted_text = ""
                if ocr_text and ocr_text.get("status") == "success":
                    extracted_text = ocr_text.get("extracted_text", "").strip()
                
                # 构建AI分析提示
                prompt = f"""
                请分析这张图片，基于以下信息：
                
                图片信息：
                - 文件名：{analysis_data.get('basic_info', {}).get('file_name', '未知')}
                - 尺寸：{content_analysis.get('width', '未知')} x {content_analysis.get('height', '未知')}
                - 格式：{content_analysis.get('format', '未知')}
                
                内容分析：
                - 场景描述：{content_analysis.get('scene_description', {}).get('description', '未知')}
                - 物体检测：{content_analysis.get('object_detection', {}).get('description', '未知')}
                - 颜色分析：{content_analysis.get('color_analysis', {}).get('description', '未知')}
                - 构图分析：{content_analysis.get('composition_analysis', {}).get('description', '未知')}
                """
                
                # 如果有OCR识别的文字内容，添加到提示中
                if extracted_text:
                    prompt += f"""
                
                OCR识别的文字内容：
                {extracted_text}
                
                请基于以上信息，特别是OCR识别的文字内容，对这张图片进行全面的AI分析。包括：
                1. 图片的整体内容和主题
                2. 识别出的文字内容的含义和重要性
                3. 图片的风格、用途和可能的背景
                4. 文字与图片内容的关联性分析
                5. 专业见解和建议
                """
                else:
                    prompt += f"""
                
                文字识别：{content_analysis.get('text_extraction', {}).get('description', '未知')}
                
                请从AI的角度分析这张图片的内容、风格、可能的用途等，给出专业的见解。
                """
                
            except json.JSONDecodeError:
                # 如果不是JSON格式，使用原始结果
                print(f"⚠️ 分析结果不是JSON格式，使用原始结果")
                prompt = f"""
                请分析这张图片，基于以下技术分析结果：
                
                {analysis_result}
                
                请从AI的角度分析这张图片的内容、风格、可能的用途等，给出专业的见解。
                """
            
            # 调用AI生成分析，提供空的上下文信息
            context_info = {}
            response = self._generate_response_with_context(prompt, context_info)
            return response
            
        except Exception as e:
            print(f"❌ AI分析生成失败: {str(e)}")
            return f"AI分析生成失败: {str(e)}"

    def _generate_document_ai_analysis(self, file_path, analysis_result):
        """生成文档的AI分析"""
        try:
            # 解析分析结果
            import json
            analysis_data = json.loads(analysis_result)
            content_analysis = analysis_data.get("content_analysis", {})
            
            # 构建AI分析提示
            prompt = f"""
            请分析这个文档，基于以下信息：
            
            文档信息：
            - 文件名：{analysis_data.get('basic_info', {}).get('file_name', '未知')}
            - 文件类型：{content_analysis.get('type', '未知')}
            
            内容分析：
            - 文本统计：{content_analysis.get('description', '未知')}
            - 关键词：{', '.join(content_analysis.get('keywords', []))}
            - 内容预览：{content_analysis.get('content_preview', '未知')}
            
            请从AI的角度分析这个文档的主题、内容质量、可能的用途等，给出专业的见解。
            """
            
            # 调用AI生成分析，提供空的上下文信息
            context_info = {}
            response = self._generate_response_with_context(prompt, context_info)
            return response
            
        except Exception as e:
            return f"AI分析生成失败: {str(e)}"

    def _is_image_file(self, file_path):
        """判断是否为图片文件"""
        from pathlib import Path
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
        return Path(file_path).suffix.lower() in image_extensions

    def _is_document_file(self, file_path):
        """判断是否为文档文件"""
        from pathlib import Path
        document_extensions = {'.pdf', '.txt', '.doc', '.docx', '.csv', '.json', '.xml'}
        return Path(file_path).suffix.lower() in document_extensions

    
    def _filter_ocr_text(self, text):
        """过滤OCR识别的文字，去除明显错误的结果"""
        if not text:
            return ""
        
        import re
        
        # 去除单个字符或明显无意义的字符组合
        if len(text.strip()) < 2:
            return ""
        
        # 去除只包含数字和特殊字符的文本（除非是合理的数字）
        if re.match(r'^[\d\s\-\.\,]+$', text.strip()) and len(text.strip()) < 5:
            return ""
        
        # 去除重复字符过多的文本
        if len(set(text)) < len(text) * 0.3:  # 如果重复字符超过70%
            return ""
        
        # 去除明显无意义的字符组合
        meaningless_patterns = [
            r'^[^\w\s]+$',  # 只包含特殊字符
            r'^[a-zA-Z]{1,2}$',  # 单个或两个英文字母
            r'^[一-龯]{1,2}$',  # 单个或两个中文字符
        ]
        
        for pattern in meaningless_patterns:
            if re.match(pattern, text.strip()):
                return ""
        
        # 清理文本
        cleaned_text = text.strip()
        # 去除多余的空格
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
        
        return cleaned_text

    def process_image(self, file_path):
        """处理图片文件"""
        try:
            print(f"🖼️ 开始处理图片: {file_path}")
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                return "错误：文件不存在"
            
            # 检查是否为图片文件
            if not self._is_image_file(file_path):
                return "错误：不是有效的图片文件"
            
            # 使用智能文件分析工具
            analysis_result = self._analyze_file_with_tools(file_path)
            
            if not analysis_result:
                return "错误：文件分析失败"
            
            # 生成AI分析
            ai_analysis = self._generate_image_ai_analysis(file_path, analysis_result)
            
            return ai_analysis
            
        except Exception as e:
            print(f"❌ 图片处理失败: {str(e)}")
            return f"图片处理失败: {str(e)}"

    def _analyze_file_with_tools(self, file_path):
        """使用工具分析文件"""
        try:
            # 调用MCP工具进行文件分析
            result = self.mcp_tools.server.call_tool("智能文件分析", file_path=file_path)
            return result
        except Exception as e:
            print(f"❌ 文件分析工具调用失败: {str(e)}")
            return None

    def _get_recent_weather_info(self):
        """获取最近的天气信息"""
        # 从最近的对话中查找天气信息
        for conv in reversed(self.session_conversations):
            ai_response = conv.get("ai_response", "")
            if "天气预报" in ai_response or "天气" in ai_response:
                return ai_response
        return None

    def _analyze_weather_quality(self, weather_info):
        """分析天气质量并给出评价"""
        try:
            # 解析天气信息
            weather_text = weather_info.lower()
            
            # 提取关键信息
            temperature = None
            weather_condition = None
            wind = None
            
            # 提取温度信息
            import re
            temp_match = re.search(r'(\d+)°c', weather_text)
            if temp_match:
                temperature = int(temp_match.group(1))
            
            # 提取天气状况
            if "晴" in weather_text:
                weather_condition = "晴"
            elif "多云" in weather_text:
                weather_condition = "多云"
            elif "阴" in weather_text:
                weather_condition = "阴"
            elif "雨" in weather_text:
                weather_condition = "雨"
            elif "雪" in weather_text:
                weather_condition = "雪"
            
            # 提取风力信息
            wind_match = re.search(r'([东南西北]风\d+-\d+级)', weather_text)
            if wind_match:
                wind = wind_match.group(1)
            
            # 分析天气质量
            analysis = "（快速分析天气数据）"
            
            # 温度评价
            if temperature:
                if temperature < 10:
                    temp_eval = "偏冷"
                elif temperature < 20:
                    temp_eval = "凉爽"
                elif temperature < 28:
                    temp_eval = "舒适"
                elif temperature < 35:
                    temp_eval = "较热"
                else:
                    temp_eval = "炎热"
            else:
                temp_eval = "适中"
            
            # 天气状况评价
            if weather_condition == "晴":
                condition_eval = "晴朗宜人"
            elif weather_condition == "多云":
                condition_eval = "温和舒适"
            elif weather_condition == "阴":
                condition_eval = "略显沉闷"
            elif weather_condition == "雨":
                condition_eval = "需要注意防雨"
            elif weather_condition == "雪":
                condition_eval = "需要注意保暖"
            else:
                condition_eval = "天气一般"
            
            # 综合评价
            if temperature and weather_condition:
                if temperature >= 20 and temperature <= 28 and weather_condition in ["晴", "多云"]:
                    overall_eval = "非常好的天气"
                    recommendation = "适合户外活动、出行和运动"
                elif temperature >= 15 and temperature <= 30 and weather_condition in ["晴", "多云", "阴"]:
                    overall_eval = "不错的天气"
                    recommendation = "适合日常活动和出行"
                elif weather_condition == "雨":
                    overall_eval = "需要注意的天气"
                    recommendation = "建议携带雨具，注意防滑"
                elif temperature < 10 or temperature > 35:
                    overall_eval = "需要适应的天气"
                    recommendation = "注意保暖或防暑降温"
                else:
                    overall_eval = "一般的天气"
                    recommendation = "根据个人情况安排活动"
            else:
                overall_eval = "天气状况一般"
                recommendation = "建议关注实时天气变化"
            
            # 构建分析结果
            analysis += f"\n\n🌤️ 天气质量分析\n"
            analysis += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            if temperature:
                analysis += f"🌡️ 温度评价：{temp_eval} ({temperature}°C)\n"
            if weather_condition:
                analysis += f"☁️ 天气状况：{condition_eval}\n"
            if wind:
                analysis += f"💨 风力情况：{wind}\n"
            analysis += f"\n📊 综合评价：{overall_eval}\n"
            analysis += f"💡 建议：{recommendation}\n"
            analysis += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            
            return analysis
            
        except Exception as e:
            return f"（微微皱眉）抱歉训练员，分析天气时遇到了问题：{str(e)}"

    def update_tts_config(self, config):
        """更新TTS配置"""
        try:
            tts_engine = config.get("tts_engine", "azure")  # 默认使用Azure TTS

            # 检查是否需要切换TTS引擎
            if hasattr(self, 'tts_engine') and self.tts_engine != tts_engine:
                # 切换TTS引擎
                if tts_engine == "gpt_sovits":
                    # 切换到GPT-SoVITS TTS
                    gpt_sovits_api_url = config.get("gpt_sovits_api_url", "http://127.0.0.1:9880")
                    ref_audio_path = config.get("gpt_sovits_ref_audio", "")
                    from gpt_sovits_simple import SimpleGPTSoVITS
                    self.tts_manager = SimpleGPTSoVITS(gpt_sovits_api_url, ref_audio_path)
                    self.tts_engine = "gpt_sovits"
                    print("✅ 已切换到GPT-SoVITS TTS")
                else:
                    # 切换到Azure TTS
                    from tts_manager import TTSManager
                    azure_key = config.get("azure_tts_key", "")
                    azure_region = config.get("azure_region", "eastasia")
                    if azure_key:
                        self.tts_manager = TTSManager(azure_key, azure_region)
                        self.tts_engine = "azure"
                        print("✅ 已切换到Azure TTS")
                    else:
                        self.tts_manager = None
                        self.tts_engine = None
                        print("ℹ️ 未配置Azure TTS密钥，TTS功能已禁用")
            else:
                # 不切换引擎，只更新配置
                if self.tts_engine == "gpt_sovits" and self.tts_manager:
                    # 更新GPT-SoVITS配置
                    gpt_sovits_api_url = config.get("gpt_sovits_api_url", "http://127.0.0.1:9880")
                    ref_audio_path = config.get("gpt_sovits_ref_audio", "")

                    # 如果API URL或参考音频发生变化，重新创建管理器
                    if (gpt_sovits_api_url != self.tts_manager.api_url or 
                        ref_audio_path != self.tts_manager.ref_audio_path):
                        from gpt_sovits_simple import SimpleGPTSoVITS
                        self.tts_manager = SimpleGPTSoVITS(gpt_sovits_api_url, ref_audio_path)
                        print("✅ GPT-SoVITS TTS配置已更新")
                    else:
                        print("✅ GPT-SoVITS TTS配置无需更新")
                elif self.tts_engine == "azure" and self.tts_manager:
                    # 更新Azure TTS配置
                    from tts_manager import TTSManager
            
                    azure_key = config.get("azure_tts_key", "")
                    azure_region = config.get("azure_region", "eastasia")
            
                    # 如果TTS管理器不存在，创建新的
                    if not hasattr(self, 'tts_manager') or self.tts_manager is None:
                        self.tts_manager = TTSManager(azure_key, azure_region)
                        print("✅ Azure TTS管理器已创建")
                    else:
                        # 更新现有TTS配置
                        self.tts_manager.update_config(azure_key, azure_region)
                        print("✅ Azure TTS配置已更新")
            
            # 如果TTS已启用，设置语音和语速
            if config.get("tts_enabled", False) and self.tts_manager:
                if self.tts_engine == "azure":
                    self.tts_manager.set_voice(config.get("tts_voice", "zh-CN-XiaoxiaoNeural"))
                # 设置语速（两个引擎都支持）
                self.tts_manager.set_speaking_rate(config.get("tts_speaking_rate", 1.0))
                print("✅ TTS功能已启用")
            else:
                print("ℹ️ TTS功能已禁用")
                
        except Exception as e:
            print(f"⚠️ TTS配置更新失败: {str(e)}")
            self.tts_manager = None
    
    def stop_tts(self):
        """停止TTS播放"""
        if hasattr(self, 'tts_manager'):
            self.tts_manager.stop_speaking()
    
    def cleanup_tts(self):
        """清理TTS资源"""
        if hasattr(self, 'tts_manager'):
            self.tts_manager.cleanup()
    
    def test_tts(self):
        """测试TTS功能"""
        if hasattr(self, 'tts_manager') and self.tts_manager:
            return self.tts_manager.test_tts("你好，这是东海帝王的TTS测试")
        else:
            print("❌ TTS管理器未初始化")
            return False

    def _simple_parse_file_info(self, user_input, context_info):
        """简单解析文件信息（AI智能优先）"""
        try:
            print(f"🔍 开始AI智能解析文件信息: {user_input}")
            
            file_info = {
                "title": "未命名文件",
                "filename": "未命名文件.txt",
                "location": "D:/",
                "content": context_info
            }
            
            # 从用户输入和上下文中提取旅游目的地
            destination = self._extract_travel_destination(user_input, context_info)
            
            # 从用户输入中提取信息
            if "旅游" in user_input or "旅行" in user_input or "旅游计划" in user_input or "攻略" in user_input:
                if destination:
                    file_info["title"] = f"{destination}旅游攻略"
                    file_info["filename"] = f"{destination}旅游攻略.txt"
                else:
                    file_info["title"] = "旅游攻略"
                    file_info["filename"] = "旅游攻略.txt"
                
                # 从上下文中提取旅游计划内容
                if destination and destination in context_info:
                    # 提取包含目的地的内容
                    lines = context_info.split('\n')
                    relevant_lines = []
                    for line in lines:
                        if destination in line or "旅游" in line or "旅行" in line or "攻略" in line or "景点" in line or "行程" in line:
                            relevant_lines.append(line)
                    if relevant_lines:
                        file_info["content"] = "\n".join(relevant_lines)
                    else:
                        file_info["content"] = context_info
                else:
                    file_info["content"] = context_info
            elif "音乐" in user_input or "歌单" in user_input or "歌曲" in user_input:
                # 用户明确要求音乐相关文件
                file_info["title"] = "音乐推荐"
                file_info["filename"] = "音乐推荐.txt"
                file_info["content"] = context_info
            elif "保存" in user_input:
                # 检查用户是否明确指定了文件类型
                if ".py" in user_input.lower() or "python" in user_input.lower():
                    file_info["title"] = "Python代码"
                    file_info["filename"] = "Python代码.py"
                elif ".cpp" in user_input.lower() or "c++" in user_input.lower():
                    file_info["title"] = "C++代码"
                    file_info["filename"] = "C++代码.cpp"
                elif ".java" in user_input.lower():
                    file_info["title"] = "Java代码"
                    file_info["filename"] = "Java代码.java"
                elif ".js" in user_input.lower() or "javascript" in user_input.lower():
                    file_info["title"] = "JavaScript代码"
                    file_info["filename"] = "JavaScript代码.js"
                elif ".txt" in user_input.lower():
                    # 用户明确要求txt文件，根据上下文内容确定类型
                    if "音乐" in context_info or "歌" in context_info or "歌曲" in context_info or "推荐" in context_info:
                        file_info["title"] = "音乐推荐"
                        file_info["filename"] = "音乐推荐.txt"
                    elif "旅游" in context_info or "旅行" in context_info or "攻略" in context_info:
                        file_info["title"] = "旅游攻略"
                        file_info["filename"] = "旅游攻略.txt"
                    elif "代码" in context_info or "程序" in context_info or "```" in context_info:
                        file_info["title"] = "代码文件"
                        file_info["filename"] = "代码文件.txt"
                    else:
                        file_info["title"] = "文档"
                        file_info["filename"] = "文档.txt"
                else:
                    # 🚀 AI智能识别文件类型（最高优先级）
                    print(f"🤖 用户说'帮我保存'，开始AI智能识别文件类型")
                    ai_file_type = self._ai_identify_file_type(user_input, context_info)
                    if ai_file_type:
                        print(f"✅ AI智能识别文件类型成功: {ai_file_type}")
                        file_info["title"] = ai_file_type["title"]
                        file_info["filename"] = ai_file_type["filename"]
                    else:
                        print(f"⚠️ AI智能识别文件类型失败，使用关键词识别后备方案")
                        # 关键词识别后备方案 - 优先检查当前对话的上下文
                        # 检查是否包含旅游相关内容
                        if any(keyword in context_info for keyword in ["旅游", "旅行", "攻略", "景点", "行程"]):
                            # 🚀 智能提取目的地名称 - 优先从用户问题中提取
                            destinations = [
                                "法兰克福", "贝尔格莱德", "柏林", "塔林", "巴黎", "伦敦", "罗马", "东京", "纽约",
                                "阿姆斯特丹", "巴塞罗那", "维也纳", "布拉格", "布达佩斯", "华沙", "莫斯科", "圣彼得堡",
                                "伊斯坦布尔", "迪拜", "新加坡", "曼谷", "首尔", "悉尼", "墨尔本", "温哥华", "多伦多"
                            ]
                            
                            destination = None
                            
                            # 首先尝试从用户问题中提取（优先级最高）
                            user_question = ""
                            for conv in self.session_conversations[-3:]:  # 检查最近3轮对话
                                if "旅游" in conv.get("user_input", "") or "攻略" in conv.get("user_input", ""):
                                    user_question = conv.get("user_input", "")
                                    break
                            
                            if user_question:
                                for dest in destinations:
                                    if dest in user_question:
                                        destination = dest
                                        print(f"✅ 从用户问题中提取到目的地: {destination}")
                                        break
                            
                            # 如果用户问题中没有找到，再从上下文中查找
                            if not destination:
                                for dest in destinations:
                                    if dest in context_info:
                                        destination = dest
                                        print(f"✅ 从上下文中提取到目的地: {destination}")
                                        break
                            
                            if destination:
                                file_info["title"] = f"{destination}旅游攻略"
                                file_info["filename"] = f"{destination}旅游攻略.txt"
                                print(f"✅ 生成文件名: {file_info['filename']}")
                            else:
                                file_info["title"] = "旅游攻略"
                                file_info["filename"] = "旅游攻略.txt"
                                print(f"⚠️ 未找到具体目的地，使用通用名称")
                        elif any(keyword in context_info for keyword in ["代码", "程序", "```", "python", "c++", "java"]):
                            file_info["title"] = "代码文件"
                            file_info["filename"] = "代码文件.txt"
                        elif any(keyword in context_info for keyword in ["笔记", "记录", "备忘"]):
                            file_info["title"] = "笔记"
                            file_info["filename"] = "笔记.txt"
                        else:
                            # 如果都无法确定，使用AI智能识别的结果
                            file_info["title"] = "文档"
                            file_info["filename"] = "文档.txt"
                file_info["content"] = context_info
            elif "笔记" in user_input:
                file_info["title"] = "笔记"
                file_info["filename"] = "笔记.txt"
                file_info["content"] = context_info
            elif "代码" in user_input or "程序" in user_input or "python" in user_input.lower():
                # 根据编程语言确定文件扩展名
                if "python" in user_input.lower() or "py" in user_input.lower():
                    file_info["title"] = "Python代码"
                    file_info["filename"] = "Python代码.py"
                elif "c++" in user_input.lower() or "cpp" in user_input.lower():
                    file_info["title"] = "C++代码"
                    file_info["filename"] = "C++代码.cpp"
                elif "java" in user_input.lower():
                    file_info["title"] = "Java代码"
                    file_info["filename"] = "Java代码.java"
                elif "javascript" in user_input.lower() or "js" in user_input.lower():
                    file_info["title"] = "JavaScript代码"
                    file_info["filename"] = "JavaScript代码.js"
                else:
                    file_info["title"] = "代码文件"
                    file_info["filename"] = "代码文件.txt"
                file_info["content"] = context_info
            else:
                file_info["title"] = "文档"
                file_info["filename"] = "文档.txt"
                file_info["content"] = context_info
            
            # 🚀 AI智能路径识别（优先级最高）
            ai_path_result = self._ai_identify_save_path(user_input, context_info)
            if ai_path_result:
                print(f"✅ AI智能识别路径成功: {ai_path_result}")
                file_info["location"] = ai_path_result
            else:
                print(f"⚠️ AI智能识别路径失败，使用关键词识别后备方案")
                # 关键词识别作为后备方案
                import re
                
                # 优先检查用户是否明确指定了路径
                if "d盘" in user_input.lower() or "d:" in user_input.lower():
                    file_info["location"] = "D:/"
                elif "c盘" in user_input.lower() or "c:" in user_input.lower():
                    file_info["location"] = "C:/"
                else:
                    # 匹配各种路径格式
                    path_patterns = [
                        r'保存到\s*([A-Za-z]:[^，。\s]*)',  # 保存到D:\测试_
                        r'保存到\s*([A-Za-z]:[^，。\s]*)',  # 保存到D:/测试_
                        r'位置在\s*([A-Za-z]:[^，。\s]*)',  # 位置在D:\测试_
                        r'位置\s*是\s*([A-Za-z]:[^，。\s]*)',  # 位置是D:\测试_
                        r'([A-Za-z]:[^，。\s]*)',  # 直接说D:\测试_
                    ]
                    
                    extracted_path = None
                    for pattern in path_patterns:
                        match = re.search(pattern, user_input, re.IGNORECASE)
                        if match:
                            extracted_path = match.group(1)
                            break
                    
                    if extracted_path:
                        # 标准化路径格式
                        extracted_path = extracted_path.replace('\\', '/')
                        if not extracted_path.endswith('/'):
                            extracted_path += '/'
                        file_info["location"] = extracted_path
                    else:
                        # 使用默认保存路径
                        default_path = self.config.get("default_save_path", "D:/东海帝王文件/")
                        if default_path and os.path.exists(default_path):
                            file_info["location"] = default_path
                        else:
                            # 如果默认路径不存在，尝试创建
                            try:
                                os.makedirs(default_path, exist_ok=True)
                                file_info["location"] = default_path
                            except:
                                # 如果创建失败，使用D盘根目录
                                file_info["location"] = "D:/"
            
            print(f"🔍 简单解析结果: {file_info['title']} -> {file_info['filename']} -> {file_info['location']}")
            return file_info
            
        except Exception as e:
            print(f"❌ 简单解析失败: {str(e)}")
            return None

    def _ai_identify_save_path(self, user_input, context_info):
        """使用AI智能识别保存路径"""
        try:
            print(f"🤖 开始AI智能识别保存路径: {user_input}")
            
            # 检查是否有API密钥
            model = self.config.get("selected_model", "deepseek-chat")
            api_key = self.config.get("deepseek_key", "") if "deepseek" in model else self.config.get("openai_key", "")
            
            if not api_key:
                print("⚠️ 没有API密钥，无法使用AI智能识别路径")
                return None
            
            # 构建AI提示词
            prompt = f"""
请分析用户的文件保存请求，智能识别他们想要保存文件的具体路径。

用户输入：{user_input}

上下文信息：{context_info}

请从以下选项中选择最合适的保存路径：
1. D:/ - 如果用户明确说"D盘"、"D:"或暗示要保存到D盘
2. C:/ - 如果用户明确说"C盘"、"C:"或暗示要保存到C盘
3. E:/ - 如果用户明确说"E盘"、"E:"或暗示要保存到E盘
4. D:/东海帝王文件/ - 如果用户没有指定具体位置，使用默认路径
5. 其他具体路径 - 如果用户明确指定了其他路径

请只返回路径字符串，不要包含任何其他文字。例如：
- 如果用户说"保存到D盘"，返回：D:/
- 如果用户说"保存到C盘根目录"，返回：C:/
- 如果用户说"保存到桌面"，返回：C:/Users/用户名/Desktop/
- 如果用户没有指定位置，返回：D:/东海帝王文件/
"""
            
            # 设置API客户端
            if "deepseek" in model:
                client = openai.OpenAI(
                    api_key=api_key,
                    base_url="https://api.deepseek.com/v1"
                )
            else:
                client = openai.OpenAI(api_key=api_key)
            
            # 调用AI API
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一个文件路径识别专家，请根据用户输入智能识别保存路径。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.1,
                timeout=30
            )
            
            # 提取AI响应
            ai_response = response.choices[0].message.content.strip()
            print(f"🤖 AI路径识别响应: {ai_response}")
            
            # 验证AI响应是否为有效路径
            if ai_response and self._is_valid_path(ai_response):
                return ai_response
            else:
                print(f"⚠️ AI返回的路径无效: {ai_response}")
                return None
                
        except Exception as e:
            print(f"❌ AI智能识别路径失败: {str(e)}")
            return None

    def _is_valid_path(self, path):
        """验证路径是否有效"""
        try:
            import re
            # 检查是否是有效的Windows路径格式
            if re.match(r'^[A-Za-z]:[/\\]', path):
                return True
            # 检查是否是相对路径
            elif path.startswith('./') or path.startswith('../'):
                return True
            # 检查是否是网络路径
            elif path.startswith('\\\\'):
                return True
            else:
                return False
        except:
            return False

    def _extract_travel_destination(self, user_input, context_info):
        """从用户输入和上下文中提取旅游目的地"""
        # 常见的旅游目的地
        destinations = [
            "北京", "上海", "广州", "深圳", "杭州", "南京", "苏州", "成都", "重庆", "西安",
            "香港", "澳门", "台湾", "日本", "韩国", "泰国", "新加坡", "马来西亚", "越南",
            "美国", "加拿大", "英国", "法国", "德国", "意大利", "西班牙", "澳大利亚", "新西兰"
        ]
        
        # 从用户输入中查找目的地
        for dest in destinations:
            if dest in user_input:
                return dest
        
        # 从上下文中查找目的地
        for dest in destinations:
            if dest in context_info:
                return dest
        
        return None

    def _analyze_user_request_type(self, user_input):
        """分析用户请求的类型"""
        user_input_lower = user_input.lower()
        
        # 明确的文件创建请求
        file_creation_keywords = ["保存", "创建文件", "写入文件", "生成文件", "输出文件", "保存到", "创建到"]
        if any(keyword in user_input_lower for keyword in file_creation_keywords):
            # 进一步判断是什么类型的文件
            if any(keyword in user_input_lower for keyword in ["音乐", "歌", "歌曲", "歌单"]):
                return "music_file"
            elif any(keyword in user_input_lower for keyword in ["旅游", "旅行", "攻略", "景点"]):
                return "travel_file"
            elif any(keyword in user_input_lower for keyword in ["代码", "程序", "c++", "python", "java"]):
                return "code_file"
            elif any(keyword in user_input_lower for keyword in ["笔记", "记录", "备忘"]):
                return "note_file"
            elif any(keyword in user_input_lower for keyword in ["文件夹", "目录"]):
                return "folder"
            else:
                return "general_file"
        
        # 代码展示请求（不是文件创建）
        code_display_keywords = ["帮我写", "写一个", "用c++写", "用python写", "用java写", "写个", "帮我用"]
        if any(keyword in user_input_lower for keyword in code_display_keywords):
            return "code_display"
        
        # 音乐相关请求
        music_keywords = ["音乐", "歌", "歌曲", "歌单", "播放", "推荐音乐", "推荐"]
        if any(keyword in user_input_lower for keyword in music_keywords):
            return "music"
        
        # 旅游相关请求
        travel_keywords = ["旅游", "旅行", "攻略", "景点", "行程", "酒店", "机票"]
        if any(keyword in user_input_lower for keyword in travel_keywords):
            return "travel"
        
        # 笔记相关请求
        note_keywords = ["笔记", "记录", "备忘", "清单", "计划"]
        if any(keyword in user_input_lower for keyword in note_keywords):
            return "note"
        
        # 文件夹相关请求
        folder_keywords = ["文件夹", "目录", "创建文件夹", "新建文件夹"]
        if any(keyword in user_input_lower for keyword in folder_keywords):
            return "folder"
        
        return "unknown"

    def _ai_identify_file_type(self, user_input, context_info):
        """使用AI智能识别文件类型"""
        try:
            print(f"🤖 开始AI智能识别文件类型: {user_input}")
            
            # 检查是否有API密钥
            model = self.config.get("selected_model", "deepseek-chat")
            api_key = self.config.get("deepseek_key", "") if "deepseek" in model else self.config.get("openai_key", "")
            
            if not api_key:
                print("⚠️ 没有API密钥，无法使用AI智能识别文件类型")
                return None
            
            # 构建AI提示词
            prompt = f"""
请分析用户的文件保存请求，智能识别他们想要保存的文件类型。

用户输入：{user_input}

上下文信息：{context_info}

🚀 重要提示：请仔细分析用户的问题和对话内容，准确识别：
1. 如果是旅游攻略，请从用户问题中提取具体的城市名称（如法兰克福、柏林、巴黎等）
2. 如果是音乐推荐，请识别是中文歌、英文歌还是其他类型
3. 如果是代码文件，请识别编程语言类型
4. 如果是笔记文档，请识别具体内容类型

请从以下选项中选择最合适的文件类型：
1. 旅游攻略 - 如果上下文包含旅游、旅行、攻略、景点、行程、城市名称等信息
2. 音乐推荐 - 如果上下文包含音乐、歌曲、歌单、推荐等信息
3. 代码文件 - 如果上下文包含代码、程序、编程等信息
4. 笔记文档 - 如果上下文包含笔记、记录、备忘等信息
5. 其他类型 - 根据具体内容确定

请返回JSON格式：
{{
    "title": "文件标题",
    "filename": "文件名.扩展名"
}}

例如：
- 如果用户要保存法兰克福旅游攻略，返回：{{"title": "法兰克福旅游攻略", "filename": "法兰克福旅游攻略.txt"}}
- 如果用户要保存柏林旅游攻略，返回：{{"title": "柏林旅游攻略", "filename": "柏林旅游攻略.txt"}}
- 如果用户要保存贝尔格莱德旅游攻略，返回：{{"title": "贝尔格莱德旅游攻略", "filename": "贝尔格莱德旅游攻略.txt"}}
- 如果用户要保存中文歌推荐，返回：{{"title": "中文歌推荐", "filename": "中文歌推荐.txt"}}
- 如果用户要保存代码，返回：{{"title": "代码文件", "filename": "代码文件.py"}}

请只返回JSON，不要包含任何其他文字。
"""
            
            # 设置API客户端
            if "deepseek" in model:
                client = openai.OpenAI(
                    api_key=api_key,
                    base_url="https://api.deepseek.com/v1"
                )
            else:
                client = openai.OpenAI(api_key=api_key)
            
            # 调用AI API
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一个文件类型识别专家，请根据用户输入和上下文智能识别文件类型。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.1,
                timeout=60
            )
            
            # 提取AI响应
            ai_response = response.choices[0].message.content.strip()
            print(f"🤖 AI文件类型识别响应: {ai_response}")
            
            # 尝试解析JSON响应
            try:
                import json
                # 清理JSON字符串
                if ai_response.startswith('```json'):
                    ai_response = ai_response[7:]
                if ai_response.endswith('```'):
                    ai_response = ai_response[:-3]
                ai_response = ai_response.strip()
                
                file_type_info = json.loads(ai_response)
                
                # 验证返回的信息
                if "title" in file_type_info and "filename" in file_type_info:
                    return file_type_info
                else:
                    print(f"⚠️ AI返回的文件类型信息不完整: {file_type_info}")
                    return None
                    
            except json.JSONDecodeError as e:
                print(f"⚠️ AI返回的JSON格式无效: {str(e)}")
                return None
                
        except Exception as e:
            print(f"❌ AI智能识别文件类型失败: {str(e)}")
            return None


