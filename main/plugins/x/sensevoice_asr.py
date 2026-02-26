# -*- coding: utf-8 -*-
"""
SenseVoice ASR核心模块
"""

import os
import sys
import time
import logging
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write

# 直接加载插件配置，避免导入冲突
PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))

# 模型配置
MODEL_PATH = os.path.join(PLUGIN_DIR, "pretrained_models", "iic", "SenseVoiceSmall")
MODEL_NAME = "SenseVoiceSmall"

# 音频配置
SAMPLE_RATE = 16000  # 音频采样率
CHANNELS = 1  # 音频通道数

# ASR配置
LANGUAGE = "auto"  # 语言设置: auto, zh, en, yue, ja, ko, nospeech
USE_ITN = False  # 是否使用ITN（数字文本化）

# 日志配置
LOG_LEVEL = "INFO"
LOG_FILE = os.path.join(PLUGIN_DIR, "sensevoice.log")

# 缓存配置
CACHE_DIR = os.path.join(PLUGIN_DIR, "cache")
ENABLE_CACHE = True

# 配置日志
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SenseVoiceASR:
    """SenseVoice语音识别类"""

    def __init__(self, model_path=None, sample_rate=None, language=None, use_itn=None):
        """
        初始化SenseVoice ASR

        Args:
            model_path: 模型路径，默认使用配置文件中的路径
            sample_rate: 音频采样率，默认使用配置文件中的采样率
            language: 语言设置，默认使用配置文件中的语言设置
            use_itn: 是否使用ITN，默认使用配置文件中的设置
        """
        self.model_path = model_path or MODEL_PATH
        self.sample_rate = sample_rate or SAMPLE_RATE
        self.language = language or LANGUAGE
        self.use_itn = use_itn if use_itn is not None else USE_ITN

        self.model = None
        self.is_initialized = False

        # 初始化缓存目录
        if ENABLE_CACHE and not os.path.exists(CACHE_DIR):
            os.makedirs(CACHE_DIR, exist_ok=True)

        # 设置SenseVoice模块路径
        self._setup_sensevoice_path()

        # 初始化模型
        self._initialize_model()

    def _setup_sensevoice_path(self):
        """设置SenseVoice模块路径"""
        try:
            # 获取插件目录
            plugin_dir = os.path.dirname(os.path.abspath(__file__))

            # 查找SenseVoice模块所在目录
            sensevoice_path = os.path.join(plugin_dir, "pretrained_models", "iic", "SenseVoiceSmall")

            # 检查目录是否存在
            if not os.path.isdir(sensevoice_path):
                logger.warning(f"SenseVoice模型目录不存在: {sensevoice_path}")
                return

            # 将模型根目录加入Python路径
            if sensevoice_path not in sys.path:
                sys.path.insert(0, sensevoice_path)
                logger.info(f"已将SenseVoice模型目录加入Python路径: {sensevoice_path}")

            # 创建一个临时的model.py文件，用于解决模块导入问题
            # 根据错误信息，funasr尝试从model模块加载远程代码
            # 我们创建一个空的model模块，避免导入错误
            temp_model_file = os.path.join(sensevoice_path, "model.py")
            logger.info(f"创建临时model.py文件: {temp_model_file}")
            with open(temp_model_file, "w", encoding="utf-8") as f:
                f.write("# -*- coding: utf-8 -*-\n")
                f.write("# 临时model.py文件，用于解决模块导入问题\n")
                f.write("# 根据错误信息，funasr尝试从model模块加载远程代码\n")
                f.write("# 我们创建一个空的model模块，避免导入错误\n")
                f.write("import sys\n")
                f.write("import os\n")
                f.write("\n")
                f.write("# 定义一个空的SenseVoiceSmall类，避免导入错误\n")
                f.write("class SenseVoiceSmall:\n")
                f.write("    pass\n")
                f.write("\n")
                f.write("# 导出所有公共类和函数\n")
                f.write("__all__ = ['SenseVoiceSmall']\n")
        except Exception as e:
            logger.warning(f"设置SenseVoice模块路径失败: {str(e)}")

    def _initialize_model(self):
        """初始化SenseVoice模型"""
        try:
            logger.info(f"正在加载SenseVoice模型: {self.model_path}")

            # 设置环境变量，禁用在线更新和远程代码加载
            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["TRANSFORMERS_OFFLINE"] = "1"

            # 检查本地模型是否存在
            model_file = os.path.join(self.model_path, "model.pt")
            config_file = os.path.join(self.model_path, "config.yaml")

            logger.info(f"检查模型文件: {model_file}, 存在: {os.path.exists(model_file)}")
            logger.info(f"检查配置文件: {config_file}, 存在: {os.path.exists(config_file)}")

            if os.path.exists(model_file) and os.path.exists(config_file):
                logger.info(f"使用本地模型: {self.model_path}")

                # 使用funasr加载模型
                from funasr import AutoModel

                logger.info("开始加载模型...")
                # 使用本地模型路径，不使用trust_remote_code
                self.model = AutoModel(
                    model=self.model_path,
                    disable_log=True,
                    disable_update=True,
                    device="cpu",
                    disable_pbar=True,
                    trust_remote_code=False,
                )
                logger.info("模型加载完成")
            else:
                logger.error(f"本地模型不存在: {model_file} 或 {config_file}")
                self.model = None
                self.is_initialized = False
                return

            self.is_initialized = True
            logger.info("SenseVoice模型加载成功")
        except Exception as e:
            logger.error(f"SenseVoice模型加载失败: {str(e)}")
            import traceback
            traceback.print_exc()
            self.model = None
            self.is_initialized = False


    def is_available(self):
        """检查ASR是否可用"""
        return self.is_initialized and self.model is not None


    def record_audio(self, filename=None, duration=None):
        """
        录制音频

        Args:
            filename: 保存的音频文件名，如果为None则生成临时文件名
            duration: 录音时长（秒），如果为None则使用默认时长

        Returns:
            str: 音频文件路径，失败返回None
        """
        if filename is None:
            # 生成临时文件名
            timestamp = int(time.time())
            filename = os.path.join(CACHE_DIR, f"recording_{timestamp}.wav")

        # 如果没有指定时长，使用默认时长
        if duration is None:
            duration = 5  # 默认录音5秒

        try:
            logger.info(f"开始录音，时长: {duration}秒...")
            recording = []

            def callback(indata, frames, time_info, status):
                if status:
                    logger.warning(f"录音状态: {status}")
                recording.append(indata.copy())

            # 指定时长录音
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=CHANNELS,
                callback=callback
            ):
                time.sleep(duration)

            # 保存录音
            if recording:
                audio_data = np.concatenate(recording, axis=0)
                write(filename, self.sample_rate, (audio_data * 32767).astype(np.int16))
                logger.info(f"录音已保存为 {filename}")
                return filename
            return None

        except Exception as e:
            logger.error(f"录音失败: {str(e)}")
            return None

    def transcribe(self, audio_file, language=None, use_itn=None):
        """
        将音频转换为文本

        Args:
            audio_file: 音频文件路径
            language: 语言设置，如果为None则使用初始化时的设置
            use_itn: 是否使用ITN，如果为None则使用初始化时的设置

        Returns:
            str: 识别的文本，失败返回None
        """
        if not self.is_available():
            logger.error("ASR模型未初始化")
            return None

        # 使用传入的参数或初始化时的参数
        lang = language if language is not None else self.language
        itn = use_itn if use_itn is not None else self.use_itn

        try:
            logger.info(f"开始识别音频: {audio_file}")

            # 调用模型进行识别
            res = self.model.generate(
                input=audio_file,
                cache={},
                language=lang,
                use_itn=itn,
            )

            if res and len(res) > 0:
                # 提取识别结果
                text = res[0].get('text', '')
                logger.info(f"识别结果: {text}")
                return text
            else:
                logger.warning("未获取到识别结果")
                return None

        except Exception as e:
            logger.error(f"语音识别失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def record_and_transcribe(self, duration=None, language=None, use_itn=None, keep_audio=False):
        """
        录音并识别（一步完成）

        Args:
            duration: 录音时长（秒），如果为None则需要手动停止
            language: 语言设置
            use_itn: 是否使用ITN
            keep_audio: 是否保留录音文件

        Returns:
            tuple: (识别文本, 音频文件路径)，失败返回(None, None)
        """
        # 生成临时文件名
        timestamp = int(time.time())
        temp_file = os.path.join(CACHE_DIR, f"temp_recording_{timestamp}.wav")

        try:
            # 录音
            audio_file = self.record_audio(temp_file, duration)
            if not audio_file:
                return None, None

            # 识别
            text = self.transcribe(audio_file, language, use_itn)

            # 清理临时文件（如果不需要保留）
            if not keep_audio and os.path.exists(audio_file):
                os.remove(audio_file)
                logger.info(f"已删除临时文件: {audio_file}")

            return text, audio_file

        except Exception as e:
            logger.error(f"录音识别失败: {str(e)}")
            # 清理临时文件
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
            return None, None


class ModelWrapper:
    """模型包装器，用于直接加载本地模型"""

    def __init__(self, model_dict, config):
        """初始化模型包装器"""
        self.model_dict = model_dict
        self.config = config

    def generate(self, input, cache, language=None, use_itn=None):
        """生成识别结果"""
        # 这里只是一个占位符，实际实现需要根据模型结构来编写
        # 由于直接加载模型比较复杂，这里返回一个空结果
        return [{"text": ""}]
