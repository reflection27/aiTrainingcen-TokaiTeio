
# -*- coding: utf-8 -*-
"""
改进的记忆系统
借鉴bopang2的向量数据库架构，使用FAISS + SQLite
"""

import os
import sqlite3
import time
from functools import wraps

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

class PerformanceTracker:
    """性能跟踪器，用于分析各环节的耗时"""

    def __init__(self):
        self.metrics = {}

    def record(self, operation: str, duration: float):
        """记录操作耗时"""
        if operation not in self.metrics:
            self.metrics[operation] = []
        self.metrics[operation].append(duration)

    def get_stats(self, operation: str = None) -> Dict:
        """获取性能统计信息"""
        if operation:
            if operation not in self.metrics:
                return {}
            durations = self.metrics[operation]
            return {
                "count": len(durations),
                "total": sum(durations),
                "avg": sum(durations) / len(durations),
                "min": min(durations),
                "max": max(durations)
            }
        else:
            # 返回所有操作的统计信息
            return {
                op: self.get_stats(op)
                for op in self.metrics
            }

    def print_stats(self):
        """打印性能统计信息"""
        print("\n📊 性能统计信息:")
        for op, stats in self.get_stats().items():
            print(f"  {op}:")
            print(f"    调用次数: {stats['count']}")
            print(f"    总耗时: {stats['total']:.3f}秒")
            print(f"    平均耗时: {stats['avg']:.3f}秒")
            print(f"    最小耗时: {stats['min']:.3f}秒")
            print(f"    最大耗时: {stats['max']:.3f}秒")

# 全局性能跟踪器
perf_tracker = PerformanceTracker()

