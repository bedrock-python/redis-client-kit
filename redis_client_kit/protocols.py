"""Protocols for Redis client kit."""

from __future__ import annotations

from typing import Protocol


class RedisMetricsProtocol(Protocol):
    """Protocol for Redis metrics collection.

    Defines the interface for collecting Redis client metrics.
    Implementation can use any metrics library (Prometheus, StatsD, etc.).

    Example implementation: RedisMetrics from redis_client_kit.metrics
    """

    def record_command(
        self,
        command: str,
        status: str,
        duration: float,
    ) -> None:
        """Record a completed Redis command.

        Args:
            command: Redis command name (e.g., "GET", "SET", "HGETALL")
            status: Execution status ("success" or "error")
            duration: Command execution duration in seconds
        """
        ...

    def record_error(
        self,
        error_type: str,
    ) -> None:
        """Record a Redis connection or execution error.

        Args:
            error_type: Error type name (e.g., "ConnectionError", "TimeoutError")
        """
        ...

    def record_pool_stats(
        self,
        pool_size: int,
        pool_checked_out: int,
    ) -> None:
        """Record Redis connection pool statistics.

        Args:
            pool_size: Total number of connections in the pool
            pool_checked_out: Number of connections currently in use
        """
        ...
