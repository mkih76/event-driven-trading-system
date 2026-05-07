"""
事件分析服务 - 核心业务逻辑
"""
import time
import hashlib
import json
from typing import Optional, Tuple
from datetime import datetime
from pydantic import BaseModel
from fastapi import HTTPException, Header
from .llm_client import get_llm, LLMError, LLMUnavailableError, RuleBasedFallbackClient
from .prompts import (
    format_event_analysis_prompt,
    format_chain_transmission_prompt,
    format_signal_generation_prompt,
    format_rag_event_analysis_prompt,
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
from ..config import settings
from .causal_reasoning import get_industry_graph, get_dynamic_learner
from .impact_quant import get_backtest_engine, get_signal_store


class AnalysisDegradation(BaseModel):
    """降级状态信息"""
    is_degraded: bool = False
    reason: str = ""
    fallback_used: str = ""

    @property
    def message(self) -> str:
        if self.is_degraded:
            return f"当前使用规则模式，分析精度可能下降。({self.reason})"
        return ""


async def verify_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """
    验证 API Key 认证

    Args:
        x_api_key: 请求头中的 API Key

    Returns:
        验证通过返回 "verified"

    Raises:
        HTTPException: 认证失败
    """
    if not settings.API_AUTH_ENABLED:
        return "skip"

    if not settings.API_KEY:
        # 未配置 API Key，跳过认证（防止自己被锁）
        return "skip"

    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="需要 API Key。请在请求头中添加 X-API-Key"
        )

    if x_api_key != settings.API_KEY:
        raise HTTPException(
            status_code=403,
            detail="API Key 无效"
        )

    return "verified"


class SignalList(BaseModel):
    """信号列表响应"""
    signals: list[StockSignal]