def measure_performance(operation_name: str = None):
    """性能测量装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation_name or func.__name__
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                perf_tracker.record(op_name, duration)
                print(f"⏱️ {op_name} 耗时: {duration:.3f}秒")
                return result
            except Exception as e:
                duration = time.time() - start_time
                perf_tracker.record(f"{op_name}_error", duration)
                print(f"⏱️ {op_name} 失败，耗时: {duration:.3f}秒，错误: {str(e)}")
                raise
        return wrapper
    return decorator

class ImprovedMemorySystem:
    """改进的记忆系统（借鉴bopang2的FAISS + SQLite架构）"""

    # 类变量：全局嵌入模型实例
    _embeddings = None
    _initialization_lock = None
    _base_path = None

    @classmethod
    def get_initialization_lock(cls):
        """获取初始化锁（延迟创建以避免导入时创建事件循环）"""
        if cls._initialization_lock is None:
            cls._initialization_lock = asyncio.Lock()
        return cls._initialization_lock

    @classmethod
    async def initialize_embeddings(cls, base_path: str = "data/memory"):
        """异步初始化全局嵌入模型（只执行一次）

        参数:
            base_path: 基础路径，用于存储模型缓存

        返回:
            None
        """
        async with cls.get_initialization_lock():
            # 双重检查，避免重复初始化
            if cls._embeddings is not None:
                return

            print("🔄 开始异步加载嵌入模型...")

            try:
                base_path = Path(base_path)
                cache_folder = base_path / "model_cache"
                cache_folder.mkdir(parents=True, exist_ok=True)

                # 保存基础路径供后续使用
                cls._base_path = base_path

                # 在线程池中加载模型（避免阻塞事件循环）
                loop = asyncio.get_running_loop()

                def load_model():
                    """在线程池中加载嵌入模型"""
                    # 检测本地缓存是否存在，存在则跳过网络请求
                    model_cache = cache_folder / "models--BAAI--bge-small-zh-v1.5"
                    local_only = model_cache.exists()
                    return HuggingFaceEmbeddings(
                        model_name="BAAI/bge-small-zh-v1.5",
                        cache_folder=str(cache_folder),
                        model_kwargs={"trust_remote_code": True, "local_files_only": local_only},
                        encode_kwargs={"normalize_embeddings": True}
                    )

                cls._embeddings = await loop.run_in_executor(
                    None,
                    load_model
                )

                print("✅ 嵌入模型加载完成")

                # 预热模型：执行多次嵌入操作以充分预热
                print("🔥 正在预热嵌入模型...")
                test_texts = [
                    "测试文本",
                    "这是一段测试用的中文文本",
                    "Vector database optimization",
                    "模型预热测试"
                ]

                # 批量预热，确保模型完全加载到内存
                for text in test_texts:
                    await loop.run_in_executor(
                        None,
                        lambda t=text: cls._embeddings.embed_query(t)
                    )

                # 预热embed_documents方法（用于向量数据库查询）
                await loop.run_in_executor(
                    None,
                    lambda: cls._embeddings.embed_documents(test_texts)
                )

                print("✅ 嵌入模型预热完成")

            except Exception as e:
                print(f"❌ 嵌入模型初始化失败: {str(e)}")
                cls._embeddings = None
                raise

    @classmethod
    def get_embeddings(cls):
        """获取全局嵌入模型实例

        返回:
            HuggingFaceEmbeddings: 嵌入模型实例

        异常:
            RuntimeError: 如果模型未初始化
        """
        if cls._embeddings is None:
            raise RuntimeError(
                "嵌入模型未初始化，请先调用ImprovedMemorySystem.initialize_embeddings()"
            )
        return cls._embeddings

    def __init__(self, base_path: str = "data/memory"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        # 使用全局嵌入模型（如果已初始化）
        if ImprovedMemorySystem._embeddings is not None:
            self.embeddings = ImprovedMemorySystem._embeddings
        else:
            # 如果未初始化，回退到原来的方式（兼容性）
            print("⚠️ 嵌入模型未预加载，使用即时加载模式")
            cache_folder = self.base_path / "model_cache"
            cache_folder.mkdir(parents=True, exist_ok=True)

            model_cache = cache_folder / "models--BAAI--bge-small-zh-v1.5"
            local_only = model_cache.exists()
            self.embeddings = HuggingFaceEmbeddings(
                model_name="BAAI/bge-small-zh-v1.5",
                cache_folder=str(cache_folder),
                model_kwargs={"trust_remote_code": True, "local_files_only": local_only},
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

        # 预热向量数据库查询
        self._warmup_vectorstore()

    @measure_performance("_init_vectorstore")
    def _init_vectorstore(self) -> FAISS:
        """初始化向量数据库"""
        if self.vector_db_path.exists() and any(self.vector_db_path.iterdir()):
            return FAISS.load_local(
                str(self.vector_db_path),
                self.embeddings,
                allow_dangerous_deserialization=True
            )
        return FAISS.from_texts([""], self.embeddings, metadatas=[{"__placeholder__": True}])

    @measure_performance("_warmup_vectorstore")
    def _warmup_vectorstore(self):
        """预热向量数据库，确保首次查询不会延迟"""
        try:
            print("🔥 正在预热向量数据库...")
            # 执行一次相似性搜索，预热FAISS索引
            test_query = "测试查询"
            docs = self.vectorstore.similarity_search(test_query, k=1)
            print(f"✅ 向量数据库预热完成，查询返回 {len(docs)} 个结果")
        except Exception as e:
            print(f"⚠️ 向量数据库预热失败: {str(e)}")
            # 预热失败不影响正常使用，仅记录日志

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
        """异步保存对话（带异常处理和安全检查）"""
        try:
            # 安全获取事件循环
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # 如果没有运行中的事件循环，创建一个新的
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # 检查事件循环是否已关闭
            if loop.is_closed():
                print("⚠️ 事件循环已关闭，跳过保存对话")
                return

            # 在线程池中执行保存操作
            await loop.run_in_executor(
                self.executor,
                self.save_conversation,
                user_input,
                ai_response,
                user_id,
                session_id,
                context_summary
            )
        except RuntimeError as e:
            if "Event loop is closed" in str(e):
                print("⚠️ 事件循环已关闭，跳过保存对话")
            else:
                print(f"❌ 保存对话失败: {str(e)}")
        except Exception as e:
            print(f"❌ 保存对话失败: {str(e)}")
            import traceback
            traceback.print_exc()

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
        """异步获取最近的对话历史（带安全检查）"""
        try:
            # 安全获取事件循环
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # 检查事件循环是否已关闭
            if loop.is_closed():
                print("⚠️ 事件循环已关闭，返回空历史")
                return []

            return await loop.run_in_executor(
                self.executor,
                self.get_recent_history,
                session_id,
                limit
            )
        except RuntimeError as e:
            if "Event loop is closed" in str(e):
                print("⚠️ 事件循环已关闭，返回空历史")
                return []
            else:
                raise
        except Exception as e:
            print(f"❌ 获取历史失败: {str(e)}")
            return []

    @measure_performance("get_recent_history")
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
        """异步添加知识（带安全检查）"""
        try:
            # 安全获取事件循环
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # 检查事件循环是否已关闭
            if loop.is_closed():
                print("⚠️ 事件循环已关闭，跳过添加知识")
                return

            await loop.run_in_executor(
                self.executor,
                self.add_knowledge,
                text,
                metadata
            )
        except RuntimeError as e:
            if "Event loop is closed" in str(e):
                print("⚠️ 事件循环已关闭，跳过添加知识")
            else:
                raise
        except Exception as e:
            print(f"❌ 添加知识失败: {str(e)}")

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
        """异步搜索相关知识（带安全检查）"""
        try:
            # 安全获取事件循环
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # 检查事件循环是否已关闭
            if loop.is_closed():
                print("⚠️ 事件循环已关闭，返回空搜索结果")
                return []

            return await loop.run_in_executor(
                self.executor,
                self.search_knowledge,
                query,
                k
            )
        except RuntimeError as e:
            if "Event loop is closed" in str(e):
                print("⚠️ 事件循环已关闭，返回空搜索结果")
                return []
            else:
                raise
        except Exception as e:
            print(f"❌ 搜索知识失败: {str(e)}")
            return []

    @measure_performance("search_knowledge")
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
        import time
        start_time = time.time()

        history, knowledge = await asyncio.gather(
            self.get_recent_history_async(session_id, history_limit),
            self.search_knowledge_async(query, knowledge_k)
        )

        total_time = time.time() - start_time
        print(f"⏱️ 获取上下文总耗时: {total_time:.3f}秒")

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
        """异步删除知识（带安全检查）"""
        try:
            # 安全获取事件循环
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # 检查事件循环是否已关闭
            if loop.is_closed():
                print("⚠️ 事件循环已关闭，跳过删除知识")
                return False

            return await loop.run_in_executor(
                self.executor,
                self.delete_knowledge,
                content
            )
        except RuntimeError as e:
            if "Event loop is closed" in str(e):
                print("⚠️ 事件循环已关闭，跳过删除知识")
                return False
            else:
                raise
        except Exception as e:
            print(f"❌ 删除知识失败: {str(e)}")
            return False

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
