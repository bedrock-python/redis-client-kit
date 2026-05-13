from unittest.mock import MagicMock, patch

import pytest

from redis_client_kit.utils import (
    _validate_pem_format,
    build_base_redis_kwargs,
    build_redis_retry,
    mask_redis_kwargs,
    parse_redis_url_node,
)


def test__parse_redis_url_node__valid_formats__parses_correctly() -> None:
    # Arrange - Use 127.0.0.1 instead of localhost for stability in tests
    ipv4_node = "127.0.0.1:6379"
    ipv6_node = "[::1]:6379"
    url_node = "redis://localhost:6379"
    url_ipv6_node = "redis://[::1]:6379"

    # Act
    host, port = parse_redis_url_node(ipv4_node)
    host_v6, port_v6 = parse_redis_url_node(ipv6_node)
    host_url, port_url = parse_redis_url_node(url_node)
    host_url_v6, port_url_v6 = parse_redis_url_node(url_ipv6_node)

    # Assert
    assert host == "127.0.0.1"
    assert port == 6379
    assert host_v6 == "::1"
    assert port_v6 == 6379
    assert host_url == "localhost"
    assert port_url == 6379
    assert host_url_v6 == "::1"
    assert port_url_v6 == 6379


def test__parse_redis_url_node__invalid_input__raises_value_error() -> None:
    # Act & Assert
    with pytest.raises(ValueError, match="cannot be empty"):
        parse_redis_url_node("")

    with pytest.raises(ValueError, match="Invalid Redis node"):
        parse_redis_url_node("invalid-node")


def test__build_redis_retry__retry_disabled__returns_none(mock_redis_settings: MagicMock) -> None:
    # Arrange
    mock_redis_settings.retry.enabled = False

    # Act
    result = build_redis_retry(mock_redis_settings)

    # Assert
    assert result is None


def test__build_redis_retry__retry_enabled__returns_retry_object(mock_redis_settings: MagicMock) -> None:
    # Arrange
    mock_redis_settings.retry.enabled = True
    mock_redis_settings.retry.max_attempts = 5

    # Act
    retry = build_redis_retry(mock_redis_settings)

    # Assert
    assert retry is not None
    assert getattr(retry, "_retries", 0) == 5


def test__build_redis_retry__no_max_attempts__returns_none(mock_redis_settings: MagicMock) -> None:
    # Arrange
    mock_redis_settings.retry.enabled = True
    mock_redis_settings.retry.max_attempts = None

    # Act
    result = build_redis_retry(mock_redis_settings)

    # Assert
    assert result is None


def test__build_base_redis_kwargs__full_config__returns_all_parameters(mock_redis_settings: MagicMock) -> None:
    # Arrange
    mock_redis_settings.pool.max_connections = 20
    mock_redis_settings.pool.socket_timeout = 5.0
    mock_redis_settings.health_check_interval = 30
    mock_redis_settings.connection.get_password.return_value = "secret"

    # Act
    kwargs = build_base_redis_kwargs(mock_redis_settings)

    # Assert
    assert kwargs["password"] == "secret"
    assert kwargs["max_connections"] == 20
    assert kwargs["socket_timeout"] == 5.0
    assert kwargs["health_check_interval"] == 30
    assert kwargs["decode_responses"] is True
    assert "retry" in kwargs


def test__build_base_redis_kwargs__retry_disabled__excludes_retry_parameter(
    mock_redis_settings: MagicMock,
) -> None:
    # Arrange
    mock_redis_settings.retry.enabled = False

    # Act
    kwargs = build_base_redis_kwargs(mock_redis_settings)

    # Assert
    assert "retry" not in kwargs


def test__build_base_redis_kwargs__ssl_enabled__includes_ssl_parameters(mock_redis_settings: MagicMock) -> None:
    # Arrange
    mock_redis_settings.ssl.enabled = True
    mock_redis_settings.ssl.ca_certs = "ca.pem"
    mock_redis_settings.ssl.certfile = "cert.pem"
    mock_redis_settings.ssl.keyfile = "key.pem"

    # Act
    with patch("pathlib.Path.read_text") as mock_read_text:
        mock_read_text.side_effect = [
            "-----BEGIN CERTIFICATE-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA\n-----END CERTIFICATE-----",
            "-----BEGIN CERTIFICATE-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA\n-----END CERTIFICATE-----",
            "-----BEGIN PRIVATE KEY-----\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEA\n-----END PRIVATE KEY-----",
        ]
        kwargs = build_base_redis_kwargs(mock_redis_settings)

    # Assert
    assert kwargs["ssl"] is True
    assert kwargs["ssl_ca_certs"] == "ca.pem"
    assert kwargs["ssl_certfile"] == "cert.pem"
    assert kwargs["ssl_keyfile"] == "key.pem"


def test__build_base_redis_kwargs__invalid_pem__raises_value_error(mock_redis_settings: MagicMock) -> None:
    # Arrange
    mock_redis_settings.ssl.enabled = True
    mock_redis_settings.ssl.ca_certs = "ca.pem"

    # Act & Assert
    with (
        patch("pathlib.Path.read_text", return_value="invalid"),
        pytest.raises(ValueError, match="Invalid PEM format"),
    ):
        build_base_redis_kwargs(mock_redis_settings)


def test__parse_redis_url_node__invalid_port__raises_value_error() -> None:
    # Act & Assert - Port > 65535
    with pytest.raises(ValueError):
        parse_redis_url_node("localhost:70000")

    # Act & Assert - Port 0
    with pytest.raises(ValueError, match="Invalid Redis port"):
        parse_redis_url_node("localhost:0")


def test__validate_pem_format__invalid_base64__raises_value_error() -> None:
    # Arrange
    pem_content = "-----BEGIN CERTIFICATE-----\nNOTBASE64!!!\n-----END CERTIFICATE-----"

    # Act & Assert
    with (
        patch("pathlib.Path.read_text", return_value=pem_content),
        pytest.raises(ValueError, match="Invalid base64 content"),
    ):
        _validate_pem_format("fake.pem", "CERTIFICATE")


def test__mask_redis_kwargs__sensitive_data__masks_password() -> None:
    # Arrange
    kwargs: dict[str, object] = {"host": "localhost", "port": 6379, "password": "secret_password", "db": 0}
    kwargs_no_pwd: dict[str, object] = {"host": "localhost"}

    # Act
    masked = mask_redis_kwargs(kwargs)
    masked_no_pwd = mask_redis_kwargs(kwargs_no_pwd)

    # Assert
    assert masked["password"] == "********"
    assert masked["host"] == "localhost"
    assert kwargs["password"] == "secret_password"  # Ensure original is not modified
    assert masked_no_pwd == kwargs_no_pwd
