"""Type definitions for async Redis clients."""

from redis.asyncio import Redis
from redis.asyncio.cluster import RedisCluster

# Type alias for Redis client (single or cluster mode)
# Can be plain redis-py client or instrumented version with metrics
AsyncRedisClient = Redis | RedisCluster

__all__ = ["AsyncRedisClient"]
