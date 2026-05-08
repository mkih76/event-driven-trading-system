"""
LLM 客户端统一封装
支持 OpenAI / Claude / Ollama / SiliconFlow
"""
import os
import re
import json
import asyncio
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, TypeVar, Any, Union
from typing import get_origin, get_args
from pydantic import BaseModel
from ..config import settings
import anthropic

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class LLMError(Exception):
    """LLM 调用异常"""
    def __init__(self, message: str, provider: str, is_retryable: bool = True):
        super().__init__(message)
        self.provider = provider
        self.is_retryable = is_retryable


class LLMUnavailableError(LLMError):
    """LLM 服务不可用（降级触发）"""
    def __init__(self, provider: str, reason: str = ""):
        super().__init__(f"{provider} unavailable: {reason}", provider, is_retryable=False)


class BaseLLMClient(ABC):
    """LLM 客户端基类"""

    def __init__(self):
        self.timeout = 60  # 默认超时60秒
        self.max_retries = 2
        self._available = True  # 可用性状态
        self._consecutive_failures = 0
        self._failure_threshold = 3  # 连续失败3次标记为不可用

    @property
    def is_available(self) -> bool:
        """检查客户端是否可用"""
        return self._available

    def mark_unavailable(self, reason: str = ""):
        """标记为不可用"""
        self._available = False
        logger.warning(f"{self.__class__.__name__} marked unavailable: {reason}")

    def mark_available(self):
        """标记为可用"""
        self._available = True
        self._consecutive_failures = 0

    def _record_failure(self):
        """记录一次失败"""
        self._consecutive_failures += 1
        if self._consecutive_failures >= self._failure_threshold:
            self.mark_unavailable(f"连续{self._consecutive_failures}次失败")

    def _record_success(self):
        """记录一次成功"""
        self._consecutive_failures = 0
        if not self._available:
            self.mark_available()

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

    def _parse_json_response(self, text: str, response_model: Type[BaseModel]) -> BaseModel:
        """解析 JSON 响应，支持多级降级"""
        import re

        # 尝试解析整个响应
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # 尝试提取代码块中的 JSON
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
            if json_match:
                try:
                    data = json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    data = self._extract_json_from_text(text)
            else:
                data = self._extract_json_from_text(text)

        # LLM 偶发返回多选（如"地缘政治/经济数据"），取第一个匹配值
        data = self._fix_multi_value_enums(data, response_model)

        return response_model(**data)

    def _extract_json_from_text(self, text: str) -> dict:
        """从文本中提取 JSON"""
        import re
        start = text.find('{')
        end = text.rfind('}') + 1
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
        raise LLMError(f"响应中找不到有效JSON: {text[:200]}", self.__class__.__name__)

    def _fix_multi_value_enums(self, data: dict, response_model: Type[BaseModel]) -> dict:
        """
        处理 LLM 返回多值及别名映射。
        对 EventAnalysisResult 及其嵌套结构中所有 enum 字段做：
        1. 多值拆分（/ 或 , 分隔）
        2. 别名精确映射
        3. 模糊关键字匹配兜底
        """
        # 定义所有需要修复的 enum 字段及其有效值集合
        # 格式：field_path -> (valid_values_set, alias_map_dict)
        # field_path 支持点号访问嵌套字段（如 direct_impacts.impact_direction）
        enum_fields = {
            # DirectImpact nested fields
            'direct_impacts.impact_direction': ({
                '利好', '利空', '中性', '上行', '下行', '无', '无影响'
            }, {
                '中': '中性', '不利': '利空', '负面影响': '利空', '负面': '利空',
                '利好': '利好', '正面影响': '利好', '正面': '利好', '上升': '利好',
                '中立': '中性', '平稳': '中性', '中性偏多': '中性', '中性偏空': '中性',
                '无直接': '无', '无直接受损': '无', '无影响': '无影响',
                '上行': '上行', '上涨': '上行', '下行': '下行', '下跌': '下行',
            }),
            'direct_impacts.impact_magnitude': ({
                '高', '中', '低', '显著', '轻微', '严重'
            }, {
                '中': '中', '高': '高', '低': '低', '显著': '显著', '轻微': '轻微', '严重': '严重',
            }),
            # Top-level fields
            'event_type': ({
                '地缘政治', '政策', '灾难', '经济数据', '财报', '技术突破', '其他'
            }, {
                '地缘政治': '地缘政治', '政策': '政策', '灾难': '灾难',
                '经济数据': '经济数据', '财报': '财报', '技术突破': '技术突破', '其他': '其他',
                '战争': '地缘政治', '制裁': '地缘政治', '封锁': '地缘政治',
                '监管': '政策', '法规': '政策', '财政': '政策',
                '自然灾害': '灾难', '疫情': '灾难', '事故': '灾难',
                'GDP': '经济数据', 'CPI': '经济数据', '利率': '经济数据', '宏观经济': '经济数据',
                '业绩': '财报', '财报公告': '财报',
                '创新': '技术突破', '突破': '技术突破',
                '地缘政治/经济数据': '地缘政治', '不确定': '其他', '未知': '其他',
            }),
            'signal_type': ({
                '强烈买入', '买入', '观望', '卖出', '强烈卖出'
            }, {
                '强烈买入': '强烈买入', '买入': '买入', '观望': '观望', '卖出': '卖出', '强烈卖出': '强烈卖出',
                '做多': '买入', '做空': '卖出', '平仓': '观望',
            }),
            'event_intensity': ({
                '高', '中', '低', '显著', '轻微', '严重'
            }, {
                '中': '中', '高': '高', '低': '低', '显著': '显著', '轻微': '轻微', '严重': '严重',
            }),
        }

        def fix_value(val: str, enum_def: tuple) -> str:
            """对单个字符串值做修复"""
            valid_vals, alias_map = enum_def
            if val in valid_vals:
                return val
            # 1. 别名精确映射
            if val in alias_map:
                mapped = alias_map[val]
                if mapped in valid_vals:
                    return mapped
            # 2. 多值拆分
            if '/' in val or ',' in val:
                for part in re.split(r'[,/]', val):
                    part = part.strip()
                    if part in valid_vals:
                        return part
                    if part in alias_map:
                        mapped = alias_map[part]
                        if mapped in valid_vals:
                            return mapped
            # 3. 包含匹配
            for ev in valid_vals:
                if ev in val or val in ev:
                    return ev
            # 4. 关键字兜底（仅 impact_direction）
            if enum_def == enum_fields.get('direct_impacts.impact_direction', (set(), {})):
                neg_kw = ['负', '跌', '降', '减', '弱', '软', '弊', '损', '害']
                pos_kw = ['正', '涨', '增', '强', '利', '好', '硬', '上', '买']
                neu_kw = ['中', '稳', '平', '观', '望']
                for kw in neg_kw:
                    if kw in val:
                        return '利空'
                for kw in pos_kw:
                    if kw in val:
                        return '利好'
                for kw in neu_kw:
                    if kw in val:
                        return '中性'
            # 5. 无法修复返回原值（保留让 Pydantic 报错而非静默丢失）
            return val

        def fix_dict(d: dict, prefix: str = ''):
            """递归修复 dict 中所有 enum 字段"""
            for field, (valid_vals, alias_map) in enum_fields.items():
                if not field.startswith(prefix):
                    continue
                # 去掉前缀，定位字段名
                actual_field = field[len(prefix):] if prefix else field
                if actual_field not in d:
                    continue
                val = d[actual_field]
                if isinstance(val, list):
                    d[actual_field] = [fix_value(v, (valid_vals, alias_map)) if isinstance(v, str) else v for v in val]
                elif isinstance(val, str):
                    d[actual_field] = fix_value(val, (valid_vals, alias_map))

        # 直接字段
        fix_dict(data)
        # 嵌套字段（如 direct_impacts 列表）
        if 'direct_impacts' in data and isinstance(data['direct_impacts'], list):
            for item in data['direct_impacts']:
                if isinstance(item, dict):
                    fix_dict(item, 'direct_impacts.')
        return data

    async def _call_with_retry(
        self,
        func,
        *args,
        **kwargs
    ) -> Any:
        """带重试的调用"""
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                last_error = LLMError(f"调用超时 ({self.timeout}s)", self.__class__.__name__, is_retryable=True)
                logger.warning(f"LLM 调用超时，重试 {attempt + 1}/{self.max_retries}")
            except (ConnectionError, OSError) as e:
                # 网络错误，可重试
                last_error = LLMError(f"网络错误: {e}", self.__class__.__name__, is_retryable=True)
                logger.warning(f"LLM 网络错误: {e}，重试 {attempt + 1}/{self.max_retries}")
            except Exception as e:
                error_msg = str(e)
                # 判断是否可重试
                is_retryable = any(x in error_msg.lower() for x in ["rate", "limit", "timeout", "connection", "temporarily"])
                last_error = LLMError(error_msg, self.__class__.__name__, is_retryable=is_retryable)
                logger.warning(f"LLM 调用失败: {e}，重试 {attempt + 1}/{self.max_retries}")

            if attempt < self.max_retries:
                await asyncio.sleep(1 * (attempt + 1))  # 指数退避

        self._record_failure()
        raise last_error


