"""Dishka provider for the Prometheus Redis metrics collector."""

from ..config import RedisSettingsProtocol
from ..protocols import RedisMetricsProtocol
from ._deps import Provider, Scope, provide


class PrometheusRedisMetricsProvider(Provider):  # type: ignore[misc]
    """Dishka provider for the collector ``AsyncRedisProvider`` records into.

    Provides ``RedisMetricsProtocol | None`` -- the key ``AsyncRedisProvider`` reads -- as
    ``get_redis_metrics(prefix)`` when ``settings.metrics_enabled`` and ``None`` otherwise,
    so the client is instrumented exactly when the settings say so. Register it with
    ``AsyncRedisProvider(provide_default_metrics=False)``, or after ``AsyncRedisProvider()``,
    since the last provider of a type wins.

    The collector comes from ``get_redis_metrics``: one instance per prefix on the default
    registry, so a container rebuilt per test never asks Prometheus to register the same
    series twice. Resolving it with metrics on needs the ``metrics`` extra; without it the
    import raises ``ImportError`` naming the extra.
    """

    scope = Scope.APP  # type: ignore[misc]

    def __init__(self, *, prefix: str | None = None) -> None:
        """Remember the prefix the collector is created with.

        Args:
            prefix: Metric name prefix (``"myapp"`` gives ``myapp_redis_pool_size``)
        """
        super().__init__()
        self._prefix = prefix

    @provide
    def get_metrics(self, redis_settings: RedisSettingsProtocol) -> RedisMetricsProtocol | None:
        """Provide the collector when ``metrics_enabled`` is on, ``None`` otherwise."""
        if not redis_settings.metrics_enabled:
            return None
        from ..metrics import get_redis_metrics  # noqa: PLC0415 - lazy: needs the [metrics] extra

        return get_redis_metrics(self._prefix)


__all__ = ["PrometheusRedisMetricsProvider"]
