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

The model is **grouped, not flat**. Six group models go in as objects — `connection`,
`cluster`, `pool`, `retry`, `ssl` and `response` — alongside the top-level `key_prefix`,
`health_check_interval` and `metrics_enabled`. It forbids extra keywords, so a flat
`BaseRedisSettings(host="localhost")` raises `ValidationError: Extra inputs are not
permitted`, and `key_prefix` is required.

```python
from redis_client_kit.settings import (
    BaseRedisSettings,
    RedisConnectionSettings,
    RedisPoolSettings,
    RedisResponseSettings,
)

settings = BaseRedisSettings(
    key_prefix="myapp",
    connection=RedisConnectionSettings(host="localhost", port=6379),
    pool=RedisPoolSettings(max_connections=10, socket_timeout=5.0),
    response=RedisResponseSettings(decode_responses=True, encoding="utf-8"),
    health_check_interval=30,
)
```

`key_prefix` is required but never read by this library — it is a value you carry and
apply to your own keys.

Subclass it when you want different defaults or extra fields of your own:

```python
from pydantic import Field

class MySettings(BaseRedisSettings):
    key_prefix: str = "myapp"
    connection: RedisConnectionSettings = Field(
        default_factory=lambda: RedisConnectionSettings(host="redis.internal"),
    )
```

## Connection Settings

### Basic Connection

```python
from redis_client_kit.settings import BaseRedisSettings, RedisConnectionSettings

settings = BaseRedisSettings(
    key_prefix="myapp",
    connection=RedisConnectionSettings(
        host="redis.example.com",
        port=6379,
        password="secret",   # stored as SecretStr, read with get_password()
        db=0,
        client_name="myapp",
        protocol=2,          # RESP protocol version (2 or 3)
    ),
)
```

### From Environment Variables

`BaseRedisSettings` sets no `env_prefix` and no `env_nested_delimiter`, so out of the box
the names are the bare field names and a group is one JSON document:

```bash
KEY_PREFIX=myapp
HEALTH_CHECK_INTERVAL=15
CONNECTION='{"host": "redis.example.com", "port": 6379}'
```

Subclass it for the usual per-field shape:

```python
from pydantic_settings import SettingsConfigDict

class Settings(BaseRedisSettings):
    model_config = SettingsConfigDict(
        env_prefix="REDIS_",
        env_nested_delimiter="__",
        env_file=".env",
    )

# Set environment variables:
# REDIS_KEY_PREFIX=myapp
# REDIS_CONNECTION__HOST=redis.example.com
# REDIS_CONNECTION__PORT=6379
# REDIS_CONNECTION__PASSWORD=secret

settings = Settings()
```

## Connection Pool Settings

Configure connection pool behavior:

```python
import socket

from redis_client_kit.settings import RedisPoolSettings

settings = BaseRedisSettings(
    key_prefix="myapp",
    pool=RedisPoolSettings(
        max_connections=20,               # Maximum connections in pool
        socket_timeout=5.0,               # Socket operation timeout (seconds)
        socket_connect_timeout=5.0,       # Connection timeout (seconds)
        socket_keepalive=True,            # Enable TCP keepalive
        socket_keepalive_options={        # TCP keepalive options
            socket.TCP_KEEPIDLE: 1,
            socket.TCP_KEEPINTVL: 1,
            socket.TCP_KEEPCNT: 3,
        },
    ),
)
```

## Retry Settings

Configure automatic retry with exponential backoff:

```python
from redis_client_kit.settings import RedisRetrySettings

settings = BaseRedisSettings(
    key_prefix="myapp",
    retry=RedisRetrySettings(
        enabled=True,
        max_attempts=3,      # Max retry attempts
        backoff_base=0.1,    # Base delay in seconds
        backoff_cap=1.0,     # Maximum delay in seconds
    ),
)
```

`max_attempts` defaults to `0`, and `enabled=True` on its own retries nothing: the `Retry`
object is handed to redis-py only when both `enabled` and `max_attempts` are truthy.

Retry logic uses exponential backoff:
```
delay = min(backoff_cap, backoff_base * (2 ** failures))
```

It covers connection failures — redis-py retries on `ConnectionError`, `TimeoutError` and
`socket.timeout`. A `ResponseError` from a bad command is raised on the first try.

## SSL/TLS Settings

Configure secure connections:

