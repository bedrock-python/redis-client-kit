"""Dishka providers for Redis dependency injection."""

from ._deps import HAS_DISHKA

if not HAS_DISHKA:
    raise ImportError("dishka not installed. Install redis-client-kit[providers] to use AsyncRedisProvider.")

from .redis import AsyncRedisProvider

__all__ = ["AsyncRedisProvider"]
