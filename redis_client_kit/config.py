"""Redis configuration protocols."""

from typing import Protocol


class RedisConnectionProtocol(Protocol):
    """Protocol for Redis connection settings."""

    host: str
    port: int
    db: int
    client_name: str | None
    protocol: int

    def get_password(self) -> str | None:
        """Return password as plain string."""
        ...


class RedisClusterProtocol(Protocol):
    """Protocol for Redis cluster settings."""

    enabled: bool
    nodes: list[str] | None
    require_full_coverage: bool
    read_from_replicas: bool


class RedisPoolProtocol(Protocol):
    """Protocol for Redis connection pool settings."""

    max_connections: int
    socket_timeout: float
    socket_connect_timeout: float
    socket_keepalive: bool
    socket_keepalive_options: dict[int, int | bytes] | None


class RedisRetryProtocol(Protocol):
    """Protocol for Redis retry settings."""

    enabled: bool
    max_attempts: int
    backoff_base: float
    backoff_cap: float


class RedisSSLProtocol(Protocol):
    """Protocol for Redis SSL/TLS settings."""

    enabled: bool
    cert_reqs: str | None
    ca_certs: str | None
    certfile: str | None
    keyfile: str | None


class RedisResponseProtocol(Protocol):
    """Protocol for Redis response settings."""

    decode_responses: bool
    encoding: str


class RedisSettingsProtocol(Protocol):
    """Protocol for Redis configuration with grouped settings.

    Examples:
        Single node setup:
        >>> class Settings(RedisSettingsProtocol):
        ...     connection = RedisConnectionSettings(host="localhost", port=6379, db=0)
        ...     cluster = RedisClusterSettings(enabled=False)
        ...     # ... other attributes ...

        Redis Cluster setup:
        >>> class ClusterSettings(RedisSettingsProtocol):
        ...     connection = RedisConnectionSettings(...)
        ...     cluster = RedisClusterSettings(
        ...         enabled=True,
        ...         nodes=["redis-1:6379", "redis-2:6379", "redis-3:6379"]
        ...     )
        ...     # ... other attributes ...
    """

    connection: RedisConnectionProtocol
    cluster: RedisClusterProtocol
    pool: RedisPoolProtocol
    retry: RedisRetryProtocol
    ssl: RedisSSLProtocol
    response: RedisResponseProtocol
    health_check_interval: int | None
