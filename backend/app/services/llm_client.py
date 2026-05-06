"""
LLM 客户端统一封装
支持 OpenAI / Claude / Ollama
"""
import os
import json
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Type, TypeVar
from pydantic import BaseModel
from ..config import settings
import anthropic

T = TypeVar('T', bound=BaseModel)


class BaseLLMClient(ABC):
    """LLM 客户端基类"""

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
