"""Dishka provider for Redis."""

import functools
import logging
from collections.abc import AsyncIterator

from redis.exceptions import RedisError

from ..aio import AsyncRedisClient, check_async_redis_health, close_async_redis_client, create_async_redis_client
from ..config import RedisSettingsProtocol
from ..protocols import RedisMetricsProtocol
from ._deps import Provider, Scope, provide
from .utils import retry_async_connection, safe_async_cleanup

logger = logging.getLogger(__name__)


class AsyncRedisProvider(Provider):  # type: ignore[misc]
    """Dishka provider for Redis dependencies.

    Provides two Redis client options:
    - get_redis(): Simple client without startup health check
    - get_redis_with_health_check(): Client with connection verification and retries

    Choose get_redis() for faster startup when Redis availability is not critical.
    Choose get_redis_with_health_check() for guaranteed connection on startup.
    """

    scope = Scope.APP  # type: ignore[misc]

    @provide  # type: ignore[misc]
    async def get_redis(
        self,
        redis_settings: RedisSettingsProtocol,
        metrics: RedisMetricsProtocol | None = None,
    ) -> AsyncIterator[AsyncRedisClient]:
        """Provide Redis client without startup health check.

        Creates Redis client and yields it immediately without verifying connection.
        Use this for faster application startup when Redis availability is not critical.

        Args:
            redis_settings: Redis configuration
            metrics: Optional metrics collector

        Yields:
            Configured AsyncRedisClient instance
        """
        client = create_async_redis_client(redis_settings, metrics=metrics)

        try:
            yield client
        finally:
            await safe_async_cleanup(
                cleanup_func=functools.partial(close_async_redis_client, client),
                service_name="Redis client",
                exception_type=RedisError,
            )

    @provide  # type: ignore[misc]
    async def get_redis_with_health_check(
        self,
        redis_settings: RedisSettingsProtocol,
        metrics: RedisMetricsProtocol | None = None,
    ) -> AsyncIterator[AsyncRedisClient]:
        """Provide Redis client with startup health check and retry.

        Creates Redis client and verifies connection with exponential backoff retry.
        Application startup will be blocked until Redis is available or max retries reached.

        Args:
            redis_settings: Redis configuration
            metrics: Optional metrics collector

        Yields:
            Configured and verified AsyncRedisClient instance

        Raises:
            Exception: If connection fails after max retry attempts
        """
        client = create_async_redis_client(redis_settings, metrics=metrics)

        await retry_async_connection(
            connect_func=lambda: check_async_redis_health(client),
            service_name="Redis",
        )

        try:
            yield client
        finally:
            await safe_async_cleanup(
                cleanup_func=functools.partial(close_async_redis_client, client),
                service_name="Redis client",
                exception_type=RedisError,
            )

    @provide  # type: ignore[misc]
    def get_default_metrics(self) -> RedisMetricsProtocol | None:
        """Provide default None for metrics if not provided in container."""
        return None


__all__ = ["AsyncRedisProvider"]
