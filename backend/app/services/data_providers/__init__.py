"""
数据提供者模块
支持新闻和行情数据获取
"""
from .base import BaseDataProvider, NewsItem, MarketData
from .tushare_provider import TushareProvider
from .akshare_provider import AKShareProvider

_providers = {}

def get_news_provider():
    """获取新闻提供者实例"""
    from .config import settings
    provider_type = settings.NEWS_API_PROVIDER

    if provider_type == "tushare":
        if "tushare" not in _providers:
            _providers["tushare"] = TushareProvider()
        return _providers["tushare"]
    elif provider_type == "akshare":
        if "akshare" not in _providers:
            _providers["akshare"] = AKShareProvider()
        return _providers["akshare"]
    else:
        raise ValueError(f"不支持的新闻提供者: {provider_type}")

def get_market_provider():
    """获取行情提供者实例"""
    from .config import settings
    provider_type = settings.MARKET_DATA_PROVIDER

    if provider_type == "tushare":
        if "tushare_market" not in _providers:
            _providers["tushare_market"] = TushareProvider()
        return _providers["tushare_market"]
    elif provider_type == "akshare":
        if "akshare_market" not in _providers:
            _providers["akshare_market"] = AKShareProvider()
        return _providers["akshare_market"]
    else:
        raise ValueError(f"不支持的行情提供者: {provider_type}")