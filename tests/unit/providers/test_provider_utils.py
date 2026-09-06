"""Tests for the connection retry helper used by the Dishka providers."""

from unittest.mock import AsyncMock, patch

import pytest

from redis_client_kit.providers.utils import retry_async_connection, safe_async_cleanup


@pytest.mark.asyncio
async def test__retry_async_connection__connect_succeeds__returns_without_sleeping() -> None:
    # Arrange
    connect = AsyncMock(return_value=True)

    # Act
    with patch("redis_client_kit.providers.utils.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await retry_async_connection(connect_func=connect, service_name="Redis")

    # Assert
    assert connect.await_count == 1
    mock_sleep.assert_not_awaited()


@pytest.mark.asyncio
async def test__retry_async_connection__connect_always_returns_false__raises_connection_error() -> None:
    # Arrange
    connect = AsyncMock(return_value=False)

    # Act & Assert
    mock_sleep = AsyncMock()
    with (
        patch("redis_client_kit.providers.utils.asyncio.sleep", mock_sleep),
        pytest.raises(ConnectionError, match="Redis did not report a healthy connection"),
    ):
        await retry_async_connection(connect_func=connect, service_name="Redis", max_attempts=3)

    assert connect.await_count == 3
    assert [call.args[0] for call in mock_sleep.await_args_list] == [1.0, 2.0]


@pytest.mark.asyncio
async def test__retry_async_connection__connect_recovers__returns_after_backoff() -> None:
    # Arrange
    connect = AsyncMock(side_effect=[False, True])

    # Act
    with patch("redis_client_kit.providers.utils.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await retry_async_connection(connect_func=connect, service_name="Redis", backoff_base=0.5)

    # Assert
    assert connect.await_count == 2
    mock_sleep.assert_awaited_once_with(0.5)


@pytest.mark.asyncio
async def test__retry_async_connection__connect_always_raises__reraises_original_error() -> None:
    # Arrange
    connect = AsyncMock(side_effect=OSError("no route to host"))

    # Act & Assert
    with (
        patch("redis_client_kit.providers.utils.asyncio.sleep", new_callable=AsyncMock),
        pytest.raises(OSError, match="no route to host"),
    ):
        await retry_async_connection(connect_func=connect, service_name="Redis", max_attempts=2)

    assert connect.await_count == 2


@pytest.mark.asyncio
async def test__safe_async_cleanup__cleanup_raises__swallows_error() -> None:
    # Arrange
    cleanup = AsyncMock(side_effect=RuntimeError("close failed"))

    # Act
    await safe_async_cleanup(cleanup_func=cleanup, service_name="Redis client", exception_type=OSError)

    # Assert
    cleanup.assert_awaited_once()
