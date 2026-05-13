"""Base Redis configuration."""

from typing import Literal

from ._deps import BaseModel, BaseSettings, Field, SecretStr, model_validator


class RedisConnectionSettings(BaseModel):  # type: ignore[misc]
    """Redis connection settings."""

    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, ge=1, le=65535, description="Redis port")
    password: SecretStr | None = Field(default=None, description="Redis password (optional)")
    db: int = Field(default=0, ge=0, le=15, description="Redis database number (ignored in cluster mode)")
    client_name: str | None = Field(default=None, description="Identifier for this client in Redis")
    protocol: int = Field(default=2, ge=2, le=3, description="Redis protocol version (2 or 3)")

    def get_password(self) -> str | None:
        """Return password as plain string."""
        if self.password is None:
            return None
        return self.password.get_secret_value()  # type: ignore[no-any-return]


class RedisClusterSettings(BaseModel):  # type: ignore[misc]
    """Redis cluster settings."""

    enabled: bool = Field(default=False, description="Use Redis Cluster")
    nodes: list[str] | None = Field(
        default=None,
        description="Cluster nodes list, e.g. ['host1:6379', 'host2:6379']",
    )
    require_full_coverage: bool = Field(default=True, description="Require all slots to be covered")
    read_from_replicas: bool = Field(default=False, description="Allow reading from replicas")


class RedisPoolSettings(BaseModel):  # type: ignore[misc]
    """Redis connection pool settings."""

    max_connections: int = Field(default=10, ge=1, description="Maximum pool connections")
    socket_timeout: float = Field(default=5.0, ge=0, description="Socket timeout in seconds")
    socket_connect_timeout: float = Field(default=5.0, ge=0, description="Connection timeout")
    socket_keepalive: bool = Field(default=True, description="Enable TCP keepalive")
    socket_keepalive_options: dict[int, int | bytes] | None = Field(
        default=None, description="Detailed TCP keepalive options"
    )


class RedisRetrySettings(BaseModel):  # type: ignore[misc]
    """Redis retry settings."""

    enabled: bool = Field(default=False, description="Enable retry mechanism")
    max_attempts: int = Field(default=0, ge=0, description="Maximum retry attempts (0 = no retry)")
    backoff_base: float = Field(default=1.0, ge=0, description="Exponential backoff base in seconds")
    backoff_cap: float = Field(default=10.0, ge=0, description="Exponential backoff cap in seconds")


class RedisSSLSettings(BaseModel):  # type: ignore[misc]
    """Redis SSL/TLS settings."""

    enabled: bool = Field(default=False, description="Enable SSL/TLS")
    cert_reqs: Literal["none", "optional", "required"] | None = Field(default=None, description="SSL cert requirements")
    ca_certs: str | None = Field(default=None, description="Path to CA certs file")
    certfile: str | None = Field(default=None, description="Path to client cert file")
    keyfile: str | None = Field(default=None, description="Path to client key file")


class RedisResponseSettings(BaseModel):  # type: ignore[misc]
    """Redis response settings."""

    decode_responses: bool = Field(default=False, description="Decode Redis responses as strings")
    encoding: str = Field(default="utf-8", description="Encoding for decode_responses")


class BaseRedisSettings(BaseSettings):
    """Base Redis configuration with grouped settings.

    Attributes:
        connection: Connection settings (host, port, password, etc.)
        cluster: Cluster mode settings
        pool: Connection pool settings
        retry: Retry mechanism settings
        ssl: SSL/TLS settings
        response: Response decoding settings
        key_prefix: Application-level key prefix
        health_check_interval: Health check interval in seconds
        metrics_enabled: Enable metrics collection
    """

    connection: RedisConnectionSettings = Field(default_factory=RedisConnectionSettings)
    cluster: RedisClusterSettings = Field(default_factory=RedisClusterSettings)
    pool: RedisPoolSettings = Field(default_factory=RedisPoolSettings)
    retry: RedisRetrySettings = Field(default_factory=RedisRetrySettings)
    ssl: RedisSSLSettings = Field(default_factory=RedisSSLSettings)
    response: RedisResponseSettings = Field(default_factory=RedisResponseSettings)

    key_prefix: str = Field(description="Redis key prefix")
    health_check_interval: int | None = Field(
        default=30,
        ge=0,
        description="Health check interval in seconds (None = disabled)",
    )
    metrics_enabled: bool = Field(default=False, description="Enable Redis metrics")

    @model_validator(mode="after")
    def _validate_cluster_and_tls(self) -> "BaseRedisSettings":
        if self.cluster.enabled:
            if not self.cluster.nodes and not self.connection.host:
                raise ValueError("Either cluster.nodes or connection.host must be provided when cluster is enabled")
            if self.connection.db != 0:
                raise ValueError(f"connection.db must be 0 when cluster is enabled, got {self.connection.db}")

        if self.ssl.enabled and self.ssl.cert_reqs is None:
            raise ValueError("ssl.cert_reqs is required when SSL is enabled")

        return self


__all__ = ["BaseRedisSettings"]
