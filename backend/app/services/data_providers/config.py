"""
数据提供者配置
"""
from pydantic_settings import BaseSettings
from typing import Optional


class DataProviderSettings(BaseSettings):
    """数据提供者配置"""

    # 新闻 API
    NEWS_API_PROVIDER: str = "akshare"  # akshare / tushare
    NEWSAPI_API_KEY: Optional[str] = None

    # 行情 API
    MARKET_DATA_PROVIDER: str = "akshare"  # akshare / tushare

    # Tushare
    TUSHARE_TOKEN: Optional[str] = None

    # 缓存 TTL (秒)
    NEWS_CACHE_TTL: int = 300       # 5 分钟
    MARKET_CACHE_TTL: int = 60      # 1 分钟
    SECTOR_CACHE_TTL: int = 120     # 2 分钟

    # RAG 设置
    RAG_ENABLED: bool = True
    RAG_TOP_K: int = 5
    RAG_MAX_CONTEXT_LENGTH: int = 4000

    class Config:
        env_file = ".env"
        extra = "allow"


data_provider_settings = DataProviderSettings()