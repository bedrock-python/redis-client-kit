"""Type definitions for sync Redis clients."""

from redis import Redis
from redis.cluster import RedisCluster

# Type alias for Redis client (single or cluster mode)
# Can be plain redis-py client or instrumented version with metrics
SyncRedisClient = Redis | RedisCluster

__all__ = ["SyncRedisClient"]
