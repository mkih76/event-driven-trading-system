"""
日志配置模块
提供统一的日志配置和监控指标收集
"""
import logging
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from functools import wraps
from contextlib import contextmanager

# 日志配置
LOG_DIR = Path(__file__).parent.parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / "event_trading.log"
METRICS_FILE = LOG_DIR / "metrics.json"


class StructuredLogger:
    """结构化日志记录器"""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # 文件处理器
        fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
        fh.setLevel(logging.INFO)

        # 控制台处理器
        ch = logging.StreamHandler()
        ch.setLevel(logging.WARNING)

        # 格式化
        formatter = logging.Formatter(
            "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        self.logger.addHandler(fh)
        self.logger.addHandler(ch)

    def info(self, message: str, **kwargs):
        """记录信息日志"""
        extra = self._format_extra(kwargs)
        self.logger.info(f"{message} | {extra}")

    def warning(self, message: str, **kwargs):
        """记录警告日志"""
        extra = self._format_extra(kwargs)
        self.logger.warning(f"{message} | {extra}")

    def error(self, message: str, **kwargs):
        """记录错误日志"""
        extra = self._format_extra(kwargs)
        self.logger.error(f"{message} | {extra}")

    def _format_extra(self, kwargs: Dict[str, Any]) -> str:
        """格式化额外参数"""
        if not kwargs:
            return ""
        return " | ".join(f"{k}={v}" for k, v in kwargs.items())


class MetricsCollector:
    """指标收集器"""

    def __init__(self):
        self._metrics: List[Dict[str, Any]] = []
        self._counters: Dict[str, int] = {}
        self._timers: Dict[str, List[float]] = {}

    def record(self, metric_type: str, name: str, value: float, tags: Dict[str, str] = None):
        """记录指标"""
        self._metrics.append({
            "timestamp": datetime.now().isoformat(),
            "type": metric_type,
            "name": name,
            "value": value,
            "tags": tags or {}
        })

    def increment(self, counter: str, value: int = 1):
        """递增计数器"""
        self._counters[counter] = self._counters.get(counter, 0) + value

    def timing(self, timer: str, duration_ms: float):
        """记录计时"""
        if timer not in self._timers:
            self._timers[timer] = []
        self._timers[timer].append(duration_ms)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            "timestamp": datetime.now().isoformat(),
            "counters": self._counters.copy(),
            "timers": {}
        }

        for name, values in self._timers.items():
            if values:
                stats["timers"][name] = {
                    "count": len(values),
                    "avg_ms": sum(values) / len(values),
                    "min_ms": min(values),
                    "max_ms": max(values)
                }

        return stats

    def save(self):
        """保存指标到文件"""
        try:
            data = {
                "metrics": self._metrics[-1000:],  # 保最近1000条
                "stats": self.get_stats()
            }
            with open(METRICS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to save metrics: {e}")


# 全局实例
_logger: Optional[StructuredLogger] = None
_metrics: Optional[MetricsCollector] = None


def get_logger(name: str = "event_trading") -> StructuredLogger:
    """获取日志记录器"""
    global _logger
    if _logger is None:
        _logger = StructuredLogger(name)
    return _logger


def get_metrics() -> MetricsCollector:
    """获取指标收集器"""
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollector()
    return _metrics


def log_analysis_event(event_type: str, title: str, duration_ms: int, success: bool, error: str = None):
    """记录分析事件"""
    logger = get_logger()
    metrics = get_metrics()

    logger.info(
        f"Analysis completed: {event_type}",
        title=title[:50] if title else "",
        duration_ms=duration_ms,
        success=success
    )

    metrics.increment("analysis.total")
    if success:
        metrics.increment("analysis.success")
    else:
        metrics.increment("analysis.error")
        if error:
            logger.error(f"Analysis failed: {error}")

    metrics.timing("analysis.duration", duration_ms)


def log_llm_call(provider: str, model: str, duration_ms: int, success: bool, tokens_used: int = 0):
    """记录LLM调用"""
    metrics = get_metrics()

    metrics.increment(f"llm.{provider}.total")
    if success:
        metrics.increment(f"llm.{provider}.success")
    else:
        metrics.increment(f"llm.{provider}.error")

    metrics.timing(f"llm.{provider}.duration", duration_ms)

    if tokens_used > 0:
        metrics.record("token", f"{provider}.{model}", tokens_used)


@contextmanager
def track_duration(name: str):
    """上下文管理器：追踪操作耗时"""
    start = time.time()
    try:
        yield
    finally:
        duration_ms = (time.time() - start) * 1000
        metrics = get_metrics()
        metrics.timing(name, duration_ms)


def timing_decorator(func):
    """计时装饰器"""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            duration_ms = (time.time() - start) * 1000
            metrics = get_metrics()
            metrics.timing(f"func.{func.__name__}", duration_ms)

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            duration_ms = (time.time() - start) * 1000
            metrics = get_metrics()
            metrics.timing(f"func.{func.__name__}", duration_ms)

    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper