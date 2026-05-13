"""Tests for BaseRedisSettings validation and configuration."""

import pytest
from pydantic import SecretStr, ValidationError

from redis_client_kit.settings import BaseRedisSettings
from redis_client_kit.settings.redis import (
    RedisClusterSettings,
    RedisConnectionSettings,
    RedisPoolSettings,
    RedisResponseSettings,
    RedisRetrySettings,
    RedisSSLSettings,
)


def test__base_redis_settings__default_values__uses_expected_defaults() -> None:
    # Arrange & Act
    settings = BaseRedisSettings(key_prefix="myapp")

    # Assert
    assert settings.connection.host == "localhost"
    assert settings.connection.port == 6379
    assert settings.connection.db == 0
    assert settings.cluster.enabled is False
    assert settings.pool.max_connections == 10
    assert settings.retry.enabled is False
    assert settings.ssl.enabled is False
    assert settings.response.decode_responses is False
    assert settings.key_prefix == "myapp"


def test__base_redis_settings__custom_connection__overrides_defaults() -> None:
    # Arrange & Act
    settings = BaseRedisSettings(
        key_prefix="myapp",
        connection=RedisConnectionSettings(
            host="redis.example.com",
            port=6380,
            db=1,
        ),
    )

    # Assert
    assert settings.connection.host == "redis.example.com"
    assert settings.connection.port == 6380
    assert settings.connection.db == 1


def test__base_redis_settings__cluster_mode_with_nodes__validates_successfully() -> None:
    # Arrange & Act
    settings = BaseRedisSettings(
        key_prefix="myapp",
        cluster=RedisClusterSettings(
            enabled=True,
            nodes=["node1.example.com:6379", "node2.example.com:6379"],
        ),
    )

    # Assert
    assert settings.cluster.enabled is True
    assert len(settings.cluster.nodes) == 2


def test__base_redis_settings__cluster_mode_without_nodes_or_host__raises_validation_error() -> None:
    # Arrange & Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        BaseRedisSettings(
            key_prefix="myapp",
            connection=RedisConnectionSettings(host=""),
            cluster=RedisClusterSettings(enabled=True),
        )

    # Assert
    assert "Either cluster.nodes or connection.host must be provided" in str(exc_info.value)


def test__base_redis_settings__cluster_mode_with_non_zero_db__raises_validation_error() -> None:
    # Arrange & Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        BaseRedisSettings(
            key_prefix="myapp",
            connection=RedisConnectionSettings(host="localhost", db=1),
            cluster=RedisClusterSettings(enabled=True),
        )

    # Assert
    assert "connection.db must be 0 when cluster is enabled" in str(exc_info.value)


def test__base_redis_settings__ssl_enabled_without_cert_reqs__raises_validation_error() -> None:
    # Arrange & Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        BaseRedisSettings(
            key_prefix="myapp",
            ssl=RedisSSLSettings(enabled=True, cert_reqs=None),
        )

    # Assert
    assert "ssl.cert_reqs is required when SSL is enabled" in str(exc_info.value)


def test__base_redis_settings__ssl_with_cert_reqs__validates_successfully() -> None:
    # Arrange & Act
    settings = BaseRedisSettings(
        key_prefix="myapp",
        ssl=RedisSSLSettings(
            enabled=True,
            cert_reqs="required",
            ca_certs="/path/to/ca.pem",
        ),
    )

    # Assert
    assert settings.ssl.enabled is True
    assert settings.ssl.cert_reqs == "required"
    assert settings.ssl.ca_certs == "/path/to/ca.pem"


def test__base_redis_settings__password_as_secret_str__masks_value() -> None:
    # Arrange & Act
    settings = BaseRedisSettings(
        key_prefix="myapp",
        connection=RedisConnectionSettings(
            password=SecretStr("my-secret-password"),
        ),
    )

    # Assert
    assert settings.connection.password is not None
    assert settings.connection.password.get_secret_value() == "my-secret-password"


def test__base_redis_settings__get_password__returns_plain_string() -> None:
    # Arrange
    settings = BaseRedisSettings(
        key_prefix="myapp",
        connection=RedisConnectionSettings(
            password=SecretStr("my-secret-password"),
        ),
    )

    # Act
    password = settings.connection.get_password()

    # Assert
    assert password == "my-secret-password"


def test__base_redis_settings__get_password_none__returns_none() -> None:
    # Arrange
    settings = BaseRedisSettings(
        key_prefix="myapp",
        connection=RedisConnectionSettings(password=None),
    )

    # Act
    password = settings.connection.get_password()

    # Assert
    assert password is None


def test__base_redis_settings__retry_configuration__includes_all_parameters() -> None:
    # Arrange & Act
    settings = BaseRedisSettings(
        key_prefix="myapp",
        retry=RedisRetrySettings(
            enabled=True,
            max_attempts=5,
            backoff_base=0.5,
            backoff_cap=10.0,
        ),
    )

    # Assert
    assert settings.retry.enabled is True
    assert settings.retry.max_attempts == 5
    assert settings.retry.backoff_base == 0.5
    assert settings.retry.backoff_cap == 10.0


def test__base_redis_settings__pool_configuration__includes_all_parameters() -> None:
    # Arrange & Act
    settings = BaseRedisSettings(
        key_prefix="myapp",
        pool=RedisPoolSettings(
            max_connections=50,
            socket_timeout=10.0,
            socket_connect_timeout=5.0,
            socket_keepalive=True,
        ),
    )

    # Assert
    assert settings.pool.max_connections == 50
    assert settings.pool.socket_timeout == 10.0
    assert settings.pool.socket_connect_timeout == 5.0
    assert settings.pool.socket_keepalive is True


def test__base_redis_settings__response_configuration__includes_all_parameters() -> None:
    # Arrange & Act
    settings = BaseRedisSettings(
        key_prefix="myapp",
        response=RedisResponseSettings(
            decode_responses=True,
            encoding="utf-8",
        ),
    )

    # Assert
    assert settings.response.decode_responses is True
    assert settings.response.encoding == "utf-8"


def test__base_redis_settings__health_check_interval__configurable() -> None:
    # Arrange & Act
    settings = BaseRedisSettings(key_prefix="myapp", health_check_interval=60)

    # Assert
    assert settings.health_check_interval == 60


def test__base_redis_settings__metrics_enabled__configurable() -> None:
    # Arrange & Act
    settings = BaseRedisSettings(key_prefix="myapp", metrics_enabled=True)

    # Assert
    assert settings.metrics_enabled is True
