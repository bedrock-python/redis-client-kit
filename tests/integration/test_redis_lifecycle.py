"""Integration tests for Redis client lifecycle and cancellation safety."""

import asyncio
import time

import pytest
from redis.exceptions import TimeoutError as RedisTimeoutError
from testcontainers.core.container import DockerContainer
from testcontainers.redis import RedisContainer

from redis_client_kit import (
    check_async_redis_health,
    check_redis_health,
    close_async_redis_client,
    close_redis_client,
    create_async_redis_client,
    create_redis_client,
)
from redis_client_kit.utils import WRITE_PROBE_TTL_S

from .conftest import REDIS_PORT, FakeRedisSettings, is_docker_available

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


@pytest.mark.asyncio
async def test__async_redis_client__retry_disabled_and_redis_paused__raises_within_socket_timeout(
    redis_container: RedisContainer,
) -> None:
    # Arrange
    settings = FakeRedisSettings()
    settings.connection.host = redis_container.get_container_host_ip()
    settings.connection.port = int(redis_container.get_exposed_port(redis_container.port))
    settings.pool.socket_timeout = 0.5
    settings.pool.socket_connect_timeout = 0.5
    settings.retry.enabled = False
    client = create_async_redis_client(settings)
    container = redis_container.get_wrapped_container()
    await client.ping()

    # Act
    container.pause()
    try:
        started = time.perf_counter()
        with pytest.raises(RedisTimeoutError):
            await client.get("paused")
        elapsed = time.perf_counter() - started
    finally:
        container.unpause()
        await close_async_redis_client(client)

    # Assert
    assert elapsed < 2.0


@pytest.mark.asyncio
async def test__async_redis_client__retry_enabled_and_redis_paused__retries_before_raising(
    redis_container: RedisContainer,
) -> None:
    # Arrange
    settings = FakeRedisSettings()
    settings.connection.host = redis_container.get_container_host_ip()
    settings.connection.port = int(redis_container.get_exposed_port(redis_container.port))
    settings.pool.socket_timeout = 0.5
    settings.pool.socket_connect_timeout = 0.5
    settings.retry.enabled = True
    settings.retry.max_attempts = 3
    settings.retry.backoff_base = 0.1
    settings.retry.backoff_cap = 1.0
    client = create_async_redis_client(settings)
    container = redis_container.get_wrapped_container()
    await client.ping()

    # Act
    container.pause()
    try:
        started = time.perf_counter()
        with pytest.raises(RedisTimeoutError):
            await client.get("paused")
        elapsed = time.perf_counter() - started
    finally:
        container.unpause()
        await close_async_redis_client(client)

    # Assert - four attempts of 0.5 s plus 0.2 + 0.4 + 0.8 s of backoff, not a single attempt
    assert 3.0 <= elapsed < 6.0


def test__sync_redis_client__retry_disabled_and_redis_paused__raises_within_socket_timeout(
    redis_container: RedisContainer,
) -> None:
    # Arrange
    settings = FakeRedisSettings()
    settings.connection.host = redis_container.get_container_host_ip()
    settings.connection.port = int(redis_container.get_exposed_port(redis_container.port))
    settings.pool.socket_timeout = 0.5
    settings.pool.socket_connect_timeout = 0.5
    settings.retry.enabled = False
    client = create_redis_client(settings)
    container = redis_container.get_wrapped_container()
    client.ping()

    # Act
    container.pause()
    try:
        started = time.perf_counter()
        with pytest.raises(RedisTimeoutError):
            client.get("paused")
        elapsed = time.perf_counter() - started
    finally:
        container.unpause()
        close_redis_client(client)

    # Assert
    assert elapsed < 2.0


def test__sync_redis_client__retry_enabled_and_redis_paused__retries_before_raising(
    redis_container: RedisContainer,
) -> None:
    # Arrange
    settings = FakeRedisSettings()
    settings.connection.host = redis_container.get_container_host_ip()
    settings.connection.port = int(redis_container.get_exposed_port(redis_container.port))
    settings.pool.socket_timeout = 0.5
    settings.pool.socket_connect_timeout = 0.5
    settings.retry.enabled = True
    settings.retry.max_attempts = 3
    settings.retry.backoff_base = 0.1
    settings.retry.backoff_cap = 1.0
    client = create_redis_client(settings)
    container = redis_container.get_wrapped_container()
    client.ping()

    # Act
    container.pause()
    try:
        started = time.perf_counter()
        with pytest.raises(RedisTimeoutError):
            client.get("paused")
        elapsed = time.perf_counter() - started
    finally:
        container.unpause()
        close_redis_client(client)

    # Assert - four attempts of 0.5 s plus 0.2 + 0.4 + 0.8 s of backoff, not a single attempt
    assert 3.0 <= elapsed < 6.0


