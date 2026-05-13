from unittest.mock import MagicMock, patch

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from redis_client_kit.aio import InstrumentedRedis, InstrumentedRedisCluster


@pytest.mark.asyncio
async def test__instrumented_redis__uvloop_handler_closed_error__translates_to_connection_error() -> None:
    # Arrange
    mock_metrics = MagicMock()
    client = InstrumentedRedis(host="localhost", port=6379, metrics=mock_metrics)
    msg = (
        "unable to perform operation on <TCPTransport closed=True reading=False 0x63001cea35e0>; the handler is closed"
    )

    # Act & Assert
    with patch("redis.asyncio.Redis.execute_command", side_effect=RuntimeError(msg)):
        with pytest.raises(RedisConnectionError) as exc_info:
            await client.execute_command("GET", "key")

        assert "the handler is closed" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test__instrumented_redis_cluster__uvloop_handler_closed_error__translates_to_connection_error() -> None:
    # Arrange
    mock_metrics = MagicMock()
    msg = (
        "unable to perform operation on <TCPTransport closed=True reading=False 0x63001cea35e0>; the handler is closed"
    )

    # Act & Assert
    with patch("redis.asyncio.cluster.RedisCluster.__init__", return_value=None):
        client = InstrumentedRedisCluster(metrics=mock_metrics)

        with patch("redis.asyncio.cluster.RedisCluster.execute_command", side_effect=RuntimeError(msg)):
            with pytest.raises(RedisConnectionError) as exc_info:
                await client.execute_command("GET", "key")

            assert "the handler is closed" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test__instrumented_redis__other_runtime_error__preserves_original_exception() -> None:
    # Arrange
    mock_metrics = MagicMock()
    client = InstrumentedRedis(host="localhost", port=6379, metrics=mock_metrics)

    # Act & Assert
    with patch("redis.asyncio.Redis.execute_command", side_effect=RuntimeError("some other error")):
        with pytest.raises(RuntimeError) as exc_info:
            await client.execute_command("GET", "key")

        assert "some other error" in str(exc_info.value)
        assert not isinstance(exc_info.value, RedisConnectionError)
