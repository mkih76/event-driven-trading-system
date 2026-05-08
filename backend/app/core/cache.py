"""
Redis 缓存模块
提供事件分析结果的缓存和信号存储
"""
import json
import hashlib
import logging
from datetime import timedelta
from typing import Optional, Any, List, Dict
from pathlib import Path

logger = logging.getLogger(__name__)

# Redis 客户端（可选依赖）
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None


class CacheClient:
    """缓存客户端 - 支持 Redis 或本地文件缓存"""

    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url
        self._client = None
        self._use_redis = False

        if REDIS_AVAILABLE and redis_url:
            try:
                self._client = redis.from_url(redis_url)
                self._client.ping()
                self._use_redis = True
                logger.info("[缓存] 使用 Redis 缓存")
            except Exception as e:
                logger.warning(f"[缓存] Redis 连接失败，使用本地缓存: {e}")
                self._client = None

        if not self._use_redis:
            self._cache_dir = Path(__file__).parent.parent.parent.parent / "cache"
            self._cache_dir.mkdir(exist_ok=True)
            logger.info("[缓存] 使用本地文件缓存")

    def _get_cache_key(self, key: str) -> str:
        """生成缓存键"""
        return f"event_trading:{hashlib.md5(key.encode()).hexdigest()}"

    def _local_cache_path(self, key: str) -> Path:
        """本地缓存路径"""
        cache_key = self._get_cache_key(key)
        return self._cache_dir / f"{cache_key}.json"

    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        cache_key = self._get_cache_key(key)

        if self._use_redis and self._client:
            try:
                data = self._client.get(cache_key)
                if data:
                    return json.loads(data)
            except Exception as e:
                logger.warning(f"[缓存] Redis 获取失败: {e}")

        # 本地缓存
        cache_path = self._local_cache_path(key)
        if cache_path.exists():
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # 检查过期
                    if data.get("expires_at"):
                        from datetime import datetime
                        if datetime.fromisoformat(data["expires_at"]) < datetime.now():
                            cache_path.unlink()
                            return None
                    return data.get("value")
            except Exception:
                return None

        return None

    def set(self, key: str, value: Any, ttl_seconds: int = 3600):
        """设置缓存"""
        cache_key = self._get_cache_key(key)

        if self._use_redis and self._client:
            try:
                self._client.setex(
                    cache_key,
                    timedelta(seconds=ttl_seconds),
                    json.dumps(value, ensure_ascii=False)
                )
                return
            except Exception as e:
                logger.warning(f"[缓存] Redis 设置失败: {e}")

        # 本地缓存
        cache_path = self._local_cache_path(key)
        from datetime import datetime
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump({
                    "value": value,
                    "expires_at": (datetime.now() + timedelta(seconds=ttl_seconds)).isoformat(),
                    "created_at": datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"[缓存] 本地缓存写入失败: {e}")

    def delete(self, key: str):
        """删除缓存"""
        cache_key = self._get_cache_key(key)

        if self._use_redis and self._client:
            try:
                self._client.delete(cache_key)
            except Exception:
                pass

        cache_path = self._local_cache_path(key)
        if cache_path.exists():
            cache_path.unlink()

    def clear_expired(self):
        """清除过期缓存"""
        from datetime import datetime
        now = datetime.now()

        for cache_file in self._cache_dir.glob("*.json"):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("expires_at"):
                    if datetime.fromisoformat(data["expires_at"]) < now:
                        cache_file.unlink()
            except Exception:
                pass


class SignalStore:
    """信号存储 - 使用 Redis 或本地文件"""

    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url
        self._client = None
        self._use_redis = False
        self._store_dir = Path(__file__).parent.parent.parent.parent / "data" / "signals"
        self._store_dir.mkdir(exist_ok=True)

        if REDIS_AVAILABLE and redis_url:
            try:
                self._client = redis.from_url(redis_url)
                self._client.ping()
                self._use_redis = True
                logger.info("[信号库] 使用 Redis 存储")
            except Exception:
                self._client = None

        if not self._use_redis:
            logger.info("[信号库] 使用本地文件存储")

    def save_signal(self, signal: Dict[str, Any]) -> str:
        """保存信号"""
        import uuid
        from datetime import datetime

        signal_id = signal.get("signal_id") or str(uuid.uuid4())
        signal["signal_id"] = signal_id
        signal["created_at"] = datetime.now().isoformat()

        if self._use_redis and self._client:
            try:
                self._client.lpush("signals", json.dumps(signal, ensure_ascii=False))
                self._client.ltrim("signals", 0, 999)  # 保留最近1000条
                return signal_id
            except Exception as e:
                logger.warning(f"[信号库] Redis 保存失败: {e}")

        # 本地存储
        signal_file = self._store_dir / f"{signal_id}.json"
        with open(signal_file, "w", encoding="utf-8") as f:
            json.dump(signal, f, ensure_ascii=False, indent=2)

        return signal_id

    def get_signals(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取最近信号"""
        if self._use_redis and self._client:
            try:
                data = self._client.lrange("signals", 0, limit - 1)
                return [json.loads(d) for d in data]
            except Exception:
                pass

        # 本地存储
        signals = []
        for signal_file in sorted(self._store_dir.glob("*.json"), reverse=True)[:limit]:
            try:
                with open(signal_file, "r", encoding="utf-8") as f:
                    signals.append(json.load(f))
            except Exception:
                pass

        return signals

    def get_signals_by_event(self, event_id: str) -> List[Dict[str, Any]]:
        """获取指定事件的信号"""
        all_signals = self.get_signals(limit=1000)
        return [s for s in all_signals if s.get("event_id") == event_id]


# 全局实例
_cache_client: Optional[CacheClient] = None
_signal_store: Optional[SignalStore] = None


def get_cache_client(redis_url: str = None) -> CacheClient:
    """获取缓存客户端"""
    global _cache_client
    if _cache_client is None:
        _cache_client = CacheClient(redis_url)
    return _cache_client


def get_signal_store(redis_url: str = None) -> SignalStore:
    """获取信号存储"""
    global _signal_store
    if _signal_store is None:
        _signal_store = SignalStore(redis_url)
    return _signal_store