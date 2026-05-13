"""Tests for sync Redis client lifecycle functions."""

from unittest.mock import MagicMock

import pytest
from redis.exceptions import RedisError

from redis_client_kit.sync import check_redis_health, close_redis_client


def test__close_redis_client__redis_error__logs_warning_without_raising() -> None:
    # Arrange
    mock_client = MagicMock()
    mock_client.close.side_effect = RedisError("Redis error during close")

    # Act & Assert - Should not raise
    close_redis_client(mock_client)

    # Assert
    mock_client.close.assert_called_once()


def test__close_redis_client__timeout_with_retry__logs_and_continues() -> None:
    # Arrange
    mock_client = MagicMock()
    mock_client.close.side_effect = TimeoutError("Timeout during close")

    # Act & Assert - Should not raise
    close_redis_client(mock_client)

    # Assert
    mock_client.close.assert_called_once()


def test__check_redis_health__redis_error__returns_false() -> None:
    # Arrange
    mock_client = MagicMock()
    mock_client.ping.side_effect = RedisError("Redis connection error")

    # Act
    result = check_redis_health(mock_client)

    # Assert
    assert result is False


def test__check_redis_health__timeout_error__returns_false() -> None:
    # Arrange
    mock_client = MagicMock()
    mock_client.ping.side_effect = TimeoutError("Connection timeout")

    # Act
    result = check_redis_health(mock_client)

    # Assert
    assert result is False


def test__close_redis_client__keyboard_interrupt__reraises() -> None:
    # Arrange
    mock_client = MagicMock()
    mock_client.close.side_effect = KeyboardInterrupt()

    # Act & Assert
    with pytest.raises(KeyboardInterrupt):
        close_redis_client(mock_client)


def test__close_redis_client__system_exit__reraises() -> None:
    # Arrange
    mock_client = MagicMock()
    mock_client.close.side_effect = SystemExit(1)

    # Act & Assert
    with pytest.raises(SystemExit):
        close_redis_client(mock_client)


def test__check_redis_health__keyboard_interrupt__reraises() -> None:
    # Arrange
    mock_client = MagicMock()
    mock_client.ping.side_effect = KeyboardInterrupt()

    # Act & Assert
    with pytest.raises(KeyboardInterrupt):
        check_redis_health(mock_client)


def test__check_redis_health__system_exit__reraises() -> None:
    # Arrange
    mock_client = MagicMock()
    mock_client.ping.side_effect = SystemExit(1)

    # Act & Assert
    with pytest.raises(SystemExit):
        check_redis_health(mock_client)


def test__check_redis_health__unexpected_exception__returns_false() -> None:
    # Arrange
    mock_client = MagicMock()
    mock_client.ping.side_effect = ValueError("Unexpected error")

    # Act
    result = check_redis_health(mock_client)

    # Assert
    assert result is False
