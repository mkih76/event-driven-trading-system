"""
Tushare 数据提供者
需要 TUSHARE_TOKEN
"""
import os
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from .base import BaseDataProvider, NewsItem, MarketData, SectorData
from .config import data_provider_settings

logger = logging.getLogger(__name__)

class TushareProvider(BaseDataProvider):
    """Tushare 数据提供者 - 需要 API Token"""

    def __init__(self):
        self.token = data_provider_settings.TUSHARE_TOKEN or os.getenv("TUSHARE_TOKEN")
        if not self.token:
            raise ValueError("TUSHARE_TOKEN is required for Tushare provider")
        self._init_api()
        self._has_pro = None   # None: 未检测, True/False: 是否有Pro权限

    def _init_api(self):
        """初始化 Tushare API"""
        try:
            import tushare as ts
            self.api = ts.pro(self.token)
        except ImportError:
            raise ImportError("请安装 tushare: pip install tushare")
        except Exception as e:
            raise ValueError(f"Tushare 初始化失败: {e}")

    def _check_pro_access(self) -> bool:
        """检测当前token是否拥有Pro会员权限（调用需要Pro的接口进行试探）"""
        if self._has_pro is not None:
            return self._has_pro
        try:
            # 尝试调用一个需要Pro会员的接口（板块信息）
            df = self.api.sector(sector='上证板块', fields='sector')
            self._has_pro = df is not None and not df.empty
        except Exception as e:
            logger.warning(f"Tushare Pro 权限检测失败: {e}，将降级处理")
            self._has_pro = False
        return self._has_pro

    async def get_news(
        self,
        keywords: List[str],
        limit: int = 10,
        days: int = 3
    ) -> List[NewsItem]:
        """获取财经新闻"""
        try:
            news_items = []
            try:
                df = self.api.news_basic(source='sina', limit=limit)
                for _, row in df.iterrows():
                    content = str(row.get('content', ''))[:500]
                    if keywords:
                        text = (str(row.get('title', '')) + content).lower()
                        if any(kw.lower() in text for kw in keywords):
                            news_items.append(NewsItem(
                                title=str(row.get('title', '')),
                                content=content,
                                source=str(row.get('source', '新浪')),
                                publish_time=row.get('datetime', datetime.now()),
                                keywords=keywords
                            ))
            except Exception as e:
                logger.error(f"获取新闻失败: {e}")
            return news_items[:limit]
        except Exception as e:
            logger.error(f"Tushare 获取新闻失败: {e}")
            return []

    async def get_market_data(
        self,
        symbols: List[str]
    ) -> List[MarketData]:
        """获取股票行情"""
        if not symbols:
            return []
        try:
            market_data = []
            ts_codes = []
            for symbol in symbols:
                code = symbol.replace('.SH', '').replace('.SZ', '')
                market = 'SH' if code.startswith(('6', '5', '8', '9')) else 'SZ'
                ts_codes.append(f"{code}.{market}")

            # 免费接口可获取单个或少量股票行情，批量可能受限制
            df = self.api.daily(ts_code=','.join(ts_codes)[:20], trade_date=datetime.now().strftime('%Y%m%d'))
            for _, row in df.iterrows():
                market_data.append(MarketData(
                    symbol=f"{row['ts_code']}",
                    name="",
                    price=row.get('close', 0),
                    change=row.get('change', 0),
                    change_pct=row.get('pct_chg', 0),
                    volume=row.get('vol', 0),
                    amount=row.get('amount', 0),
                    timestamp=datetime.now()
                ))
            return market_data
        except Exception as e:
            logger.error(f"Tushare 获取行情失败: {e}")
            return []

    async def get_sector_data(
        self,
        sector_name: str
    ) -> Optional[SectorData]:
        """获取板块数据 - 需要会员权限"""
        if not self._check_pro_access():
            logger.warning("Tushare Pro 权限不足，无法获取板块数据")
            return None
        try:
            df = self.api.sector(sector=sector_name)
            if df.empty:
                return None
            row = df.iloc[0]
            return SectorData(
                name=sector_name,
                change_pct=float(row.get('pct_change', 0)),
                top_stocks=[]
            )
        except Exception as e:
            logger.error(f"获取板块数据失败: {e}")
            return None

    async def search_stocks(
        self,
        keyword: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """搜索股票"""
        try:
            df = self.api.stock_basic(exchange='', list_status='L')
            mask = df['symbol'].str.contains(keyword, na=False) | \
                   df['name'].str.contains(keyword, na=False)
            results = df[mask].head(limit)
            return [
                {
                    "symbol": f"{r['ts_code']}",
                    "name": r['name'],
                    "industry": r.get('industry', '')
                }
                for _, r in results.iterrows()
            ]
        except Exception as e:
            logger.error(f"Tushare 搜索股票失败: {e}")
            return []

    async def get_hot_sectors(self) -> List[SectorData]:
        """获取热门板块 - 需要会员权限"""
        if not self._check_pro_access():
            logger.warning("Tushare Pro 权限不足，无法获取热门板块")
            return []
        try:
            df = self.api.sector(limit=10, sort='pct_change', asc=False)
            sectors = []
            for _, row in df.iterrows():
                sectors.append(SectorData(
                    name=row['sector'],
                    change_pct=float(row.get('pct_change', 0)),
                    top_stocks=[]
                ))
            return sectors
        except Exception as e:
            logger.error(f"获取热门板块失败: {e}")
            return []