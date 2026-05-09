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

    # LLM 配置 (支持 OpenAI / Claude / Ollama / SiliconFlow / Gemini)
    LLM_PROVIDER: str = "gemini"  # openai / claude / ollama / siliconflow / gemini

    # Gemini (Google)
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o"

    # SiliconFlow (硅基流动)
    SILICONFLOW_API_KEY: Optional[str] = None
    SILICONFLOW_BASE_URL: str = "https://api.siliconflow.cn/v1"
    SILICONFLOW_MODEL: str = "deepseek-ai/DeepSeek-V3"  # 或其他可用模型

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

    # CORS 配置
    ALLOWED_ORIGINS: str = "http://localhost:3000"  # 逗号分隔，设为 "*" 允许所有

    # API 认证
    API_AUTH_ENABLED: bool = False  # 设为 True 启用认证
    API_KEY: Optional[str] = None  # 设置 API Key

    # 管理端点密钥
    ADMIN_KEY: Optional[str] = None  # 用于管理端点（如图谱重载）

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"

    def get_allowed_origins(self) -> list[str]:
        """获取允许的来源列表"""
        if self.ALLOWED_ORIGINS == "*":
            return ["*"]
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]


settings = Settings()