class ClaudeClient(BaseLLMClient):
    """Claude 客户端"""

    def __init__(self):
        super().__init__()
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

        async def _call():
            return self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
                **kwargs
            )

        response = await self._call_with_retry(_call)
        text = response.content[0].text
        self._record_success()

        if response_model:
            return self._parse_json_response(text, response_model)
        return text

    async def batch_complete(
        self,
        prompts: list[str],
        **kwargs
    ) -> list[str]:
        """批量调用 Claude（并发执行）"""
        tasks = [self.complete(prompt, **kwargs) for prompt in prompts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [str(r) if isinstance(r, Exception) else r for r in results]


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

        async def _call():
            return await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                **kwargs
            )

        response = await self._call_with_retry(_call)
        text = response.choices[0].message.content
        self._record_success()

        if response_model:
            return self._parse_json_response(text, response_model)
        return text

    async def batch_complete(
        self,
        prompts: list[str],
        **kwargs
    ) -> list[str]:
        """批量调用 OpenAI（并发执行）"""
        tasks = [self.complete(prompt, **kwargs) for prompt in prompts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [str(r) if isinstance(r, Exception) else r for r in results]


class OllamaClient(BaseLLMClient):
    """Ollama 本地模型客户端"""

    def __init__(self):
        super().__init__()
        try:
            import openai
        except ImportError:
            raise ImportError("请安装 openai: pip install openai")

        self.client = openai.OpenAI(
            base_url=f"{settings.OLLAMA_BASE_URL}/v1",
            api_key="ollama"
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

        async def _call():
            return self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                **kwargs
            )

        response = await self._call_with_retry(_call)
        text = response.choices[0].message.content
        self._record_success()

        if response_model:
            return self._parse_json_response(text, response_model)
        return text

    async def batch_complete(
        self,
        prompts: list[str],
        **kwargs
    ) -> list[str]:
        """批量调用 Ollama（并发执行）"""
        tasks = [self.complete(prompt, **kwargs) for prompt in prompts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [str(r) if isinstance(r, Exception) else r for r in results]


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

        async def _call():
            return await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                **kwargs
            )

        response = await self._call_with_retry(_call)
        text = response.choices[0].message.content
        self._record_success()

        if response_model:
            return self._parse_json_response(text, response_model)
        return text

    async def batch_complete(
        self,
        prompts: list[str],
        **kwargs
    ) -> list[str]:
        """批量调用 SiliconFlow（并发执行）"""
        tasks = [self.complete(prompt, **kwargs) for prompt in prompts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [str(r) if isinstance(r, Exception) else r for r in results]


class DS2APIClient(BaseLLMClient):
    """ds2api 本地代理 - OpenAI 兼容"""

    def __init__(self):
        super().__init__()
        try:
            from openai import AsyncOpenAI
        except ImportError:
            logger.warning("openai package not installed, DS2APIClient unavailable")
            self.client = None
            return
        api_key = os.getenv("ZYAPI_API_KEY") or os.getenv("DS2API_API_KEY") or "dummy"
        base_url = os.getenv("DS2API_BASE_URL", "http://host.docker.internal:5001")
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=60.0)
        self._available = True

    @property
    def provider_name(self) -> str:
        return "DS2API"

    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        response_model: Optional[type[BaseModel]] = None,
    ) -> Union[str, BaseModel]:
        if not self.client:
            raise RuntimeError("openai package not installed")
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        _model = model or "deepseek-v4-flash"

        async def _call():
            return await self.client.chat.completions.create(
                model=_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        response = await self._call_with_retry(_call)
        text = response.choices[0].message.content
        logger.info(f"[DS2APIClient] raw (len={len(text)}): {text[:300]}")
        self._record_success()
        if response_model:
            return self._parse_json_response(text, response_model)
        return text
    """知遥 API (zyapi.tuluo.top) - OpenAI 兼容"""

    def __init__(self):
        super().__init__()
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError("请安装 openai: pip install openai")

        api_key = settings.ZYAPI_API_KEY or os.getenv("ZYAPI_API_KEY")
        if not api_key:
            raise ValueError("ZYAPI_API_KEY is required")

        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=settings.ZYAPI_BASE_URL
        )
        self.model = settings.ZYAPI_MODEL

    async def complete(
        self,
        prompt: str,
        response_model: Optional[Type[BaseModel]] = None,
        system: Optional[str] = None,
        **kwargs
    ) -> Any:
        """调用知遥 API 生成回复"""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        async def _call():
            return await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                **kwargs
            )

        response = await self._call_with_retry(_call)
        text = response.choices[0].message.content
        logger.info(f"[ZyAPIClient] raw (len={len(text)}): {text[:300]}")
        self._record_success()

        if response_model:
            try:
                return self._parse_json_response(text, response_model)
            except Exception as e:
                logger.error(f"[ZyAPIClient] parse error: {e}, text={text[:300]}")
                raise
        return text

    async def batch_complete(
        self,
        prompts: list[str],
        **kwargs
    ) -> list[str]:
        """批量调用知遥 API（并发执行）"""
        tasks = [self.complete(prompt, **kwargs) for prompt in prompts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [str(r) if isinstance(r, Exception) else r for r in results]


class NVIDIAAPIClient(BaseLLMClient):
    """NVIDIA NIM 免费模型 - 直连 https://integrate.api.nvidia.com"""

    def __init__(self):
        super().__init__()
        from openai import AsyncOpenAI
        self.model = getattr(settings, 'NVIDIA_MODEL', 'nvidia/llama-3.1-nemotron-70b-instruct')
        self.client = AsyncOpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=settings.NVIDIA_API_KEY,
            timeout=60.0,
            max_retries=2,
        )

    @property
    def is_available(self) -> bool:
        return bool(settings.NVIDIA_API_KEY)

    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        response_model: Type[BaseModel] | None = None,
        **kwargs
    ) -> str | BaseModel:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async def _call():
            return await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                **kwargs
            )

        response = await self._call_with_retry(_call)
        text = response.choices[0].message.content
        logger.info(f"[NVIDIA] raw (len={len(text)}): {text[:200]}")
        self._record_success()

        if response_model:
            try:
                return self._parse_json_response(text, response_model)
            except Exception as e:
                logger.error(f"[NVIDIA] parse error: {e}, text={text[:200]}")
                raise
        return text

    async def batch_complete(
        self,
        prompts: list[str],
        **kwargs
    ) -> list[str]:
        """批量补全（顺序执行）"""
        return [await self.complete(prompt, **kwargs) for prompt in prompts]


