"""Tests for sync Redis client factory and lifecycle."""

from unittest.mock import MagicMock, patch

import pytest

from redis_client_kit.sync import (
    check_redis_health,
    close_redis_client,
    create_redis_client,
)


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


def test__create_redis_client__retry_disabled__excludes_retry_from_kwargs(
    mock_redis_settings: MagicMock,
) -> None:
    # Arrange
    mock_redis_settings.cluster.enabled = False
    mock_redis_settings.retry.enabled = False
    mock_metrics = MagicMock()

    # Act
    with patch("redis_client_kit.sync.factory.InstrumentedRedis") as mock_redis:
        create_redis_client(mock_redis_settings, metrics=mock_metrics)

        # Assert
        kwargs = mock_redis.call_args[1]
        assert "retry" not in kwargs


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
