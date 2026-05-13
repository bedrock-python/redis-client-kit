"""Redis infrastructure utilities."""

import base64
import binascii
from pathlib import Path
from urllib.parse import urlparse

from redis.backoff import ExponentialBackoff
from redis.retry import Retry

from .config import RedisSettingsProtocol


def parse_redis_url_node(node: str) -> tuple[str, int]:
    """Parse Redis node from host:port, [ipv6]:port or redis:// URL string."""
    normalized_node = node.strip()
    if not normalized_node:
        raise ValueError("Redis node cannot be empty")

    # If already a URL, don't prepend scheme
    url = normalized_node if normalized_node.startswith(("redis://", "rediss://")) else f"redis://{normalized_node}"

    parsed = urlparse(url)
    host = parsed.hostname
    port = parsed.port

    if host is None or port is None:
        raise ValueError(f"Invalid Redis node: {node!r}")

    # Validate port range
    if not (1 <= port <= 65535):
        raise ValueError(f"Invalid Redis port {port}: must be between 1 and 65535")

    return host, port


def build_base_redis_kwargs(settings: RedisSettingsProtocol) -> dict[str, object]:
    """Build base Redis client keyword arguments."""
    retry = build_redis_retry(settings)

    if settings.ssl.enabled:
        if settings.ssl.ca_certs:
            _validate_pem_format(settings.ssl.ca_certs, "CERTIFICATE")
        if settings.ssl.certfile:
            _validate_pem_format(settings.ssl.certfile, "CERTIFICATE")
        if settings.ssl.keyfile:
            _validate_pem_format(settings.ssl.keyfile, "PRIVATE KEY")

    kwargs: dict[str, object] = {
        "password": settings.connection.get_password(),
        "max_connections": settings.pool.max_connections,
        "socket_timeout": settings.pool.socket_timeout,
        "socket_connect_timeout": settings.pool.socket_connect_timeout,
        "socket_keepalive": settings.pool.socket_keepalive,
        "socket_keepalive_options": settings.pool.socket_keepalive_options,
        "health_check_interval": settings.health_check_interval,
        "decode_responses": settings.response.decode_responses,
        "encoding": settings.response.encoding,
        "client_name": settings.connection.client_name,
        "protocol": settings.connection.protocol,
        # SSL
        "ssl": settings.ssl.enabled,
        "ssl_cert_reqs": settings.ssl.cert_reqs,
        "ssl_ca_certs": settings.ssl.ca_certs,
        "ssl_certfile": settings.ssl.certfile,
        "ssl_keyfile": settings.ssl.keyfile,
    }

    if settings.cluster.enabled:
        kwargs["require_full_coverage"] = settings.cluster.require_full_coverage
        kwargs["read_from_replicas"] = settings.cluster.read_from_replicas

    if retry is not None:
        kwargs["retry"] = retry

    return kwargs


def build_redis_retry(settings: RedisSettingsProtocol) -> Retry | None:
    """Build Redis Retry object from settings."""
    if settings.retry.enabled and settings.retry.max_attempts:
        return Retry(
            backoff=ExponentialBackoff(
                cap=settings.retry.backoff_cap,
                base=settings.retry.backoff_base,
            ),
            retries=settings.retry.max_attempts,
        )
    return None


def _validate_pem_format(path: str | Path, file_type: str) -> None:
    """Validate that the file at path is a valid PEM file of given type.

    Checks for headers, footers, and that the content between them is valid base64.
    """
    p = Path(path)
    content_str = p.read_text().strip()
    header = f"-----BEGIN {file_type}-----"
    footer = f"-----END {file_type}-----"

    if not (content_str.startswith(header) and content_str.endswith(footer)):
        raise ValueError(f"Invalid PEM format in {p}: missing {file_type} header/footer")

    # Extract base64 content between header and footer
    inner_content = content_str[len(header) : -len(footer)].replace("\n", "").replace("\r", "").strip()
    try:
        base64.b64decode(inner_content, validate=True)
    except (ValueError, binascii.Error) as e:
        raise ValueError(f"Invalid base64 content in PEM file {p}: {e!s}") from e


def mask_redis_kwargs(kwargs: dict[str, object]) -> dict[str, object]:
    """Return a copy of Redis kwargs with sensitive data masked for logging."""
    masked = kwargs.copy()
    if masked.get("password"):
        masked["password"] = "********"
    return masked
