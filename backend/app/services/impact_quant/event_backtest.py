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

    def __init__(self, history_data_path: Optional[str] = None, auto_save: bool = True):
        self.history_data_path = Path(history_data_path) if history_data_path else HISTORY_DATA_PATH
        self.auto_save = auto_save
        self._events: List[Dict[str, Any]] = []
        self._load_history()
        self._new_events: List[Dict[str, Any]] = []  # 新增待保存事件

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

    def _save_history(self):
        """保存历史事件（追加新事件）"""
        if not self._new_events:
            return

        try:
            # 读取现有数据
            with open(self.history_data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 追加新事件
            data["events"].extend(self._new_events)

            # 保存
            with open(self.history_data_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"历史事件库已更新，追加 {len(self._new_events)} 条")
            self._new_events.clear()

        except Exception as e:
            logger.error(f"保存历史事件失败: {e}")

    def add_event(
        self,
        title: str,
        event_type: str,
        core_entities: List[str],
        sentiment: float,
        direct_impacts: List[Dict[str, Any]],
        transmission_chain: List[Dict[str, Any]],
        investment_signals: List[Dict[str, Any]],
        actual_outcome: str = "",
        win_rate: float = 0.5
    ):
        """
        添加新事件到历史库

        Args:
            title: 事件标题
            event_type: 事件类型
            core_entities: 核心实体
            sentiment: 情绪值
            direct_impacts: 直接影响列表
            transmission_chain: 传导链
            investment_signals: 投资信号
            actual_outcome: 实际结果
            win_rate: 胜率
        """
        event_id = f"evt_{len(self._events) + len(self._new_events) + 1:03d}"

        new_event = {
            "id": event_id,
            "title": title,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "event_type": event_type,
            "core_entities": core_entities,
            "sentiment": sentiment,
            "event_intensity": "中",
            "direct_impacts": direct_impacts,
            "transmission_chain": transmission_chain,
            "investment_signals": investment_signals,
            "actual_outcome": actual_outcome,
            "win_rate": win_rate,
            "source": "auto_learned"
        }

        self._new_events.append(new_event)

        if self.auto_save:
            self._save_history()

    def learn_from_analysis(
        self,
        event_title: str,
        event_type: str,
        core_entities: List[str],
        sentiment: float,
        direct_impacts: List[Dict],
        transmission_chain: List[Dict],
        signals: List[Dict]
    ):
        """
        从分析结果学习并添加到历史库

        Args:
            event_title: 事件标题
            event_type: 事件类型
            core_entities: 核心实体
            sentiment: 情绪值
            direct_impacts: 直接影响
            transmission_chain: 传导链
            signals: 投资信号
        """
        # 检查是否已存在相似事件（避免重复）
        existing_matches = self.find_similar_events(
            title=event_title,
            event_type=event_type,
            core_entities=core_entities,
            sentiment=sentiment
        )

        # 如果相似度太高，跳过（避免重复）
        if existing_matches and existing_matches[0].similarity_score > 0.85:
            logger.debug(f"跳过重复事件: {event_title}")
            return

        # 添加到历史库
        self.add_event(
            title=event_title,
            event_type=event_type,
            core_entities=core_entities,
            sentiment=sentiment,
            direct_impacts=direct_impacts,
            transmission_chain=transmission_chain,
            investment_signals=signals
        )

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

        # 关键词包容匹配 - 检查类型1的关键词是否出现在类型2中
        keywords = ["supply", "oil", "原油", "减产", "能源", "cut", "production"]
        for kw in keywords:
            if kw in type1 and kw in type2:
                return True

        # 类型映射
        type_groups = {
            "政策": ["政策", "货币", "财政", "监管", "interest", "rate", "加息", "降息"],
            "地缘政治": ["地缘政治", "战争", "冲突", "制裁", "geopolitical", "war"],
            "能源": ["能源", "原油", "天然气", "石油", "oil", "能源", "supply", "cut", "减产", "供给"],
            "灾难": ["灾难", "灾害", "事故", "disaster", "accident"],
            "经济数据": ["经济数据", "就业", "通胀", "GDP", "economic", "data"],
            "财报": ["财报", "业绩", "季报", "年报", "earnings", "report"],
            "供应冲击": ["供应冲击", "供给冲击", "supply_shock", "supply", "cut"],
        }

        for group_name, variants in type_groups.items():
            # 检查任一类型是否属于该组
            in_group1 = type1 in variants or any(type1.find(v) >= 0 for v in variants if len(v) > 2)
            in_group2 = type2 in variants or any(type2.find(v) >= 0 for v in variants if len(v) > 2)
            if in_group1 and in_group2:
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
            match.similarity_score > 0.4 and
            details["entity_overlap"] > 0.25 and
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

        if not similar_events or similar_events[0].similarity_score < 0.2:
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