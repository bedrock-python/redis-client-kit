"""Tests for sync Redis instrumented client metrics recording."""

from unittest.mock import MagicMock, patch

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from redis_client_kit.protocols import RedisMetricsProtocol
from redis_client_kit.sync.instrumented import InstrumentedRedis, InstrumentedRedisCluster


@pytest.fixture
def mock_metrics() -> MagicMock:
    """Create a mock metrics instance."""
    return MagicMock(spec=RedisMetricsProtocol)


def test__instrumented_redis__execute_command_success__records_metrics_and_pool_stats(
    mock_metrics: MagicMock,
) -> None:
    # Arrange
    client = InstrumentedRedis(metrics=mock_metrics)

    # Create mock pool with proper attributes (_available_connections + _in_use_connections)
    mock_pool = MagicMock()
    mock_pool._available_connections = [1, 2]  # 2 available connections
    mock_pool._in_use_connections = {3}  # 1 in-use connection (set, not list)
    client.connection_pool = mock_pool

    # Act
    with patch("redis.Redis.execute_command") as mock_execute:
        mock_execute.return_value = "OK"
        result = client.execute_command("SET", "key", "val")

    # Assert
    assert result == "OK"
    mock_metrics.record_pool_stats.assert_called_with(pool_size=3, pool_checked_out=1)
    mock_metrics.record_command.assert_called_with(command="SET", status="success", duration=pytest.approx(0, abs=1))


def test__instrumented_redis__execute_command_failure__records_error_metrics(
    mock_metrics: MagicMock,
) -> None:
    # Arrange
    client = InstrumentedRedis(metrics=mock_metrics)

    # Create mock pool with proper attributes
    mock_pool = MagicMock()
    mock_pool._available_connections = [1, 2]
    mock_pool._in_use_connections = {3}
    client.connection_pool = mock_pool

    # Act
    with patch("redis.Redis.execute_command") as mock_execute:
        mock_execute.side_effect = RedisConnectionError("Redis error")
        with pytest.raises(RedisConnectionError):
            client.execute_command("SET", "key", "val")

    # Assert
    mock_metrics.record_pool_stats.assert_called_with(pool_size=3, pool_checked_out=1)
    mock_metrics.record_command.assert_called_with(command="SET", status="error", duration=pytest.approx(0, abs=1))


def test__instrumented_redis__no_connection_pool__skips_pool_stats(
    mock_metrics: MagicMock,
) -> None:
    # Arrange
    client = InstrumentedRedis(metrics=mock_metrics)
    client.connection_pool = None

    # Act
    with patch("redis.Redis.execute_command") as mock_execute:
        mock_execute.return_value = "OK"
        result = client.execute_command("SET", "key", "val")

    # Assert
    assert result == "OK"
    mock_metrics.record_pool_stats.assert_not_called()
    mock_metrics.record_command.assert_called_with(command="SET", status="success", duration=pytest.approx(0, abs=1))


def test__instrumented_redis__pool_without_connections__records_zero_stats(
    mock_metrics: MagicMock,
) -> None:
    # Arrange
    client = InstrumentedRedis(metrics=mock_metrics)

    # Create mock pool with empty connections
    mock_pool = MagicMock()
    mock_pool._available_connections = []
    mock_pool._in_use_connections = set()
    client.connection_pool = mock_pool

    # Act
    with patch("redis.Redis.execute_command") as mock_execute:
        mock_execute.return_value = "OK"
        result = client.execute_command("SET", "key", "val")

    # Assert
    assert result == "OK"
    mock_metrics.record_pool_stats.assert_called_with(pool_size=0, pool_checked_out=0)
    mock_metrics.record_command.assert_called_with(command="SET", status="success", duration=pytest.approx(0, abs=1))


def test__instrumented_redis_cluster__execute_command_success__records_command_metrics(
    mock_metrics: MagicMock,
) -> None:
    # Arrange
    with patch("redis.cluster.RedisCluster.__init__", return_value=None):
        client = InstrumentedRedisCluster(metrics=mock_metrics, host="localhost", port=6379)

    # Act
    with patch("redis.cluster.RedisCluster.execute_command") as mock_execute:
        mock_execute.return_value = "OK"
        result = client.execute_command("SET", "key", "val")

    # Assert
    assert result == "OK"
    mock_metrics.record_command.assert_called_with(command="SET", status="success", duration=pytest.approx(0, abs=1))


