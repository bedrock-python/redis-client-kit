"""Integration tests configuration.

Automatically applies pytest.mark.integration to all tests in integration/ directory.
"""

try:
    import docker
    from docker.errors import DockerException
except ImportError:
    docker = None  # type: ignore[assignment]
    DockerException = Exception  # type: ignore[assignment, misc]

import pytest
from testcontainers.redis import RedisContainer

from redis_client_kit import RedisSettingsProtocol


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
    with RedisContainer("redis:7-alpine") as redis:
        yield redis


@pytest.fixture
def fake_redis_settings() -> FakeRedisSettings:
    """Provide fake Redis settings for testing."""
    return FakeRedisSettings()
