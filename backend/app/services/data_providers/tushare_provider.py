"""
Tushare 数据提供者
需要 TUSHARE_TOKEN
"""
import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from .base import BaseDataProvider, NewsItem, MarketData, SectorData
from .config import data_provider_settings


class TushareProvider(BaseDataProvider):
    """Tushare 数据提供者 - 需要 API Token"""

    def __init__(self):
        self.token = data_provider_settings.TUSHARE_TOKEN or os.getenv("TUSHARE_TOKEN")
        if not self.token:
            raise ValueError("TUSHARE_TOKEN is required for Tushare provider")
        self._init_api()

    def _init_api(self):
        """初始化 Tushare API"""
        try:
            import tushare as ts
            self.api = ts.pro(self.token)
        except ImportError:
            raise ImportError("请安装 tushare: pip install tushare")
        except Exception as e:
            raise ValueError(f"Tushare 初始化失败: {e}")

    async def get_news(
        self,
        keywords: List[str],
        limit: int = 10,
        days: int = 3
    ) -> List[NewsItem]:
        """获取财经新闻"""
        try:
            # Tushare 新闻接口
            news_items = []

            # 获取财经要闻
            try:
                df = self.api.news_basic(source='sina', limit=limit)
                for _, row in df.iterrows():
                    content = str(row.get('content', ''))[:500]
                    # 过滤关键词
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
                print(f"获取新闻失败: {e}")

            return news_items[:limit]

        except Exception as e:
            print(f"Tushare 获取新闻失败: {e}")
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

            # 转换代码格式
            ts_codes = []
            for symbol in symbols:
                code = symbol.replace('.SH', '').replace('.SZ', '')
                market = 'SH' if code.startswith(('6', '5', '8', '9')) else 'SZ'
                ts_codes.append(f"{code}.{market}")

            # 批量查询
            df = self.api.daily(ts_code=','.join(ts_codes)[:20], trade_date=datetime.now().strftime('%Y%m%d'))

            for _, row in df.iterrows():
                market_data.append(MarketData(
                    symbol=f"{row['ts_code']}",
                    name="",  # Tushare 需要单独查询
                    price=row.get('close', 0),
                    change=row.get('change', 0),
                    change_pct=row.get('pct_chg', 0),
                    volume=row.get('vol', 0),
                    amount=row.get('amount', 0),
                    timestamp=datetime.now()
                ))

            return market_data

        except Exception as e:
            print(f"Tushare 获取行情失败: {e}")
            return []

    async def get_sector_data(
        self,
        sector_name: str
    ) -> Optional[SectorData]:
        """获取板块数据 - 需要会员权限"""
        # Tushare 板块数据需要 pro 会员
        print("Tushare 板块数据需要 pro 会员权限")
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
            print(f"Tushare 搜索股票失败: {e}")
            return []

    async def get_hot_sectors(self) -> List[SectorData]:
        """获取热门板块 - 需要会员权限"""
        print("Tushare 热门板块需要 pro 会员权限")
        return []