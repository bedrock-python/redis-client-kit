# redis-client-kit

Production-ready Redis client with optional Pydantic settings, Prometheus metrics, and Dishka dependency injection support.

[![PyPI](https://img.shields.io/pypi/v/redis-client-kit?color=blue)](https://pypi.org/project/redis-client-kit/)
[![Python](https://img.shields.io/pypi/pyversions/redis-client-kit)](https://pypi.org/project/redis-client-kit/)
[![License](https://img.shields.io/github/license/bedrock-python/redis-client-kit)](LICENSE)
[![CI](https://github.com/bedrock-python/redis-client-kit/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/bedrock-python/redis-client-kit/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/bedrock-python/redis-client-kit/graph/badge.svg)](https://codecov.io/gh/bedrock-python/redis-client-kit)
[![Docs](https://img.shields.io/badge/docs-online-blue)](https://bedrock-python.github.io/redis-client-kit/)

## Features

| Feature | Included | Extra Required |
|---------|----------|----------------|
| **Async & Sync Clients** | ✅ Core | - |
| **Redis Cluster Support** | ✅ Core | - |
| **Connection Pooling** | ✅ Core | - |
| **Health Checks** | ✅ Core | - |
| **Retry Logic** | ✅ Core | - |
| **SSL/TLS** | ✅ Core | - |
| **Metrics Protocol** | ✅ Core | - |
| **Pydantic Settings** | ⚙️ Optional | `[settings]` |
| **Prometheus Metrics** | ⚙️ Optional | `[metrics]` |
| **Dishka DI** | ⚙️ Optional | `[providers]` |

## Installation

### Core only (zero dependencies except redis-py)

```bash
pip install redis-client-kit
```

### With optional features

```bash
# Pydantic settings support
pip install redis-client-kit[settings]

# Prometheus metrics
pip install redis-client-kit[metrics]

# Dishka dependency injection
pip install redis-client-kit[providers]

# Everything
pip install redis-client-kit[all]
```

**Requirements:** Python 3.10+

## Quick Start

### Basic Usage (Core)

```python
from redis_client_kit import create_async_redis_client
from redis_client_kit.config import RedisSettingsProtocol

# Define your settings (can be a dataclass, dict, or Pydantic model)
class MySettings:
    class connection:
        host = "localhost"
        port = 6379
        db = 0
        
        @staticmethod
        def get_password():
            return None
    
    class cluster:
        enabled = False
        nodes = None
        require_full_coverage = True
        read_from_replicas = False
    
    class pool:
        max_connections = 10
        socket_timeout = 5.0
        socket_connect_timeout = 5.0
        socket_keepalive = True
        socket_keepalive_options = None
    
    class retry:
        enabled = True
        max_attempts = 3
        backoff_base = 0.1
        backoff_cap = 1.0
    
    class ssl:
        enabled = False
        cert_reqs = None
        ca_certs = None
        certfile = None
        keyfile = None
    
    class response:
        decode_responses = True
        encoding = "utf-8"
    
    health_check_interval = 30

# Create client
settings = MySettings()
client = create_async_redis_client(settings)

# Use it
await client.set("key", "value")
value = await client.get("key")
print(value)  # "value"

# Clean up
await client.aclose()
```

### With Pydantic Settings

```python
from redis_client_kit import create_async_redis_client
from redis_client_kit.settings import BaseRedisSettings, RedisConnectionSettings

# Use BaseRedisSettings with custom connection settings
settings = BaseRedisSettings(
    key_prefix="myapp",
    connection=RedisConnectionSettings(
        host="localhost",
        port=6379,
    ),
)

client = create_async_redis_client(settings)
await client.set("key", "value")
await client.aclose()
```

### With Metrics (Prometheus)

```python
from redis_client_kit import create_async_redis_client
from redis_client_kit.protocols import RedisMetricsProtocol

class MyMetrics(RedisMetricsProtocol):
    def record_command(self, command: str, status: str, duration: float) -> None:
        # Record to Prometheus
        redis_command_duration.labels(command=command, status=status).observe(duration)
    
    def record_error(self, error_type: str) -> None:
        redis_errors_total.labels(error_type=error_type).inc()
    
    def record_pool_stats(self, pool_size: int, pool_checked_out: int) -> None:
        redis_pool_size.set(pool_size)
        redis_pool_checked_out.set(pool_checked_out)

metrics = MyMetrics()
client = create_async_redis_client(settings, metrics=metrics)
```

### With Prometheus Metrics (Built-in)

```python
from redis_client_kit import create_async_redis_client
from redis_client_kit.metrics import RedisMetrics

# Create metrics instance (with optional prefix)
metrics = RedisMetrics(prefix="myapp")

# Create instrumented client
client = create_async_redis_client(settings, metrics=metrics)

# Metrics are automatically collected:
# - myapp_redis_pool_size
# - myapp_redis_pool_checked_out
# - myapp_redis_commands_total{command, status}
# - myapp_redis_command_duration_seconds{command}
# - myapp_redis_connection_errors_total{error_type}
```

### With Dishka DI

```python
from dishka import make_async_container
from redis_client_kit.providers import AsyncRedisProvider

container = make_async_container(
    AsyncRedisProvider(),
    SettingsProvider(),  # Your settings provider
)

async with container() as ctx:
    redis_client = await ctx.get(AsyncRedisClient)
    await redis_client.set("key", "value")
```

## Redis Cluster

```python
from redis_client_kit.settings import BaseRedisSettings, RedisClusterSettings

settings = BaseRedisSettings(
    key_prefix="myapp",
    cluster=RedisClusterSettings(
        enabled=True,
        nodes=["node1:6379", "node2:6379", "node3:6379"],
    ),
)

client = create_async_redis_client(settings)
```

## Synchronous Client

```python
from redis_client_kit.sync import create_redis_client

# Same API, but synchronous
client = create_redis_client(settings)
client.set("key", "value")
value = client.get("key")
client.close()
```

## Key Features

### Zero Overhead by Default

When you don't provide metrics, you get plain `redis-py` clients with zero instrumentation overhead:

```python
# No metrics = plain Redis client (no performance cost)
client = create_async_redis_client(settings, metrics=None)

# With metrics = instrumented client
client = create_async_redis_client(settings, metrics=my_metrics)
```

### Health Checks

```python
from redis_client_kit import check_async_redis_health

is_healthy = await check_async_redis_health(client)
if is_healthy:
    print("Redis is ready!")
```

### Graceful Shutdown

```python
from redis_client_kit import close_async_redis_client

# Safe cleanup with timeout and asyncio.shield
await close_async_redis_client(client)
```

### SSL/TLS Support

```python
from redis_client_kit.settings import RedisSSLSettings

settings = BaseRedisSettings(
    key_prefix="myapp",
    ssl=RedisSSLSettings(
        enabled=True,
        cert_reqs="required",
        ca_certs="/path/to/ca.pem",
        certfile="/path/to/cert.pem",
        keyfile="/path/to/key.pem",
    ),
)
```

### Retry Logic

```python
from redis_client_kit.settings import RedisRetrySettings

settings = BaseRedisSettings(
    key_prefix="myapp",
    retry=RedisRetrySettings(
        enabled=True,
        max_attempts=5,
        backoff_base=0.5,
        backoff_cap=2.0,
    ),
)
```

## Documentation

Full documentation: [bedrock-python.github.io/redis-client-kit](https://bedrock-python.github.io/redis-client-kit/)

- [Quick Start Guide](https://bedrock-python.github.io/redis-client-kit/guide/quickstart/)
- [Configuration Guide](https://bedrock-python.github.io/redis-client-kit/guide/configuration/)
- [Advanced Usage](https://bedrock-python.github.io/redis-client-kit/guide/advanced/)
- [API Reference](https://bedrock-python.github.io/redis-client-kit/reference/api/)

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

Apache 2.0 — see [LICENSE](LICENSE).
