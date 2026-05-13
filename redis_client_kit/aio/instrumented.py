"""Instrumented Redis clients with Prometheus metrics collection."""

from __future__ import annotations

import logging
import time
from typing import Any

from redis.asyncio import Redis
from redis.asyncio.cluster import RedisCluster
from redis.exceptions import ConnectionError as RedisConnectionError

from ..protocols import RedisMetricsProtocol

logger = logging.getLogger(__name__)


class InstrumentedRedis(Redis):
    """Redis client with Prometheus metrics collection."""

    def __init__(self, *args: Any, metrics: RedisMetricsProtocol, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._metrics = metrics

    async def execute_command(self, *args: Any, **options: Any) -> Any:
        """Execute command and record metrics."""
        command = args[0] if args else "unknown"
        start = time.perf_counter()
        status = "success"

        # Update pool metrics
        pool = self.connection_pool
        if pool:
            try:
                # redis-py async pool has _all_connections and _in_use_connections
                self._metrics.record_pool_stats(
                    pool_size=len(getattr(pool, "_all_connections", [])),
                    pool_checked_out=len(getattr(pool, "_in_use_connections", [])),
                )
            except Exception:
                logger.exception("Failed to record Redis pool metrics")

        try:
            return await super().execute_command(*args, **options)
        except RuntimeError as e:
            # uvloop raises RuntimeError when transport is closed but still being used.
            # We translate it to ConnectionError so redis-py can handle it (retry or reconnect).
            if "the handler is closed" in str(e).lower() or "transport is closed" in str(e).lower():
                raise RedisConnectionError(str(e)) from e
            raise
        except Exception as e:
            status = "error"
            error_type = type(e).__name__
            try:
                self._metrics.record_error(error_type=error_type)
            except Exception:
                logger.exception("Failed to record Redis error metrics")
            raise
        finally:
            duration = time.perf_counter() - start
            try:
                self._metrics.record_command(
                    command=str(command).upper(),
                    status=status,
                    duration=duration,
                )
            except Exception:
                logger.exception("Failed to record Redis command metrics")


class InstrumentedRedisCluster(RedisCluster):
    """Redis Cluster client with Prometheus metrics collection."""

    def __init__(self, *args: Any, metrics: RedisMetricsProtocol, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._metrics = metrics

    async def execute_command(self, *args: Any, **options: Any) -> Any:
        """Execute command and record metrics."""
        command = args[0] if args else "unknown"
        start = time.perf_counter()
        status = "success"

        # Pool metrics are harder for cluster, but we can still track command stats and errors

        try:
            return await super().execute_command(*args, **options)
        except RuntimeError as e:
            # uvloop raises RuntimeError when transport is closed but still being used.
            # We translate it to ConnectionError so redis-py can handle it (retry or reconnect).
            if "the handler is closed" in str(e).lower() or "transport is closed" in str(e).lower():
                raise RedisConnectionError(str(e)) from e
            raise
        except Exception as e:
            status = "error"
            error_type = type(e).__name__
            try:
                self._metrics.record_error(error_type=error_type)
            except Exception:
                logger.exception("Failed to record Redis error metrics")
            raise
        finally:
            duration = time.perf_counter() - start
            try:
                self._metrics.record_command(
                    command=str(command).upper(),
                    status=status,
                    duration=duration,
                )
            except Exception:
                logger.exception("Failed to record Redis command metrics")


__all__ = ["InstrumentedRedis", "InstrumentedRedisCluster"]
