"""Tests for AsyncRedisProvider registration and startup behaviour."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from dishka import Provider, Scope, make_async_container, provide

from redis_client_kit import AsyncRedisClient
from redis_client_kit.aio import InstrumentedRedis
from redis_client_kit.config import RedisSettingsProtocol
from redis_client_kit.protocols import RedisMetricsProtocol
from redis_client_kit.providers import AsyncRedisProvider


def _settings_provider(settings: MagicMock) -> Provider:
    provider = Provider(scope=Scope.APP)
    provider.provide(lambda: settings, provides=RedisSettingsProtocol)
    return provider


class _MetricsProvider(Provider):
    scope = Scope.APP

    @provide
    def metrics(self) -> RedisMetricsProtocol | None:
        return MagicMock(spec=RedisMetricsProtocol)


@pytest.mark.asyncio
async def test__provider__redis_unreachable__fails_container_startup(mock_redis_settings: MagicMock) -> None:
    # Arrange
    container = make_async_container(AsyncRedisProvider(), _settings_provider(mock_redis_settings))

    # Act & Assert
    with (
        patch("redis_client_kit.providers.redis.check_async_redis_health", new_callable=AsyncMock) as mock_health,
        patch("redis_client_kit.providers.utils.asyncio.sleep", new_callable=AsyncMock),
    ):
        mock_health.return_value = False

        with pytest.raises(ConnectionError, match="Redis did not report a healthy connection"):
            await container.get(AsyncRedisClient)

    assert mock_health.await_count == 3
    await container.close()


@pytest.mark.asyncio
async def test__provider__redis_reachable__yields_client(mock_redis_settings: MagicMock) -> None:
    # Arrange
    container = make_async_container(AsyncRedisProvider(), _settings_provider(mock_redis_settings))

    # Act
    with patch("redis_client_kit.providers.redis.check_async_redis_health", new_callable=AsyncMock) as mock_health:
        mock_health.return_value = True
        client = await container.get(AsyncRedisClient)

    # Assert
    assert client is not None
    mock_health.assert_awaited_once()
    await container.close()


@pytest.mark.asyncio
async def test__provider__health_check_disabled__skips_the_check(mock_redis_settings: MagicMock) -> None:
    # Arrange
    container = make_async_container(
        AsyncRedisProvider(check_health_on_startup=False),
        _settings_provider(mock_redis_settings),
    )

    # Act
    with patch("redis_client_kit.providers.redis.check_async_redis_health", new_callable=AsyncMock) as mock_health:
        client = await container.get(AsyncRedisClient)

    # Assert
    assert client is not None
    mock_health.assert_not_awaited()
    await container.close()


@pytest.mark.asyncio
async def test__provider__default_metrics_disabled__keeps_metrics_provider_registered_first(
    mock_redis_settings: MagicMock,
) -> None:
    # Arrange
    container = make_async_container(
        _MetricsProvider(),
        AsyncRedisProvider(check_health_on_startup=False, provide_default_metrics=False),
        _settings_provider(mock_redis_settings),
    )

    # Act
    client = await container.get(AsyncRedisClient)

    # Assert
    assert isinstance(client, InstrumentedRedis)
    await container.close()


@pytest.mark.asyncio
async def test__provider__registered_first__keeps_metrics_provider(mock_redis_settings: MagicMock) -> None:
    # Arrange
    container = make_async_container(
        AsyncRedisProvider(check_health_on_startup=False),
        _MetricsProvider(),
        _settings_provider(mock_redis_settings),
    )

    # Act
    client = await container.get(AsyncRedisClient)

    # Assert
    assert isinstance(client, InstrumentedRedis)
    await container.close()
