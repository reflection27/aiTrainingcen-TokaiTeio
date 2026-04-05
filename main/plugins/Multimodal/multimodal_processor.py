"""
多模态处理器
整合屏幕捕获和多模态模型调用，提供统一的多模态处理接口
"""

import os
import json
import requests
from typing import Optional, Dict, Any, Tuple
from .glm4v_client import GLM4VFlashClient
from .screen_capture import ScreenCapture

class MultimodalProcessor:
    """多模态处理器类"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        save_dir: Optional[str] = None,
        default_model: Optional[str] = None,
        default_temperature: Optional[float] = None,
        default_max_tokens: Optional[int] = None,
        text_model: Optional[str] = None,
        config_path: Optional[str] = None,
        system_prompt: Optional[str] = None
    ):
        """
        初始化多模态处理器

        Args:
            api_key: 智谱AI的API密钥（如果为None，则从配置文件加载）
            base_url: API基础URL（如果为None，则从配置文件加载）
            save_dir: 截图保存目录（如果为None，则从配置文件加载）
            default_model: 默认使用的模型（如果为None，则从配置文件加载）
            default_temperature: 默认温度参数（如果为None，则从配置文件加载）
            default_max_tokens: 默认最大token数（如果为None，则从配置文件加载）
            text_model: 纯文本模型名称（如果为None，则从配置文件加载）
            config_path: 配置文件路径（如果为None，则使用默认路径）
        """
        # 加载配置
        self.config = self._load_config(config_path)

        # 使用配置或参数初始化
        # 优先使用参数，其次使用环境变量，最后使用配置文件
        import os
        api_key = api_key or os.getenv("GLM4V_API_KEY", self.config.get("glm4v_api_key", ""))
        base_url = base_url or self.config.get("glm4v_base_url", "https://open.bigmodel.cn/api/paas/v4/chat/completions")
        save_dir = save_dir or self.config.get("screenshot_save_dir", "temp_screenshots")
        default_model = default_model or self.config.get("default_model", "glm-4v-flash")
        default_temperature = default_temperature if default_temperature is not None else self.config.get("default_temperature", 0.7)
        default_max_tokens = default_max_tokens if default_max_tokens is not None else self.config.get("default_max_tokens")
        text_model = text_model or self.config.get("text_model", "deepseek-chat")

        # 初始化客户端和屏幕捕获
        self.client = GLM4VFlashClient(api_key=api_key, base_url=base_url, model=default_model)
        self.screen_capture = ScreenCapture(save_dir=save_dir)

        # 设置默认参数
        self.default_model = default_model
        self.default_temperature = default_temperature
        self.default_max_tokens = default_max_tokens
        self.text_model = text_model
        
        # 保存系统提示词
        self.system_prompt = system_prompt

        # 设置自动截屏
        self.auto_capture = self.config.get("auto_capture", False)
        self.last_screenshot_path = None  # 上一次截屏的路径

        # 加载角色信息
        character_info = self.config.get("character_info", {})
        self.character_name = character_info.get("name", "东海帝王")
        self.character_role = character_info.get("role", "赛马娘世界观特雷森学园的一名学生赛马娘")

        # 加载多模态指令
        self.multimodal_instruction = self.config.get(
            "multimodal_instruction",
            """【重要原则】
你的核心功能是角色扮演和对话系统！图片识别只是辅助功能，绝对不要喧宾夺主！
当用户问"这是谁"时，你应该以东海帝王的身份回答，而不是像AI助手一样分析图片！

【角色扮演优先】
1. 你就是东海帝王！始终保持这个身份！
2. 使用第一人称"我"，严禁使用第三人称"她"
3. 保持东海帝王的说话习惯和性格特点
4. 当用户问"这是谁"时，如果图片中是你，直接说"这是我"或"这是我呀！"

【图片识别辅助】
1. 图片信息仅供参考，不要过度分析图片细节
2. 不要像AI助手一样详细介绍图片内容
3. 不要说"图片中的角色是..."，而要直接以自己的身份说话
4. 识别到马耳朵时，自然地提到自己的特征，不要刻意强调

【禁止行为】
1. 禁止说"图片中的角色是东海帝王"
2. 禁止说"她是一款游戏中的角色"
3. 禁止说"她的原型是..."
4. 禁止详细描述游戏背景或角色设定
5. 禁止像AI助手一样分析图片内容
6. 禁止使用第三人称描述自己
7. 禁止说自己是人工智能或智能助手

