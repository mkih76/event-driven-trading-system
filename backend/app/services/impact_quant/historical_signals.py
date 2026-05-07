"""
历史信号库 - 存储和管理历史事件产生的交易信号及其实际表现
"""
import json
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)

# 历史信号数据路径
SIGNALS_DATA_PATH = Path(__file__).parent / "historical_signals.json"


class SignalStatus(Enum):
    """信号状态"""
    PENDING = "pending"        # 待验证
    WIN = "win"               # 盈利
    LOSS = "loss"             # 亏损
    NEUTRAL = "neutral"       # 中性


class SignalType(Enum):
    """信号类型"""
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class HistoricalSignal:
    """历史信号"""
    # 基础信息
    signal_id: str
    event_id: str
    event_title: str
    stock_code: str
    stock_name: str
    signal_type: str  # BUY/SELL

    # 信号质量
    confidence: float          # 置信度 0-100
    impact_score: float        # 影响分数 -100 to 100
    chain_depth: int           # 传导深度 1-5

    # 信号依据
    entry_rationale: str      # 入场理由
    risk_factors: List[str]    # 风险因素

    # 关联股票
    related_stocks: List[str]  # 相关股票

    # 时间信息
    generated_at: str          # 生成时间
    event_date: str            # 事件日期

    # 回测结果
    actual_entry_price: float = 0.0     # 实际入场价格
    actual_exit_price: float = 0.0     # 实际出场价格
    actual_return: float = 0.0          # 实际收益率
    holding_days: int = 0               # 持仓天数

    # 评估结果
    status: str = "pending"             # pending/win/loss/neutral
    win_rate: float = 0.5               # 历史胜率

    @property
    def signal_type_enum(self) -> SignalType:
        return SignalType.BUY if self.signal_type == "BUY" else SignalType.SELL


@dataclass
class SignalStatistics:
    """信号统计"""
    total_signals: int
    win_signals: int
    loss_signals: int
    neutral_signals: int
    pending_signals: int
    win_rate: float
    avg_return: float
    best_signal: Dict[str, Any]
    worst_signal: Dict[str, Any]
    signals_by_depth: Dict[int, Dict[str, int]]
    signals_by_confidence_range: Dict[str, Dict[str, int]]