class EventAnalysisService:
    """事件分析服务"""

    def __init__(self):
        self.llm = get_llm()
        # 简单内存缓存
        self._cache = {}
        self._degradation = AnalysisDegradation()

    @property
    def degradation(self) -> AnalysisDegradation:
        """获取当前降级状态"""
        return self._degradation

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
    ) -> Tuple[FullAnalysisResult, AnalysisDegradation]:
        """
        完整的事件分析流程

        流程:
        1. 事件理解 (LLM)
        2. 产业链传导 (LLM)
        3. 信号生成 (LLM)
        4. 结果整合

        返回: (result, degradation_info)
        """
        start_time = time.time()
        cache_key = self._get_cache_key(title, content)

        # 检查缓存
        if use_cache:
            cached = self._load_from_cache(cache_key)
            if cached:
                return cached, self._degradation

        print(f"[分析开始] {title[:50]}...")

        # 检查 LLM 可用性
        llm = get_llm()
        if isinstance(llm, RuleBasedFallbackClient):
            self._degradation = AnalysisDegradation(
                is_degraded=True,
                reason="LLM服务不可用",
                fallback_used="RuleBasedFallback"
            )
            print("[警告] LLM不可用，使用规则降级模式")
        else:
            self._degradation = AnalysisDegradation()

        # Step 1: 事件理解
        event_analysis = await self._analyze_event(title, content)
        print(f"[Step 1 完成] 事件类型: {event_analysis.event_type}")

        # Step 2: 产业链传导
        transmission = await self._analyze_transmission(event_analysis)
        print(f"[Step 2 完成] 传导链长度: {len(transmission.transmission_chain)}")

        # Step 3: 信号生成
        signals = await self._generate_signals(event_analysis, transmission)
        print(f"[Step 3 完成] 生成信号数: {len(signals)}")

        # Step 3.5: 历史回测 + 置信度调整
        backtest_eval = {}
        try:
            backtest_engine = get_backtest_engine()
            if signals and backtest_engine.event_count > 0:
                for signal in signals[:3]:  # 只对top3信号评估
                    eval_result = backtest_engine.evaluate_signal(
                        title=title,
                        event_type=event_analysis.event_type.value,
                        core_entities=event_analysis.core_entities,
                        sentiment=event_analysis.sentiment,
                        signal_confidence=signal.confidence
                    )
                    signal.confidence = eval_result.get("adjusted_confidence", signal.confidence)
                    signal.backtest_reference = eval_result  # 存储回测参考
                backtest_eval = {
                    "has_reference": len([s for s in signals if hasattr(s, 'backtest_reference') and s.backtest_reference.get("has_historical_reference")]) > 0,
                    "avg_confidence_adjustment": sum(
                        s.backtest_reference.get("confidence_change", 0)
                        for s in signals if hasattr(s, 'backtest_reference')
                    ) / min(len(signals), 3) if signals else 0
                }
                print(f"[Step 3.5 完成] 回测参考: {backtest_eval.get('has_reference')}, 置信度调整: {backtest_eval.get('avg_confidence_adjustment', 0):+.1f}")
        except Exception as e:
            print(f"[回测警告] 历史回测评估失败: {e}")

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

        # Step 4: 动态学习（从分析结果中学习新关系和模式）
        try:
            dynamic_learner = get_dynamic_learner()

            # 转换传导链为学习格式
            transmission_chain_data = [
                {
                    "from_industry": step.from_industry,
                    "to_industry": step.to_industry,
                    "relation_type": step.relation_type.value,
                    "time_lag_days": step.time_lag_days,
                    "transmission_rate": step.transmission_rate
                }
                for step in transmission.transmission_chain
            ]

            direct_impacts_data = [
                {
                    "industry": imp.industry,
                    "direction": imp.impact_direction.value,
                    "magnitude": imp.impact_magnitude.value
                }
                for imp in event_analysis.direct_impacts
            ]

            await dynamic_learner.learn_from_analysis(
                event_type=event_analysis.event_type.value,
                core_entities=event_analysis.core_entities,
                direct_impacts=direct_impacts_data,
                transmission_chain=transmission_chain_data,
                sentiment=event_analysis.sentiment
            )
            print(f"[动态学习] 关系数: {dynamic_learner.get_statistics()['total_relationships_learned']}, 模式数: {dynamic_learner.get_statistics()['total_patterns_learned']}")

            # 同时学习事件历史
            from .impact_quant import get_backtest_engine
            backtest_engine = get_backtest_engine()
            backtest_engine.learn_from_analysis(
                event_title=title,
                event_type=event_analysis.event_type.value,
                core_entities=event_analysis.core_entities,
                sentiment=event_analysis.sentiment,
                direct_impacts=direct_impacts_data,
                transmission_chain=transmission_chain_data,
                signals=[{"industry": sig.industry, "signal": sig.signal, "confidence": sig.confidence} for sig in signals]
            )
        except Exception as e:
            print(f"[动态学习] 学习失败: {e}")

        print(f"[分析完成] 耗时: {processing_time}ms")

        return result, self._degradation

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
        """产业链传导分析 - 集成知识图谱约束"""
        # 格式化直接影响的行业
        direct_impacts_str = "\n".join([
            f"- {impact.industry}: {impact.impact_direction.value} {impact.impact_magnitude.value}"
            for impact in event_analysis.direct_impacts
        ])

        # 获取知识图谱约束
        kg_constraints = ""
        try:
            kg = get_industry_graph()

            # 注入动态学习的关系
            dynamic_learner = get_dynamic_learner()
            dynamic_rels = dynamic_learner.get_dynamic_relationships(min_confidence=0.6)
            if dynamic_rels:
                kg.add_dynamic_relationships(dynamic_rels)

            # 从核心实体匹配图谱节点
            matched_nodes = kg.match_nodes(event_analysis.core_entities)

            if matched_nodes:
                # 获取传导路径骨架
                kg_constraints = kg.get_graph_constraints(matched_nodes, depth=3, max_paths=8)
                print(f"[知识图谱] 匹配节点: {matched_nodes}, 生成 {len(kg_constraints)} 字符约束")
        except Exception as e:
            print(f"[知识图谱] 获取约束失败: {e}")

        prompt = format_chain_transmission_prompt(
            event_summary=event_analysis.summary,
            event_type=event_analysis.event_type.value,
            sentiment=event_analysis.sentiment,
            direct_impacts=direct_impacts_str,
            kg_constraints=kg_constraints  # 注入图谱约束
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

    async def analyze_with_realtime(
        self,
        title: str,
        content: str = "",
        use_cache: bool = True,
        include_real_time: bool = True
    ) -> Tuple[FullAnalysisResult, AnalysisDegradation]:
        """
        RAG 增强的事件分析

        流程:
        1. 获取实时数据上下文 (RAG)
        2. 事件理解 (LLM + 实时数据)
        3. 产业链传导 (LLM)
        4. 信号生成 (LLM)
        5. 结果整合

        返回: (result, degradation_info)
        """
        start_time = time.time()
        cache_key = self._get_cache_key(title, content)

        # 检查缓存
        if use_cache:
            cached = self._load_from_cache(cache_key)
            if cached:
                return cached, self._degradation

        print(f"[RAG分析开始] {title[:50]}...")

        # 检查 LLM 可用性
        llm = get_llm()
        if isinstance(llm, RuleBasedFallbackClient):
            self._degradation = AnalysisDegradation(
                is_degraded=True,
                reason="LLM服务不可用",
                fallback_used="RuleBasedFallback"
            )
        else:
            self._degradation = AnalysisDegradation()

        # Step 0: 获取实时上下文 (传入事件类型以选择性注入)
        real_time_context = ""
        if include_real_time:
            try:
                from .rag_service import get_rag_service
                rag_service = get_rag_service()
                real_time_context = await rag_service.get_context_for_event(
                    title=title,
                    content=content,
                    event_type="其他"  # 先用默认，等事件分析后可以更新
                )
                print(f"[RAG获取] 实时上下文长度: {len(real_time_context)}")
            except Exception as e:
                print(f"[RAG警告] 获取实时数据失败: {e}")

        # Step 1: 事件理解 (RAG 增强)
        if real_time_context:
            event_analysis = await self._analyze_event_with_context(title, content, real_time_context)
        else:
            event_analysis = await self._analyze_event(title, content)

        print(f"[Step 1 完成] 事件类型: {event_analysis.event_type}")

        # 更新RAG上下文（根据事件类型重新获取更相关的上下文）
        if include_real_time and not real_time_context:
            try:
                rag_service = get_rag_service()
                real_time_context = await rag_service.get_context_for_event(
                    title=title,
                    content=content,
                    event_type=event_analysis.event_type.value
                )
            except Exception:
                pass

        # Step 2: 产业链传导
        transmission = await self._analyze_transmission(event_analysis)
        print(f"[Step 2 完成] 传导链长度: {len(transmission.transmission_chain)}")

        # Step 3: 信号生成
        signals = await self._generate_signals(event_analysis, transmission)
        print(f"[Step 3 完成] 生成信号数: {len(signals)}")

        # Step 3.5: 历史回测 + 置信度调整
        try:
            backtest_engine = get_backtest_engine()
            if signals and backtest_engine.event_count > 0:
                for signal in signals[:3]:
                    eval_result = backtest_engine.evaluate_signal(
                        title=title,
                        event_type=event_analysis.event_type.value,
                        core_entities=event_analysis.core_entities,
                        sentiment=event_analysis.sentiment,
                        signal_confidence=signal.confidence
                    )
                    signal.confidence = eval_result.get("adjusted_confidence", signal.confidence)
                    signal.backtest_reference = eval_result
                print(f"[Step 3.5 完成] 回测置信度调整已应用")
        except Exception as e:
            print(f"[回测警告] 历史回测评估失败: {e}")

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

        # Step 4: 动态学习（从分析结果中学习新关系和模式）
        try:
            dynamic_learner = get_dynamic_learner()

            transmission_chain_data = [
                {
                    "from_industry": step.from_industry,
                    "to_industry": step.to_industry,
                    "relation_type": step.relation_type.value,
                    "time_lag_days": step.time_lag_days,
                    "transmission_rate": step.transmission_rate
                }
                for step in transmission.transmission_chain
            ]

            direct_impacts_data = [
                {
                    "industry": imp.industry,
                    "direction": imp.impact_direction.value,
                    "magnitude": imp.impact_magnitude.value
                }
                for imp in event_analysis.direct_impacts
            ]

            await dynamic_learner.learn_from_analysis(
                event_type=event_analysis.event_type.value,
                core_entities=event_analysis.core_entities,
                direct_impacts=direct_impacts_data,
                transmission_chain=transmission_chain_data,
                sentiment=event_analysis.sentiment
            )
            print(f"[动态学习] 关系数: {dynamic_learner.get_statistics()['total_relationships_learned']}, 模式数: {dynamic_learner.get_statistics()['total_patterns_learned']}")

            # 同时学习事件历史
            from .impact_quant import get_backtest_engine
            backtest_engine = get_backtest_engine()
            backtest_engine.learn_from_analysis(
                event_title=title,
                event_type=event_analysis.event_type.value,
                core_entities=event_analysis.core_entities,
                sentiment=event_analysis.sentiment,
                direct_impacts=direct_impacts_data,
                transmission_chain=transmission_chain_data,
                signals=[{"industry": sig.industry, "signal": sig.signal, "confidence": sig.confidence} for sig in signals]
            )
        except Exception as e:
            print(f"[动态学习] 学习失败: {e}")

        print(f"[分析完成] 耗时: {processing_time}ms, RAG启用: {bool(real_time_context)}")

        return result, self._degradation

    async def _analyze_event_with_context(
        self,
        title: str,
        content: str,
        real_time_context: str
    ) -> EventAnalysisResult:
        """带实时上下文的事件理解"""
        prompt = format_rag_event_analysis_prompt(title, content, real_time_context)

        result = await self.llm.complete(
            prompt=prompt,
            response_model=EventAnalysisResult
        )

        return result


# 全局服务实例
_analysis_service: Optional[EventAnalysisService] = None


def get_analysis_service() -> EventAnalysisService:
    """获取分析服务实例"""
    global _analysis_service
    if _analysis_service is None:
        _analysis_service = EventAnalysisService()
    return _analysis_service
