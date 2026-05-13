# Configuration

Complete guide to configuring redis-client-kit.

## Settings Protocol

redis-client-kit uses `RedisSettingsProtocol` which allows you to use any configuration system:

- Plain Python classes or dataclasses
- Pydantic models (via `[settings]` extra)
- Dictionary-based configs
- Environment variables (via Pydantic)

## BaseRedisSettings (Pydantic)

The easiest way to configure redis-client-kit is using `BaseRedisSettings`:

```bash
pip install redis-client-kit[settings]
```

```python
from redis_client_kit.settings import BaseRedisSettings

class MySettings(BaseRedisSettings):
    host: str = "localhost"
    port: int = 6379
    password: str | None = None
    db: int = 0
    
    # Connection pool
    max_connections: int = 10
    socket_timeout: float = 5.0
    
    # Health checks
    health_check_interval: int = 30
    
    # Response format
    decode_responses: bool = True
    encoding: str = "utf-8"
```

## Connection Settings

### Basic Connection

```python
settings = BaseRedisSettings(
    host="redis.example.com",
    port=6379,
    password="secret",
    db=0,
    client_name="myapp",
    protocol=2,  # RESP protocol version (2 or 3)
)
```

### From Environment Variables

```python
from pydantic_settings import SettingsConfigDict

class Settings(BaseRedisSettings):
    model_config = SettingsConfigDict(
        env_prefix="REDIS_",  # Read from REDIS_HOST, REDIS_PORT, etc.
        env_file=".env",
    )

# Set environment variables:
# REDIS_HOST=redis.example.com
# REDIS_PORT=6379
# REDIS_PASSWORD=secret

settings = Settings()
```

## Connection Pool Settings

Configure connection pool behavior:

```python
settings = BaseRedisSettings(
    max_connections=20,              # Maximum connections in pool
    socket_timeout=5.0,               # Socket operation timeout (seconds)
    socket_connect_timeout=5.0,       # Connection timeout (seconds)
    socket_keepalive=True,            # Enable TCP keepalive
    socket_keepalive_options={        # TCP keepalive options
        socket.TCP_KEEPIDLE: 1,
        socket.TCP_KEEPINTVL: 1,
        socket.TCP_KEEPCNT: 3,
    },
)
```

## Retry Settings

Configure automatic retry with exponential backoff:

```python
settings = BaseRedisSettings(
    retry_enabled=True,
    retry_max_attempts=3,      # Max retry attempts
    retry_backoff_base=0.1,    # Base delay in seconds
    retry_backoff_cap=1.0,     # Maximum delay in seconds
)
```

Retry logic uses exponential backoff:
```
delay = min(backoff_base * (2 ** attempt), backoff_cap)
```

## SSL/TLS Settings

Configure secure connections:

```python
settings = BaseRedisSettings(
    ssl=True,
    ssl_cert_reqs="required",  # "required", "optional", or "none"
    ssl_ca_certs="/path/to/ca.pem",
    ssl_certfile="/path/to/cert.pem",
    ssl_keyfile="/path/to/key.pem",
)
```

### SSL Certificate Validation

redis-client-kit validates PEM files automatically when SSL is enabled:

```python
from pathlib import Path

settings = BaseRedisSettings(
    ssl=True,
    ssl_cert_reqs="required",
    ssl_ca_certs=str(Path("/certs/ca.pem").absolute()),
)
```

## Cluster Settings

Configure Redis Cluster:

```python
settings = BaseRedisSettings(
    cluster_mode=True,
    cluster_nodes=[
        "node1.example.com:6379",
        "node2.example.com:6379",
        "node3.example.com:6379",
    ],
    require_full_coverage=True,    # Require all slots covered
    read_from_replicas=False,      # Read from replicas
)
```

### Cluster Discovery

If `cluster_nodes` is empty, uses `host:port` as the entry point:

```python
settings = BaseRedisSettings(
    cluster_mode=True,
    host="cluster-entry.example.com",
    port=6379,
)
```

## Response Settings

Configure response format:

