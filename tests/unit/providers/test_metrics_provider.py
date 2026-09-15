"""Tests for PrometheusRedisMetricsProvider next to AsyncRedisProvider."""

import sys
from unittest.mock import MagicMock

import pytest
from dishka import AsyncContainer, Provider, Scope, make_async_container
from redis.asyncio import Redis

from redis_client_kit import AsyncRedisClient
from redis_client_kit.aio import InstrumentedRedis
from redis_client_kit.config import RedisSettingsProtocol
from redis_client_kit.metrics import RedisMetrics, get_redis_metrics
from redis_client_kit.protocols import RedisMetricsProtocol
from redis_client_kit.providers import AsyncRedisProvider, PrometheusRedisMetricsProvider


def _settings_provider(settings: MagicMock) -> Provider:
    provider = Provider(scope=Scope.APP)
    provider.provide(lambda: settings, provides=RedisSettingsProtocol)
    return provider


def _container(settings: MagicMock, *, prefix: str | None = None) -> AsyncContainer:
    """The reporter's container: the kit's client provider with its default metrics off, and ours."""
    return make_async_container(
        AsyncRedisProvider(check_health_on_startup=False, provide_default_metrics=False),
        PrometheusRedisMetricsProvider(prefix=prefix),
        _settings_provider(settings),
    )


@pytest.mark.asyncio
async def test__metrics_provider__metrics_disabled__client_is_plain(mock_redis_settings: MagicMock) -> None:
    # Arrange
    mock_redis_settings.metrics_enabled = False
    container = _container(mock_redis_settings)

    # Act
    metrics = await container.get(RedisMetricsProtocol | None)
    client = await container.get(AsyncRedisClient)

    # Assert
    assert metrics is None
    assert type(client) is Redis
    await container.close()


@pytest.mark.asyncio
async def test__metrics_provider__metrics_enabled__client_gets_the_cached_collector(
    mock_redis_settings: MagicMock,
) -> None:
    # Arrange
    mock_redis_settings.metrics_enabled = True
    container = _container(mock_redis_settings)

    # Act
    client = await container.get(AsyncRedisClient)

    # Assert
    assert isinstance(client, InstrumentedRedis)
    assert client._metrics is get_redis_metrics()
    await container.close()


@pytest.mark.asyncio
async def test__metrics_provider__prefix__names_the_collector(mock_redis_settings: MagicMock) -> None:
    # Arrange
    mock_redis_settings.metrics_enabled = True
    container = _container(mock_redis_settings, prefix="provider_prefix_test")

    # Act
    metrics = await container.get(RedisMetricsProtocol | None)

    # Assert
    assert isinstance(metrics, RedisMetrics)
    assert metrics.pool_size._name == "provider_prefix_test_redis_pool_size"
    await container.close()


@pytest.mark.asyncio
async def test__metrics_provider__container_rebuilt__does_not_register_twice(mock_redis_settings: MagicMock) -> None:
    """The per-test container: the second build hands out the collector the first one registered."""
    # Arrange
    mock_redis_settings.metrics_enabled = True
    first = _container(mock_redis_settings)
    second = _container(mock_redis_settings)

    # Act
    first_metrics = await first.get(RedisMetricsProtocol | None)
    second_metrics = await second.get(RedisMetricsProtocol | None)

    # Assert
    assert first_metrics is second_metrics
    await first.close()
    await second.close()


@pytest.mark.asyncio
async def test__metrics_provider__registered_after_default__wins(mock_redis_settings: MagicMock) -> None:
    """AsyncRedisProvider() keeps its None default; the last provider of the type wins, so ours must follow it."""
    # Arrange
    mock_redis_settings.metrics_enabled = True
    container = make_async_container(
        AsyncRedisProvider(check_health_on_startup=False),
        PrometheusRedisMetricsProvider(),
        _settings_provider(mock_redis_settings),
    )

    # Act
    client = await container.get(AsyncRedisClient)

    # Assert
    assert isinstance(client, InstrumentedRedis)
    await container.close()


@pytest.mark.asyncio
async def test__metrics_provider__metrics_extra_missing__raises_import_error_naming_the_extra(
    mock_redis_settings: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange
    mock_redis_settings.metrics_enabled = True
    container = _container(mock_redis_settings)
    for module in [key for key in sys.modules if key.startswith("redis_client_kit.metrics")]:
        monkeypatch.delitem(sys.modules, module)
    mock_deps = MagicMock()
    mock_deps.HAS_PROMETHEUS = False
    monkeypatch.setitem(sys.modules, "redis_client_kit.metrics._deps", mock_deps)

    # Act & Assert
    with pytest.raises(ImportError, match=r"redis-client-kit\[metrics\]"):
        await container.get(RedisMetricsProtocol | None)
    await container.close()
