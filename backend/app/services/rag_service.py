"""
RAG 检索增强服务
结合实时数据与 LLM 分析
按事件类型选择性注入上下文
"""
import logging
from typing import List, Optional, Dict, Any
from .data_providers import get_news_provider, get_market_provider
from .data_providers.base import NewsItem, MarketData, SectorData
from .data_providers.config import data_provider_settings

logger = logging.getLogger(__name__)


# 事件类型 -> 上下文需求映射
EVENT_TYPE_CONTEXT_MAP = {
    "地缘政治": {
        "news_priority": ["地缘", "冲突", "制裁", "外交"],
        "market_data": ["能源", "军工", "黄金", "外汇"],
        "include_hot_sectors": True
    },
    "政策": {
        "news_priority": ["央行", "财政", "监管", "政策"],
        "market_data": ["银行", "证券", "房地产", "保险"],
        "include_hot_sectors": True
    },
    "灾难": {
        "news_priority": ["灾害", "事故", "疫情", "气象"],
        "market_data": ["农业", "食品", "化工", "保险"],
        "include_hot_sectors": False
    },
    "经济数据": {
        "news_priority": ["CPI", "GDP", "就业", "PMI"],
        "market_data": ["宏观", "消费", "工业", "出口"],
        "include_hot_sectors": False
    },
    "财报": {
        "news_priority": ["业绩", "财报", "营收", "利润"],
        "market_data": ["相关行业", "竞争对手"],
        "include_hot_sectors": False
    },
    "技术突破": {
        "news_priority": ["技术", "研发", "专利", "创新"],
        "market_data": ["科技", "半导体", "新能源"],
        "include_hot_sectors": True
    },
    "能源": {
        "news_priority": ["原油", "天然气", "煤炭", "能源"],
        "market_data": ["原油", "天然气", "炼化", "化工"],
        "include_hot_sectors": True
    }
}


class RAGService:
    """检索增强生成服务"""

    def __init__(self):
        self.news_provider = None
        self.market_provider = None

    def _get_providers(self):
        """懒加载提供者"""
        if self.news_provider is None:
            try:
                self.news_provider = get_news_provider()
            except Exception as e:
                logger.warning(f"新闻提供者初始化失败: {e}")
                self.news_provider = None

        if self.market_provider is None:
            try:
                self.market_provider = get_market_provider()
            except Exception as e:
                logger.warning(f"行情提供者初始化失败: {e}")
                self.market_provider = None

        return self.news_provider, self.market_provider

    async def get_context_for_event(
        self,
        title: str,
        content: str = "",
        event_type: str = "其他",
        affected_industries: List[str] = None
    ) -> str:
        """
        获取事件相关上下文 - 按事件类型选择性注入

        Args:
            title: 事件标题
            content: 事件内容
            event_type: 事件类型，用于选择上下文
            affected_industries: 受影响行业列表

        Returns:
            格式化的上下文字符串
        """
        if not data_provider_settings.RAG_ENABLED:
            return ""

        news_provider, market_provider = self._get_providers()

        if news_provider is None and market_provider is None:
            return ""

        context_parts = []
        context_parts.append("=== 实时数据上下文 ===")
        context_parts.append(f"分析时间: {self._get_timestamp()}")

        # 获取事件类型对应的上下文配置
        context_config = EVENT_TYPE_CONTEXT_MAP.get(
            event_type,
            EVENT_TYPE_CONTEXT_MAP.get("其他")
        )

        # 提取关键词 - 结合通用词和类型特定词
        keywords = self._extract_keywords(title, content)
        type_keywords = context_config.get("news_priority", [])[:5]
        keywords = list(dict.fromkeys(keywords + type_keywords))[:10]

        # 1. 获取相关新闻 (根据类型优先级)
        if news_provider:
            news_items = await news_provider.get_news(keywords=keywords, limit=5)
            if news_items:
                context_parts.append("\n## 相关财经新闻:")
                for i, item in enumerate(news_items[:5], 1):
                    context_parts.append(f"{i}. [{item.source}] {item.title}")
                    if item.content:
                        context_parts.append(f"   {item.content[:200]}...")

        # 2. 获取市场数据 (优先获取类型相关行业)
        target_industries = affected_industries or []
        if context_config.get("market_data"):
            target_industries = target_industries + context_config["market_data"][:3]

        if market_provider and target_industries:
            context_parts.append("\n## 行业市场数据:")
            shown_industries = set()
            for industry in target_industries[:5]:
                if industry in shown_industries:
                    continue
                sector_data = await market_provider.get_sector_data(industry)
                if sector_data:
                    context_parts.append(f"\n【{sector_data.name}】涨跌幅: {sector_data.change_pct:.2f}%")
                    if sector_data.top_stocks:
                        context_parts.append("   领涨股:")
                        for stock in sector_data.top_stocks[:3]:
                            context_parts.append(
                                f"   - {stock.name}: {stock.price} ({stock.change_pct:+.2f}%)"
                            )
                    shown_industries.add(industry)

        # 3. 热门板块 (可选，根据类型)
        if market_provider and context_config.get("include_hot_sectors"):
            hot_sectors = await market_provider.get_hot_sectors()
            if hot_sectors:
                context_parts.append("\n## 当前热门板块:")
                for sector in hot_sectors[:5]:
                    context_parts.append(f"- {sector.name}: {sector.change_pct:+.2f}%")

        return "\n".join(context_parts)

    def _extract_keywords(self, title: str, content: str) -> List[str]:
        """从事件中提取关键词"""
        import re
        text = (title + " " + content).lower()

        # 常见关键词模式
        patterns = [
            r'[\u4e00-\u9fa5]+(?:战争|冲突|制裁|封锁)',
            r'[\u4e00-\u9fa5]+(?:加息|降息|宽松|紧缩)',
            r'[\u4e00-\u9fa5]+(?:疫情|病毒|疫苗|变异)',
            r'[\u4e00-\u9fa5]+(?:贸易|关税|制裁|出口|进口)',
            r'(美国|欧洲|日本|中东|中国|俄罗斯|伊朗|朝鲜)',
        ]

        keywords = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            keywords.extend(matches)

        # 去重，保留前10个
        return list(dict.fromkeys(keywords))[:10]

    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def format_context_for_prompt(
        self,
        context: str,
        max_length: int = 4000
    ) -> str:
        """格式化上下文，限制长度"""
        if len(context) <= max_length:
            return context
        return context[:max_length] + "\n...(上下文已截断)"


# 全局 RAG 服务实例
_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """获取 RAG 服务实例"""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service