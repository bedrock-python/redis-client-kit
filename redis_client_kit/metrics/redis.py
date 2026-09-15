"""Redis Prometheus metrics implementation."""

from ._deps import Counter, Gauge, Histogram

# Default buckets for Redis command duration (seconds)
REDIS_COMMAND_DURATION_BUCKETS = (0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0)


class RedisMetrics:
    """Redis client Prometheus metrics.

    Provides instrumentation for Redis operations including:
    - Command execution metrics (count, duration)
    - Connection pool statistics
    - Error tracking

    Metrics:
        redis_pool_size: Current Redis connection pool size
        redis_pool_checked_out: Number of Redis connections currently in use
        redis_commands_total: Total number of Redis commands executed
        redis_command_duration_seconds: Redis command execution duration histogram
        redis_connection_errors_total: Number of connection errors

    Labels:
        command: Redis command name (GET, SET, HGETALL, etc)
        status: Command execution status (success, error)
        error_type: Type of connection error

    Example:
        >>> metrics = RedisMetrics(prefix="myapp")
        >>> metrics.record_command("GET", "success", 0.001)
        >>> metrics.record_pool_stats(pool_size=10, pool_checked_out=3)

    Prometheus registers a metric name once per registry, so a second instance with the
    same prefix raises ``ValueError``; ``get_redis_metrics`` hands back the first one instead.
    """

    def __init__(self, prefix: str | None = None) -> None:
        """Initialize Redis Prometheus metrics.

        Args:
            prefix: Optional metric name prefix (e.g., "myapp" -> "myapp_redis_pool_size")

        Raises:
            ValueError: If a metric of the same name is already registered on the default
                registry -- see ``get_redis_metrics`` for the second instance.
        """
        metric_prefix = f"{prefix}_" if prefix else ""

        self.pool_size = Gauge(
            f"{metric_prefix}redis_pool_size",
            "Current Redis connection pool size",
        )
        self.pool_checked_out = Gauge(
            f"{metric_prefix}redis_pool_checked_out",
            "Number of Redis connections currently in use",
        )
        self.commands_total = Counter(
            f"{metric_prefix}redis_commands_total",
            "Total number of Redis commands executed",
            ["command", "status"],
        )
        self.command_duration = Histogram(
            f"{metric_prefix}redis_command_duration_seconds",
            "Redis command execution duration",
            ["command"],
            buckets=list(REDIS_COMMAND_DURATION_BUCKETS),
        )
        self.connection_errors_total = Counter(
            f"{metric_prefix}redis_connection_errors_total",
            "Number of Redis connection errors",
            ["error_type"],
        )

    def record_command(self, command: str, status: str, duration: float) -> None:
        """Record a completed Redis command.

        Args:
            command: Redis command name (e.g., "GET", "SET", "HGETALL")
            status: Execution status ("success" or "error")
            duration: Command execution duration in seconds
        """
        self.commands_total.labels(command=command, status=status).inc()
        self.command_duration.labels(command=command).observe(duration)

    def record_error(self, error_type: str) -> None:
        """Record a Redis connection or execution error.

        Args:
            error_type: Error type name (e.g., "ConnectionError", "TimeoutError")
        """
        self.connection_errors_total.labels(error_type=error_type).inc()

    def record_pool_stats(self, pool_size: int, pool_checked_out: int) -> None:
        """Record Redis connection pool statistics.

        Args:
            pool_size: Total number of connections in the pool
            pool_checked_out: Number of connections currently in use
        """
        self.pool_size.set(float(pool_size))
        self.pool_checked_out.set(float(pool_checked_out))


_REDIS_METRICS_CACHE: dict[str | None, RedisMetrics] = {}


def get_redis_metrics(prefix: str | None = None) -> RedisMetrics:
    """Get (or lazily create) the cached ``RedisMetrics`` for a prefix, on the default registry.

    Caching by prefix is what lets a container be rebuilt -- a test suite does it per test --
    without Prometheus refusing the second registration of the same series.

    Args:
        prefix: The metric name prefix the instance was, or is, created with; ``""`` and
            ``None`` are the same unprefixed instance.

    Returns:
        The one instance for that prefix.
    """
    key = prefix or None
    metrics = _REDIS_METRICS_CACHE.get(key)
    if metrics is None:
        metrics = _REDIS_METRICS_CACHE[key] = RedisMetrics(prefix=key)
    return metrics


__all__ = ["REDIS_COMMAND_DURATION_BUCKETS", "RedisMetrics", "get_redis_metrics"]
