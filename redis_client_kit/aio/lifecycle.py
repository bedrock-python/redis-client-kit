"""Lifecycle management functions for async Redis clients."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from redis.exceptions import RedisClusterException, RedisError

from .types import AsyncRedisClient

logger = logging.getLogger(__name__)

ACLOSE_TIMEOUT_S = 10.0


async def close_async_redis_client(client: AsyncRedisClient) -> None:
    """Close async Redis client and release pool connections.

    Args:
        client: Redis client (single or cluster) to close

    Note:
        Uses asyncio.shield to ensure close operation completes even if task is cancelled.
    """
    try:
        await asyncio.wait_for(asyncio.shield(client.aclose()), timeout=ACLOSE_TIMEOUT_S)
    except TimeoutError:
        logger.warning("Redis client aclose timed out", extra={"timeout_s": ACLOSE_TIMEOUT_S})
    except (asyncio.CancelledError, KeyboardInterrupt):
        raise
    except Exception as e:
        logger.warning("Error closing Redis client", extra={"error": str(e)})
    else:
        logger.info("Closed Redis client")


async def check_async_redis_health(client: AsyncRedisClient) -> bool:
    """Check async Redis connection health.

    Args:
        client: Redis client (single or cluster) to check

    Returns:
        True if Redis is healthy, False otherwise
    """
    try:
        result: Any = await client.ping()  # type: ignore[misc]

        # Redis Cluster ping returns dict[str, bool] (node_id -> success); single node returns bool.
        if isinstance(result, dict) and result and all(isinstance(k, str) for k in result):
            return all(bool(v) for v in result.values())

        return bool(result)
    except (RedisError, RedisClusterException, OSError, ConnectionError, TimeoutError) as e:
        logger.warning(
            "Async Redis health check failed",
            extra={"error": str(e), "error_type": type(e).__name__},
        )
        return False
    except (asyncio.CancelledError, KeyboardInterrupt, SystemExit):
        raise
    except Exception:
        # Catch unexpected errors like encoding/decoding or internal redis-py bugs.
        # We return False to indicate unhealthy state but log the full exception for debugging.
        logger.exception("Unexpected error during Redis health check")
        return False


__all__ = ["check_async_redis_health", "close_async_redis_client"]