class RuleBasedFallbackClient(BaseLLMClient):
    """基于规则的降级客户端（LLM不可用时使用）"""

    def __init__(self):
        super().__init__()
        self._available = True  # 始终可用

    @property
    def is_available(self) -> bool:
        return True  # 规则引擎始终可用

    async def complete(
        self,
        prompt: str,
        response_model: Optional[Type[BaseModel]] = None,
        system: Optional[str] = None,
        **kwargs
    ) -> Any:
        """基于关键词规则的降级分析"""
        # 从prompt中提取关键信息
        title_match = prompt.find("标题:")
        if title_match != -1:
            title_end = prompt.find("\n", title_match)
            title = prompt[title_match + 3:title_end].strip() if title_end != -1 else ""

        # 简单的关键词匹配
        text = prompt.lower()

        if response_model:
            # 返回降级版本的response
            return self._rule_based_analysis(text, response_model)
        return "Rule-based analysis completed"

    def _rule_based_analysis(self, text: str, response_model: Type[BaseModel]) -> BaseModel:
        """基于关键词规则的分析"""
        # 简单的关键词映射
        keywords_positive = ["利好", "增加", "上涨", "突破", "增长", "扩张", "合作", "协议"]
        keywords_negative = ["利空", "减少", "下跌", "制裁", "封锁", "冲突", "战争", "减产", "禁止"]
        keywords_geopolitical = ["美国", "中国", "伊朗", "俄罗斯", "欧盟", "中东", "霍尔木兹"]
        keywords_commodity = ["原油", "石油", "黄金", "天然气", "煤炭", "粮食"]

        sentiment = 0.0
        if any(k in text for k in keywords_positive):
            sentiment = 0.5
        if any(k in text for k in keywords_negative):
            sentiment = -0.5

        # 返回一个最小化的响应
        class MinimalResult(BaseModel):
            event_type: str = "其他"
            core_entities: list = []
            sentiment: float = 0.0
            event_intensity: str = "中"
            summary: str = "基于规则的分析"
            direct_impacts: list = []

        return MinimalResult()

    async def batch_complete(
        self,
        prompts: list[str],
        **kwargs
    ) -> list[str]:
        """批量降级分析"""
        results = []
        for prompt in prompts:
            result = await self.complete(prompt, **kwargs)
            results.append(str(result))
        return results


