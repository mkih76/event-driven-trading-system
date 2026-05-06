"""
数据提供者基类
定义新闻和行情数据的抽象接口
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class NewsItem:
    """新闻条目结构"""
    title: str
    content: str
    source: str
    publish_time: datetime
    url: Optional[str] = None
    sentiment_score: Optional[float] = None
    keywords: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "content": self.content,
            "source": self.source,
            "publish_time": self.publish_time.isoformat() if self.publish_time else None,
            "url": self.url,
            "sentiment_score": self.sentiment_score,
            "keywords": self.keywords
        }


@dataclass
class MarketData:
    """行情数据结构"""
    symbol: str          # 股票代码，如 600519.SH
    name: str            # 股票名称
    price: float         # 当前价格
    change: float        # 涨跌额
    change_pct: float    # 涨跌幅 %
    volume: int          # 成交量
    amount: float        # 成交额
    timestamp: datetime  # 数据时间
    sector: Optional[str] = None  # 所属行业

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "price": self.price,
            "change": self.change,
            "change_pct": self.change_pct,
            "volume": self.volume,
            "amount": self.amount,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "sector": self.sector
        }


@dataclass
class SectorData:
    """板块数据"""
    name: str
    change_pct: float
    top_stocks: List[MarketData]
    concept: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "change_pct": self.change_pct,
            "top_stocks": [s.to_dict() for s in self.top_stocks],
            "concept": self.concept
        }


class BaseDataProvider(ABC):
    """数据提供者抽象基类"""

    @abstractmethod
    async def get_news(
        self,
        keywords: List[str],
        limit: int = 10,
        days: int = 3
    ) -> List[NewsItem]:
        """
        获取相关新闻

        Args:
            keywords: 关键词列表
            limit: 返回数量
            days: 搜索最近天数

        Returns:
            新闻列表
        """
        pass

    @abstractmethod
    async def get_market_data(
        self,
        symbols: List[str]
    ) -> List[MarketData]:
        """
        获取股票行情

        Args:
            symbols: 股票代码列表

        Returns:
            行情列表
        """
        pass

    @abstractmethod
    async def get_sector_data(
        self,
        sector_name: str
    ) -> Optional[SectorData]:
        """
        获取板块数据

        Args:
            sector_name: 板块名称

        Returns:
            板块数据
        """
        pass

    async def search_stocks(
        self,
        keyword: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        搜索股票

        Args:
            keyword: 搜索关键词
            limit: 返回数量

        Returns:
            股票列表
        """
        pass

    async def get_hot_sectors(self) -> List[SectorData]:
        """
        获取热门板块

        Returns:
            热门板块列表
        """
        pass