@pytest.mark.asyncio
async def test__async_health_check__write_key_on_a_healthy_server__returns_true_and_the_key_expires(
    redis_container: RedisContainer,
) -> None:
    # Arrange
    settings = FakeRedisSettings()
    settings.connection.host = redis_container.get_container_host_ip()
    settings.connection.port = int(redis_container.get_exposed_port(redis_container.port))
    client = create_async_redis_client(settings)

    # Act
    try:
        is_healthy = await check_async_redis_health(client, write_key="test:health")
        ttl = await client.ttl("test:health")
    finally:
        await close_async_redis_client(client)

    # Assert
    assert is_healthy is True
    assert 0 < ttl <= WRITE_PROBE_TTL_S


@pytest.mark.asyncio
async def test__async_health_check__read_only_replica__ping_says_healthy_and_the_write_probe_does_not(
    read_only_replica: DockerContainer,
) -> None:
    # Arrange
    settings = FakeRedisSettings()
    settings.connection.host = read_only_replica.get_container_host_ip()
    settings.connection.port = int(read_only_replica.get_exposed_port(REDIS_PORT))
    client = create_async_redis_client(settings)

    # Act
    try:
        ping_only = await check_async_redis_health(client)
        with_write_probe = await check_async_redis_health(client, write_key="test:health")
    finally:
        await close_async_redis_client(client)

    # Assert
    assert ping_only is True
    assert with_write_probe is False


@pytest.mark.asyncio
async def test__async_health_check__full_noeviction_server__ping_says_healthy_and_the_write_probe_does_not(
    full_noeviction_redis: DockerContainer,
) -> None:
    # Arrange
    settings = FakeRedisSettings()
    settings.connection.host = full_noeviction_redis.get_container_host_ip()
    settings.connection.port = int(full_noeviction_redis.get_exposed_port(REDIS_PORT))
    client = create_async_redis_client(settings)

    # Act
    try:
        ping_only = await check_async_redis_health(client)
        with_write_probe = await check_async_redis_health(client, write_key="test:health")
    finally:
        await close_async_redis_client(client)

    # Assert
    assert ping_only is True
    assert with_write_probe is False


def test__sync_health_check__write_key_on_a_healthy_server__returns_true_and_the_key_expires(
    redis_container: RedisContainer,
) -> None:
    # Arrange
    settings = FakeRedisSettings()
    settings.connection.host = redis_container.get_container_host_ip()
    settings.connection.port = int(redis_container.get_exposed_port(redis_container.port))
    client = create_redis_client(settings)

    # Act
    try:
        is_healthy = check_redis_health(client, write_key="test:health")
        ttl = client.ttl("test:health")
    finally:
        close_redis_client(client)

    # Assert
    assert is_healthy is True
    assert 0 < ttl <= WRITE_PROBE_TTL_S


def test__sync_health_check__read_only_replica__ping_says_healthy_and_the_write_probe_does_not(
    read_only_replica: DockerContainer,
) -> None:
    # Arrange
    settings = FakeRedisSettings()
    settings.connection.host = read_only_replica.get_container_host_ip()
    settings.connection.port = int(read_only_replica.get_exposed_port(REDIS_PORT))
    client = create_redis_client(settings)

    # Act
    try:
        ping_only = check_redis_health(client)
        with_write_probe = check_redis_health(client, write_key="test:health")
    finally:
        close_redis_client(client)

    # Assert
    assert ping_only is True
    assert with_write_probe is False


def test__sync_health_check__full_noeviction_server__ping_says_healthy_and_the_write_probe_does_not(
    full_noeviction_redis: DockerContainer,
) -> None:
    # Arrange
    settings = FakeRedisSettings()
    settings.connection.host = full_noeviction_redis.get_container_host_ip()
    settings.connection.port = int(full_noeviction_redis.get_exposed_port(REDIS_PORT))
    client = create_redis_client(settings)

    # Act
    try:
        ping_only = check_redis_health(client)
        with_write_probe = check_redis_health(client, write_key="test:health")
    finally:
        close_redis_client(client)

    # Assert
    assert ping_only is True
    assert with_write_probe is False
