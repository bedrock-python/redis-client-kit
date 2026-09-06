"""Dishka provider for Redis."""

import functools
import logging
from collections.abc import AsyncIterator

from redis.exceptions import RedisError

from ..aio import AsyncRedisClient, check_async_redis_health, close_async_redis_client, create_async_redis_client
from ..config import RedisSettingsProtocol
from ..protocols import RedisMetricsProtocol
from ._deps import Provider, Scope
from .utils import retry_async_connection, safe_async_cleanup

logger = logging.getLogger(__name__)


class AsyncRedisProvider(Provider):  # type: ignore[misc]
    """Dishka provider for Redis dependencies.

    Provides one ``AsyncRedisClient``, chosen when the provider is constructed:

    - ``AsyncRedisProvider()`` verifies the connection on startup with retries and
      raises when Redis stays unreachable, so startup fails instead of handing out
      a client that cannot answer.
    - ``AsyncRedisProvider(check_health_on_startup=False)`` yields the client without
      contacting Redis, for a faster startup when Redis availability is not critical.

    It also provides ``RedisMetricsProtocol | None`` as ``None`` so a container with no
    metrics provider still resolves. Dishka lets the last registered provider of a type
    win, so this default overrides a metrics provider registered before it: either
    register this provider first, or construct it with ``provide_default_metrics=False``.
    """

    scope = Scope.APP  # type: ignore[misc]

    def __init__(
        self,
        *,
        check_health_on_startup: bool = True,
        provide_default_metrics: bool = True,
    ) -> None:
        """Register the client factory, and the default metrics factory when asked to.

        Args:
            check_health_on_startup: Verify the connection before yielding the client
            provide_default_metrics: Provide ``RedisMetricsProtocol | None`` as ``None``
        """
        super().__init__()
        self.provide(self.get_redis_with_health_check if check_health_on_startup else self.get_redis)
        if provide_default_metrics:
            self.provide(self.get_default_metrics)

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
            ConnectionError: If Redis is still unreachable after the last attempt
        """
        client = create_async_redis_client(redis_settings, metrics=metrics)

        try:
            await retry_async_connection(
                connect_func=lambda: check_async_redis_health(client),
                service_name="Redis",
            )
        except BaseException:
            await safe_async_cleanup(
                cleanup_func=functools.partial(close_async_redis_client, client),
                service_name="Redis client",
                exception_type=RedisError,
            )
            raise

        try:
            yield client
        finally:
            await safe_async_cleanup(
                cleanup_func=functools.partial(close_async_redis_client, client),
                service_name="Redis client",
                exception_type=RedisError,
            )

    def get_default_metrics(self) -> RedisMetricsProtocol | None:
        """Provide default None for metrics if not provided in container."""
        return None


__all__ = ["AsyncRedisProvider"]
