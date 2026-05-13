"""Tests for sync instrumented Redis client initialization."""

from unittest.mock import MagicMock, patch

import pytest

from redis_client_kit.protocols import RedisMetricsProtocol
from redis_client_kit.sync.instrumented import InstrumentedRedis, InstrumentedRedisCluster


@pytest.fixture
def mock_metrics() -> MagicMock:
    """Create a mock metrics instance."""
    return MagicMock(spec=RedisMetricsProtocol)


def test__instrumented_redis__initialization__stores_metrics(
    mock_metrics: MagicMock,
) -> None:
    # Arrange & Act
    client = InstrumentedRedis(metrics=mock_metrics)

    # Assert
    assert client._metrics is mock_metrics


def test__instrumented_redis__with_connection_params__passes_to_base(
    mock_metrics: MagicMock,
) -> None:
    # Arrange & Act
    client = InstrumentedRedis(
        metrics=mock_metrics,
        host="localhost",
        port=6379,
        db=0,
        decode_responses=True,
    )

    # Assert
    assert client._metrics is mock_metrics
    assert client.connection_pool.connection_kwargs["host"] == "localhost"
    assert client.connection_pool.connection_kwargs["port"] == 6379
    assert client.connection_pool.connection_kwargs["db"] == 0
    assert client.connection_pool.connection_kwargs["decode_responses"] is True


def test__instrumented_redis_cluster__initialization__stores_metrics(
    mock_metrics: MagicMock,
) -> None:
    # Arrange & Act
    with patch("redis.cluster.RedisCluster.__init__", return_value=None):
        client = InstrumentedRedisCluster(
            metrics=mock_metrics,
            host="localhost",
            port=6379,
        )

        # Assert
        assert client._metrics is mock_metrics


def test__instrumented_redis_cluster__with_connection_params__passes_to_base(
    mock_metrics: MagicMock,
) -> None:
    # Arrange & Act
    with patch("redis.cluster.RedisCluster.__init__", return_value=None):
        client = InstrumentedRedisCluster(
            metrics=mock_metrics,
            host="localhost",
            port=6379,
            decode_responses=True,
        )

        # Assert
        assert client._metrics is mock_metrics
