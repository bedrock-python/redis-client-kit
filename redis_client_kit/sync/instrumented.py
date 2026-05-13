"""Instrumented Redis clients with Prometheus metrics collection."""

from __future__ import annotations

import logging
import time
from typing import Any

from redis import Redis
from redis.cluster import RedisCluster
from redis.exceptions import ConnectionError as RedisConnectionError

from ..protocols import RedisMetricsProtocol

logger = logging.getLogger(__name__)


class InstrumentedRedis(Redis):
    """Redis client with Prometheus metrics collection."""

    def __init__(self, *args: Any, metrics: RedisMetricsProtocol, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._metrics = metrics

    def execute_command(self, *args: Any, **options: Any) -> Any:
        """Execute command and record metrics."""
        command = args[0] if args else "unknown"
        start = time.perf_counter()
        status = "success"

        # Update pool metrics
        pool = self.connection_pool
        if pool:
            try:
                # redis-py sync pool has _available_connections and _in_use_connections
                available: list[Any] = getattr(pool, "_available_connections", [])
                in_use: set[Any] = getattr(pool, "_in_use_connections", set())
                pool_size = len(available) + len(in_use)
                self._metrics.record_pool_stats(
                    pool_size=pool_size,
                    pool_checked_out=len(in_use),
                )
            except Exception:
                logger.exception("Failed to record Redis pool metrics")

        try:
            return super().execute_command(*args, **options)
        except RuntimeError as e:
            # Handle closed connection errors
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

    def execute_command(self, *args: Any, **options: Any) -> Any:
        """Execute command and record metrics."""
        command = args[0] if args else "unknown"
        start = time.perf_counter()
        status = "success"

        # Pool metrics are harder for cluster, but we can still track command stats and errors

        try:
            return super().execute_command(*args, **options)
        except RuntimeError as e:
            # Handle closed connection errors
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