def test__instrumented_redis_cluster__execute_command_failure__records_error_metrics(
    mock_metrics: MagicMock,
) -> None:
    # Arrange
    with patch("redis.cluster.RedisCluster.__init__", return_value=None):
        client = InstrumentedRedisCluster(metrics=mock_metrics, host="localhost", port=6379)

    # Act
    with patch("redis.cluster.RedisCluster.execute_command") as mock_execute:
        mock_execute.side_effect = RedisConnectionError("Cluster error")
        with pytest.raises(RedisConnectionError):
            client.execute_command("SET", "key", "val")

    # Assert
    mock_metrics.record_command.assert_called_with(command="SET", status="error", duration=pytest.approx(0, abs=1))


def test__instrumented_redis__pool_stats_exception__logs_and_continues(
    mock_metrics: MagicMock,
) -> None:
    # Arrange
    client = InstrumentedRedis(metrics=mock_metrics)

    # Create mock pool that raises exception when accessing attributes
    mock_pool = MagicMock()
    type(mock_pool)._available_connections = property(lambda self: (_ for _ in ()).throw(Exception("Pool error")))
    client.connection_pool = mock_pool

    # Act
    with patch("redis.Redis.execute_command") as mock_execute:
        mock_execute.return_value = "OK"
        result = client.execute_command("SET", "key", "val")

    # Assert - Should not raise, just log
    assert result == "OK"
    mock_metrics.record_command.assert_called_with(command="SET", status="success", duration=pytest.approx(0, abs=1))


def test__instrumented_redis__record_error_exception__logs_and_reraises_original(
    mock_metrics: MagicMock,
) -> None:
    # Arrange
    client = InstrumentedRedis(metrics=mock_metrics)
    mock_metrics.record_error.side_effect = Exception("Metrics error")

    # Act & Assert
    with patch("redis.Redis.execute_command") as mock_execute:
        mock_execute.side_effect = Exception("Redis error")
        with pytest.raises(Exception, match="Redis error"):
            client.execute_command("SET", "key", "val")


def test__instrumented_redis__record_command_exception__logs_and_continues(
    mock_metrics: MagicMock,
) -> None:
    # Arrange
    client = InstrumentedRedis(metrics=mock_metrics)
    mock_metrics.record_command.side_effect = Exception("Metrics error")

    # Act
    with patch("redis.Redis.execute_command") as mock_execute:
        mock_execute.return_value = "OK"
        result = client.execute_command("SET", "key", "val")

    # Assert - Should not raise, just log
    assert result == "OK"


def test__instrumented_redis__runtime_error_handler_closed__converts_to_connection_error(
    mock_metrics: MagicMock,
) -> None:
    # Arrange
    client = InstrumentedRedis(metrics=mock_metrics)

    # Act & Assert
    with patch("redis.Redis.execute_command") as mock_execute:
        mock_execute.side_effect = RuntimeError("the handler is closed")
        with pytest.raises(RedisConnectionError):
            client.execute_command("SET", "key", "val")


def test__instrumented_redis_cluster__runtime_error_handler_closed__converts_to_connection_error(
    mock_metrics: MagicMock,
) -> None:
    # Arrange
    with patch("redis.cluster.RedisCluster.__init__", return_value=None):
        client = InstrumentedRedisCluster(metrics=mock_metrics, host="localhost", port=6379)

    # Act & Assert
    with patch("redis.cluster.RedisCluster.execute_command") as mock_execute:
        mock_execute.side_effect = RuntimeError("the handler is closed")
        with pytest.raises(RedisConnectionError):
            client.execute_command("SET", "key", "val")


def test__instrumented_redis_cluster__record_error_exception__logs_and_reraises_original(
    mock_metrics: MagicMock,
) -> None:
    # Arrange
    with patch("redis.cluster.RedisCluster.__init__", return_value=None):
        client = InstrumentedRedisCluster(metrics=mock_metrics, host="localhost", port=6379)

    mock_metrics.record_error.side_effect = Exception("Metrics error")

    # Act & Assert
    with patch("redis.cluster.RedisCluster.execute_command") as mock_execute:
        mock_execute.side_effect = Exception("Cluster error")
        with pytest.raises(Exception, match="Cluster error"):
            client.execute_command("SET", "key", "val")


def test__instrumented_redis_cluster__record_command_exception__logs_and_continues(
    mock_metrics: MagicMock,
) -> None:
    # Arrange
    with patch("redis.cluster.RedisCluster.__init__", return_value=None):
        client = InstrumentedRedisCluster(metrics=mock_metrics, host="localhost", port=6379)

    mock_metrics.record_command.side_effect = Exception("Metrics error")

    # Act
    with patch("redis.cluster.RedisCluster.execute_command") as mock_execute:
        mock_execute.return_value = "OK"
        result = client.execute_command("SET", "key", "val")

    # Assert - Should not raise, just log
    assert result == "OK"
