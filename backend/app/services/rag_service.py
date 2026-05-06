"""
RAG 检索增强服务
结合实时数据与 LLM 分析
"""
from typing import List, Optional, Dict, Any
from .data_providers import get_news_provider, get_market_provider
from .data_providers.base import NewsItem, MarketData, SectorData
from .data_providers.config import data_provider_settings


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
                print(f"新闻提供者初始化失败: {e}")
                self.news_provider = None

        if self.market_provider is None:
            try:
                self.market_provider = get_market_provider()
            except Exception as e:
                print(f"行情提供者初始化失败: {e}")
                self.market_provider = None

        return self.news_provider, self.market_provider

    async def get_context_for_event(
        self,
        title: str,
        content: str = "",
        affected_industries: List[str] = None
    ) -> str:
        """
        获取事件相关上下文

        Args:
            title: 事件标题
            content: 事件内容
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

        # 提取关键词
        keywords = self._extract_keywords(title, content)

        # 1. 获取相关新闻
        if news_provider:
            news_items = await news_provider.get_news(keywords=keywords, limit=5)
            if news_items:
                context_parts.append("\n## 相关财经新闻:")
                for i, item in enumerate(news_items[:5], 1):
                    context_parts.append(f"{i}. [{item.source}] {item.title}")
                    if item.content:
                        context_parts.append(f"   {item.content[:200]}...")

        # 2. 获取市场数据
        if market_provider and affected_industries:
            context_parts.append("\n## 行业市场数据:")
            for industry in affected_industries[:3]:
                sector_data = await market_provider.get_sector_data(industry)
                if sector_data:
                    context_parts.append(f"\n【{sector_data.name}】涨跌幅: {sector_data.change_pct:.2f}%")
                    if sector_data.top_stocks:
                        context_parts.append("   领涨股:")
                        for stock in sector_data.top_stocks[:3]:
                            context_parts.append(
                                f"   - {stock.name}: {stock.price} ({stock.change_pct:+.2f}%)"
                            )

        # 3. 热门板块
        if market_provider:
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