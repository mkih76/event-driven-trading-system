"""
LLM 因果传导增强模块
使用 LLM 推理增强知识图谱路径，评估传导方向、置信度、强度
"""
import logging
import hashlib
import json
import time
from typing import Optional, List, Dict, Tuple
from pydantic import BaseModel, Field
from ..llm_client import get_llm, RuleBasedFallbackClient
from ..analysis import EventAnalysisResult, TransmissionChainResult
from ..config import settings

logger = logging.getLogger(__name__)


class CausalPathScore(BaseModel):
    """因果路径评分"""
    path_id: int
    from_industry: str
    to_industry: str
    direction: str = Field(description="positive/negative/neutral")
    confidence: float = Field(ge=0.0, le=1.0, description="置信度 0-1")
    intensity_score: float = Field(ge=-10.0, le=10.0, description="影响分数 -10 到 +10")
    reasoning: str = Field(description="评分理由")
    cross_sector: bool = Field(default=False, description="是否跨行业传导")


class CrossSectorEffect(BaseModel):
    """跨行业效应"""
    source_industry: str
    target_sector: str
    effect_type: str = Field(description="risk_appetite/flight_to_safety/market_sentiment")
    description: str


class EnhancedTransmission(BaseModel):
    """增强后的传导结果"""
    original_chain: List[dict]
    enhanced_scores: List[CausalPathScore]
    cross_sector_effects: List[CrossSectorEffect] = Field(default_factory=list)
    total_impact_assessment: str = Field(description="总体影响评估")
    confidence: float = Field(ge=0.0, le=1.0)


LLM_REASONING_PROMPT = """# 角色
你是顶级产业经济学家，精通全球供应链传导机制和金融市场。

# 任务
给定一个事件和产业链传导路径，使用 LLM 推理评估每个传导路径的影响方向、置信度和强度。

# 输入信息
事件摘要: {event_summary}
事件类型: {event_type}
情绪: {sentiment}

传导路径:
{chain_paths}

# 评估标准
对于每条传导路径，评估:
1. **方向**: positive(利好), negative(利空), neutral(中性)
2. **置信度**: 0.0-1.0，考虑历史数据和逻辑清晰度
3. **强度**: -10到+10，考虑影响幅度和持续时间
4. **跨行业**: 是否存在跨行业间接效应（如风险偏好）

# 输出 JSON 格式
{{
    "enhanced_scores": [
        {{
            "path_id": 1,
            "from_industry": "原油",
            "to_industry": "化工",
            "direction": "positive/negative/neutral",
            "confidence": 0.0-1.0,
            "intensity_score": -10到+10,
            "reasoning": "评分理由",
            "cross_sector": false
        }}
    ],
    "cross_sector_effects": [
        {{
            "source_industry": "原油",
            "target_sector": "金融市场",
            "effect_type": "risk_appetite/flight_to_safety",
            "description": "原油上涨导致避险情绪上升"
        }}
    ],
    "total_impact_assessment": "总体影响评估描述",
    "confidence": 0.0-1.0
}}

# 要求
1. 只输出 JSON，不要解释
2. 为每条路径给出评分
3. 如果有跨行业效应，单独列出
4. 置信度不要全是 1.0，应该有合理分布
"""


