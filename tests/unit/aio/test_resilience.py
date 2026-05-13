from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from redis.asyncio import RedisCluster
from redis.exceptions import BusyLoadingError, ClusterDownError, TimeoutError
from redis.retry import Retry

from redis_client_kit import check_async_redis_health, create_async_redis_client


def test__create_async_redis_client__retry_enabled__passes_retry_to_client(mock_redis_settings: MagicMock) -> None:
    # Arrange
    mock_redis_settings.retry.enabled = True
    mock_redis_settings.retry.max_attempts = 5
    mock_redis_settings.retry_backoff_base = 0.5
    mock_metrics = MagicMock()

    # Act
    with patch("redis_client_kit.aio.factory.InstrumentedRedis") as mock_redis:
        create_async_redis_client(mock_redis_settings, metrics=mock_metrics)

        # Assert
        kwargs = mock_redis.call_args[1]
        assert "retry" in kwargs
        assert isinstance(kwargs["retry"], Retry)


def test__create_async_redis_client__ssl_enabled__passes_ssl_config_to_client(mock_redis_settings: MagicMock) -> None:
    # Arrange
    mock_redis_settings.ssl.enabled = True
    mock_metrics = MagicMock()

    # Act
    with (
        patch("redis_client_kit.utils._validate_pem_format"),
        patch("redis_client_kit.aio.factory.InstrumentedRedis") as mock_redis,
    ):
        create_async_redis_client(mock_redis_settings, metrics=mock_metrics)

        # Assert
        kwargs = mock_redis.call_args[1]
        assert kwargs["ssl"] is True
        assert kwargs["ssl_ca_certs"] == mock_redis_settings.ssl.ca_certs
        assert kwargs["ssl_certfile"] == mock_redis_settings.ssl.certfile
        assert kwargs["ssl_keyfile"] == mock_redis_settings.ssl.keyfile


@pytest.mark.asyncio
async def test__check_async_redis_health__cluster_down_error__returns_false() -> None:
    # Arrange
    mock_client = AsyncMock(spec=RedisCluster)
    mock_client.ping.side_effect = ClusterDownError("Cluster is down during failover")

    # Act
    result = await check_async_redis_health(mock_client)

    # Assert
    assert result is False


@pytest.mark.parametrize(
    "exception",
    [
        BusyLoadingError("Redis is loading data"),
        TimeoutError("Connection timed out"),
    ],
    ids=["busy-loading", "timeout"],
)
@pytest.mark.asyncio
async def test__check_async_redis_health__recoverable_error__returns_false(exception: Exception) -> None:
    # Arrange
    mock_client = AsyncMock()
    mock_client.ping.side_effect = exception

    # Act
    result = await check_async_redis_health(mock_client)

    # Assert
    assert result is False
