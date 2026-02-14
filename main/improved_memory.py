
# -*- coding: utf-8 -*-
"""
改进的记忆系统
借鉴bopang2的向量数据库架构，使用FAISS + SQLite
"""

import os
import sqlite3

# 减少不必要的警告信息
os.environ["TRANSFORMERS_VERBOSITY"] = "error"

# 设置HuggingFace镜像源
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
import asyncio
from concurrent.futures import ThreadPoolExecutor

class ImprovedMemorySystem:
    """改进的记忆系统（借鉴bopang2的FAISS + SQLite架构）"""

    def __init__(self, base_path: str = "data/memory"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        # 初始化嵌入模型（使用支持 safetensors 的模型）
        # 设置本地缓存路径，避免每次启动都从HuggingFace下载
        cache_folder = self.base_path / "model_cache"
        cache_folder.mkdir(parents=True, exist_ok=True)

        self.embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-small-zh-v1.5",
            cache_folder=str(cache_folder),
            model_kwargs={"trust_remote_code": True},
            encode_kwargs={"normalize_embeddings": True}
        )

        # 初始化向量数据库
        self.vector_db_path = self.base_path / "vector_db"
        self.vectorstore = self._init_vectorstore()

        # 初始化SQLite数据库
        self.chat_db_path = self.base_path / "chat_history.db"
        self._init_chat_db()

        # 线程池用于异步操作
        self.executor = ThreadPoolExecutor(max_workers=4)

    def _init_vectorstore(self) -> FAISS:
        """初始化向量数据库"""
        if self.vector_db_path.exists() and any(self.vector_db_path.iterdir()):
            return FAISS.load_local(
                str(self.vector_db_path),
                self.embeddings,
                allow_dangerous_deserialization=True
            )
        return FAISS.from_texts([""], self.embeddings, metadatas=[{"__placeholder__": True}])

    def _init_chat_db(self):
        """初始化对话历史数据库"""
        with sqlite3.connect(self.chat_db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    user_id TEXT,
                    session_id TEXT,
                    user_input TEXT,
                    ai_response TEXT,
                    context_summary TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_session ON conversations (session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_user ON conversations (user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON conversations (timestamp)")

    async def save_conversation_async(
        self,
        user_input: str,
        ai_response: str,
        user_id: str = "default",
        session_id: str = "default",
        context_summary: str = ""
    ):
        """异步保存对话"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self.executor,
            self.save_conversation,
            user_input,
            ai_response,
            user_id,
            session_id,
            context_summary
        )

    def save_conversation(
        self,
        user_input: str,
        ai_response: str,
        user_id: str = "default",
        session_id: str = "default",
        context_summary: str = ""
    ):
        """保存对话到数据库"""
        with sqlite3.connect(self.chat_db_path) as conn:
            conn.execute(
                """INSERT INTO conversations 
                   (user_id, session_id, user_input, ai_response, context_summary)
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, session_id, user_input, ai_response, context_summary)
            )

    async def get_recent_history_async(
        self,
        session_id: str = "default",
        limit: int = 10
    ) -> List[Dict]:
        """异步获取最近的对话历史"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.get_recent_history,
            session_id,
            limit
        )

    def get_recent_history(
        self,
        session_id: str = "default",
        limit: int = 10
    ) -> List[Dict]:
        """获取最近的对话历史"""
        with sqlite3.connect(self.chat_db_path) as conn:
            cursor = conn.execute(
                """SELECT user_input, ai_response, timestamp
                   FROM conversations
                   WHERE session_id = ?
                   ORDER BY timestamp DESC LIMIT ?""",
                (session_id, limit)
            )
            return [
                {
                    "user": row[0],
                    "assistant": row[1],
                    "timestamp": row[2]
                }
                for row in cursor.fetchall()
            ]

    async def add_knowledge_async(
        self,
        text: str,
        metadata: Optional[Dict] = None
    ):
        """异步添加知识"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self.executor,
            self.add_knowledge,
            text,
            metadata
        )

    def add_knowledge(
        self,
        text: str,
        metadata: Optional[Dict] = None
    ):
        """添加知识到向量数据库"""
        doc = Document(page_content=text, metadata=metadata or {})
        self.vectorstore.add_documents([doc])
        self.vectorstore.save_local(str(self.vector_db_path))

    async def search_knowledge_async(
        self,
        query: str,
        k: int = 5
    ) -> List[str]:
        """异步搜索相关知识"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.search_knowledge,
            query,
            k
        )

    def search_knowledge(
        self,
        query: str,
        k: int = 5
    ) -> List[str]:
        """搜索相关知识"""
        docs = self.vectorstore.similarity_search(query, k=k)
        return [
            doc.page_content
            for doc in docs
            if not doc.metadata.get("__placeholder__")
        ]

    async def get_context_async(
        self,
        session_id: str = "default",
        query: str = "",
        history_limit: int = 10,
        knowledge_k: int = 5
    ) -> Dict:
        """异步获取综合上下文"""
        history, knowledge = await asyncio.gather(
            self.get_recent_history_async(session_id, history_limit),
            self.search_knowledge_async(query, knowledge_k)
        )

        return {
            "history": history,
            "knowledge": knowledge,
            "timestamp": datetime.now().isoformat()
        }

    def get_context(
        self,
        session_id: str = "default",
        query: str = "",
        history_limit: int = 10,
        knowledge_k: int = 5
    ) -> Dict:
        """获取综合上下文"""
        return {
            "history": self.get_recent_history(session_id, history_limit),
            "knowledge": self.search_knowledge(query, knowledge_k),
            "timestamp": datetime.now().isoformat()
        }

    async def delete_knowledge_async(self, content: str) -> bool:
        """异步删除知识"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.delete_knowledge,
            content
        )

    def delete_knowledge(self, content: str) -> bool:
        """根据内容删除知识"""
        all_docs = self.vectorstore.similarity_search(content, k=100)
        to_delete = [doc for doc in all_docs if content in doc.page_content]

        if not to_delete:
            return False

        remaining_docs = [doc for doc in all_docs if doc not in to_delete]

        if not remaining_docs:
            self.vectorstore = FAISS.from_texts([""], self.embeddings, metadatas=[{"__placeholder__": True}])
        else:
            self.vectorstore = FAISS.from_documents(remaining_docs, self.embeddings)

        self.vectorstore.save_local(str(self.vector_db_path))
        return True

    def get_memory_stats(self) -> Dict:
        """获取记忆系统统计信息"""
        # 获取对话历史统计
        with sqlite3.connect(self.chat_db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM conversations")
            total_conversations = cursor.fetchone()[0]

            cursor = conn.execute("SELECT COUNT(DISTINCT session_id) FROM conversations")
            total_sessions = cursor.fetchone()[0]

            cursor = conn.execute("SELECT COUNT(DISTINCT user_id) FROM conversations")
            total_users = cursor.fetchone()[0]

        # 获取向量数据库统计
        # 由于FAISS不直接提供文档计数，我们使用一个近似方法
        # 通过搜索一个通用查询来获取文档数量
        try:
            # 搜索所有文档（包括占位符）
            all_docs = self.vectorstore.similarity_search("", k=1000)
            # 过滤掉占位符文档
            real_docs = [doc for doc in all_docs if not doc.metadata.get("__placeholder__")]
            total_knowledge = len(real_docs)
        except Exception:
            total_knowledge = 0

        return {
            "total_conversations": total_conversations,
            "total_sessions": total_sessions,
            "total_users": total_users,
            "total_knowledge": total_knowledge,
            "vector_db_path": str(self.vector_db_path),
            "chat_db_path": str(self.chat_db_path)
        }
