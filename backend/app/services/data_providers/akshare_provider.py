"""
AKShare 数据提供者
免费数据源，无需 API Key
"""
import akshare as ak
from typing import List, Optional, Dict, Any
from datetime import datetime
from .base import BaseDataProvider, NewsItem, MarketData, SectorData
from .config import data_provider_settings
import asyncio
from functools import lru_cache
import time


class AKShareProvider(BaseDataProvider):
    """AKShare 数据提供者 - 免费A股数据"""

    def __init__(self):
        self._news_cache: Dict[str, tuple[float, List[NewsItem]]] = {}
        self._market_cache: Dict[str, tuple[float, List[MarketData]]] = {}

    def _get_cached(self, cache: Dict, key: str, ttl: int) -> Optional[List]:
        """获取缓存数据"""
        if key in cache:
            timestamp, data = cache[key]
            if time.time() - timestamp < ttl:
                return data
        return None

    def _set_cache(self, cache: Dict, key: str, data: List):
        """设置缓存"""
        cache[key] = (time.time(), data)

    async def get_news(
        self,
        keywords: List[str],
        limit: int = 10,
        days: int = 3
    ) -> List[NewsItem]:
        """获取财经新闻"""
        cache_key = f"news_{','.join(keywords)}_{limit}"
        cached = self._get_cached(self._news_cache, cache_key, data_provider_settings.NEWS_CACHE_TTL)
        if cached:
            return cached

        try:
            news_items = []

            # 获取东方财富新闻
            try:
                df = ak.stock_news_em(symbol="A股")
                for _, row in df.head(limit).iterrows():
                    news_items.append(NewsItem(
                        title=str(row.get('标题', '')),
                        content=str(row.get('内容', ''))[:500],
                        source=str(row.get('信息来源', '东方财富')),
                        publish_time=self._parse_datetime(row.get('发布时间')),
                        url=row.get('链接'),
                        keywords=keywords
                    ))
            except Exception as e:
                print(f"获取东方财富新闻失败: {e}")

            # 过滤与关键词相关的新闻
            if keywords:
                filtered = []
                for item in news_items:
                    text = (item.title + item.content).lower()
                    if any(kw.lower() in text for kw in keywords):
                        filtered.append(item)
                news_items = filtered[:limit]

            self._set_cache(self._news_cache, cache_key, news_items)
            return news_items

        except Exception as e:
            print(f"获取新闻失败: {e}")
            return []

    def _parse_datetime(self, value) -> datetime:
        """解析时间"""
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace('/', '-'))
            except:
                pass
        return datetime.now()

    async def get_market_data(
        self,
        symbols: List[str]
    ) -> List[MarketData]:
        """获取股票行情"""
        if not symbols:
            return []

        cache_key = f"market_{','.join(sorted(symbols))}"
        cached = self._get_cached(self._market_cache, cache_key, data_provider_settings.MARKET_CACHE_TTL)
        if cached:
            return cached

        try:
            market_data = []

            # 批量获取实时行情
            for symbol in symbols:
                try:
                    # 统一格式
                    code = symbol.replace('.SH', '').replace('.SZ', '')
                    if not code.startswith(('6', '5', '8', '9')):
                        code = symbol

                    df = ak.stock_zh_a_spot_em()
                    row = df[df['代码'] == code]

                    if not row.empty:
                        r = row.iloc[0]
                        market_data.append(MarketData(
                            symbol=symbol,
                            name=str(r.get('名称', '')),
                            price=float(r.get('最新价', 0)),
                            change=float(r.get('涨跌额', 0)),
                            change_pct=float(r.get('涨跌幅', 0)),
                            volume=int(r.get('成交量', 0)),
                            amount=float(r.get('成交额', 0)),
                            timestamp=datetime.now(),
                            sector=r.get('所属行业')
                        ))
                except Exception as e:
                    print(f"获取 {symbol} 行情失败: {e}")

            self._set_cache(self._market_cache, cache_key, market_data)
            return market_data

        except Exception as e:
            print(f"批量获取行情失败: {e}")
            return []

    async def get_sector_data(
        self,
        sector_name: str
    ) -> Optional[SectorData]:
        """获取板块数据"""
        try:
            # 获取板块实时行情
            df = ak.stock_board_industry_name_em()

            # 找到对应板块
            row = df[df['板块名称'].str.contains(sector_name, na=False)]
            if row.empty:
                # 尝试模糊匹配
                for _, r in df.iterrows():
                    if sector_name in str(r.get('板块名称', '')):
                        row = df[df['板块名称'] == r['板块名称']]
                        break

            if not row.empty:
                r = row.iloc[0]
                # 获取板块成分股
                try:
                    stocks_df = ak.stock_board_industry_cons_em(symbol=r['板块名称'])
                    top_stocks = []
                    for _, s in stocks_df.head(5).iterrows():
                        top_stocks.append(MarketData(
                            symbol=str(s.get('代码', '')),
                            name=str(s.get('名称', '')),
                            price=float(s.get('最新价', 0)),
                            change=float(s.get('涨跌额', 0)),
                            change_pct=float(s.get('涨跌幅', 0)),
                            volume=int(s.get('成交量', 0)),
                            amount=float(s.get('成交额', 0)),
                            timestamp=datetime.now()
                        ))
                except:
                    top_stocks = []

                return SectorData(
                    name=r['板块名称'],
                    change_pct=float(r.get('涨跌幅', 0)),
                    top_stocks=top_stocks
                )

            return None

        except Exception as e:
            print(f"获取板块数据失败: {e}")
            return None

    async def search_stocks(
        self,
        keyword: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """搜索股票"""
        try:
            df = ak.stock_zh_a_spot_em()
            # 搜索代码或名称
            mask = df['代码'].str.contains(keyword, na=False) | \
                   df['名称'].str.contains(keyword, na=False)
            results = df[mask].head(limit)

            return [
                {
                    "symbol": f"{r['代码']}.SH" if r['代码'].startswith(('6', '5')) else f"{r['代码']}.SZ",
                    "name": r['名称'],
                    "price": r['最新价'],
                    "change_pct": r['涨跌幅']
                }
                for _, r in results.iterrows()
            ]
        except Exception as e:
            print(f"搜索股票失败: {e}")
            return []

    async def get_hot_sectors(self) -> List[SectorData]:
        """获取热门板块"""
        try:
            df = ak.stock_board_industry_name_em()
            # 按涨跌幅排序
            df = df.sort_values('涨跌幅', ascending=False)

            sectors = []
            for _, r in df.head(10).iterrows():
                sectors.append(SectorData(
                    name=r['板块名称'],
                    change_pct=float(r.get('涨跌幅', 0)),
                    top_stocks=[],
                    concept=r.get('概念', r['板块名称'])
                ))

            return sectors

        except Exception as e:
            print(f"获取热门板块失败: {e}")
            return []