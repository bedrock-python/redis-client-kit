"""Tests for exception handling in sync InstrumentedRedis."""

from unittest.mock import MagicMock, patch

import pytest

from redis_client_kit.protocols import RedisMetricsProtocol
from redis_client_kit.sync.instrumented import InstrumentedRedis, InstrumentedRedisCluster


@pytest.fixture
def mock_metrics() -> MagicMock:
    """Create a mock metrics instance."""
    return MagicMock(spec=RedisMetricsProtocol)


def test__instrumented_redis__non_uvloop_runtime_error__reraises(mock_metrics: MagicMock) -> None:
    # Arrange
    client = InstrumentedRedis(metrics=mock_metrics)

    # Act & Assert
    with patch("redis.Redis.execute_command") as mock_execute:
        mock_execute.side_effect = RuntimeError("Some other runtime error")
        with pytest.raises(RuntimeError, match="Some other runtime error"):
            client.execute_command("GET", "key")


def test__instrumented_redis_cluster__non_uvloop_runtime_error__reraises(mock_metrics: MagicMock) -> None:
    # Arrange
    with patch("redis.cluster.RedisCluster.__init__", return_value=None):
        client = InstrumentedRedisCluster(metrics=mock_metrics, host="localhost", port=6379)

    # Act & Assert
    with patch("redis.cluster.RedisCluster.execute_command") as mock_execute:
        mock_execute.side_effect = RuntimeError("Some other runtime error")
        with pytest.raises(RuntimeError, match="Some other runtime error"):
            client.execute_command("GET", "key")
