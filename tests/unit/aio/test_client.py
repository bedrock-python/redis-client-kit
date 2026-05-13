import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from redis.asyncio.cluster import RedisCluster
from redis.exceptions import RedisError

from redis_client_kit.aio import (
    check_async_redis_health,
    close_async_redis_client,
    create_async_redis_client,
)


@pytest.mark.parametrize(
    "cluster_mode, expected_class",
    [
        (False, "InstrumentedRedis"),
        (True, "InstrumentedRedisCluster"),
    ],
    ids=["single-node", "cluster"],
)
def test__create_async_redis_client__with_metrics__creates_instrumented_client(
    mock_redis_settings: MagicMock, cluster_mode: bool, expected_class: str
) -> None:
    # Arrange
    mock_redis_settings.cluster.enabled = cluster_mode
    mock_metrics = MagicMock()

    # Act
    with patch(f"redis_client_kit.aio.factory.{expected_class}") as mock_class:
        create_async_redis_client(mock_redis_settings, metrics=mock_metrics)

        # Assert
        mock_class.assert_called_once()


def test__create_async_redis_client__cluster_with_nodes__creates_client_with_startup_nodes(
    mock_redis_settings: MagicMock,
) -> None:
    # Arrange
    mock_redis_settings.cluster.enabled = True
    mock_redis_settings.cluster.nodes = ["node1:6379", "node2:6379"]
    mock_metrics = MagicMock()

    # Act
    with patch("redis_client_kit.aio.factory.InstrumentedRedisCluster") as mock_cluster:
        create_async_redis_client(mock_redis_settings, metrics=mock_metrics)

        # Assert
        mock_cluster.assert_called_once()
        kwargs = mock_cluster.call_args[1]
        assert len(kwargs["startup_nodes"]) == 2
        assert kwargs["startup_nodes"][0].host == "node1"
        assert kwargs["startup_nodes"][1].host == "node2"


@pytest.mark.parametrize(
    "nodes_value",
    [None, []],
    ids=["none", "empty-list"],
)
def test__create_async_redis_client__cluster_without_nodes__uses_primary_host(
    mock_redis_settings: MagicMock, nodes_value: list[str] | None
) -> None:
    # Arrange
    mock_redis_settings.cluster.enabled = True
    mock_redis_settings.connection.host = "cluster-host"
    mock_redis_settings.cluster.nodes = nodes_value
    mock_metrics = MagicMock()

    # Act
    with patch("redis_client_kit.aio.factory.InstrumentedRedisCluster") as mock_cluster:
        create_async_redis_client(mock_redis_settings, metrics=mock_metrics)

        # Assert
        mock_cluster.assert_called_once()
        kwargs = mock_cluster.call_args[1]
        assert len(kwargs["startup_nodes"]) == 1
        assert kwargs["startup_nodes"][0].host == "cluster-host"


def test__create_async_redis_client__cluster_without_metrics__creates_uninstrumented_cluster(
    mock_redis_settings: MagicMock,
) -> None:
    # Arrange
    mock_redis_settings.cluster.enabled = True
    mock_redis_settings.cluster.nodes = ["node1:6379", "node2:6379"]

    # Act
    with patch("redis_client_kit.aio.factory.RedisCluster") as mock_cluster:
        create_async_redis_client(mock_redis_settings, metrics=None)

        # Assert
        mock_cluster.assert_called_once()
        kwargs = mock_cluster.call_args[1]
        assert "metrics" not in kwargs
        assert len(kwargs["startup_nodes"]) == 2


def test__create_async_redis_client__retry_disabled__excludes_retry_from_kwargs(
    mock_redis_settings: MagicMock,
) -> None:
    # Arrange
    mock_redis_settings.cluster.enabled = False
    mock_redis_settings.retry.enabled = False
    mock_metrics = MagicMock()

    # Act
    with patch("redis_client_kit.aio.factory.InstrumentedRedis") as mock_redis:
        create_async_redis_client(mock_redis_settings, metrics=mock_metrics)

        # Assert
        kwargs = mock_redis.call_args[1]
        assert "retry" not in kwargs


@pytest.mark.asyncio
async def test__close_async_redis_client__valid_client__calls_aclose() -> None:
    # Arrange
    mock_client = AsyncMock()

    # Act
    await close_async_redis_client(mock_client)

    # Assert
    mock_client.aclose.assert_called_once()


@pytest.mark.asyncio
async def test__close_async_redis_client__timeout__logs_warning_without_raising() -> None:
    # Arrange
    mock_client = AsyncMock()

    # Act
    with patch("asyncio.wait_for", side_effect=TimeoutError()):
        await close_async_redis_client(mock_client)

    # Assert
    # Should not raise


@pytest.mark.asyncio
async def test__close_async_redis_client__generic_exception__logs_warning_without_raising() -> None:
    # Arrange
    mock_client = AsyncMock()
    mock_client.aclose.side_effect = Exception("Unexpected error")

    # Act
    await close_async_redis_client(mock_client)

    # Assert
    # Should not raise


@pytest.mark.asyncio
async def test__close_async_redis_client__cancelled_error__reraises_exception() -> None:
    # Arrange
    mock_client = AsyncMock()
    mock_client.aclose.side_effect = asyncio.CancelledError()

    # Act & Assert
    with pytest.raises(asyncio.CancelledError):
        await close_async_redis_client(mock_client)


@pytest.mark.asyncio
async def test__check_async_redis_health__successful_ping__returns_true() -> None:
    # Arrange
    mock_client = AsyncMock()
    mock_client.ping.return_value = True

    # Act
    result = await check_async_redis_health(mock_client)

    # Assert
    assert result is True


@pytest.mark.asyncio
async def test__check_async_redis_health__cluster_all_nodes_healthy__returns_true() -> None:
    # Arrange
    mock_client = AsyncMock(spec=RedisCluster)
    mock_client.ping = AsyncMock(return_value={"node1": True, "node2": True})

    # Act
    result = await check_async_redis_health(mock_client)

    # Assert
    assert result is True


@pytest.mark.asyncio
async def test__check_async_redis_health__cluster_partial_failure__returns_false() -> None:
    # Arrange
    mock_client = AsyncMock(spec=RedisCluster)
    mock_client.ping = AsyncMock(return_value={"node1": True, "node2": False})

    # Act
    result = await check_async_redis_health(mock_client)

    # Assert
    assert result is False


@pytest.mark.parametrize(
    "exception",
    [RedisError("redis error"), Exception("generic error")],
    ids=["redis-error", "generic-exception"],
)
@pytest.mark.asyncio
async def test__check_async_redis_health__exception_raised__returns_false(exception: Exception) -> None:
    # Arrange
    mock_client = AsyncMock()
    mock_client.ping.side_effect = exception

    # Act
    result = await check_async_redis_health(mock_client)

    # Assert
    assert result is False


@pytest.mark.asyncio
async def test__check_async_redis_health__cancelled_error__reraises_exception() -> None:
    # Arrange
    mock_client = AsyncMock()
    mock_client.ping.side_effect = asyncio.CancelledError()

    # Act & Assert
    with pytest.raises(asyncio.CancelledError):
        await check_async_redis_health(mock_client)
