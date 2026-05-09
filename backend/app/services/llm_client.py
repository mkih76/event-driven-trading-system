"""
LLM 客户端统一封装
支持 OpenAI / Claude / Ollama
"""
import os
import json
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Type, TypeVar
from pydantic import BaseModel
from .config import settings
import anthropic

T = TypeVar('T', bound=BaseModel)


class LLMError(Exception):
    def __init__(self, message, provider="", is_retryable=True):
        super().__init__(message)
        self.provider = provider
        self.is_retryable = is_retryable


class LLMUnavailableError(LLMError):
    def __init__(self, provider, reason=""):
        super().__init__(f"{provider} unavailable: {reason}", provider, is_retryable=False)


class BaseLLMClient(ABC):
    """LLM 客户端基类"""

    def __init__(self):
        self.timeout = 120
        self.max_retries = 3
        self._available = True

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        response_model: Optional[Type[BaseModel]] = None,
        system: Optional[str] = None,
        **kwargs
    ) -> Any:
        """生成回复"""
        pass

    @abstractmethod
    async def batch_complete(
        self,
        prompts: list[str],
        **kwargs
    ) -> list[str]:
        """批量生成"""
        pass


class ClaudeClient(BaseLLMClient):
    """Claude 客户端"""

    def __init__(self):
        api_key = settings.ANTHROPIC_API_KEY or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is required")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = settings.ANTHROPIC_MODEL

    async def complete(
        self,
        prompt: str,
        response_model: Optional[Type[BaseModel]] = None,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        **kwargs
    ) -> Any:
        """调用 Claude 生成回复"""

        messages = [{"role": "user", "content": prompt}]

        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
            **kwargs
        )

        text = response.content[0].text

        if response_model:
            # 尝试从回复中提取 JSON
            try:
                # 尝试解析整个响应
                data = json.loads(text)
            except json.JSONDecodeError:
                # 尝试提取代码块中的 JSON
                import re
                json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
                if json_match:
                    data = json.loads(json_match.group(1))
                else:
                    # 尝试找到第一个 { 和最后一个 }
                    start = text.find('{')
                    end = text.rfind('}') + 1
                    if start != -1 and end > start:
                        data = json.loads(text[start:end])
                    else:
                        raise ValueError(f"无法从响应中提取 JSON: {text[:200]}")

            data = fix_enum_values(data)
            return response_model(**data)

        return text

    async def batch_complete(
        self,
        prompts: list[str],
        **kwargs
    ) -> list[str]:
        """批量调用 Claude"""
        results = []
        for prompt in prompts:
            result = await self.complete(prompt, **kwargs)
            results.append(result)
        return results


class OpenAIClient(BaseLLMClient):
    """OpenAI 客户端"""

    def __init__(self):
        super().__init__()
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError("请安装 openai: pip install openai")

        api_key = settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required")

        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=settings.OPENAI_BASE_URL
        )
        self.model = settings.OPENAI_MODEL

    async def complete(
        self,
        prompt: str,
        response_model: Optional[Type[BaseModel]] = None,
        system: Optional[str] = None,
        **kwargs
    ) -> Any:
        """调用 OpenAI 生成回复"""

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            **kwargs
        )

        text = response.choices[0].message.content

        if response_model:
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
                if json_match:
                    data = json.loads(json_match.group(1))
                else:
                    start = text.find('{')
                    end = text.rfind('}') + 1
                    if start != -1 and end > start:
                        data = json.loads(text[start:end])
                    else:
                        raise ValueError(f"无法从响应中提取 JSON: {text[:200]}")

            data = fix_enum_values(data)
            return response_model(**data)

        return text

    async def batch_complete(
        self,
        prompts: list[str],
        **kwargs
    ) -> list[str]:
        """批量调用 OpenAI"""
        results = []
        for prompt in prompts:
            result = await self.complete(prompt, **kwargs)
            results.append(result)
        return results


class OllamaClient(BaseLLMClient):
    """Ollama 本地模型客户端"""

    def __init__(self):
        try:
            import openai
        except ImportError:
            raise ImportError("请安装 openai: pip install openai")

        self.client = openai.OpenAI(
            base_url=f"{settings.OLLAMA_BASE_URL}/v1",
            api_key="ollama"  # Ollama 不需要真正的 API key
        )
        self.model = settings.OLLAMA_MODEL

    async def complete(
        self,
        prompt: str,
        response_model: Optional[Type[BaseModel]] = None,
        system: Optional[str] = None,
        **kwargs
    ) -> Any:
        """调用 Ollama 生成回复"""

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            **kwargs
        )

        text = response.choices[0].message.content

        if response_model:
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
                if json_match:
                    data = json.loads(json_match.group(1))
                else:
                    start = text.find('{')
                    end = text.rfind('}') + 1
                    if start != -1 and end > start:
                        data = json.loads(text[start:end])
                    else:
                        raise ValueError(f"无法从响应中提取 JSON: {text[:200]}")

            data = fix_enum_values(data)
            return response_model(**data)

        return text

    async def batch_complete(
        self,
        prompts: list[str],
        **kwargs
    ) -> list[str]:
        """批量调用 Ollama"""
        results = []
        for prompt in prompts:
            result = await self.complete(prompt, **kwargs)
            results.append(result)
        return results


