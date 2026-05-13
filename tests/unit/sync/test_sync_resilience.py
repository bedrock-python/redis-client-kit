"""Tests for sync Redis client retry logic and SSL validation."""

from unittest.mock import MagicMock, patch

from redis.retry import Retry

from redis_client_kit.sync import create_redis_client


def test__create_redis_client__retry_enabled__includes_retry_in_kwargs(
    mock_redis_settings: MagicMock,
) -> None:
    # Arrange
    mock_redis_settings.cluster.enabled = False
    mock_redis_settings.retry.enabled = True
    mock_redis_settings.retry.max_attempts = 5
    mock_redis_settings.retry.backoff_base = 0.2
    mock_redis_settings.retry.backoff_cap = 2.0

    # Act
    with patch("redis_client_kit.sync.factory.Redis") as mock_redis:
        create_redis_client(mock_redis_settings, metrics=None)

        # Assert
        kwargs = mock_redis.call_args[1]
        assert "retry" in kwargs
        retry = kwargs["retry"]
        assert isinstance(retry, Retry)


def test__create_redis_client__ssl_enabled__includes_ssl_in_kwargs(
    mock_redis_settings: MagicMock,
) -> None:
    # Arrange
    mock_redis_settings.cluster.enabled = False
    mock_redis_settings.ssl.enabled = True
    mock_redis_settings.ssl.cert_reqs = "required"
    mock_redis_settings.ssl.ca_certs = "/path/to/ca.pem"
    mock_redis_settings.ssl.certfile = "/path/to/cert.pem"
    mock_redis_settings.ssl.keyfile = "/path/to/key.pem"

    # Act
    with (
        patch("redis_client_kit.sync.factory.Redis") as mock_redis,
        patch("redis_client_kit.utils._validate_pem_format"),
    ):
        create_redis_client(mock_redis_settings, metrics=None)

        # Assert
        kwargs = mock_redis.call_args[1]
        assert kwargs["ssl"] is True
        assert kwargs["ssl_cert_reqs"] == "required"
        assert kwargs["ssl_ca_certs"] == "/path/to/ca.pem"
        assert kwargs["ssl_certfile"] == "/path/to/cert.pem"
        assert kwargs["ssl_keyfile"] == "/path/to/key.pem"


def test__create_redis_client__cluster_with_ssl__includes_ssl_in_kwargs(
    mock_redis_settings: MagicMock,
) -> None:
    # Arrange
    mock_redis_settings.cluster.enabled = True
    mock_redis_settings.cluster.nodes = ["node1:6379"]
    mock_redis_settings.ssl.enabled = True
    mock_redis_settings.ssl.cert_reqs = "required"
    mock_redis_settings.ssl.ca_certs = "/path/to/ca.pem"

    # Act
    with (
        patch("redis_client_kit.sync.factory.RedisCluster") as mock_cluster,
        patch("redis_client_kit.utils._validate_pem_format"),
    ):
        create_redis_client(mock_redis_settings, metrics=None)

        # Assert
        kwargs = mock_cluster.call_args[1]
        assert kwargs["ssl"] is True
        assert kwargs["ssl_cert_reqs"] == "required"
        assert kwargs["ssl_ca_certs"] == "/path/to/ca.pem"


def test__create_redis_client__decode_responses_true__includes_in_kwargs(
    mock_redis_settings: MagicMock,
) -> None:
    # Arrange
    mock_redis_settings.cluster.enabled = False
    mock_redis_settings.response.decode_responses = True
    mock_redis_settings.response.encoding = "utf-8"

    # Act
    with patch("redis_client_kit.sync.factory.Redis") as mock_redis:
        create_redis_client(mock_redis_settings, metrics=None)

        # Assert
        kwargs = mock_redis.call_args[1]
        assert kwargs["decode_responses"] is True
        assert kwargs["encoding"] == "utf-8"


def test__create_redis_client__health_check_interval__includes_in_kwargs(
    mock_redis_settings: MagicMock,
) -> None:
    # Arrange
    mock_redis_settings.cluster.enabled = False
    mock_redis_settings.health_check_interval = 60

    # Act
    with patch("redis_client_kit.sync.factory.Redis") as mock_redis:
        create_redis_client(mock_redis_settings, metrics=None)

        # Assert
        kwargs = mock_redis.call_args[1]
        assert kwargs["health_check_interval"] == 60
