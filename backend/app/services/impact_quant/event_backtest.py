"""
事件回测引擎 - 基于历史事件匹配当前事件并评估信号质量
"""
import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from difflib import SequenceMatcher
import re

logger = logging.getLogger(__name__)

# 历史事件数据路径
HISTORY_DATA_PATH = Path(__file__).parent / "event_history.json"


@dataclass
class BacktestResult:
    """回测结果"""
    historical_event_id: str
    title_similarity: float
    event_type_match: bool
    entity_overlap: float
    sentiment_similarity: float
    combined_score: float
    is_reliable: bool
    matched_factors: List[str]
    unmatched_factors: List[str]
    historical_win_rate: float
    expected_signal_direction: str
    confidence_adjustment: float


@dataclass
class EventMatch:
    """事件匹配结果"""
    historical_event: Dict[str, Any]
    similarity_score: float
    match_details: Dict[str, Any]
    backtest_result: Optional[BacktestResult] = None


class EventBacktestEngine:
    """事件回测引擎 - 基于历史事件库进行模式匹配和信号验证"""

    def __init__(self, history_data_path: Optional[str] = None):
        self.history_data_path = Path(history_data_path) if history_data_path else HISTORY_DATA_PATH
        self._events: List[Dict[str, Any]] = []
        self._load_history()

    def _load_history(self):
        """加载历史事件数据"""
        try:
            with open(self.history_data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._events = data.get("events", [])
            logger.info(f"历史事件库加载完成: {len(self._events)} 条记录")
        except Exception as e:
            logger.error(f"加载历史事件失败: {e}")
            self._events = []

    @property
    def event_count(self) -> int:
        """历史事件数量"""
        return len(self._events)

    def calculate_title_similarity(self, title1: str, title2: str) -> float:
        """
        计算标题相似度

        Args:
            title1: 待匹配标题
            title2: 历史标题

        Returns:
            相似度分数 0-1
        """
        # 移除标点符号和多余空格
        t1 = re.sub(r'[^\w\u4e00-\u9fff]+', '', title1.lower())
        t2 = re.sub(r'[^\w\u4e00-\u9fff]+', '', title2.lower())

        # 序列匹配
        ratio = SequenceMatcher(None, t1, t2).ratio()

        # 关键词匹配
        keywords1 = set(self._extract_keywords(title1))
        keywords2 = set(self._extract_keywords(title2))

        if keywords1 and keywords2:
            keyword_overlap = len(keywords1 & keywords2) / len(keywords1 | keywords2)
        else:
            keyword_overlap = 0

        # 加权组合
        return ratio * 0.4 + keyword_overlap * 0.6

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 中英文混合关键词提取
        keywords = []

        # 英文关键词
        english_words = re.findall(r'[a-zA-Z]{3,}', text)
        keywords.extend([w.lower() for w in english_words])

        # 中文关键词 (2-4字)
        chinese_words = re.findall(r'[\u4e00-\u9fff]{2,4}', text)
        keywords.extend(chinese_words)

        return keywords

    def match_event_type(self, type1: str, type2: str) -> bool:
        """
        判断事件类型是否匹配

        Args:
            type1: 待匹配类型
            type2: 历史类型

        Returns:
            是否匹配
        """
        type1 = type1.lower().strip()
        type2 = type2.lower().strip()

        # 完全匹配
        if type1 == type2:
            return True

        # 类型映射
        type_groups = {
            "政策": ["政策", "货币", "财政", "监管"],
            "地缘政治": ["地缘政治", "战争", "冲突", "制裁"],
            "能源": ["能源", "原油", "天然气", "石油"],
            "灾难": ["灾难", "灾害", "事故"],
            "经济数据": ["经济数据", "就业", "通胀", "GDP"],
            "财报": ["财报", "业绩", "季报", "年报"],
        }

        for group_name, variants in type_groups.items():
            if type1 in variants or type2 in variants:
                if type1 in variants and type2 in variants:
                    return True

        return False

    def calculate_entity_overlap(self, entities1: List[str], entities2: List[str]) -> float:
        """
        计算实体重叠度

        Args:
            entities1: 待匹配实体列表
            entities2: 历史实体列表

        Returns:
            重叠度分数 0-1
        """
        if not entities1 or not entities2:
            return 0.0

        entities1_lower = [e.lower() for e in entities1]
        entities2_lower = [e.lower() for e in entities2]

        overlap_count = 0
        for e1 in entities1_lower:
            for e2 in entities2_lower:
                if e1 in e2 or e2 in e1 or e1 == e2:
                    overlap_count += 1
                    break

        # 使用 Jaccard 系数
        return overlap_count / len(set(entities1_lower) | set(entities2_lower))

    def calculate_sentiment_similarity(self, sentiment1: float, sentiment2: float) -> float:
        """
        计算情绪相似度

        Args:
            sentiment1: 待匹配情绪 (-1 到 1)
            sentiment2: 历史情绪 (-1 到 1)

        Returns:
            相似度分数 0-1
        """
        # 方向必须一致
        if (sentiment1 > 0) != (sentiment2 > 0):
            return 0.3  # 方向相反，大幅降低

        # 强度相似度
        diff = abs(sentiment1 - sentiment2)
        return max(0, 1 - diff / 2)  # 最大差距为2时，相似度为0

    def find_similar_events(
        self,
        title: str,
        event_type: str,
        core_entities: List[str],
        sentiment: float,
        top_k: int = 3
    ) -> List[EventMatch]:
        """
        查找相似历史事件

        Args:
            title: 事件标题
            event_type: 事件类型
            core_entities: 核心实体
            sentiment: 情绪值
            top_k: 返回前k个匹配结果

        Returns:
            匹配结果列表，按相似度排序
        """
        matches = []

        for event in self._events:
            # 计算各维度相似度
            title_sim = self.calculate_title_similarity(title, event.get("title", ""))
            type_match = self.match_event_type(event_type, event.get("event_type", ""))
            entity_overlap = self.calculate_entity_overlap(core_entities, event.get("core_entities", []))
            sentiment_sim = self.calculate_sentiment_similarity(sentiment, event.get("sentiment", 0))

            # 综合评分 (加权平均)
            combined_score = (
                title_sim * 0.25 +
                (1.0 if type_match else 0.0) * 0.20 +
                entity_overlap * 0.30 +
                sentiment_sim * 0.25
            )

            # 类型不匹配时大幅降低分数
            if not type_match:
                combined_score *= 0.5

            match_details = {
                "title_similarity": title_sim,
                "type_match": type_match,
                "entity_overlap": entity_overlap,
                "sentiment_similarity": sentiment_sim,
            }

            matches.append(EventMatch(
                historical_event=event,
                similarity_score=combined_score,
                match_details=match_details
            ))

        # 排序并返回top_k
        matches.sort(key=lambda x: x.similarity_score, reverse=True)
        return matches[:top_k]

    def get_backtest_result(self, match: EventMatch) -> BacktestResult:
        """
        根据匹配结果生成回测评估

        Args:
            match: 事件匹配结果

        Returns:
            回测结果
        """
        event = match.historical_event
        details = match.match_details

        # 统计匹配因素
        matched_factors = []
        unmatched_factors = []

        if details["title_similarity"] > 0.6:
            matched_factors.append("标题相似")
        else:
            unmatched_factors.append("标题差异大")

        if details["type_match"]:
            matched_factors.append("类型一致")
        else:
            unmatched_factors.append("类型不同")

        if details["entity_overlap"] > 0.4:
            matched_factors.append("实体重叠")
        else:
            unmatched_factors.append("实体差异大")

        if details["sentiment_similarity"] > 0.6:
            matched_factors.append("情绪方向一致")
        else:
            unmatched_factors.append("情绪方向相反")

        # 置信度调整
        confidence_adjustment = 0.0
        if match.similarity_score > 0.8:
            confidence_adjustment = 10.0  # 高相似度增加置信度
        elif match.similarity_score > 0.6:
            confidence_adjustment = 5.0
        elif match.similarity_score > 0.4:
            confidence_adjustment = 0.0  # 中等相似度不调整
        else:
            confidence_adjustment = -10.0  # 低相似度降低置信度

        # 判断是否可靠
        is_reliable = (
            match.similarity_score > 0.5 and
            details["entity_overlap"] > 0.3 and
            details["type_match"]
        )

        # 获取历史胜率
        historical_win_rate = event.get("win_rate", 0.5)

        # 预期信号方向
        signals = event.get("investment_signals", [])
        if signals:
            expected_direction = signals[0].get("signal", "做多")
        else:
            expected_direction = "未知"

        return BacktestResult(
            historical_event_id=event.get("id", ""),
            title_similarity=details["title_similarity"],
            event_type_match=details["type_match"],
            entity_overlap=details["entity_overlap"],
            sentiment_similarity=details["sentiment_similarity"],
            combined_score=match.similarity_score,
            is_reliable=is_reliable,
            matched_factors=matched_factors,
            unmatched_factors=unmatched_factors,
            historical_win_rate=historical_win_rate,
            expected_signal_direction=expected_direction,
            confidence_adjustment=confidence_adjustment
        )

    def evaluate_signal(
        self,
        title: str,
        event_type: str,
        core_entities: List[str],
        sentiment: float,
        signal_confidence: float
    ) -> Dict[str, Any]:
        """
        评估交易信号 - 结合历史回测

        Args:
            title: 事件标题
            event_type: 事件类型
            core_entities: 核心实体
            sentiment: 情绪值
            signal_confidence: 原始信号置信度

        Returns:
            评估结果，包含调整后的置信度和回测依据
        """
        # 查找相似事件
        similar_events = self.find_similar_events(
            title=title,
            event_type=event_type,
            core_entities=core_entities,
            sentiment=sentiment
        )

        if not similar_events or similar_events[0].similarity_score < 0.3:
            return {
                "has_historical_reference": False,
                "adjusted_confidence": signal_confidence,
                "reference_count": 0,
                "evaluation": "无相似历史事件，无法进行回测验证",
                "recommendation": "依赖当前分析，保持谨慎"
            }

        # 使用最佳匹配
        best_match = similar_events[0]
        backtest_result = self.get_backtest_result(best_match)

        # 调整置信度
        adjusted_confidence = min(100, max(0,
            signal_confidence + backtest_result.confidence_adjustment
        ))

        # 历史胜率加权调整
        if backtest_result.is_reliable:
            historical_factor = backtest_result.historical_win_rate
            adjusted_confidence = adjusted_confidence * 0.7 + historical_factor * 30

        return {
            "has_historical_reference": True,
            "best_match": {
                "event_id": best_match.historical_event.get("id"),
                "title": best_match.historical_event.get("title"),
                "date": best_match.historical_event.get("date"),
                "similarity_score": round(best_match.similarity_score, 2)
            },
            "adjusted_confidence": round(adjusted_confidence, 1),
            "original_confidence": signal_confidence,
            "confidence_change": round(adjusted_confidence - signal_confidence, 1),
            "historical_win_rate": round(backtest_result.historical_win_rate, 2),
            "backtest_evaluation": {
                "is_reliable": backtest_result.is_reliable,
                "expected_signal": backtest_result.expected_signal_direction,
                "matched_factors": backtest_result.matched_factors,
                "unmatched_factors": backtest_result.unmatched_factors,
                "actual_outcome": best_match.historical_event.get("actual_outcome", "")
            },
            "recommendation": self._generate_recommendation(backtest_result, adjusted_confidence),
            "similar_events_count": len(similar_events)
        }

    def _generate_recommendation(
        self,
        backtest_result: BacktestResult,
        adjusted_confidence: float
    ) -> str:
        """生成信号建议"""
        if not backtest_result.is_reliable:
            return "历史匹配度较低，建议谨慎操作，降低仓位"

        if adjusted_confidence >= 80:
            return "历史回测支持度高，信号较强，可适当增加仓位"
        elif adjusted_confidence >= 60:
            return "历史参考正面，可以参与但需设置止损"
        else:
            return "历史参考有限，建议轻仓试探"

    def get_statistics(self) -> Dict[str, Any]:
        """获取回测引擎统计信息"""
        if not self._events:
            return {"total_events": 0}

        win_rates = [e.get("win_rate", 0.5) for e in self._events]
        avg_win_rate = sum(win_rates) / len(win_rates)

        type_counts = {}
        for e in self._events:
            t = e.get("event_type", "其他")
            type_counts[t] = type_counts.get(t, 0) + 1

        return {
            "total_events": len(self._events),
            "average_win_rate": round(avg_win_rate, 2),
            "events_by_type": type_counts,
            "high_confidence_events": sum(1 for e in self._events if e.get("win_rate", 0) >= 0.8)
        }


# 全局实例
_backtest_engine: Optional[EventBacktestEngine] = None


def get_backtest_engine() -> EventBacktestEngine:
    """获取回测引擎实例"""
    global _backtest_engine
    if _backtest_engine is None:
        _backtest_engine = EventBacktestEngine()
    return _backtest_engine