```python
settings = BaseRedisSettings(
    decode_responses=True,  # Return strings instead of bytes
    encoding="utf-8",        # String encoding
)
```

With `decode_responses=True`:
```python
await client.get("key")  # Returns "value" (str)
```

With `decode_responses=False` (default):
```python
await client.get("key")  # Returns b"value" (bytes)
```

## Health Check Settings

Configure health check behavior:

```python
settings = BaseRedisSettings(
    health_check_interval=30,  # Seconds between health checks (0 to disable)
)
```

## Custom Settings Protocol

Don't want Pydantic? Implement `RedisSettingsProtocol`:

```python
from dataclasses import dataclass
from redis_client_kit.config import (
    RedisSettingsProtocol,
    RedisConnectionProtocol,
    RedisClusterProtocol,
    RedisPoolProtocol,
    RedisRetryProtocol,
    RedisSSLProtocol,
    RedisResponseProtocol,
)

@dataclass
class MyConnection:
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    client_name: str | None = None
    protocol: int = 2
    
    def get_password(self) -> str | None:
        return None

@dataclass
class MyCluster:
    enabled: bool = False
    nodes: list[str] | None = None
    require_full_coverage: bool = True
    read_from_replicas: bool = False

@dataclass
class MyPool:
    max_connections: int = 10
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    socket_keepalive: bool = True
    socket_keepalive_options: dict[int, int | bytes] | None = None

@dataclass
class MyRetry:
    enabled: bool = True
    max_attempts: int = 3
    backoff_base: float = 0.1
    backoff_cap: float = 1.0

@dataclass
class MySSL:
    enabled: bool = False
    cert_reqs: str | None = None
    ca_certs: str | None = None
    certfile: str | None = None
    keyfile: str | None = None

@dataclass
class MyResponse:
    decode_responses: bool = True
    encoding: str = "utf-8"

@dataclass
class MySettings:
    connection: MyConnection
    cluster: MyCluster
    pool: MyPool
    retry: MyRetry
    ssl: MySSL
    response: MyResponse
    health_check_interval: int = 30

# Use it
settings = MySettings(
    connection=MyConnection(host="redis.example.com"),
    cluster=MyCluster(),
    pool=MyPool(),
    retry=MyRetry(),
    ssl=MySSL(),
    response=MyResponse(),
)

client = create_async_redis_client(settings)
```

## Configuration Best Practices

### Production Settings

```python
class ProductionSettings(BaseRedisSettings):
    # Connection
    host: str = Field(default="redis.prod.example.com")
    port: int = 6379
    password: SecretStr  # Use SecretStr for passwords
    
    # Pool
    max_connections: int = 50  # Higher for production
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 2.0
    socket_keepalive: bool = True
    
    # Retry
    retry_enabled: bool = True
    retry_max_attempts: int = 5  # More retries
    retry_backoff_base: float = 0.2
    retry_backoff_cap: float = 2.0
    
    # Security
    ssl: bool = True
    ssl_cert_reqs: str = "required"
    
    # Health
    health_check_interval: int = 30
    
    # Response
    decode_responses: bool = True
```

### Development Settings

```python
class DevelopmentSettings(BaseRedisSettings):
    host: str = "localhost"
    port: int = 6379
    password: str | None = None
    
    # Smaller pool for dev
    max_connections: int = 5
    
    # No SSL in dev
    ssl: bool = False
    
    # Decode responses for easier debugging
    decode_responses: bool = True
```

### Testing Settings

```python
class TestSettings(BaseRedisSettings):
    host: str = "localhost"
    port: int = 6380  # Different port
    db: int = 15       # Use high DB number
    
    # Fast timeouts for tests
    socket_timeout: float = 1.0
    socket_connect_timeout: float = 1.0
    
    # No retries in tests
    retry_enabled: bool = False
    
    decode_responses: bool = True
```

## Next Steps

- [Quick Start](quickstart.md) — Basic usage examples
- [Advanced Usage](advanced.md) — Metrics, instrumentation, DI
- [API Reference](../reference/) — Complete API documentation
