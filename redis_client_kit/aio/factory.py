"""Factory functions for creating async Redis clients."""

from __future__ import annotations

import logging
from typing import Any

from redis.asyncio import Redis
from redis.asyncio.cluster import ClusterNode, RedisCluster

from ..config import RedisSettingsProtocol
from ..protocols import RedisMetricsProtocol
from ..utils import build_base_redis_kwargs, parse_redis_url_node
from .instrumented import InstrumentedRedis, InstrumentedRedisCluster
from .types import AsyncRedisClient

logger = logging.getLogger(__name__)


def create_async_redis_client(
    settings: RedisSettingsProtocol, metrics: RedisMetricsProtocol | None = None
) -> AsyncRedisClient:
    """Create async Redis client with connection pool.

    Returns redis-py client (Redis or RedisCluster) with optional metrics instrumentation.
    - If metrics is None: returns plain Redis/RedisCluster (zero overhead)
    - If metrics provided: returns InstrumentedRedis/InstrumentedRedisCluster

    Automatically selects single or cluster mode based on settings.

    Args:
        settings: Redis configuration
        metrics: Optional Prometheus metrics collector (None = no instrumentation)

    Returns:
        Redis, RedisCluster, InstrumentedRedis, or InstrumentedRedisCluster instance
    """
    if settings.cluster.enabled:
        return _create_async_cluster_client(settings, metrics=metrics)

    return _create_async_single_client(settings, metrics=metrics)


def _create_async_single_client(
    settings: RedisSettingsProtocol, metrics: RedisMetricsProtocol | None = None
) -> Redis | InstrumentedRedis:
    """Create single-instance async Redis client with connection pool."""
    logger.info(
        "Creating single Redis client",
        extra={"host": settings.connection.host, "port": settings.connection.port},
    )

    client_kwargs: dict[str, Any] = build_base_redis_kwargs(settings)
    client_kwargs.update(
        {
            "host": settings.connection.host,
            "port": settings.connection.port,
            "db": settings.connection.db,
        }
    )

    if metrics is None:
        return Redis(**client_kwargs)

    client_kwargs["metrics"] = metrics
    return InstrumentedRedis(**client_kwargs)


def _create_async_cluster_client(
    settings: RedisSettingsProtocol, metrics: RedisMetricsProtocol | None = None
) -> RedisCluster | InstrumentedRedisCluster:
    """Create async Redis Cluster client with connection pool."""
    if settings.cluster.nodes:
        startup_nodes = [
            ClusterNode(host=host, port=port)
            for host, port in [parse_redis_url_node(node) for node in settings.cluster.nodes]
        ]
    else:
        startup_nodes = [ClusterNode(host=settings.connection.host, port=settings.connection.port)]

    logger.info(
        "Creating Redis Cluster client",
        extra={
            "host": settings.connection.host,
            "port": settings.connection.port,
            "startup_nodes": [str(node) for node in startup_nodes],
        },
    )

    cluster_kwargs: dict[str, Any] = build_base_redis_kwargs(settings)
    cluster_kwargs.update(
        {
            "startup_nodes": startup_nodes,
        }
    )

    if metrics is None:
        return RedisCluster(**cluster_kwargs)

    cluster_kwargs["metrics"] = metrics
    return InstrumentedRedisCluster(**cluster_kwargs)


__all__ = ["create_async_redis_client"]
