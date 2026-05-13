from unittest.mock import MagicMock, patch

import pytest

from redis_client_kit.utils import (
    _validate_pem_format,
    build_base_redis_kwargs,
    build_redis_retry,
    mask_redis_kwargs,
    parse_redis_url_node,
)

pytestmark = pytest.mark.unit


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


def test_build_redis_retry_disabled(mock_redis_settings: MagicMock) -> None:
    """Verify build_redis_retry returns None when retry is disabled."""
    mock_redis_settings.retry.enabled = False
    assert build_redis_retry(mock_redis_settings) is None


def test_build_redis_retry_enabled(mock_redis_settings: MagicMock) -> None:
    """Verify build_redis_retry returns Retry object when enabled."""
    mock_redis_settings.retry.enabled = True
    mock_redis_settings.retry.max_attempts = 5
    retry = build_redis_retry(mock_redis_settings)
    assert retry is not None
    assert getattr(retry, "_retries", 0) == 5


def test_build_redis_retry_no_attempts(mock_redis_settings: MagicMock) -> None:
    """Verify build_redis_retry returns None when max attempts is not set."""
    mock_redis_settings.retry.enabled = True
    mock_redis_settings.retry.max_attempts = None
    assert build_redis_retry(mock_redis_settings) is None


def test_build_base_redis_kwargs_full(mock_redis_settings: MagicMock) -> None:
    """Verify build_base_redis_kwargs returns all expected parameters."""
    mock_redis_settings.pool.max_connections = 20
    mock_redis_settings.pool.socket_timeout = 5.0
    mock_redis_settings.health_check_interval = 30
    mock_redis_settings.connection.get_password.return_value = "secret"

    kwargs = build_base_redis_kwargs(mock_redis_settings)

    assert kwargs["password"] == "secret"
    assert kwargs["max_connections"] == 20
    assert kwargs["socket_timeout"] == 5.0
    assert kwargs["health_check_interval"] == 30
    assert kwargs["decode_responses"] is True
    assert "retry" in kwargs


def test_build_base_redis_kwargs_no_retry(mock_redis_settings: MagicMock) -> None:
    """Verify build_base_redis_kwargs excludes retry when disabled."""
    mock_redis_settings.retry.enabled = False
    kwargs = build_base_redis_kwargs(mock_redis_settings)
    assert "retry" not in kwargs


def test_build_base_redis_kwargs_ssl(mock_redis_settings: MagicMock) -> None:
    """Verify build_base_redis_kwargs handles SSL settings with validation."""
    mock_redis_settings.ssl.enabled = True
    mock_redis_settings.ssl.ca_certs = "ca.pem"
    mock_redis_settings.ssl.certfile = "cert.pem"
    mock_redis_settings.ssl.keyfile = "key.pem"

    with patch("pathlib.Path.read_text") as mock_read_text:
        mock_read_text.side_effect = [
            "-----BEGIN CERTIFICATE-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA\n-----END CERTIFICATE-----",
            "-----BEGIN CERTIFICATE-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA\n-----END CERTIFICATE-----",
            "-----BEGIN PRIVATE KEY-----\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEA\n-----END PRIVATE KEY-----",
        ]
        kwargs = build_base_redis_kwargs(mock_redis_settings)

    assert kwargs["ssl"] is True
    assert kwargs["ssl_ca_certs"] == "ca.pem"
    assert kwargs["ssl_certfile"] == "cert.pem"
    assert kwargs["ssl_keyfile"] == "key.pem"


def test_build_base_redis_kwargs_ssl_invalid_pem(mock_redis_settings: MagicMock) -> None:
    """Verify build_base_redis_kwargs raises error for invalid PEM."""
    mock_redis_settings.ssl.enabled = True
    mock_redis_settings.ssl.ca_certs = "ca.pem"

    with (
        patch("pathlib.Path.read_text", return_value="invalid"),
        pytest.raises(ValueError, match="Invalid PEM format"),
    ):
        build_base_redis_kwargs(mock_redis_settings)


def test_parse_redis_url_node_invalid_port() -> None:
    """Verify port range validation in parse_redis_url_node."""
    # urllib.parse might raise ValueError for ports > 65535
    with pytest.raises(ValueError):
        parse_redis_url_node("localhost:70000")

    # Port 0 might be allowed by urlparse but disallowed by our logic
    with pytest.raises(ValueError, match="Invalid Redis port"):
        parse_redis_url_node("localhost:0")


def test_validate_pem_format_invalid_base64() -> None:
    """Verify base64 content validation in PEM files."""
    with (
        patch(
            "pathlib.Path.read_text",
            return_value="-----BEGIN CERTIFICATE-----\nNOTBASE64!!!\n-----END CERTIFICATE-----",
        ),
        pytest.raises(ValueError, match="Invalid base64 content"),
    ):
        _validate_pem_format("fake.pem", "CERTIFICATE")


def test_mask_redis_kwargs() -> None:
    """Verify masking of sensitive data in Redis keyword arguments."""
    kwargs: dict[str, object] = {"host": "localhost", "port": 6379, "password": "secret_password", "db": 0}
    masked = mask_redis_kwargs(kwargs)
    assert masked["password"] == "********"
    assert masked["host"] == "localhost"
    # Ensure original is not modified
    assert kwargs["password"] == "secret_password"

    # Test without password
    kwargs_no_pwd: dict[str, object] = {"host": "localhost"}
    assert mask_redis_kwargs(kwargs_no_pwd) == kwargs_no_pwd
