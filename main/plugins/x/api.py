# -*- coding: utf-8 -*-
"""
SenseVoice API服务
提供RESTful API接口供外部调用
"""

import os
import logging
import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional

from sensevoice_asr import SenseVoiceASR
from config import API_HOST, API_PORT, API_DEBUG, LOG_LEVEL

# 配置日志
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="SenseVoice ASR API",
    description="SenseVoice语音识别API服务",
    version="1.0.0"
)

# 初始化ASR实例
asr = None

@app.on_event("startup")
async def startup_event():
    """启动时初始化ASR模型"""
    global asr
    try:
        asr = SenseVoiceASR()
        if asr.is_available():
            logger.info("SenseVoice ASR模型初始化成功")
        else:
            logger.warning("SenseVoice ASR模型初始化失败")
    except Exception as e:
        logger.error(f"SenseVoice ASR模型初始化异常: {str(e)}")


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "SenseVoice ASR API服务",
        "status": "running" if asr and asr.is_available() else "error",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "ok" if asr and asr.is_available() else "error",
        "model_initialized": asr.is_available() if asr else False
    }


@app.post("/transcribe")
async def transcribe(
    audio_file: UploadFile = File(...),
    language: Optional[str] = Form(None),
    use_itn: Optional[bool] = Form(None)
):
    """
    语音识别接口

    Args:
        audio_file: 上传的音频文件
        language: 语言设置（可选）
        use_itn: 是否使用ITN（可选）

    Returns:
        JSON响应，包含识别结果
    """
    if not asr or not asr.is_available():
        raise HTTPException(status_code=503, detail="ASR模型未初始化")

    try:
        # 保存上传的音频文件
        temp_dir = os.path.join(os.path.dirname(__file__), "cache")
        os.makedirs(temp_dir, exist_ok=True)

        temp_file = os.path.join(temp_dir, f"upload_{os.getpid()}.wav")
        with open(temp_file, "wb") as f:
            f.write(await audio_file.read())

        # 进行语音识别
        text = asr.transcribe(temp_file, language, use_itn)

        # 删除临时文件
        if os.path.exists(temp_file):
            os.remove(temp_file)

        if text:
            return {
                "success": True,
                "text": text,
                "language": language or "auto"
            }
        else:
            return {
                "success": False,
                "error": "语音识别失败"
            }

    except Exception as e:
        logger.error(f"语音识别异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"语音识别异常: {str(e)}")


@app.post("/record")
async def record(
    duration: Optional[int] = Form(None),
    language: Optional[str] = Form(None),
    use_itn: Optional[bool] = Form(None),
    keep_audio: Optional[bool] = Form(False)
):
    """
    录音并识别接口

    Args:
        duration: 录音时长（秒），如果为None则需要手动停止
        language: 语言设置（可选）
        use_itn: 是否使用ITN（可选）
        keep_audio: 是否保留录音文件（可选）

    Returns:
        JSON响应，包含识别结果和音频文件路径
    """
    if not asr or not asr.is_available():
        raise HTTPException(status_code=503, detail="ASR模型未初始化")

    try:
        # 录音并识别
        text, audio_file = asr.record_and_transcribe(
            duration=duration,
            language=language,
            use_itn=use_itn,
            keep_audio=keep_audio
        )

        if text:
            return {
                "success": True,
                "text": text,
                "audio_file": audio_file if keep_audio else None,
                "language": language or "auto"
            }
        else:
            return {
                "success": False,
                "error": "录音识别失败"
            }

    except Exception as e:
        logger.error(f"录音识别异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"录音识别异常: {str(e)}")


def start_api():
    """启动API服务"""
    uvicorn.run(
        "api:app",
        host=API_HOST,
        port=API_PORT,
        reload=API_DEBUG,
        log_level=LOG_LEVEL.lower()
    )


if __name__ == "__main__":
    start_api()
