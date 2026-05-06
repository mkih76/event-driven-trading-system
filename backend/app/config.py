"""
事件驱动交易分析系统 - 配置管理
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""

    # 应用基础
    APP_NAME: str = "事件驱动交易分析系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # LLM 配置 (支持 OpenAI / Claude / Ollama / SiliconFlow)
    LLM_PROVIDER: str = "siliconflow"  # openai / claude / ollama / siliconflow

    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o"

    # SiliconFlow (硅基流动)
    SILICONFLOW_API_KEY: Optional[str] = None
    SILICONFLOW_BASE_URL: str = "https://api.siliconflow.cn/v1"
    SILICONFLOW_MODEL: str = "Qwen/Qwen2.5-7B-Instruct"  # 或其他可用模型

    # Claude (Anthropic)
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"

    # Ollama (本地)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"

    # 数据库
    DATABASE_URL: str = "sqlite:///./data/events.db"

    # Redis (可选，用于缓存)
    REDIS_URL: Optional[str] = None

    # 日志
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"


settings = Settings()
