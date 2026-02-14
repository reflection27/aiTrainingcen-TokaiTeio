
# -*- coding: utf-8 -*-
"""
异步AI代理模块
借鉴bopang2的异步处理架构，提升响应速度
"""

import asyncio
import aiohttp
import os
from typing import Optional, Dict, List
from openai import AsyncOpenAI

# 设置HuggingFace镜像源
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from pathlib import Path
import sqlite3
import json
from datetime import datetime

class AsyncVectorMemory:
    """异步向量记忆系统（借鉴bopang2的FAISS架构）"""

    def __init__(self, db_path: str = "data/vector_memory"):
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)

        # 初始化嵌入模型
        # 设置本地缓存路径，避免每次启动都从HuggingFace下载
        cache_folder = self.db_path / "model_cache"
        cache_folder.mkdir(parents=True, exist_ok=True)

        self.embeddings = HuggingFaceEmbeddings(
            model_name="GanymedeNil/text2vec-base-chinese",
            cache_folder=str(cache_folder)
        )

        # 初始化向量存储
        self.vectorstore = self._init_vectorstore()

        # 初始化SQLite数据库存储对话历史
        self.chat_db_path = self.db_path / "chat_history.db"
        self._init_chat_db()

    def _init_vectorstore(self) -> FAISS:
        """初始化向量数据库"""
        if (self.db_path / "index").exists():
            return FAISS.load_local(
                str(self.db_path),
                self.embeddings,
                allow_dangerous_deserialization=True
            )
        return FAISS.from_texts([""], self.embeddings, metadatas=[{"__placeholder__": True}])

    def _init_chat_db(self):
        """初始化对话历史数据库"""
        with sqlite3.connect(self.chat_db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    user_input TEXT,
                    ai_response TEXT,
                    session_id TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_session ON chat_history (session_id)")

    async def save_conversation(self, user_input: str, ai_response: str, session_id: str = "default"):
        """保存对话到数据库"""
        with sqlite3.connect(self.chat_db_path) as conn:
            conn.execute(
                "INSERT INTO chat_history (user_input, ai_response, session_id) VALUES (?, ?, ?)",
                (user_input, ai_response, session_id)
            )

    async def get_recent_history(self, session_id: str = "default", limit: int = 5) -> List[Dict]:
        """获取最近的对话历史"""
        with sqlite3.connect(self.chat_db_path) as conn:
            cursor = conn.execute(
                "SELECT user_input, ai_response FROM chat_history "
                "WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?",
                (session_id, limit)
            )
            return [{"user": row[0], "assistant": row[1]} for row in cursor.fetchall()]

    async def add_knowledge(self, text: str, metadata: Dict = None):
        """添加知识到向量数据库"""
        doc = Document(page_content=text, metadata=metadata or {})
        self.vectorstore.add_documents([doc])
        self.vectorstore.save_local(str(self.db_path))

    async def search_knowledge(self, query: str, k: int = 5) -> List[str]:
        """搜索相关知识"""
        docs = self.vectorstore.similarity_search(query, k=k)
        return [doc.page_content for doc in docs if not doc.metadata.get("__placeholder__")]

class AsyncAIAgent:
    """异步AI代理（借鉴bopang2的异步处理架构）"""

    def __init__(self, config: Dict):
        self.config = config
        self.memory = AsyncVectorMemory()

        # 初始化异步OpenAI客户端
        api_key = config.get("deepseek_key", "")
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com/v1"
        )

        # 响应缓存
        self.response_cache: Dict[str, str] = {}

    async def process_command_async(self, user_input: str, session_id: str = "default") -> str:
        """异步处理用户命令"""
        # 检查缓存
        cache_key = f"{session_id}:{user_input}"
        if cache_key in self.response_cache:
            return self.response_cache[cache_key]

        # 获取对话历史和知识
        history = await self.memory.get_recent_history(session_id)
        knowledge = await self.memory.search_knowledge(user_input)

        # 构建上下文
        context = self._build_context(user_input, history, knowledge)

        # 调用AI
        response = await self._call_ai_async(context)

        # 保存对话
        await self.memory.save_conversation(user_input, response, session_id)

        # 缓存响应
        self.response_cache[cache_key] = response

        return response

    def _build_context(self, user_input: str, history: List[Dict], knowledge: List[str]) -> str:
        """构建对话上下文"""
        context_parts = []

        # 添加知识库内容
        if knowledge:
            context_parts.append("[相关知识]\n" + "\n".join(knowledge))

        # 添加历史对话
        if history:
            context_parts.append("[历史对话]")
            for h in reversed(history):
                context_parts.append(f"用户: {h['user']}")
                context_parts.append(f"助手: {h['assistant']}")

        # 添加当前输入
        context_parts.append(f"当前对话:\n用户: {user_input}\n助手:")

        return "\n".join(context_parts)

    async def _call_ai_async(self, context: str) -> str:
        """异步调用AI"""
        try:
            model = self.config.get("selected_model", "deepseek-chat")

            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是东海帝王，特雷森学园的赛马娘。"},
                    {"role": "user", "content": context}
                ],
                max_tokens=2048,
                temperature=0.7
            )

            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"处理出错: {str(e)}"

    def clear_cache(self):
        """清除响应缓存"""
        self.response_cache.clear()
