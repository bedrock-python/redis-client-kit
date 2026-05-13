from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from redis_client_kit.aio import InstrumentedRedis, InstrumentedRedisCluster
from redis_client_kit.protocols import RedisMetricsProtocol


@pytest.fixture
def mock_metrics() -> MagicMock:
    return MagicMock(spec=RedisMetricsProtocol)


@pytest.mark.asyncio
async def test__instrumented_redis__execute_command_success__records_metrics_and_pool_stats(
    mock_metrics: MagicMock,
) -> None:
    # Arrange
    client = InstrumentedRedis(metrics=mock_metrics)
    client.connection_pool = MagicMock()
    client.connection_pool._all_connections = [1, 2, 3]
    client.connection_pool._in_use_connections = [1]

    # Act
    with patch("redis.asyncio.Redis.execute_command", new_callable=AsyncMock) as mock_execute:
        mock_execute.return_value = "OK"
        result = await client.execute_command("SET", "key", "val")

    # Assert
    assert result == "OK"
    mock_metrics.record_pool_stats.assert_called_with(pool_size=3, pool_checked_out=1)
    mock_metrics.record_command.assert_called_with(command="SET", status="success", duration=pytest.approx(0, abs=1))


@pytest.mark.asyncio
async def test__instrumented_redis__execute_command_error__records_error_metrics(
    mock_metrics: MagicMock,
) -> None:
    # Arrange
    client = InstrumentedRedis(metrics=mock_metrics)

    # Act & Assert
    with patch("redis.asyncio.Redis.execute_command", new_callable=AsyncMock) as mock_execute:
        mock_execute.side_effect = Exception("test error")

        with pytest.raises(Exception, match="test error"):
            await client.execute_command("GET", "key")

        mock_metrics.record_error.assert_called_with(error_type="Exception")
        mock_metrics.record_command.assert_called_with(command="GET", status="error", duration=pytest.approx(0, abs=1))


@pytest.mark.asyncio
async def test__instrumented_redis_cluster__execute_command_success__records_command_metrics(
    mock_metrics: MagicMock,
) -> None:
    # Arrange
    client = InstrumentedRedisCluster(host="localhost", port=6379, metrics=mock_metrics)

    # Act
    with patch("redis.asyncio.cluster.RedisCluster.execute_command", new_callable=AsyncMock) as mock_execute:
        mock_execute.return_value = "PONG"
        result = await client.execute_command("PING")

    # Assert
    assert result == "PONG"
    mock_metrics.record_command.assert_called_with(command="PING", status="success", duration=pytest.approx(0, abs=1))


@pytest.mark.asyncio
async def test__instrumented_redis_cluster__execute_command_error__records_error_metrics(
    mock_metrics: MagicMock,
) -> None:
    # Arrange
    client = InstrumentedRedisCluster(host="localhost", port=6379, metrics=mock_metrics)

    # Act & Assert
    with patch("redis.asyncio.cluster.RedisCluster.execute_command", new_callable=AsyncMock) as mock_execute:
        mock_execute.side_effect = Exception("cluster error")

        with pytest.raises(Exception, match="cluster error"):
            await client.execute_command("PING")

        mock_metrics.record_error.assert_called_with(error_type="Exception")
        mock_metrics.record_command.assert_called_with(command="PING", status="error", duration=pytest.approx(0, abs=1))