def get_llm_client() -> BaseLLMClient:
    """获取 LLM 客户端"""
    provider = settings.LLM_PROVIDER.lower()

    clients = {
        "claude": ClaudeClient,
        "openai": OpenAIClient,
        "ollama": OllamaClient,
        "siliconflow": SiliconFlowClient,
        "ds2api": DS2APIClient,
        "nvidia": NVIDIAAPIClient,
    }

    if provider in clients:
        try:
            return clients[provider]()
        except (ValueError, ImportError) as e:
            logger.warning(f"无法创建 {provider} 客户端: {e}，使用降级模式")
            return RuleBasedFallbackClient()
    else:
        raise ValueError(f"不支持的 LLM provider: {provider}")


# 全局 LLM 客户端实例
_llm_client: Optional[BaseLLMClient] = None
_fallback_client: Optional[RuleBasedFallbackClient] = None


def get_llm() -> BaseLLMClient:
    """获取 LLM 客户端实例（单例）"""
    global _llm_client, _fallback_client

    if _llm_client is None:
        _llm_client = get_llm_client()

    # 如果主客户端不可用，尝试降级
    if not _llm_client.is_available:
        logger.warning(f"主 LLM 客户端不可用，切换到降级模式")
        if _fallback_client is None:
            _fallback_client = RuleBasedFallbackClient()
        return _fallback_client

    return _llm_client


def reset_llm_client():
    """重置 LLM 客户端（用于切换配置后）"""
    global _llm_client, _fallback_client
    _llm_client = None
    _fallback_client = None
