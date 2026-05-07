"""
LLM 信号解释模块
将交易信号转换为自然语言市场评论
"""
import logging
from typing import List, Optional
from pydantic import BaseModel, Field
from ..llm_client import get_llm, RuleBasedFallbackClient
from ..schemas.models import StockSignal

logger = logging.getLogger(__name__)


class MarketCommentary(BaseModel):
    """市场评论"""
    summary: str = Field(description="总体概述")
    signal_overview: str = Field(description="信号概览")
    key_themes: List[str] = Field(default_factory=list, description="关键主题")
    risk_warnings: List[str] = Field(default_factory=list, description="风险提示")
    market_sentiment: str = Field(description="市场情绪解读")


COMMENTARY_PROMPT = """# 角色
你是资深金融市场评论员，擅长将量化分析结果转化为通俗易懂的市场评论。

# 输入信息
事件摘要: {event_summary}

交易信号:
{signals}

# 任务
请根据交易信号，生成一段专业的市场评论。

# 评论要求
1. 语言流畅专业，适合机构投资者阅读
2. 突出关键机会和风险
3. 解释传导逻辑（非仅罗列信号）
4. 适当引用数据支持（如有）

# 输出 JSON 格式
{{
    "summary": "一段话概括整体机会与风险",
    "signal_overview": "信号概览，说明多少做多/做空/观望",
    "key_themes": ["主题1", "主题2", "主题3"],
    "risk_warnings": ["风险提示1", "风险提示2"],
    "market_sentiment": "市场情绪解读"
}}

# 要求
只输出 JSON，不要其他解释。
"""


class LLMExplainer:
    """LLM 信号解释器"""

    def __init__(self):
        self._initialized = False

    async def initialize(self):
        """初始化"""
        if self._initialized:
            return
        self._initialized = True
        logger.info("LLMExplainer 初始化完成")

    def _format_signals(self, signals: List[StockSignal]) -> str:
        """格式化信号列表"""
        signal_strs = []
        for i, sig in enumerate(signals):
            direction = "做多" if sig.signal_type.value in ["BUY", "做多", "LONG"] else \
                        "做空" if sig.signal_type.value in ["SELL", "做空", "SHORT"] else "观望"
            signal_strs.append(
                f"{i+1}. {sig.stock_name}({sig.stock_code}): {direction}, "
                f"置信度{sig.confidence}%, 影响分{sig.impact_score}"
            )
        return "\n".join(signal_strs)

    async def generate_commentary(
        self,
        signals: List[StockSignal],
        event_summary: str = ""
    ) -> MarketCommentary:
        """
        生成市场评论

        Args:
            signals: 交易信号列表
            event_summary: 事件摘要

        Returns:
            市场评论
        """
        await self.initialize()

        if not signals:
            return self._fallback_commentary("暂无交易信号")

        signal_str = self._format_signals(signals)

        prompt = COMMENTARY_PROMPT.format(
            event_summary=event_summary or "市场事件分析",
            signals=signal_str
        )

        try:
            llm = get_llm()
            if isinstance(llm, RuleBasedFallbackClient):
                return self._fallback_commentary(event_summary, signals)

            result = await llm.complete(prompt=prompt, response_model=MarketCommentary)
            return result

        except Exception as e:
            logger.warning(f"LLM 评论生成失败: {e}，使用降级模式")
            return self._fallback_commentary(event_summary, signals)

    def _fallback_commentary(
        self,
        event_summary: str,
        signals: Optional[List[StockSignal]] = None
    ) -> MarketCommentary:
        """降级评论生成"""
        if not signals:
            return MarketCommentary(
                summary="当前无有效交易信号",
                signal_overview="观望",
                key_themes=[],
                risk_warnings=["市场方向不明确，建议观望"],
                market_sentiment="中性"
            )

        buy_signals = [s for s in signals if s.signal_type.value in ["BUY", "做多", "LONG"]]
        sell_signals = [s for s in signals if s.signal_type.value in ["SELL", "做空", "SHORT"]]

        total = len(signals)
        buy_count = len(buy_signals)
        sell_count = len(sell_signals)

        return MarketCommentary(
            summary=f"基于分析，生成了 {buy_count} 个做多信号和 {sell_count} 个做空信号，"
                    f"建议关注产业链传导机会。",
            signal_overview=f"做多信号: {buy_count} 个，做空信号: {sell_count} 个，"
                           f"做多标的: {', '.join([s.stock_name for s in buy_signals[:3]])}",
            key_themes=[
                f"传导深度 {max([s.chain_depth for s in signals]) if signals else 0} 层",
                f"最高置信度 {max([s.confidence for s in signals]) if signals else 0}%"
            ],
            risk_warnings=[
                "传导存在不确定性，请控制仓位",
                "注意市场情绪变化风险"
            ],
            market_sentiment="震荡偏多" if buy_count > sell_count else "震荡偏空" if sell_count > buy_count else "中性"
        )


# 全局实例
_llm_explainer: Optional[LLMExplainer] = None


def get_llm_explainer() -> LLMExplainer:
    """获取 LLMExplainer 实例"""
    global _llm_explainer
    if _llm_explainer is None:
        _llm_explainer = LLMExplainer()
    return _llm_explainer