class HistoricalSignalStore:
    """历史信号库"""

    def __init__(self, data_path: Optional[str] = None):
        self.data_path = Path(data_path) if data_path else SIGNALS_DATA_PATH
        self._signals: List[HistoricalSignal] = []
        self._load_signals()

    def _load_signals(self):
        """加载历史信号"""
        try:
            if self.data_path.exists():
                with open(self.data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._signals = [
                        HistoricalSignal(**s) for s in data.get("signals", [])
                    ]
                logger.info(f"历史信号加载完成: {len(self._signals)} 条")
            else:
                self._signals = []
                logger.info("历史信号库为空，创建新库")
        except Exception as e:
            logger.error(f"加载历史信号失败: {e}")
            self._signals = []

    def _save_signals(self):
        """保存历史信号"""
        try:
            data = {
                "signals": [asdict(s) for s in self._signals],
                "last_updated": datetime.now().isoformat()
            }
            with open(self.data_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"历史信号保存完成: {len(self._signals)} 条")
        except Exception as e:
            logger.error(f"保存历史信号失败: {e}")

    def add_signal(
        self,
        signal_id: str,
        event_id: str,
        event_title: str,
        stock_code: str,
        stock_name: str,
        signal_type: str,
        confidence: float,
        impact_score: float,
        chain_depth: int,
        entry_rationale: str,
        risk_factors: List[str],
        related_stocks: List[str],
        event_date: str
    ) -> HistoricalSignal:
        """
        添加新信号

        Args:
            signal_id: 信号ID
            event_id: 事件ID
            event_title: 事件标题
            stock_code: 股票代码
            stock_name: 股票名称
            signal_type: BUY/SELL
            confidence: 置信度
            impact_score: 影响分数
            chain_depth: 传导深度
            entry_rationale: 入场理由
            risk_factors: 风险因素
            related_stocks: 相关股票
            event_date: 事件日期

        Returns:
            创建的信号对象
        """
        signal = HistoricalSignal(
            signal_id=signal_id,
            event_id=event_id,
            event_title=event_title,
            stock_code=stock_code,
            stock_name=stock_name,
            signal_type=signal_type,
            confidence=confidence,
            impact_score=impact_score,
            chain_depth=chain_depth,
            entry_rationale=entry_rationale,
            risk_factors=risk_factors,
            related_stocks=related_stocks,
            generated_at=datetime.now().isoformat(),
            event_date=event_date
        )

        self._signals.append(signal)
        self._save_signals()

        return signal

    def update_signal_result(
        self,
        signal_id: str,
        actual_entry_price: float,
        actual_exit_price: float,
        holding_days: int
    ) -> bool:
        """
        更新信号结果

        Args:
            signal_id: 信号ID
            actual_entry_price: 实际入场价格
            actual_exit_price: 实际出场价格
            holding_days: 持仓天数

        Returns:
            是否更新成功
        """
        for signal in self._signals:
            if signal.signal_id == signal_id:
                signal.actual_entry_price = actual_entry_price
                signal.actual_exit_price = actual_exit_price
                signal.holding_days = holding_days

                # 计算收益率
                if signal.signal_type == "BUY":
                    signal.actual_return = (actual_exit_price - actual_entry_price) / actual_entry_price * 100
                else:  # SELL
                    signal.actual_return = (actual_entry_price - actual_exit_price) / actual_entry_price * 100

                # 判断盈亏
                if signal.actual_return > 1.0:
                    signal.status = "win"
                elif signal.actual_return < -1.0:
                    signal.status = "loss"
                else:
                    signal.status = "neutral"

                self._save_signals()
                return True

        return False

    def get_statistics(self) -> SignalStatistics:
        """
        获取信号统计

        Returns:
            统计信息
        """
        total = len(self._signals)
        if total == 0:
            return SignalStatistics(
                total_signals=0,
                win_signals=0,
                loss_signals=0,
                neutral_signals=0,
                pending_signals=0,
                win_rate=0.0,
                avg_return=0.0,
                best_signal={},
                worst_signal={},
                signals_by_depth={},
                signals_by_confidence_range={}
            )

        # 统计各状态数量
        win_count = sum(1 for s in self._signals if s.status == "win")
        loss_count = sum(1 for s in self._signals if s.status == "loss")
        neutral_count = sum(1 for s in self._signals if s.status == "neutral")
        pending_count = sum(1 for s in self._signals if s.status == "pending")

        # 计算胜率 (只考虑已结算的)
        settled = [s for s in self._signals if s.status != "pending"]
        win_rate = win_count / len(settled) if settled else 0.0

        # 平均收益
        returns = [s.actual_return for s in self._signals if s.status != "pending"]
        avg_return = sum(returns) / len(returns) if returns else 0.0

        # 最佳/最差信号
        completed = [s for s in self._signals if s.status != "pending"]
        if completed:
            best = max(completed, key=lambda s: s.actual_return)
            worst = min(completed, key=lambda s: s.actual_return)
            best_signal = asdict(best)
            worst_signal = asdict(worst)
        else:
            best_signal = {}
            worst_signal = {}

        # 按深度统计
        signals_by_depth = {}
        for depth in range(1, 6):
            depth_signals = [s for s in self._signals if s.chain_depth == depth]
            if depth_signals:
                depth_wins = sum(1 for s in depth_signals if s.status == "win")
                signals_by_depth[depth] = {
                    "total": len(depth_signals),
                    "win": depth_wins,
                    "win_rate": round(depth_wins / len(depth_signals), 2) if depth_signals else 0
                }

        # 按置信度区间统计
        confidence_ranges = {
            "90-100": (90, 101),
            "80-89": (80, 90),
            "70-79": (70, 80),
            "60-69": (60, 70),
            "50-59": (50, 60),
            "0-49": (0, 50)
        }
        signals_by_confidence = {}
        for range_name, (low, high) in confidence_ranges.items():
            range_signals = [s for s in self._signals if low <= s.confidence < high]
            if range_signals:
                range_wins = sum(1 for s in range_signals if s.status == "win")
                signals_by_confidence[range_name] = {
                    "total": len(range_signals),
                    "win": range_wins,
                    "win_rate": round(range_wins / len(range_signals), 2)
                }

        return SignalStatistics(
            total_signals=total,
            win_signals=win_count,
            loss_signals=loss_count,
            neutral_signals=neutral_count,
            pending_signals=pending_count,
            win_rate=round(win_rate, 2),
            avg_return=round(avg_return, 2),
            best_signal=best_signal,
            worst_signal=worst_signal,
            signals_by_depth=signals_by_depth,
            signals_by_confidence_range=signals_by_confidence
        )

    def get_signals_by_event(self, event_id: str) -> List[HistoricalSignal]:
        """获取指定事件的所有信号"""
        return [s for s in self._signals if s.event_id == event_id]

    def get_signals_by_stock(self, stock_code: str) -> List[HistoricalSignal]:
        """获取指定股票的所有信号"""
        return [s for s in self._signals if s.stock_code == stock_code]

    def get_recent_signals(self, limit: int = 10) -> List[HistoricalSignal]:
        """获取最近的信号"""
        sorted_signals = sorted(
            self._signals,
            key=lambda s: s.generated_at,
            reverse=True
        )
        return sorted_signals[:limit]

    def get_stock_performance(
        self,
        stock_code: str,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        获取股票的历史表现

        Args:
            stock_code: 股票代码
            limit: 返回最近limit条记录

        Returns:
            股票表现统计
        """
        signals = self.get_signals_by_stock(stock_code)
        recent = sorted(signals, key=lambda s: s.generated_at, reverse=True)[:limit]

        if not recent:
            return {"has_history": False, "message": "该股票暂无历史信号"}

        completed = [s for s in recent if s.status != "pending"]
        win_count = sum(1 for s in completed if s.status == "win")
        win_rate = win_count / len(completed) if completed else 0.0

        returns = [s.actual_return for s in completed]
        avg_return = sum(returns) / len(returns) if returns else 0.0

        return {
            "has_history": True,
            "stock_code": stock_code,
            "total_signals": len(signals),
            "recent_signals_count": len(recent),
            "recent_win_rate": round(win_rate, 2),
            "average_return": round(avg_return, 2),
            "recent_signals": [asdict(s) for s in recent]
        }

    def get_confidence_calibration(
        self,
        confidence_range: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取置信度校准数据 - 用于检验信号置信度与实际胜率的关系

        Args:
            confidence_range: 置信度区间大小

        Returns:
            校准数据列表
        """
        completed = [s for s in self._signals if s.status != "pending"]
        if not completed:
            return []

        calibration_data = []
        for low in range(0, 100, confidence_range):
            high = low + confidence_range
            range_signals = [s for s in completed if low <= s.confidence < high]

            if range_signals:
                actual_wins = sum(1 for s in range_signals if s.status == "win")
                actual_win_rate = actual_wins / len(range_signals)
                avg_confidence = sum(s.confidence for s in range_signals) / len(range_signals)

                calibration_data.append({
                    "confidence_range": f"{low}-{high}",
                    "avg_predicted_confidence": round(avg_confidence, 1),
                    "actual_win_rate": round(actual_win_rate, 2),
                    "sample_count": len(range_signals),
                    "calibration_error": round(avg_confidence / 100 - actual_win_rate, 2)
                })

        return calibration_data


# 全局实例
_signal_store: Optional[HistoricalSignalStore] = None


def get_signal_store() -> HistoricalSignalStore:
    """获取信号库实例"""
    global _signal_store
    if _signal_store is None:
        _signal_store = HistoricalSignalStore()
    return _signal_store
