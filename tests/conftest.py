"""Root conftest - only shared utilities, NO heavy fixtures."""

from unittest.mock import MagicMock

import pytest

from redis_client_kit.config import (
    RedisClusterProtocol,
    RedisConnectionProtocol,
    RedisPoolProtocol,
    RedisResponseProtocol,
    RedisRetryProtocol,
    RedisSettingsProtocol,
    RedisSSLProtocol,
)


@pytest.fixture
def mock_redis_settings() -> MagicMock:
    """Provide a mock for RedisSettingsProtocol with default values."""
    # Connection settings
    connection = MagicMock(spec=RedisConnectionProtocol)
    connection.host = "localhost"
    connection.port = 6379
    connection.db = 0
    connection.client_name = None
    connection.protocol = 2
    connection.get_password.return_value = "password"

    # Cluster settings
    cluster = MagicMock(spec=RedisClusterProtocol)
    cluster.enabled = False
    cluster.nodes = None
    cluster.require_full_coverage = True
    cluster.read_from_replicas = False

    # Pool settings
    pool = MagicMock(spec=RedisPoolProtocol)
    pool.max_connections = 10
    pool.socket_timeout = None
    pool.socket_connect_timeout = None
    pool.socket_keepalive = True
    pool.socket_keepalive_options = None

    # Retry settings
    retry = MagicMock(spec=RedisRetryProtocol)
    retry.enabled = True
    retry.max_attempts = 3
    retry.backoff_base = 0.1
    retry.backoff_cap = 1.0

    # SSL settings
    ssl = MagicMock(spec=RedisSSLProtocol)
    ssl.enabled = False
    ssl.cert_reqs = None
    ssl.ca_certs = None
    ssl.certfile = None
    ssl.keyfile = None

    # Response settings
    response = MagicMock(spec=RedisResponseProtocol)
    response.decode_responses = True
    response.encoding = "utf-8"

    # Main settings
    settings = MagicMock(spec=RedisSettingsProtocol)
    settings.connection = connection
    settings.cluster = cluster
    settings.pool = pool
    settings.retry = retry
    settings.ssl = ssl
    settings.response = response
    settings.health_check_interval = 30

    return settings
