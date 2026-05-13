"""Redis client infrastructure with optional Pydantic, Prometheus, and Dishka support."""

from importlib.metadata import PackageNotFoundError, version

# Async exports
from .aio import (
    AsyncRedisClient,
    check_async_redis_health,
    close_async_redis_client,
    create_async_redis_client,
)
from .config import RedisSettingsProtocol
from .protocols import RedisMetricsProtocol

# Sync exports
from .sync import (
    SyncRedisClient,
    check_redis_health,
    close_redis_client,
    create_redis_client,
)
from .utils import build_base_redis_kwargs, build_redis_retry, parse_redis_url_node

try:
    __version__ = version("redis-client-kit")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.1.1"

# ruff: noqa: RUF022
__all__ = [
    # Async client
    "AsyncRedisClient",
    "check_async_redis_health",
    "close_async_redis_client",
    "create_async_redis_client",
    # Sync client
    "SyncRedisClient",
    "check_redis_health",
    "close_redis_client",
    "create_redis_client",
    # Protocols
    "RedisMetricsProtocol",
    "RedisSettingsProtocol",
    # Utilities
    "build_base_redis_kwargs",
    "build_redis_retry",
    "parse_redis_url_node",
    # Version
    "__version__",
]
