"""Integration tests configuration.

Automatically applies pytest.mark.integration to all tests in integration/ directory.
"""

from collections.abc import Iterator

try:
    import docker
    from docker.errors import DockerException
except ImportError:
    docker = None  # type: ignore[assignment]
    DockerException = Exception  # type: ignore[assignment, misc]

import pytest
from redis import Redis
from redis.exceptions import OutOfMemoryError
from testcontainers.core.container import DockerContainer
from testcontainers.core.network import Network
from testcontainers.core.wait_strategies import LogMessageWaitStrategy
from testcontainers.redis import RedisContainer

from redis_client_kit import RedisSettingsProtocol

REDIS_IMAGE = "redis:7-alpine"
REDIS_PORT = 6379


def is_docker_available() -> bool:
    """Check if docker is available to run integration tests."""
    if docker is None:
        return False
    try:
        client = docker.from_env()
        client.version()
    except (DockerException, Exception):
        return False
    else:
        return True


def pytest_collection_modifyitems(items):
    """Automatically add integration marker to tests in the integration/ directory."""
    for item in items:
        # Check if the test file is under tests/integration/
        if "tests/integration" in str(item.fspath) or "tests\\integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)


# Helper classes for FakeRedisSettings


class FakeConnection:
    """Fake connection settings for testing."""

    host = "localhost"
    port = 6379
    db = 0
    client_name = None
    protocol = 2

    def get_password(self) -> str | None:
        return None


class FakeCluster:
    """Fake cluster settings for testing."""

    enabled = False
    nodes = None
    require_full_coverage = True
    read_from_replicas = False


class FakePool:
    """Fake pool settings for testing."""

    max_connections = 5
    socket_timeout = 5.0
    socket_connect_timeout = 5.0
    socket_keepalive = True
    socket_keepalive_options = None


class FakeRetry:
    """Fake retry settings for testing."""

    enabled = True
    max_attempts = 3
    backoff_base = 0.1
    backoff_cap = 1.0


class FakeSSL:
    """Fake SSL settings for testing."""

    enabled = False
    cert_reqs = None
    ca_certs = None
    certfile = None
    keyfile = None


class FakeResponse:
    """Fake response settings for testing."""

    decode_responses = True
    encoding = "utf-8"


class FakeRedisSettings(RedisSettingsProtocol):
    """Fake Redis settings for integration testing."""

    def __init__(self) -> None:
        self.connection = FakeConnection()
        self.cluster = FakeCluster()
        self.pool = FakePool()
        self.retry = FakeRetry()
        self.ssl = FakeSSL()
        self.response = FakeResponse()
        self.health_check_interval = 30


# Fixtures


@pytest.fixture(scope="module")
def redis_container() -> RedisContainer:
    """Provide a Redis container for integration tests."""
    with RedisContainer(REDIS_IMAGE) as redis:
        yield redis


@pytest.fixture
def fake_redis_settings() -> FakeRedisSettings:
    """Provide fake Redis settings for testing."""
    return FakeRedisSettings()


# Servers that answer PING and refuse writes


@pytest.fixture(scope="module")
def full_noeviction_redis() -> Iterator[DockerContainer]:
    """A primary capped at 1 MB under ``noeviction``, filled until it refuses the next write."""
    container = (
        DockerContainer(REDIS_IMAGE)
        .with_exposed_ports(REDIS_PORT)
        .with_command("redis-server --maxmemory 1mb --maxmemory-policy noeviction")
        .waiting_for(LogMessageWaitStrategy("Ready to accept connections"))
    )
    with container:
        fill_until_full(container)
        yield container


@pytest.fixture(scope="module")
def read_only_replica() -> Iterator[DockerContainer]:
    """A replica started as ``redis-server --replicaof primary 6379``, synced with a live primary."""
    with Network() as network:
        primary = (
            DockerContainer(REDIS_IMAGE)
            .with_exposed_ports(REDIS_PORT)
            .with_network(network)
            .with_network_aliases("primary")
        )
        replica = (
            DockerContainer(REDIS_IMAGE)
            .with_exposed_ports(REDIS_PORT)
            .with_network(network)
            .with_command(f"redis-server --replicaof primary {REDIS_PORT}")
            .waiting_for(LogMessageWaitStrategy("MASTER <-> REPLICA sync: Finished with success"))
        )
        with primary, replica:
            yield replica


def fill_until_full(container: DockerContainer) -> None:
    """Write 8 KB values until one is refused, so a test meets a server that is already full."""
    with Redis(host=container.get_container_host_ip(), port=int(container.get_exposed_port(REDIS_PORT))) as client:
        for i in range(512):
            try:
                client.set(f"fill:{i}", "x" * 8192)
            except OutOfMemoryError:
                return
    raise RuntimeError("Redis took 4 MB of writes under a 1 mb maxmemory cap")
