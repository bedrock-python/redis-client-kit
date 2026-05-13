import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from redis.asyncio.cluster import RedisCluster
from redis.exceptions import RedisError

from redis_client_kit.aio.client import (
    check_async_redis_health,
    close_async_redis_client,
    create_async_redis_client,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "cluster_mode, expected_class",
    [
        (False, "InstrumentedRedis"),
        (True, "InstrumentedRedisCluster"),
    ],
)
def test_create_async_redis_client_modes(
    mock_redis_settings: MagicMock, cluster_mode: bool, expected_class: str
) -> None:
    """Verify that the correct client class is instantiated based on cluster_mode."""
    mock_redis_settings.cluster.enabled = cluster_mode
    mock_metrics = MagicMock()

    with patch(f"redis_client_kit.aio.client.{expected_class}") as mock_class:
        create_async_redis_client(mock_redis_settings, metrics=mock_metrics)
        mock_class.assert_called_once()


def test_create_async_redis_cluster(mock_redis_settings: MagicMock) -> None:
    """Verify RedisCluster initialization with specific nodes."""
    mock_redis_settings.cluster.enabled = True
    mock_redis_settings.cluster.nodes = ["node1:6379", "node2:6379"]

    with patch("redis_client_kit.aio.client.InstrumentedRedisCluster") as mock_cluster:
        create_async_redis_client(mock_redis_settings)
        mock_cluster.assert_called_once()
        kwargs = mock_cluster.call_args[1]
        assert len(kwargs["startup_nodes"]) == 2
        assert kwargs["startup_nodes"][0].host == "node1"
        assert kwargs["startup_nodes"][1].host == "node2"


def test_create_async_redis_cluster_no_nodes(mock_redis_settings: MagicMock) -> None:
    """Verify RedisCluster initialization when no nodes are provided (uses primary host)."""
    mock_redis_settings.cluster.enabled = True
    mock_redis_settings.connection.host = "cluster-host"
    mock_redis_settings.cluster.nodes = None

    with patch("redis_client_kit.aio.client.InstrumentedRedisCluster") as mock_cluster:
        create_async_redis_client(mock_redis_settings)
        mock_cluster.assert_called_once()
        kwargs = mock_cluster.call_args[1]
        assert len(kwargs["startup_nodes"]) == 1
        assert kwargs["startup_nodes"][0].host == "cluster-host"


def test_create_async_redis_cluster_empty_nodes(mock_redis_settings: MagicMock) -> None:
    """Verify RedisCluster initialization when cluster_nodes is an empty list."""
    mock_redis_settings.cluster.enabled = True
    mock_redis_settings.connection.host = "cluster-host"
    mock_redis_settings.cluster.nodes = []

    with patch("redis_client_kit.aio.client.InstrumentedRedisCluster") as mock_cluster:
        create_async_redis_client(mock_redis_settings)
        mock_cluster.assert_called_once()
        kwargs = mock_cluster.call_args[1]
        assert len(kwargs["startup_nodes"]) == 1
        assert kwargs["startup_nodes"][0].host == "cluster-host"


@pytest.mark.asyncio
async def test_close_async_redis_client() -> None:
    """Verify that aclose is called when closing the client."""
    mock_client = AsyncMock()
    await close_async_redis_client(mock_client)
    mock_client.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_check_async_redis_health_success() -> None:
    """Verify health check returns True on successful ping."""
    mock_client = AsyncMock()
    mock_client.ping.return_value = True
    assert await check_async_redis_health(mock_client) is True


@pytest.mark.asyncio
async def test_check_async_redis_health_cluster_success() -> None:
    """Verify health check returns True when all cluster nodes respond successfully."""
    mock_client = AsyncMock(spec=RedisCluster)
    # Explicitly set ping as AsyncMock to ensure it's awaitable
    mock_client.ping = AsyncMock(return_value={"node1": True, "node2": True})
    assert await check_async_redis_health(mock_client) is True


@pytest.mark.asyncio
async def test_check_async_redis_health_cluster_partial_failure() -> None:
    """Verify health check returns False when any cluster node fails ping."""
    mock_client = AsyncMock(spec=RedisCluster)
    # Explicitly set ping as AsyncMock to ensure it's awaitable
    mock_client.ping = AsyncMock(return_value={"node1": True, "node2": False})
    assert await check_async_redis_health(mock_client) is False


@pytest.mark.asyncio
async def test_check_async_redis_health_redis_error() -> None:
    """Verify health check returns False on RedisError."""
    mock_client = AsyncMock()
    mock_client.ping.side_effect = RedisError("redis error")
    assert await check_async_redis_health(mock_client) is False


@pytest.mark.asyncio
async def test_check_async_redis_health_generic_exception() -> None:
    """Verify health check returns False on any generic exception."""
    mock_client = AsyncMock()
    mock_client.ping.side_effect = Exception("generic error")
    assert await check_async_redis_health(mock_client) is False


def test_create_async_redis_no_retry(mock_redis_settings: MagicMock) -> None:
    """Verify that retry object is not passed to Redis when retry is disabled."""
    mock_redis_settings.cluster.enabled = False
    mock_redis_settings.retry.enabled = False

    with patch("redis_client_kit.aio.client.InstrumentedRedis") as mock_redis:
        create_async_redis_client(mock_redis_settings)
        kwargs = mock_redis.call_args[1]
        assert "retry" not in kwargs


@pytest.mark.asyncio
async def test_close_async_redis_client_timeout() -> None:
    """Verify handling of timeout during client closure."""
    mock_client = AsyncMock()
    # Mock asyncio.wait_for to raise TimeoutError
    with patch("asyncio.wait_for", side_effect=TimeoutError()):
        # Should not raise
        await close_async_redis_client(mock_client)


@pytest.mark.asyncio
async def test_close_async_redis_client_exception() -> None:
    """Verify handling of generic exception during client closure."""
    mock_client = AsyncMock()
    mock_client.aclose.side_effect = Exception("Unexpected error")
    # Should not raise
    await close_async_redis_client(mock_client)


@pytest.mark.asyncio
async def test_close_async_redis_client_cancelled() -> None:
    """Verify that CancelledError is re-raised during client closure."""
    mock_client = AsyncMock()
    mock_client.aclose.side_effect = asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        await close_async_redis_client(mock_client)


@pytest.mark.asyncio
async def test_check_async_redis_health_cancelled() -> None:
    """Verify that CancelledError is re-raised during health check."""
    mock_client = AsyncMock()
    mock_client.ping.side_effect = asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        await check_async_redis_health(mock_client)
