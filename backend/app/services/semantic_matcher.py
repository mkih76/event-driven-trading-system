"""
语义相似事件匹配服务
使用 ChromaDB 存储事件向量，实现相似历史事件检索
"""
import os
import hashlib
from typing import Optional, List, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# ChromaDB 配置
CHROMA_PERSIST_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "chroma_db")
COLLECTION_NAME = "events"

# 向量化模型配置
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # 轻量级 embedding 模型


class SemanticMatcher:
    """语义相似事件匹配器"""

    def __init__(self):
        self._client = None
        self._collection = None
        self._embedding_model = None
        self._initialized = False

    async def initialize(self):
        """初始化 ChromaDB 和 embedding 模型"""
        if self._initialized:
            return

        try:
            import chromadb
            from chromadb.config import Settings

            # 确保目录存在
            os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)

            # 初始化 ChromaDB 客户端
            self._client = chromadb.PersistentClient(
                path=CHROMA_PERSIST_DIR,
                settings=Settings(anonymized_telemetry=False)
            )

            # 获取或创建 collection
            self._collection = self._client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"description": "事件语义向量存储"}
            )

            # 初始化 embedding 模型
            await self._init_embedding_model()

            self._initialized = True
            logger.info(f"SemanticMatcher 初始化完成，collection: {COLLECTION_NAME}")

        except ImportError as e:
            logger.warning(f"ChromaDB 未安装: {e}，使用关键词降级匹配")
            self._initialized = False

    async def _init_embedding_model(self):
        """初始化 embedding 模型"""
        try:
            from sentence_transformers import SentenceTransformer
            self._embedding_model = SentenceTransformer(EMBEDDING_MODEL)
            logger.info(f"Embedding 模型加载成功: {EMBEDDING_MODEL}")
        except ImportError:
            logger.warning("sentence-transformers 未安装，embedding 功能受限")
            self._embedding_model = None

    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """获取文本的向量表示"""
        if self._embedding_model is None:
            return None

        try:
            embedding = self._embedding_model.encode(text)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Embedding 失败: {e}")
            return None

    async def add_event(
        self,
        event_id: str,
        title: str,
        content: str,
        event_type: str,
        sentiment: float,
        direct_impacts: List[dict],
        analysis_result: dict
    ) -> bool:
        """
        添加事件到向量数据库

        Args:
            event_id: 事件唯一ID
            title: 事件标题
            content: 事件内容
            event_type: 事件类型
            sentiment: 情绪值
            direct_impacts: 直接影响行业列表
            analysis_result: 完整分析结果

        Returns:
            是否添加成功
        """
        if not self._initialized:
            await self.initialize()

        if self._collection is None:
            return False

        try:
            # 组合文本用于 embedding
            combined_text = f"{title} {content} {event_type}"
            embedding = self._get_embedding(combined_text)

            if embedding is None:
                # 使用标题的简单哈希作为降级
                embedding = self._fallback_embedding(title)

            # 添加到 ChromaDB
            self._collection.add(
                ids=[event_id],
                embeddings=[embedding],
                documents=[combined_text],
                metadatas=[{
                    "title": title,
                    "event_type": event_type,
                    "sentiment": sentiment,
                    "timestamp": datetime.now().isoformat(),
                    "direct_impacts": str(direct_impacts)
                }]
            )

            logger.info(f"事件 {event_id} 已添加到向量库")
            return True

        except Exception as e:
            logger.error(f"添加事件失败: {e}")
            return False

    def _fallback_embedding(self, text: str) -> List[float]:
        """降级embedding：基于关键词的简单哈希"""
        # 简单的词袋模型降级
        keywords = [
            "地缘政治", "战争", "制裁", "原油", "黄金", "央行", "加息",
            "政策", "监管", "灾难", "疫情", "经济数据", "财报", "技术突破"
        ]
        vector = [0.0] * len(keywords)
        for i, kw in enumerate(keywords):
            if kw in text:
                vector[i] = 1.0
        return vector

    async def find_similar_events(
        self,
        title: str,
        content: str = "",
        top_k: int = 3,
        similarity_threshold: float = 0.5
    ) -> List[dict]:
        """
        查找相似历史事件

        Args:
            title: 事件标题
            content: 事件内容（可选）
            top_k: 返回数量
            similarity_threshold: 相似度阈值

        Returns:
            相似事件列表
        """
        if not self._initialized:
            await self.initialize()

        if self._collection is None:
            return self._keyword_fallback_search(title, top_k)

        try:
            # 获取查询向量
            combined_text = f"{title} {content}"
            query_embedding = self._get_embedding(combined_text)

            if query_embedding is None:
                return self._keyword_fallback_search(title, top_k)

            # 执行向量检索
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where={"event_type": {"$ne": ""}}  # 基本过滤
            )

            # 解析结果
            similar_events = []
            if results and results.get("ids"):
                for i, event_id in enumerate(results["ids"][0]):
                    distance = results.get("distances", [[0]])[0][i]
                    # ChromaDB 的 distance 越小越相似，转换为 similarity
                    similarity = 1.0 / (1.0 + distance)

                    if similarity >= similarity_threshold:
                        metadata = results.get("metadatas", [[{}]])[0][i]
                        document = results.get("documents", [[""]])[0][i]

                        similar_events.append({
                            "event_id": event_id,
                            "title": metadata.get("title", ""),
                            "event_type": metadata.get("event_type", ""),
                            "sentiment": metadata.get("sentiment", 0.0),
                            "similarity": similarity,
                            "direct_impacts": metadata.get("direct_impacts", ""),
                            "document": document
                        })

            logger.info(f"找到 {len(similar_events)} 个相似事件")
            return similar_events

        except Exception as e:
            logger.error(f"相似事件检索失败: {e}")
            return self._keyword_fallback_search(title, top_k)

    def _keyword_fallback_search(self, title: str, top_k: int) -> List[dict]:
        """基于关键词的降级搜索"""
        # 简单关键词匹配降级
        keywords_map = {
            "伊朗": ["原油", "霍尔木兹", "地缘政治"],
            "美国": ["美股", "美元", "制裁"],
            "央行": ["利率", "货币政策", "加息"],
            "OPEC": ["原油", "减产", "能源"],
            "制裁": ["科技", "出口管制", "半导体"],
            "疫情": ["旅游", "航空", "消费"],
            "战争": ["原油", "黄金", "国防"],
        }

        matched_keywords = []
        for kw, related in keywords_map.items():
            if kw in title:
                matched_keywords.extend(related)

        # 返回基于关键词的简单匹配结果
        return [{
            "event_id": "keyword_fallback",
            "title": "基于关键词匹配",
            "event_type": "降级模式",
            "sentiment": 0.0,
            "similarity": 0.5,
            "matched_keywords": list(set(matched_keywords))[:5],
            "message": "当前使用关键词降级匹配"
        }]

    async def delete_event(self, event_id: str) -> bool:
        """删除事件"""
        if self._collection is None:
            return False

        try:
            self._collection.delete(ids=[event_id])
            logger.info(f"事件 {event_id} 已删除")
            return True
        except Exception as e:
            logger.error(f"删除事件失败: {e}")
            return False

    async def get_collection_stats(self) -> dict:
        """获取 collection 统计信息"""
        if self._collection is None:
            return {"count": 0, "initialized": False}

        try:
            return {
                "count": self._collection.count(),
                "initialized": self._initialized,
                "embedding_model": EMBEDDING_MODEL if self._embedding_model else None
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {"count": 0, "initialized": self._initialized}


# 全局实例
_semantic_matcher: Optional[SemanticMatcher] = None


def get_semantic_matcher() -> SemanticMatcher:
    """获取语义匹配器实例"""
    global _semantic_matcher
    if _semantic_matcher is None:
        _semantic_matcher = SemanticMatcher()
    return _semantic_matcher