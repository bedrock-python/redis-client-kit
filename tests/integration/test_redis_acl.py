"""Integration tests for logging in as a Redis ACL user."""

from collections.abc import Iterator

import pytest
from redis import Redis
from redis.exceptions import NoPermissionError
from testcontainers.redis import RedisContainer

from redis_client_kit import (
    check_async_redis_health,
    close_async_redis_client,
    close_redis_client,
    create_async_redis_client,
    create_redis_client,
)
from redis_client_kit.settings import BaseRedisSettings, RedisConnectionSettings

from .conftest import is_docker_available

pytestmark = pytest.mark.skipif(not is_docker_available(), reason="Docker is not available")

ACL_USER = "app"
ACL_PASSWORD = "app-secret"
# The rule docs/guide/configuration.md gives for an application user.
ACL_RULE = f"on >{ACL_PASSWORD} resetkeys ~app:* resetchannels &app:* -@all +@read +@write -@dangerous +ping"


@pytest.fixture
def admin(redis_container: RedisContainer) -> Iterator[Redis]:
    """The container's ``default`` user, with the ACL user created and another app's key written."""
    client = Redis(
        host=redis_container.get_container_host_ip(),
        port=int(redis_container.get_exposed_port(redis_container.port)),
    )
    client.execute_command("ACL", "SETUSER", ACL_USER, *ACL_RULE.split())
    client.set("other:x", "theirs")
    try:
        yield client
    finally:
        client.acl_deluser(ACL_USER)
        client.delete("other:x", "app:x", "app:probe")
        client.close()


def acl_settings(admin: Redis, *, protocol: int = 2) -> BaseRedisSettings:
    kwargs = admin.connection_pool.connection_kwargs
    return BaseRedisSettings(
        key_prefix="app",
        connection=RedisConnectionSettings(
            host=kwargs["host"],
            port=kwargs["port"],
            username=ACL_USER,
            password=ACL_PASSWORD,
            protocol=protocol,
        ),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("protocol", [2, 3], ids=["resp2", "resp3"])
async def test__async_client__acl_user__confined_to_its_keys(admin: Redis, protocol: int) -> None:
    # Arrange
    client = create_async_redis_client(acl_settings(admin, protocol=protocol))

    try:
        # Act & Assert
        assert await client.set("app:x", "mine") is True
        with pytest.raises(NoPermissionError):
            await client.get("other:x")
        with pytest.raises(NoPermissionError):
            await client.flushdb()
    finally:
        await close_async_redis_client(client)

    assert admin.get("other:x") == b"theirs"


def test__sync_client__acl_user__confined_to_its_keys(admin: Redis) -> None:
    # Arrange
    client = create_redis_client(acl_settings(admin))

    try:
        # Act & Assert
        assert client.set("app:x", "mine") is True
        with pytest.raises(NoPermissionError):
            client.get("other:x")
    finally:
        close_redis_client(client)


@pytest.mark.asyncio
async def test__check_async_redis_health__acl_user__ping_and_write_probe_pass(admin: Redis) -> None:
    # Arrange
    client = create_async_redis_client(acl_settings(admin))

    try:
        # Act
        pinged = await check_async_redis_health(client)
        probed = await check_async_redis_health(client, write_key="app:probe")

        # Assert
        assert pinged is True
        assert probed is True
    finally:
        await close_async_redis_client(client)