class LLMReasoner:
    """LLM 因果传导推理器（带缓存和 token 限制）"""

    def __init__(self):
        self._initialized = False
        self._cache: Dict[str, Tuple[EnhancedTransmission, float]] = {}  # key -> (result, timestamp)

    async def initialize(self):
        """初始化"""
        if self._initialized:
            return
        self._initialized = True
        logger.info("LLMReasoner 初始化完成，缓存 TTL: %d 秒", settings.LLM_CACHE_TTL)

    def _format_chain_paths(self, transmission: TransmissionChainResult) -> str:
        """格式化传导路径为字符串，并限制长度以减少 token"""
        paths = []
        max_steps = 10  # 只保留前10个最相关的传导步骤（按 step 顺序，通常步数越前越重要）
        for i, step in enumerate(transmission.transmission_chain):
            if i >= max_steps:
                paths.append(f"... 以及后续 {len(transmission.transmission_chain) - max_steps} 个传导步骤（已截断）")
                break
            paths.append(
                f"Step {i+1}: {step.from_industry} → {step.to_industry} "
                f"({step.relation_type.value}, 传导率{step.transmission_rate:.0%}, "
                f"滞后{step.time_lag_days}天)"
            )
        return "\n".join(paths)

    def _get_cache_key(self, event_analysis: EventAnalysisResult, transmission: TransmissionChainResult) -> str:
        """生成缓存键（基于事件摘要、类型、情绪和传导路径的哈希）"""
        # 只使用稳定的字段：事件摘要、事件类型、情绪值、传导路径的摘要
        chain_summary = "|".join([
            f"{s.from_industry}->{s.to_industry}:{s.relation_type.value}:{s.transmission_rate}"
            for s in transmission.transmission_chain[:10]  # 前10步足够区分
        ])
        content = f"{event_analysis.summary}|{event_analysis.event_type.value}|{event_analysis.sentiment}|{chain_summary}"
        return hashlib.md5(content.encode()).hexdigest()

    async def enhance_transmission(
        self,
        event_analysis: EventAnalysisResult,
        transmission: TransmissionChainResult
    ) -> EnhancedTransmission:
        """
        使用 LLM 增强传导分析（带缓存）

        Args:
            event_analysis: 事件分析结果
            transmission: 基础传导链结果

        Returns:
            增强后的传导结果
        """
        await self.initialize()

        # 检查缓存
        cache_key = self._get_cache_key(event_analysis, transmission)
        now = time.time()
        if cache_key in self._cache:
            result, timestamp = self._cache[cache_key]
            if now - timestamp < settings.LLM_CACHE_TTL:
                logger.info(f"使用缓存的 LLM 增强结果，key={cache_key[:8]}...")
                return result
            else:
                del self._cache[cache_key]

        chain_paths = self._format_chain_paths(transmission)
        # 额外截断 prompt 防止过长（保留前 2000 字符）
        if len(chain_paths) > 2000:
            chain_paths = chain_paths[:2000] + "\n... (已截断)"

        prompt = LLM_REASONING_PROMPT.format(
            event_summary=event_analysis.summary,
            event_type=event_analysis.event_type.value,
            sentiment=event_analysis.sentiment,
            chain_paths=chain_paths
        )

        try:
            llm = get_llm()
            if isinstance(llm, RuleBasedFallbackClient):
                result = self._fallback_enhance(transmission)
                # 降级结果也缓存较短时间（10分钟）
                self._cache[cache_key] = (result, now)
                return result

            result = await llm.complete(prompt=prompt, response_model=EnhancedTransmission)
            # 缓存成功结果
            self._cache[cache_key] = (result, now)
            logger.info(f"LLM 增强完成并已缓存，key={cache_key[:8]}...")
            return result

        except Exception as e:
            logger.warning(f"LLM 增强失败: {e}，使用降级模式")
            result = self._fallback_enhance(transmission)
            # 错误降级也缓存较短时间（5分钟）
            self._cache[cache_key] = (result, now)
            return result

    def _fallback_enhance(
        self,
        transmission: TransmissionChainResult
    ) -> EnhancedTransmission:
        """降级增强：基于规则评分"""
        original_chain = [
            {
                "step": s.step,
                "from_industry": s.from_industry,
                "to_industry": s.to_industry,
                "relation_type": s.relation_type.value,
                "transmission_rate": s.transmission_rate,
                "time_lag_days": s.time_lag_days
            }
            for s in transmission.transmission_chain
        ]

        enhanced_scores = []
        for i, step in enumerate(transmission.transmission_chain):
            direction = "positive" if step.impact_score > 0 else "negative" if step.impact_score < 0 else "neutral"

            enhanced_scores.append(CausalPathScore(
                path_id=i + 1,
                from_industry=step.from_industry,
                to_industry=step.to_industry,
                direction=direction,
                confidence=0.5 + step.transmission_rate * 0.3,
                intensity_score=step.impact_score * 0.8,
                reasoning=f"基于规则降级评估，传导率{step.transmission_rate:.0%}",
                cross_sector=False
            ))

        return EnhancedTransmission(
            original_chain=original_chain,
            enhanced_scores=enhanced_scores,
            cross_sector_effects=[],
            total_impact_assessment="基于规则的降级评估，LLM不可用",
            confidence=0.5
        )


# 全局实例
_llm_reasoner: Optional[LLMReasoner] = None


def get_llm_reasoner() -> LLMReasoner:
    """获取 LLMReasoner 实例"""
    global _llm_reasoner
    if _llm_reasoner is None:
        _llm_reasoner = LLMReasoner()
    return _llm_reasoner