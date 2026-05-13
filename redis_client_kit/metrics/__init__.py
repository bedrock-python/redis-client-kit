"""Prometheus metrics for Redis client."""

from ._deps import HAS_PROMETHEUS

if not HAS_PROMETHEUS:
    raise ImportError("prometheus-client not installed. Install redis-client-kit[metrics] to use metrics.")

from .redis import REDIS_COMMAND_DURATION_BUCKETS, RedisMetrics

__all__ = ["REDIS_COMMAND_DURATION_BUCKETS", "RedisMetrics"]
