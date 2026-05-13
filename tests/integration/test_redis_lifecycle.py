"""Integration tests for Redis client lifecycle and cancellation safety."""

import asyncio

import pytest
from testcontainers.redis import RedisContainer

from redis_client_kit import check_async_redis_health, close_async_redis_client, create_async_redis_client

from .conftest import FakeRedisSettings, is_docker_available

# Skip all tests in this module if docker is not available
pytestmark = pytest.mark.skipif(not is_docker_available(), reason="Docker is not available")


@pytest.mark.asyncio
async def test__redis_client__full_lifecycle__completes_successfully(redis_container: RedisContainer) -> None:
    # Arrange
    settings = FakeRedisSettings()
    settings.connection.host = redis_container.get_container_host_ip()
    settings.connection.port = int(redis_container.get_exposed_port(redis_container.port))
    client = create_async_redis_client(settings)

    try:
        # Act - Check health
        is_healthy = await check_async_redis_health(client)

        # Assert
        assert is_healthy is True

        # Act - Basic operations
        await client.set("test_key", "test_value")
        val = await client.get("test_key")

        # Assert
        assert val == "test_value"

    finally:
        # Cleanup
        await close_async_redis_client(client)


@pytest.mark.asyncio
async def test__redis_client__cancellation_during_operation__cleanup_succeeds(
    redis_container: RedisContainer,
) -> None:
    # Arrange
    settings = FakeRedisSettings()
    settings.connection.host = redis_container.get_container_host_ip()
    settings.connection.port = int(redis_container.get_exposed_port(redis_container.port))
    client = create_async_redis_client(settings)

    async def run_and_cancel():
        await client.set("cancel_test", "1")
        await asyncio.sleep(10)

    # Act
    task = asyncio.create_task(run_and_cancel())
    await asyncio.sleep(0.1)
    task.cancel()

    try:
        await task
    except asyncio.CancelledError:
        pass

    # Assert - This should not raise even after parent task cancellation
    # because of asyncio.shield in close_async_redis_client
    await close_async_redis_client(client)
