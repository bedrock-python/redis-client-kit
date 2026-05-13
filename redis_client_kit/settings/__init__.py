"""Pydantic settings for Redis configuration."""

from ._deps import HAS_PYDANTIC_SETTINGS

if not HAS_PYDANTIC_SETTINGS:
    raise ImportError("pydantic-settings not installed. Install redis-client-kit[settings] to use BaseRedisSettings.")

from .redis import (
    BaseRedisSettings,
    RedisClusterSettings,
    RedisConnectionSettings,
    RedisPoolSettings,
    RedisResponseSettings,
    RedisRetrySettings,
    RedisSSLSettings,
)

__all__ = [
    "BaseRedisSettings",
    "RedisClusterSettings",
    "RedisConnectionSettings",
    "RedisPoolSettings",
    "RedisResponseSettings",
    "RedisRetrySettings",
    "RedisSSLSettings",
]
