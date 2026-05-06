"""
事件分析服务 - 核心业务逻辑
"""
import time
import hashlib
import json
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from .llm_client import get_llm
from .prompts import (
    format_event_analysis_prompt,
    format_chain_transmission_prompt,
    format_signal_generation_prompt,
)
from ..schemas.models import (
    FullAnalysisResult,
    EventAnalysisResult,
    TransmissionChainResult,
    TransmissionStep,
    StockSignal,
    SignalType,
    TransmissionRelationType,
    ImpactMagnitude,
    DirectImpact,
    InvestmentSignal,
)


class SignalList(BaseModel):
    """信号列表响应"""
    signals: list[StockSignal]


class EventAnalysisService:
    """事件分析服务"""

    def __init__(self):
        self.llm = get_llm()
        # 简单内存缓存
        self._cache = {}

    def _get_cache_key(self, title: str, content: str = "") -> str:
        """生成缓存键"""
        text = f"{title}|{content}"
        return hashlib.md5(text.encode()).hexdigest()

    def _load_from_cache(self, cache_key: str) -> Optional[FullAnalysisResult]:
        """从缓存加载"""
        if cache_key in self._cache:
            return FullAnalysisResult(**self._cache[cache_key])
        return None

    def _save_to_cache(self, cache_key: str, result: FullAnalysisResult):
        """保存到缓存"""
        self._cache[cache_key] = result.model_dump(mode='json')

    async def analyze(
        self,
        title: str,
        content: str = "",
        use_cache: bool = True
    ) -> FullAnalysisResult:
        """
        完整的事件分析流程

        流程:
        1. 事件理解 (LLM)
        2. 产业链传导 (LLM)
        3. 信号生成 (LLM)
        4. 结果整合
        """
        start_time = time.time()
        cache_key = self._get_cache_key(title, content)

        # 检查缓存
        if use_cache:
            cached = self._load_from_cache(cache_key)
            if cached:
                return cached

        print(f"[分析开始] {title[:50]}...")

        # Step 1: 事件理解
        event_analysis = await self._analyze_event(title, content)
        print(f"[Step 1 完成] 事件类型: {event_analysis.event_type}")

        # Step 2: 产业链传导
        transmission = await self._analyze_transmission(event_analysis)
        print(f"[Step 2 完成] 传导链长度: {len(transmission.transmission_chain)}")

        # Step 3: 信号生成
        signals = await self._generate_signals(event_analysis, transmission)
        print(f"[Step 3 完成] 生成信号数: {len(signals)}")

        # 整合结果
        processing_time = int((time.time() - start_time) * 1000)

        result = FullAnalysisResult(
            input_title=title,
            input_content=content,
            event_analysis=event_analysis,
            transmission=transmission,
            signals=signals,
            analysis_timestamp=datetime.now(),
            processing_time_ms=processing_time
        )

        # 保存缓存
        if use_cache:
            self._save_to_cache(cache_key, result)

        print(f"[分析完成] 耗时: {processing_time}ms")

        return result

    async def _analyze_event(
        self,
        title: str,
        content: str
    ) -> EventAnalysisResult:
        """事件理解"""
        prompt = format_event_analysis_prompt(title, content)

        result = await self.llm.complete(
            prompt=prompt,
            response_model=EventAnalysisResult
        )

        return result

    async def _analyze_transmission(
        self,
        event_analysis: EventAnalysisResult
    ) -> TransmissionChainResult:
        """产业链传导分析"""
        # 格式化直接影响的行业
        direct_impacts_str = "\n".join([
            f"- {impact.industry}: {impact.impact_direction.value} {impact.impact_magnitude.value}"
            for impact in event_analysis.direct_impacts
        ])

        prompt = format_chain_transmission_prompt(
            event_summary=event_analysis.summary,
            event_type=event_analysis.event_type.value,
            sentiment=event_analysis.sentiment,
            direct_impacts=direct_impacts_str
        )

        result = await self.llm.complete(
            prompt=prompt,
            response_model=TransmissionChainResult
        )

        return result

    async def _generate_signals(
        self,
        event_analysis: EventAnalysisResult,
        transmission: TransmissionChainResult
    ) -> list[StockSignal]:
        """生成交易信号"""
        # 格式化传导结果
        transmission_str = "\n".join([
            f"Step {step.step}: {step.from_industry} → {step.to_industry} "
            f"({step.relation_type.value}, {step.time_lag_days}天)"
            for step in transmission.transmission_chain[:5]
        ])

        signals_str = "\n".join([
            f"- {sig.industry}: {sig.signal} (置信度{sig.confidence}%)"
            for sig in transmission.investment_signals
        ])

        prompt = format_signal_generation_prompt(
            transmission_results=transmission_str,
            investment_signals=signals_str
        )

        result = await self.llm.complete(
            prompt=prompt,
            response_model=SignalList
        )

        return result.signals

    async def quick_analyze(self, title: str) -> dict:
        """快速分析（简化版）"""
        prompt = f"""分析这个金融事件: {title}

输出JSON: {{"summary": "总结", "affected_sectors": ["行业1", "行业2"], "investment_advice": "建议", "confidence": 70, "reasoning": "理由"}}
只输出JSON。"""

        return await self.llm.complete(prompt)


# 全局服务实例
_analysis_service: Optional[EventAnalysisService] = None


def get_analysis_service() -> EventAnalysisService:
    """获取分析服务实例"""
    global _analysis_service
    if _analysis_service is None:
        _analysis_service = EventAnalysisService()
    return _analysis_service