class SiliconFlowClient(BaseLLMClient):
    """SiliconFlow (硅基流动) 客户端 - OpenAI 兼容"""

    def __init__(self):
        super().__init__()
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError("请安装 openai: pip install openai")

        api_key = settings.SILICONFLOW_API_KEY or os.getenv("SILICONFLOW_API_KEY")
        if not api_key:
            raise ValueError("SILICONFLOW_API_KEY is required")

        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=settings.SILICONFLOW_BASE_URL
        )
        self.model = settings.SILICONFLOW_MODEL

    async def complete(
        self,
        prompt: str,
        response_model: Optional[Type[BaseModel]] = None,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        **kwargs
    ) -> Any:
        """调用 SiliconFlow 生成回复"""

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            **kwargs
        )

        text = response.choices[0].message.content

        if response_model:
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
                if json_match:
                    data = json.loads(json_match.group(1))
                else:
                    start = text.find('{')
                    end = text.rfind('}') + 1
                    if start != -1 and end > start:
                        data = json.loads(text[start:end])
                    else:
                        raise ValueError(f"无法从响应中提取 JSON: {text[:200]}")

            data = fix_enum_values(data)
            return response_model(**data)

        return text

    async def batch_complete(
        self,
        prompts: list[str],
        **kwargs
    ) -> list[str]:
        """批量调用 SiliconFlow"""
        results = []
        for prompt in prompts:
            result = await self.complete(prompt, **kwargs)
            results.append(result)
        return results


def get_llm_client() -> BaseLLMClient:
    """获取 LLM 客户端"""
    provider = settings.LLM_PROVIDER.lower()

    if provider == "claude":
        return ClaudeClient()
    elif provider == "openai":
        return OpenAIClient()
    elif provider == "ollama":
        return OllamaClient()
    elif provider == "siliconflow":
        return SiliconFlowClient()
    else:
        raise ValueError(f"不支持的 LLM provider: {provider}")


# 全局 LLM 客户端实例
_llm_client: Optional[BaseLLMClient] = None


def get_llm() -> BaseLLMClient:
    """获取 LLM 客户端实例（单例）"""
    global _llm_client
    if _llm_client is None:
        _llm_client = get_llm_client()
    return _llm_client

# ========== 枚举值自动修复 ==========
ENUM_MAPPING = {
    # relation_type 映射
    "风险偏好传导": "风险偏好",
    "需求传导": "需求增加",
    "供给传导": "供给增加",
    "利率下降": "利率变动",
    "资本流入": "资金流动",
    "资本流出": "资金流动",
    "避险资金": "避险需求",
    "避险": "避险需求",
    "金融属性": "风险偏好",
    "避险情绪": "避险需求",
    "情绪传导": "风险偏好",
    "恐慌情绪": "风险偏好",
    "风险偏好上升": "风险偏好",
    "风险偏好下降": "风险偏好",
    "需求上升": "需求增加",
    "需求下降": "需求减少",
    "供给上升": "供给增加",
    "供给下降": "供给减少",
    # event_type 映射
    "地缘政治/政策": "地缘政治",
    "政策/地缘政治": "地缘政治",
    "经济数据/政策": "经济数据",
    "地缘政治/经济数据": "地缘政治",
    "其他/地缘政治": "其他",
    # impact_direction 映射
    "无": "中性",
    "未知": "中性",
    "不确定": "中性",
    # impact_magnitude 映射
}

def fix_enum_values(data):
    """递归修复枚举值"""
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, str):
                # 修复 event_type 字段
                if key == "event_type":
                    data[key] = ENUM_MAPPING.get(value, value)
                # 修复 relation_type 字段
                elif key == "relation_type":
                    data[key] = ENUM_MAPPING.get(value, value)
                # 修复 impact_direction 字段
                elif key == "impact_direction":
                    data[key] = ENUM_MAPPING.get(value, value)
                # 修复 impact_magnitude 字段
                elif key == "impact_magnitude":
                    if value not in ["高", "中", "低"]:
                        data[key] = "中"  # 默认值为中
            elif isinstance(value, (dict, list)):
                fix_enum_values(value)
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                fix_enum_values(item)
    return data


class RuleBasedFallbackClient(BaseLLMClient):
    """基于规则的降级客户端（LLM不可用时使用）"""

    def __init__(self):
        self._available = True

    @property
    def is_available(self) -> bool:
        return True

    async def complete(
        self,
        prompt: str,
        response_model: Optional[Type[BaseModel]] = None,
        system: Optional[str] = None,
        **kwargs
    ) -> Any:
        """基于关键词规则的降级分析"""
        text = prompt.lower()
        sentiment = 0.0
        if any(k in text for k in ["利好", "增加", "上涨", "增长"]):
            sentiment = 0.5
        if any(k in text for k in ["利空", "减少", "下跌", "制裁"]):
            sentiment = -0.5
        return {"sentiment": sentiment, "event_type": "其他", "summary": "规则降级分析"}

    async def batch_complete(self, prompts: list[str], **kwargs) -> list[str]:
        return [await self.complete(p, **kwargs) for p in prompts]


def get_llm() -> BaseLLMClient:
    """获取 LLM 客户端"""
    provider = settings.LLM_PROVIDER.lower()
    clients = {
        "claude": ClaudeClient,
        "openai": OpenAIClient,
        "ollama": OllamaClient,
        "siliconflow": SiliconFlowClient,
    }
    if provider == "gemini":
        return RuleBasedFallbackClient()
    elif provider in clients:
        try:
            return clients[provider]()
        except (ValueError, ImportError):
            return RuleBasedFallbackClient()
    return RuleBasedFallbackClient()
