"""Tests for sync Redis client factory and lifecycle."""

from unittest.mock import MagicMock, patch

import pytest
from redis.backoff import NoBackoff
from redis.exceptions import OutOfMemoryError, ReadOnlyError
from redis.retry import Retry

from redis_client_kit.sync import (
    check_redis_health,
    close_redis_client,
    create_redis_client,
)
from redis_client_kit.utils import WRITE_PROBE_TTL_S


@pytest.mark.parametrize(
    "cluster_mode, expected_class",
    [(False, "InstrumentedRedis"), (True, "InstrumentedRedisCluster")],
    ids=["single-node", "cluster"],
)
def test__create_redis_client__with_metrics__creates_instrumented_client(
    mock_redis_settings: MagicMock, cluster_mode: bool, expected_class: str
) -> None:
    # Arrange
    mock_redis_settings.cluster.enabled = cluster_mode
    mock_metrics = MagicMock()

    # Act
    with patch(f"redis_client_kit.sync.factory.{expected_class}") as mock_class:
        create_redis_client(mock_redis_settings, metrics=mock_metrics)

        # Assert
        mock_class.assert_called_once()


def test__create_redis_client__without_metrics__creates_plain_client(
    mock_redis_settings: MagicMock,
) -> None:
    # Arrange
    mock_redis_settings.cluster.enabled = False

    # Act
    with patch("redis_client_kit.sync.factory.Redis") as mock_redis:
        create_redis_client(mock_redis_settings, metrics=None)

        # Assert
        mock_redis.assert_called_once()


def test__create_redis_client__cluster_with_nodes__creates_client_with_startup_nodes(
    mock_redis_settings: MagicMock,
) -> None:
    # Arrange
    mock_redis_settings.cluster.enabled = True
    mock_redis_settings.cluster.nodes = ["node1:6379", "node2:6379"]
    mock_metrics = MagicMock()

    # Act
    with patch("redis_client_kit.sync.factory.InstrumentedRedisCluster") as mock_cluster:
        create_redis_client(mock_redis_settings, metrics=mock_metrics)

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
def test__create_redis_client__cluster_without_nodes__uses_primary_host(
    mock_redis_settings: MagicMock, nodes_value: list[str] | None
) -> None:
    # Arrange
    mock_redis_settings.cluster.enabled = True
    mock_redis_settings.connection.host = "cluster-host"
    mock_redis_settings.cluster.nodes = nodes_value
    mock_metrics = MagicMock()

    # Act
    with patch("redis_client_kit.sync.factory.InstrumentedRedisCluster") as mock_cluster:
        create_redis_client(mock_redis_settings, metrics=mock_metrics)

        # Assert
        mock_cluster.assert_called_once()
        kwargs = mock_cluster.call_args[1]
        assert len(kwargs["startup_nodes"]) == 1
        assert kwargs["startup_nodes"][0].host == "cluster-host"


@pytest.mark.parametrize(
    "cluster_mode, expected_class",
    [(False, "InstrumentedRedis"), (True, "InstrumentedRedisCluster")],
    ids=["single-node", "cluster"],
)
def test__create_redis_client__retry_disabled__passes_zero_retries_to_client(
    mock_redis_settings: MagicMock, cluster_mode: bool, expected_class: str
) -> None:
    # Arrange
    mock_redis_settings.cluster.enabled = cluster_mode
    mock_redis_settings.retry.enabled = False
    mock_metrics = MagicMock()

    # Act
    with patch(f"redis_client_kit.sync.factory.{expected_class}") as mock_class:
        create_redis_client(mock_redis_settings, metrics=mock_metrics)

        # Assert
        retry = mock_class.call_args[1]["retry"]
        assert isinstance(retry, Retry)
        assert retry._retries == 0
        assert isinstance(retry._backoff, NoBackoff)


def test__close_redis_client__valid_client__calls_close() -> None:
    # Arrange
    mock_client = MagicMock()

    # Act
    close_redis_client(mock_client)

    # Assert
    mock_client.close.assert_called_once()


def test__close_redis_client__exception__logs_warning_without_raising() -> None:
    # Arrange
    mock_client = MagicMock()
    mock_client.close.side_effect = Exception("Unexpected error")

    # Act
    close_redis_client(mock_client)

    # Assert - Should not raise


def test__check_redis_health__successful_ping__returns_true() -> None:
    # Arrange
    mock_client = MagicMock()
    mock_client.ping.return_value = True

    # Act
    result = check_redis_health(mock_client)

    # Assert
    assert result is True


def test__check_redis_health__cluster_all_nodes_healthy__returns_true() -> None:
    # Arrange
    mock_client = MagicMock()
    mock_client.ping.return_value = {"node1": True, "node2": True}

    # Act
    result = check_redis_health(mock_client)

    # Assert
    assert result is True


def test__check_redis_health__cluster_partial_failure__returns_false() -> None:
    # Arrange
    mock_client = MagicMock()
    mock_client.ping.return_value = {"node1": True, "node2": False}

    # Act
    result = check_redis_health(mock_client)

    # Assert
    assert result is False


@pytest.mark.parametrize(
    "exception",
    [Exception("redis error"), Exception("generic error")],
    ids=["redis-error", "generic-exception"],
)
def test__check_redis_health__exception_raised__returns_false(exception: Exception) -> None:
    # Arrange
    mock_client = MagicMock()
    mock_client.ping.side_effect = exception

    # Act
    result = check_redis_health(mock_client)

    # Assert
    assert result is False


def test__check_redis_health__no_write_key__pings_only() -> None:
    # Arrange
    mock_client = MagicMock()
    mock_client.ping.return_value = True

    # Act
    result = check_redis_health(mock_client)

    # Assert
    assert result is True
    mock_client.set.assert_not_called()


def test__check_redis_health__write_key__sets_it_with_a_ttl_after_the_ping() -> None:
    # Arrange
    mock_client = MagicMock()
    mock_client.ping.return_value = True
    mock_client.set.return_value = True

    # Act
    result = check_redis_health(mock_client, write_key="myapp:health")

    # Assert
    assert result is True
    mock_client.ping.assert_called_once()
    mock_client.set.assert_called_once_with("myapp:health", "1", ex=WRITE_PROBE_TTL_S)


@pytest.mark.parametrize(
    "exception",
    [
        ReadOnlyError("You can't write against a read only replica."),
        OutOfMemoryError("command not allowed when used memory > 'maxmemory'."),
    ],
    ids=["read-only-replica", "out-of-memory"],
)
def test__check_redis_health__write_refused__returns_false(exception: Exception) -> None:
    # Arrange
    mock_client = MagicMock()
    mock_client.ping.return_value = True
    mock_client.set.side_effect = exception

    # Act
    result = check_redis_health(mock_client, write_key="myapp:health")

    # Assert
    assert result is False


def test__check_redis_health__failed_ping_with_write_key__does_not_write() -> None:
    # Arrange
    mock_client = MagicMock()
    mock_client.ping.return_value = False

    # Act
    result = check_redis_health(mock_client, write_key="myapp:health")

    # Assert
    assert result is False
    mock_client.set.assert_not_called()


def test__check_redis_health__cluster_with_write_key__pings_every_node_then_writes() -> None:
    # Arrange
    mock_client = MagicMock()
    mock_client.ping.return_value = {"node1": True, "node2": True}
    mock_client.set.return_value = True

    # Act
    result = check_redis_health(mock_client, write_key="myapp:health")

    # Assert
    assert result is True
    mock_client.set.assert_called_once_with("myapp:health", "1", ex=WRITE_PROBE_TTL_S)
