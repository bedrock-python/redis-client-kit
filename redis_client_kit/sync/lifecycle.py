"""Lifecycle management functions for sync Redis clients."""

from __future__ import annotations

import logging
from typing import Any

from redis.exceptions import RedisClusterException, RedisError

from ..utils import WRITE_PROBE_TTL_S
from .types import SyncRedisClient

logger = logging.getLogger(__name__)


def close_redis_client(client: SyncRedisClient) -> None:
    """Close sync Redis client and release pool connections.

    Args:
        client: Redis client (single or cluster) to close
    """
    try:
        client.close()
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception as e:
        logger.warning("Error closing Redis client", extra={"error": str(e)})
    else:
        logger.info("Closed Redis client")


def check_redis_health(client: SyncRedisClient, *, write_key: str | None = None) -> bool:
    """Check sync Redis connection health.

    Pings the server, and with ``write_key`` writes that key as well. A ping alone is a
    liveness answer: a read-only replica and a server at ``maxmemory`` under ``noeviction``
    both reply PONG and refuse every write. The write probe turns that into a readiness
    answer for a service that needs Redis for more than reads.

    Args:
        client: Redis client (single or cluster) to check
        write_key: Key to ``SET`` after the ping, expiring after ``WRITE_PROBE_TTL_S``
            seconds. None, the default, pings only. Prefix it yourself; this package
            applies no key prefix.

    Returns:
        True if Redis is healthy, False otherwise
    """
    try:
        result: Any = client.ping()  # type: ignore[misc]

        # Redis Cluster ping returns dict[str, bool] (node_id -> success); single node returns bool.
        if isinstance(result, dict) and result and all(isinstance(k, str) for k in result):
            healthy = all(bool(v) for v in result.values())
        else:
            healthy = bool(result)

        if healthy and write_key is not None:
            healthy = bool(client.set(write_key, "1", ex=WRITE_PROBE_TTL_S))
    except (RedisError, RedisClusterException, OSError, ConnectionError, TimeoutError) as e:
        logger.warning(
            "Redis health check failed",
            extra={"error": str(e), "error_type": type(e).__name__},
        )
        return False
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception:
        # Catch unexpected errors like encoding/decoding or internal redis-py bugs.
        # We return False to indicate unhealthy state but log the full exception for debugging.
        logger.exception("Unexpected error during Redis health check")
        return False
    else:
        return healthy


__all__ = ["check_redis_health", "close_redis_client"]