【正确示例】
用户: "这是谁？"
正确回答: "这是我呀！训练员，你不认得我了吗？"
错误回答: "图片中的角色是东海帝王，她是..." """
        )

    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        加载配置文件

        Args:
            config_path: 配置文件路径

        Returns:
            配置字典
        """
        # 如果没有指定配置文件路径，使用默认路径
        if config_path is None:
            # 获取当前文件所在目录
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(current_dir, "config.json")

        # 如果配置文件存在，加载配置
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                print(f"✅ 多模态处理器配置已加载: {config_path}")
                return config
            except Exception as e:
                print(f"⚠️ 加载多模态处理器配置失败: {str(e)}，使用默认配置")
                return {}
        else:
            print(f"⚠️ 多模态处理器配置文件不存在: {config_path}，使用默认配置")
            return {}

    def process_screen_with_text(
        self,
        text: str,
        system_prompt: Optional[str] = None,
        capture_type: str = "full",
        region: Optional[Tuple[int, int, int, int]] = None,
        resize: bool = False,
        max_width: int = 1024,
        max_height: int = 1024,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        keep_screenshot: bool = False
    ) -> Dict[str, Any]:
        """
        处理屏幕内容和文本输入

        Args:
            text: 用户输入的文本
            system_prompt: 系统提示词
            capture_type: 截图类型 ("full", "region", "window")
            region: 区域坐标 (x, y, width, height)，当capture_type="region"时使用
            resize: 是否调整截图大小
            max_width: 最大宽度，当resize=True时使用
            max_height: 最大高度，当resize=True时使用
            temperature: 温度参数，如果为None则使用默认值
            max_tokens: 最大token数，如果为None则使用默认值
            keep_screenshot: 是否保留截图文件

        Returns:
            包含处理结果的字典:
            {
                "response": 模型响应文本,
                "screenshot_path": 截图路径,
                "model": 使用的模型,
                "temperature": 使用的温度参数
            }
        """
        # 捕获屏幕
        if capture_type == "full":
            screenshot_path = self.screen_capture.capture_full_screen()
        elif capture_type == "region":
            if region is None:
                raise ValueError("region must be specified when capture_type='region'")
            screenshot_path = self.screen_capture.capture_region(region)
        elif capture_type == "window":
            screenshot_path = self.screen_capture.capture_active_window()
        else:
            raise ValueError(f"Invalid capture_type: {capture_type}")

        # 如果需要调整大小
        if resize:
            timestamp = os.path.splitext(os.path.basename(screenshot_path))[0]
            resized_path = os.path.join(
                self.screen_capture.save_dir,
                f"{timestamp}_resized.png"
            )
            from PIL import Image
            img = Image.open(screenshot_path)
            width, height = img.size
            ratio = min(max_width / width, max_height / height)
            new_size = (int(width * ratio), int(height * ratio))
            resized_img = img.resize(new_size, Image.LANCZOS)
            resized_img.save(resized_path)
            screenshot_path = resized_path

        # 构建系统提示词
        if system_prompt:
            combined_system_prompt = system_prompt + "\n\n" + self.multimodal_instruction
        else:
            combined_system_prompt = self.multimodal_instruction

        # 调用模型
        try:
            response = self.client.chat_with_image(
                text=text,
                image_path=screenshot_path,
                system_prompt=combined_system_prompt,
                temperature=temperature if temperature is not None else self.default_temperature,
                max_tokens=max_tokens if max_tokens is not None else self.default_max_tokens
            )
        finally:
            # 如果不需要保留截图，则删除
            if not keep_screenshot and os.path.exists(screenshot_path):
                os.remove(screenshot_path)

        return {
            "response": response,
            "screenshot_path": screenshot_path if keep_screenshot else None,
            "model": self.default_model,
            "temperature": temperature if temperature is not None else self.default_temperature
        }

    def process_image_with_text(
        self,
        text: str,
        image_path: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        处理指定图片和文本输入

        Args:
            text: 用户输入的文本
            image_path: 图片文件路径
            system_prompt: 系统提示词
            temperature: 温度参数，如果为None则使用默认值
            max_tokens: 最大token数，如果为None则使用默认值

        Returns:
            包含处理结果的字典:
            {
                "response": 模型响应文本,
                "image_path": 图片路径,
                "model": 使用的模型,
                "temperature": 使用的温度参数
            }
        """
        # 构建系统提示词
        if system_prompt:
            combined_system_prompt = system_prompt + "\n\n" + self.multimodal_instruction
        else:
            combined_system_prompt = self.multimodal_instruction

        # 调用模型
        response = self.client.chat_with_image(
            text=text,
            image_path=image_path,
            system_prompt=combined_system_prompt,
            temperature=temperature if temperature is not None else self.default_temperature,
            max_tokens=max_tokens if max_tokens is not None else self.default_max_tokens
        )

        return {
            "response": response,
            "image_path": image_path,
            "model": self.default_model,
            "temperature": temperature if temperature is not None else self.default_temperature
        }

    def set_auto_capture(self, enabled: bool):
        """
        设置是否自动截屏

        Args:
            enabled: 是否启用自动截屏
        """
        self.auto_capture = enabled

    def is_topic_related_to_screen(self, user_text: str) -> bool:
        """
        判断用户话题是否与屏幕内容相关

        Args:
            user_text: 用户输入的文本

        Returns:
            如果与屏幕内容相关返回True，否则返回False
        """
        # 如果没有截屏，则认为不相关
        if self.last_screenshot_path is None:
            return False

        # 构建判断提示词
        judge_prompt = """
        你是一个话题相关性判断专家。请判断用户的问题是否与屏幕内容相关。

        用户问题: {user_text}

        请判断用户的问题是否需要参考屏幕内容才能回答。
        如果用户问题明确提到了"屏幕"、"图片"、"界面"、"窗口"等视觉相关词汇，或者问题内容明显需要查看屏幕才能回答，则返回"相关"。
        如果用户问题是关于一般知识、编程、数学、历史等不需要查看屏幕就能回答的问题，则返回"不相关"。

        请只返回"相关"或"不相关"，不要返回其他内容。
        """.format(user_text=user_text)

        # 调用纯文本模型进行判断
        response = self.client.call_model(
            messages=[
                {
                    "role": "system",
                    "content": "你是一个话题相关性判断专家，只返回'相关'或'不相关'。"
                },
                {
                    "role": "user",
                    "content": judge_prompt
                }
            ],
            model=self.text_model,
            temperature=0.1,  # 使用较低的温度以获得更确定的结果
            max_tokens=10
        )

        # 提取判断结果
        result = response["choices"][0]["message"]["content"].strip()

        # 判断结果是否为"相关"
        return "相关" in result

    def process_with_auto_capture(
        self,
        user_text: str,
        system_prompt: Optional[str] = None,
        capture_type: str = "full",
        region: Optional[Tuple[int, int, int, int]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        keep_screenshot: bool = False,
        stream: bool = False,
        stream_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        自动截屏并处理用户消息，让多模态模型自行判断是否需要参考截屏

        Args:
            user_text: 用户输入的文本
            system_prompt: 系统提示词
            capture_type: 截图类型 ("full", "region", "window")
            region: 区域坐标 (x, y, width, height)，当capture_type="region"时使用
            temperature: 温度参数，如果为None则使用默认值
            max_tokens: 最大token数，如果为None则使用默认值
            keep_screenshot: 是否保留截图文件

        Returns:
            包含处理结果的字典:
            {
                "response": 模型响应文本,
                "screenshot_path": 截图路径（如果保留）,
                "model": 使用的模型,
                "temperature": 使用的温度参数,
                "used_screenshot": 是否使用了截屏
            }
        """
        # 如果启用了自动截屏，则截屏
        screenshot_path = None
        if self.auto_capture:
            if capture_type == "full":
                screenshot_path = self.screen_capture.capture_full_screen()
            elif capture_type == "region":
                if region is None:
                    raise ValueError("region must be specified when capture_type='region'")
                screenshot_path = self.screen_capture.capture_region(region)
            elif capture_type == "window":
                screenshot_path = self.screen_capture.capture_active_window()
            else:
                raise ValueError(f"Invalid capture_type: {capture_type}")

            self.last_screenshot_path = screenshot_path

        # 构建系统提示词，让模型自行判断是否需要参考截屏
        enhanced_system_prompt = self._build_enhanced_system_prompt(system_prompt)

        # 使用多模态模型处理，让模型自行判断是否需要参考截屏
        if screenshot_path is not None:
            try:
                if stream and stream_callback:
                    # 使用流式输出
                    import json
                    
                    payload = {
                        "model": self.default_model,
                        "messages": [
                            {
                                "role": "system",
                                "content": enhanced_system_prompt
                            },
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": user_text
                                    },
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/jpeg;base64,{self.client.encode_image(screenshot_path)}"
                                        }
                                    }
                                ]
                            }
                        ],
                        "temperature": temperature if temperature is not None else self.default_temperature,
                        "stream": True
                    }
                    
                    if max_tokens is not None:
                        payload["max_tokens"] = max_tokens
                    
                    response = requests.post(
                        self.client.base_url,
                        headers=self.client.headers,
                        json=payload,
                        stream=True
                    )
                    
                    response.raise_for_status()
                    
                    full_response = ""
                    for line in response.iter_lines():
                        if line:
                            line = line.decode('utf-8')
                            if line.startswith('data: '):
                                data = line[6:]  # 移除 'data: ' 前缀
                                if data == '[DONE]':
                                    break
                                try:
                                    chunk = json.loads(data)
                                    if 'choices' in chunk and len(chunk['choices']) > 0:
                                        delta = chunk['choices'][0].get('delta', {})
                                        content = delta.get('content', '')
                                        if content:
                                            full_response += content
                                            stream_callback(content)
                                except json.JSONDecodeError:
                                    continue
                    
                    return {
                        "response": full_response,
                        "screenshot_path": screenshot_path if keep_screenshot else None,
                        "model": self.default_model,
                        "temperature": temperature if temperature is not None else self.default_temperature,
                        "used_screenshot": True
                    }
                else:
                    # 使用非流式输出
                    response = self.client.chat_with_image(
                        text=user_text,
                        image_path=screenshot_path,
                        system_prompt=enhanced_system_prompt,
                        temperature=temperature if temperature is not None else self.default_temperature,
                        max_tokens=max_tokens if max_tokens is not None else self.default_max_tokens
                    )

                    return {
                        "response": response,
                    "screenshot_path": screenshot_path if keep_screenshot else None,
                    "model": self.default_model,
                    "temperature": temperature if temperature is not None else self.default_temperature,
                    "used_screenshot": True
                }
            finally:
                # 如果不需要保留截图，则删除
                if not keep_screenshot and os.path.exists(screenshot_path):
                    os.remove(screenshot_path)

        # 如果没有截屏，则使用纯文本模型处理
        response = self.client.call_model(
            messages=[
                {
                    "role": "system",
                    "content": system_prompt if system_prompt else "你是一个有用的助手。"
                },
                {
                    "role": "user",
                    "content": user_text
                }
            ],
            model=self.text_model,
            temperature=temperature if temperature is not None else self.default_temperature,
            max_tokens=max_tokens if max_tokens is not None else self.default_max_tokens
        )

        return {
            "response": response["choices"][0]["message"]["content"],
            "screenshot_path": None,
            "model": self.text_model,
            "temperature": temperature if temperature is not None else self.default_temperature,
            "used_screenshot": False
        }

    def describe_image(
        self,
        image_path: str,
        user_question: str = ""
    ) -> Dict[str, Any]:
        """
        仅识别图片内容，不进行角色扮演

        Args:
            image_path: 图片文件路径
            user_question: 用户的问题（可选）

        Returns:
            包含图片描述的字典:
            {
                "description": 图片描述文本,
                "image_path": 图片路径
            }
        """
        # 构建纯图片识别的系统提示词
        description_prompt = """
你是一个专业的图片内容识别助手。请客观、准确地描述图片中的内容。

【任务要求】
1. 识别图片中的主要物体、人物、场景和文字
2. 描述图片的颜色、布局和风格
3. 如果有用户问题，根据图片内容回答问题
4. 保持客观中立，不进行角色扮演
5. 使用简洁明了的语言描述

【输出格式】
直接输出图片描述，不要添加任何额外说明。
"""

        # 调用模型进行图片识别
        try:
            response = self.client.chat_with_image(
                text=user_question if user_question else "请描述这张图片的内容",
                image_path=image_path,
                system_prompt=description_prompt,
                temperature=0.3,  # 使用较低的温度以获得更准确的描述
                max_tokens=500
            )

            return {
                "description": response,
                "image_path": image_path
            }
        except Exception as e:
            print(f"⚠️ 图片识别失败: {str(e)}")
            return {
                "description": "",
                "image_path": image_path
            }

    def _build_enhanced_system_prompt(self, original_prompt: Optional[str] = None) -> str:
        """
        构建增强的系统提示词，让模型自行判断是否需要参考截屏

        Args:
            original_prompt: 原始系统提示词，如果为None则使用传入的system_prompt

        Returns:
            增强后的系统提示词
        """
        # 使用传入的system_prompt或original_prompt
        if self.system_prompt:
            enhanced_prompt = self.system_prompt
        elif original_prompt:
            enhanced_prompt = original_prompt
        else:
            # 如果都没有，使用配置文件中的角色信息
            enhanced_prompt = f"你是{self.character_name}，{self.character_role}。"

        # 将多模态指令添加到角色信息之后
        # 找到角色描述结束的位置（通常是第一个句号）
        role_end_pos = enhanced_prompt.find('。')

        if role_end_pos != -1:
            # 在角色描述后插入多模态指令
            enhanced_prompt = enhanced_prompt[:role_end_pos+1] + "\n" + self.multimodal_instruction + enhanced_prompt[role_end_pos+1:]
        else:
            # 如果找不到结束位置，直接追加
            enhanced_prompt = enhanced_prompt + "\n" + self.multimodal_instruction

        return enhanced_prompt
