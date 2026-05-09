"""
语义相似事件匹配服务
使用 ChromaDB 存储事件向量，实现相似历史事件检索
支持历史事件批量导入
"""
import os
import json
import requests
from typing import Optional, List, Tuple
from datetime import datetime
import logging

from app.services.config import settings

logger = logging.getLogger(__name__)

# ChromaDB 配置
CHROMA_PERSIST_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "chroma_db")
COLLECTION_NAME = "events"

# 历史事件文件路径
EVENT_HISTORY_PATH = os.path.join(os.path.dirname(__file__), "impact_quant", "event_history.json")

# Jina API 配置
JINA_API_KEY = os.getenv("JINA_API_KEY")
JINA_API_URL = "https://api.jina.ai/v1/embeddings"
JINA_MODEL = "jina-embeddings-v3"


class SemanticMatcher:
    """语义相似事件匹配器（使用 Jina Embeddings API）"""

    def __init__(self):
        self._client = None
        self._collection = None
        self._initialized = False

    async def initialize(self):
        """初始化 ChromaDB 和 embedding 客户端"""
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

            # 检查 Jina API Key
            if not JINA_API_KEY:
                logger.warning("JINA_API_KEY 未设置，使用降级匹配")
            else:
                logger.info("Jina Embeddings API 准备就绪")

            # 获取或创建 collection
            try:
                self._collection = self._client.get_or_create_collection(
                    name=COLLECTION_NAME,
                    metadata={"description": "事件语义向量存储"}
                )
            except Exception as coll_err:
                logger.warning(f"获取 collection 失败: {coll_err}，尝试删除重建")
                try:
                    self._client.delete_collection(COLLECTION_NAME)
                    self._collection = self._client.get_or_create_collection(
                        name=COLLECTION_NAME,
                        metadata={"description": "事件语义向量存储"}
                    )
                except Exception as recreate_err:
                    logger.error(f"重建 collection 失败: {recreate_err}")
                    self._collection = None

            self._initialized = True
            logger.info(f"SemanticMatcher 初始化完成，collection: {COLLECTION_NAME}")

        except ImportError as e:
            logger.warning(f"ChromaDB 未安装: {e}，使用关键词降级匹配")
            self._initialized = False

    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """通过 Jina API 获取文本的向量表示"""
        if not JINA_API_KEY:
            logger.warning("JINA_API_KEY 未配置，无法获取 embedding")
            return None

        try:
            headers = {
                "Authorization": f"Bearer {JINA_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": JINA_MODEL,
                "input": text[:8192]  # 限制输入长度
            }
            response = requests.post(JINA_API_URL, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]
        except Exception as e:
            logger.error(f"Jina API 调用失败: {e}")
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
        similarity_threshold: float = None
    ) -> List[dict]:
        """
        查找相似历史事件

        Args:
            title: 事件标题
            content: 事件内容（可选）
            top_k: 返回数量
            similarity_threshold: 相似度阈值（默认使用配置值）

        Returns:
            相似事件列表
        """
        # 使用配置中的默认值
        if similarity_threshold is None:
            similarity_threshold = settings.SEMANTIC_SIMILARITY_THRESHOLD

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
                "embedding_model": JINA_MODEL if JINA_API_KEY else None,
                "jina_api_configured": bool(JINA_API_KEY)
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {"count": 0, "initialized": self._initialized}

    async def _ensure_initialized(self):
        """确保已初始化"""
        if not self._initialized:
            await self.initialize()

    async def import_historical_events(self, force_reload: bool = False) -> dict:
        """
        从 event_history.json 批量导入历史事件到向量库

        Args:
            force_reload: 是否强制重新导入（即使已存在）

        Returns:
            导入统计信息
        """
        if not self._initialized:
            await self.initialize()

        if self._collection is None:
            return {"success": False, "message": "ChromaDB 未初始化"}

        # 检查是否已有数据且不是强制重载
        existing_count = self._collection.count()
        if existing_count > 0 and not force_reload:
            return {
                "success": True,
                "message": f"向量库已有 {existing_count} 个事件，跳过导入",
                "imported": 0,
                "skipped": existing_count
            }

        if not os.path.exists(EVENT_HISTORY_PATH):
            return {"success": False, "message": f"历史事件文件不存在: {EVENT_HISTORY_PATH}"}

        try:
            with open(EVENT_HISTORY_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)

            events = data.get("events", [])
            if not events:
                return {"success": True, "message": "历史事件文件为空", "imported": 0}

            # 用于跟踪已导入的 ID，避免重复
            existing_ids = set(self._collection.get()["ids"]) if self._collection.count() > 0 else set()

            imported = 0
            failed = 0
            skipped = 0
            batch_size = 10  # 批量导入大小

            for i in range(0, len(events), batch_size):
                batch = events[i:i + batch_size]
                ids = []
                embeddings = []
                documents = []
                metadatas = []

                for event in batch:
                    event_id = event.get("id", f"hist_{i}")
                    title = event.get("title", "")
                    summary = event.get("summary", "")
                    event_type = event.get("event_type", "")
                    sentiment = event.get("sentiment", 0.0)
                    date = event.get("date", "")
                    direct_impacts = event.get("direct_impacts", [])

                    # 跳过已存在的事件
                    if event_id in existing_ids:
                        skipped += 1
                        continue

                    # 组合文本
                    combined_text = f"{title} {summary} {event_type}"

                    # 获取 embedding
                    embedding = self._get_embedding(combined_text)
                    if embedding is None:
                        # Jina 不可用时，跳过此事件（避免维度不匹配）
                        logger.warning(f"跳过事件 {event_id}：Jina API 不可用")
                        failed += 1
                        continue

                    ids.append(event_id)
                    embeddings.append(embedding)
                    documents.append(combined_text)
                    metadatas.append({
                        "title": title,
                        "event_type": event_type,
                        "sentiment": sentiment,
                        "date": date,
                        "direct_impacts": json.dumps(direct_impacts, ensure_ascii=False),
                        "is_historical": True
                    })

                # 批量添加到 ChromaDB
                if ids:
                    try:
                        self._collection.add(
                            ids=ids,
                            embeddings=embeddings,
                            documents=documents,
                            metadatas=metadatas
                        )
                        imported += len(ids)
                        existing_ids.update(ids)
                    except Exception as batch_err:
                        logger.error(f"批量导入失败: {batch_err}")
                        failed += len(ids)

            logger.info(f"历史事件导入完成: 成功 {imported}, 失败 {failed}, 跳过 {skipped}")
            return {
                "success": True,
                "imported": imported,
                "failed": failed,
                "skipped": skipped,
                "total_in_file": len(events)
            }

        except Exception as e:
            logger.error(f"导入历史事件失败: {e}")
            return {"success": False, "message": str(e)}

    async def search_historical_events(
        self,
        query: str,
        event_type: Optional[str] = None,
        date_range: Optional[tuple] = None,
        top_k: int = 5
    ) -> List[dict]:
        """
        搜索历史事件（带额外过滤条件）

        Args:
            query: 搜索查询
            event_type: 事件类型过滤
            date_range: 日期范围 (start_date, end_date)
            top_k: 返回数量

        Returns:
            匹配的历史事件列表
        """
        if not self._initialized:
            await self.initialize()

        if self._collection is None:
            return []

        try:
            # 构建 where 过滤条件
            where_conditions = {}
            if event_type:
                where_conditions["event_type"] = event_type

            # 获取 embedding
            embedding = self._get_embedding(query)
            if embedding is None:
                return []

            # 执行查询
            results = self._collection.query(
                query_embeddings=[embedding],
                n_results=top_k,
                where=where_conditions if where_conditions else None
            )

            # 解析结果
            events = []
            if results and results.get("ids"):
                for i, event_id in enumerate(results["ids"][0]):
                    distance = results.get("distances", [[0]])[0][i]
                    similarity = 1.0 / (1.0 + distance)
                    metadata = results.get("metadatas", [[{}]])[0][i]
                    document = results.get("documents", [[""]])[0][i]

                    # 日期过滤
                    if date_range:
                        event_date = metadata.get("date", "")
                        if event_date:
                            from datetime import datetime
                            try:
                                dt = datetime.strptime(event_date, "%Y-%m-%d")
                                start, end = date_range
                                if dt < start or dt > end:
                                    continue
                            except ValueError:
                                pass

                    # 解析直接影响的行业
                    direct_impacts_raw = metadata.get("direct_impacts", "[]")
                    try:
                        direct_impacts = json.loads(direct_impacts_raw)
                    except:
                        direct_impacts = []

                    events.append({
                        "event_id": event_id,
                        "title": metadata.get("title", ""),
                        "event_type": metadata.get("event_type", ""),
                        "sentiment": metadata.get("sentiment", 0.0),
                        "date": metadata.get("date", ""),
                        "similarity": similarity,
                        "direct_impacts": direct_impacts,
                        "document": document
                    })

            return events

        except Exception as e:
            logger.error(f"搜索历史事件失败: {e}")
            return []

    async def clear_all_events(self) -> bool:
        """清空向量库中的所有事件"""
        if not self._initialized:
            await self.initialize()

        if self._collection is None:
            return False

        try:
            # 获取所有 ID 并删除
            all_ids = self._collection.get()["ids"]
            if all_ids:
                self._collection.delete(ids=all_ids)
            logger.info("向量库已清空")
            return True
        except Exception as e:
            logger.error(f"清空向量库失败: {e}")
            return False


# 全局实例
_semantic_matcher: Optional[SemanticMatcher] = None


def get_semantic_matcher() -> SemanticMatcher:
    """获取语义匹配器实例"""
    global _semantic_matcher
    if _semantic_matcher is None:
        _semantic_matcher = SemanticMatcher()
    return _semantic_matcher