```python
from redis_client_kit.settings import RedisSSLSettings

settings = BaseRedisSettings(
    key_prefix="myapp",
    ssl=RedisSSLSettings(
        enabled=True,
        cert_reqs="required",  # "required", "optional", or "none"
        ca_certs="/path/to/ca.pem",
        certfile="/path/to/cert.pem",
        keyfile="/path/to/key.pem",
    ),
)
```

`cert_reqs` is mandatory once `enabled` is set: `ssl.enabled` with `cert_reqs=None` raises
`ValueError` from the model validator.

### SSL Certificate Validation

redis-client-kit validates PEM files when the client is built, not when it connects:

```python
from pathlib import Path

settings = BaseRedisSettings(
    key_prefix="myapp",
    ssl=RedisSSLSettings(
        enabled=True,
        cert_reqs="required",
        ca_certs=str(Path("/certs/ca.pem").absolute()),
    ),
)
```

## Cluster Settings

Configure Redis Cluster:

```python
from redis_client_kit.settings import RedisClusterSettings

settings = BaseRedisSettings(
    key_prefix="myapp",
    cluster=RedisClusterSettings(
        enabled=True,
        nodes=[
            "node1.example.com:6379",
            "node2.example.com:6379",
            "node3.example.com:6379",
        ],
        require_full_coverage=True,    # Require all slots covered
        read_from_replicas=False,      # Read from replicas
    ),
)
```

Every node string needs an explicit port; `node1.example.com` raises `ValueError` when the
factory parses it. `connection.db` must be `0` when the cluster is enabled.

### Cluster Discovery

If `cluster.nodes` is empty, uses `connection.host:port` as the entry point:

```python
settings = BaseRedisSettings(
    key_prefix="myapp",
    cluster=RedisClusterSettings(enabled=True),
    connection=RedisConnectionSettings(host="cluster-entry.example.com", port=6379),
)
```

## Response Settings

Configure response format:

```python
from redis_client_kit.settings import RedisResponseSettings

settings = BaseRedisSettings(
    key_prefix="myapp",
    response=RedisResponseSettings(
        decode_responses=True,  # Return strings instead of bytes
        encoding="utf-8",       # String encoding
    ),
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

`health_check_interval` is redis-py's per-connection ping interval, not the
`check_*_redis_health` function. `0` and `None` both disable it.

```python
settings = BaseRedisSettings(
    key_prefix="myapp",
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

Every attribute the protocols name has to be there: the factory reads all of them and
raises `AttributeError` on the first one missing. The protocols are not
`@runtime_checkable`, so `isinstance(settings, RedisSettingsProtocol)` raises `TypeError`.

## Configuration Best Practices

### Production Settings

```python
def production_settings(password: str) -> BaseRedisSettings:
    return BaseRedisSettings(
        key_prefix="myapp",
        connection=RedisConnectionSettings(
            host="redis.prod.example.com",
            port=6379,
            password=password,  # stored as SecretStr
        ),
        pool=RedisPoolSettings(
            max_connections=50,          # Higher for production
            socket_timeout=5.0,
            socket_connect_timeout=2.0,
            socket_keepalive=True,
        ),
        retry=RedisRetrySettings(
            enabled=True,
            max_attempts=5,              # More retries
            backoff_base=0.2,
            backoff_cap=2.0,
        ),
        ssl=RedisSSLSettings(enabled=True, cert_reqs="required"),
        response=RedisResponseSettings(decode_responses=True),
        health_check_interval=30,
    )
```

### Development Settings

```python
def development_settings() -> BaseRedisSettings:
    return BaseRedisSettings(
        key_prefix="myapp",
        connection=RedisConnectionSettings(host="localhost", port=6379),
        pool=RedisPoolSettings(max_connections=5),          # Smaller pool for dev
        response=RedisResponseSettings(decode_responses=True),
    )
```

### Testing Settings

```python
def test_settings() -> BaseRedisSettings:
    return BaseRedisSettings(
        key_prefix="test",
        connection=RedisConnectionSettings(
            host="localhost",
            port=6380,  # Different port
            db=15,      # Use high DB number
        ),
        pool=RedisPoolSettings(
            socket_timeout=1.0,          # Fast timeouts for tests
            socket_connect_timeout=1.0,
        ),
        retry=RedisRetrySettings(enabled=False),            # No retries in tests
        response=RedisResponseSettings(decode_responses=True),
    )
```

## Next Steps

- [Quick Start](quickstart.md) — Basic usage examples
- [Advanced Usage](advanced.md) — Metrics, instrumentation, DI
- [API Reference](../reference/index.md) — Complete API documentation
