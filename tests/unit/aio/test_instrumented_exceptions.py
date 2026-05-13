"""Tests for exception handling in InstrumentedRedis."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from redis_client_kit.aio.instrumented import InstrumentedRedis, InstrumentedRedisCluster
from redis_client_kit.protocols import RedisMetricsProtocol


@pytest.fixture
def mock_metrics() -> MagicMock:
    """Create a mock metrics instance."""
    return MagicMock(spec=RedisMetricsProtocol)


@pytest.mark.asyncio
async def test__instrumented_redis__pool_stats_exception__logs_and_continues(mock_metrics: MagicMock) -> None:
    # Arrange
    client = InstrumentedRedis(metrics=mock_metrics)

    # Create mock pool that raises exception when accessing attributes
    mock_pool = MagicMock()
    type(mock_pool)._all_connections = property(lambda self: (_ for _ in ()).throw(Exception("Pool error")))
    client.connection_pool = mock_pool

    # Act
    with patch("redis.asyncio.Redis.execute_command", new_callable=AsyncMock) as mock_execute:
        mock_execute.return_value = "OK"
        result = await client.execute_command("GET", "key")

    # Assert - Should not raise, just log
    assert result == "OK"
    mock_metrics.record_command.assert_called_once()


@pytest.mark.asyncio
async def test__instrumented_redis__record_error_exception__logs_and_reraises_original(mock_metrics: MagicMock) -> None:
    # Arrange
    client = InstrumentedRedis(metrics=mock_metrics)
    mock_metrics.record_error.side_effect = Exception("Metrics error")

    # Act & Assert
    with patch("redis.asyncio.Redis.execute_command", new_callable=AsyncMock) as mock_execute:
        mock_execute.side_effect = Exception("Redis error")
        with pytest.raises(Exception, match="Redis error"):
            await client.execute_command("GET", "key")


@pytest.mark.asyncio
async def test__instrumented_redis__record_command_exception__logs_and_continues(mock_metrics: MagicMock) -> None:
    # Arrange
    client = InstrumentedRedis(metrics=mock_metrics)
    mock_metrics.record_command.side_effect = Exception("Metrics error")

    # Act
    with patch("redis.asyncio.Redis.execute_command", new_callable=AsyncMock) as mock_execute:
        mock_execute.return_value = "OK"
        result = await client.execute_command("GET", "key")

    # Assert - Should not raise, just log
    assert result == "OK"


@pytest.mark.asyncio
async def test__instrumented_redis__non_uvloop_runtime_error__reraises(mock_metrics: MagicMock) -> None:
    # Arrange
    client = InstrumentedRedis(metrics=mock_metrics)

    # Act & Assert
    with patch("redis.asyncio.Redis.execute_command", new_callable=AsyncMock) as mock_execute:
        mock_execute.side_effect = RuntimeError("Some other runtime error")
        with pytest.raises(RuntimeError, match="Some other runtime error"):
            await client.execute_command("GET", "key")


@pytest.mark.asyncio
async def test__instrumented_redis_cluster__record_error_exception__logs_and_reraises_original(
    mock_metrics: MagicMock,
) -> None:
    # Arrange
    with patch("redis.asyncio.cluster.RedisCluster.__init__", return_value=None):
        client = InstrumentedRedisCluster(metrics=mock_metrics, host="localhost", port=6379)

    mock_metrics.record_error.side_effect = Exception("Metrics error")

    # Act & Assert
    with patch("redis.asyncio.cluster.RedisCluster.execute_command", new_callable=AsyncMock) as mock_execute:
        mock_execute.side_effect = Exception("Cluster error")
        with pytest.raises(Exception, match="Cluster error"):
            await client.execute_command("GET", "key")


@pytest.mark.asyncio
async def test__instrumented_redis_cluster__record_command_exception__logs_and_continues(
    mock_metrics: MagicMock,
) -> None:
    # Arrange
    with patch("redis.asyncio.cluster.RedisCluster.__init__", return_value=None):
        client = InstrumentedRedisCluster(metrics=mock_metrics, host="localhost", port=6379)

    mock_metrics.record_command.side_effect = Exception("Metrics error")

    # Act
    with patch("redis.asyncio.cluster.RedisCluster.execute_command", new_callable=AsyncMock) as mock_execute:
        mock_execute.return_value = "OK"
        result = await client.execute_command("GET", "key")

    # Assert - Should not raise, just log
    assert result == "OK"


@pytest.mark.asyncio
async def test__instrumented_redis_cluster__non_uvloop_runtime_error__reraises(mock_metrics: MagicMock) -> None:
    # Arrange
    with patch("redis.asyncio.cluster.RedisCluster.__init__", return_value=None):
        client = InstrumentedRedisCluster(metrics=mock_metrics, host="localhost", port=6379)

    # Act & Assert
    with patch("redis.asyncio.cluster.RedisCluster.execute_command", new_callable=AsyncMock) as mock_execute:
        mock_execute.side_effect = RuntimeError("Some other runtime error")
        with pytest.raises(RuntimeError, match="Some other runtime error"):
            await client.execute_command("GET", "key")
