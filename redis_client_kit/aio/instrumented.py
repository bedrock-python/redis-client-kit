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


def _translate_closed_transport(error: RuntimeError) -> RedisConnectionError | None:
    """Translate a uvloop closed-transport RuntimeError into a Redis ConnectionError.

    uvloop raises RuntimeError when the transport is closed but still being used.
    redis-py only handles its own ConnectionError (retry or reconnect), so the error
    is translated. Returns None for any other RuntimeError.
    """
    message = str(error).lower()
    if "the handler is closed" in message or "transport is closed" in message:
        return RedisConnectionError(str(error))
    return None


def _record_error(metrics: RedisMetricsProtocol, error: BaseException) -> None:
    """Record an error without letting the metrics backend break the command."""
    try:
        metrics.record_error(error_type=type(error).__name__)
    except Exception:
        logger.exception("Failed to record Redis error metrics")


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
                # redis-py async pool has _available_connections and _in_use_connections
                available: list[Any] = getattr(pool, "_available_connections", [])
                in_use: set[Any] = getattr(pool, "_in_use_connections", set())
                self._metrics.record_pool_stats(
                    pool_size=len(available) + len(in_use),
                    pool_checked_out=len(in_use),
                )
            except Exception:
                logger.exception("Failed to record Redis pool metrics")

        try:
            return await super().execute_command(*args, **options)
        except RuntimeError as e:
            status = "error"
            translated = _translate_closed_transport(e)
            _record_error(self._metrics, translated or e)
            if translated is not None:
                raise translated from e
            raise
        except Exception as e:
            status = "error"
            _record_error(self._metrics, e)
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
            status = "error"
            translated = _translate_closed_transport(e)
            _record_error(self._metrics, translated or e)
            if translated is not None:
                raise translated from e
            raise
        except Exception as e:
            status = "error"
            _record_error(self._metrics, e)
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
