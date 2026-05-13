# Advanced Usage

Advanced features for production deployments.

## Metrics and Observability

### Custom Metrics Implementation

Implement `RedisMetricsProtocol` to collect metrics:

```python
from redis_client_kit.protocols import RedisMetricsProtocol
from prometheus_client import Counter, Histogram, Gauge

class PrometheusRedisMetrics(RedisMetricsProtocol):
    def __init__(self):
        self.command_duration = Histogram(
            "redis_command_duration_seconds",
            "Redis command duration",
            ["command", "status"],
        )
        self.command_total = Counter(
            "redis_commands_total",
            "Total Redis commands",
            ["command", "status"],
        )
        self.errors_total = Counter(
            "redis_errors_total",
            "Total Redis errors",
            ["error_type"],
        )
        self.pool_size = Gauge(
            "redis_pool_size",
            "Redis connection pool size",
        )
        self.pool_checked_out = Gauge(
            "redis_pool_checked_out",
            "Redis connections checked out from pool",
        )
    
    def record_command(self, command: str, status: str, duration: float) -> None:
        self.command_duration.labels(command=command, status=status).observe(duration)
        self.command_total.labels(command=command, status=status).inc()
    
    def record_error(self, error_type: str) -> None:
        self.errors_total.labels(error_type=error_type).inc()
    
    def record_pool_stats(self, pool_size: int, pool_checked_out: int) -> None:
        self.pool_size.set(pool_size)
        self.pool_checked_out.set(pool_checked_out)

# Use it
metrics = PrometheusRedisMetrics()
client = create_async_redis_client(settings, metrics=metrics)
```

### Zero Overhead Mode

When metrics aren't provided, you get plain redis-py clients with zero overhead:

```python
# No metrics = zero overhead
client = create_async_redis_client(settings, metrics=None)

# With metrics = instrumented client
client = create_async_redis_client(settings, metrics=my_metrics)
```

## Built-in Prometheus Metrics

```bash
pip install redis-client-kit[metrics]
```

### Using RedisMetrics

```python
from redis_client_kit.metrics import RedisMetrics
from redis_client_kit import create_async_redis_client

# Create metrics instance with optional prefix
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

### Metrics Configuration

```python
from redis_client_kit.metrics import RedisMetrics, REDIS_COMMAND_DURATION_BUCKETS

# Custom buckets for command duration
metrics = RedisMetrics(prefix="myapp")

# Default buckets: (0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0)
# These cover typical Redis command latencies from 0.1ms to 5 seconds
```

## Dishka Dependency Injection

```bash
pip install redis-client-kit[providers]
```

### Basic Setup

```python
from dishka import make_async_container, Provider, Scope, provide
from redis_client_kit import AsyncRedisClient
from redis_client_kit.providers import AsyncRedisProvider
from redis_client_kit.config import RedisSettingsProtocol

class SettingsProvider(Provider):
    scope = Scope.APP
    
    @provide
    def get_redis_settings(self) -> RedisSettingsProtocol:
        return BaseRedisSettings(
            host="localhost",
            port=6379,
        )

# Create container
container = make_async_container(
    AsyncRedisProvider(),
    SettingsProvider(),
)

# Use it
async with container() as ctx:
    redis_client = await ctx.get(AsyncRedisClient)
    await redis_client.set("key", "value")
```

### With Metrics

```python
from redis_client_kit.protocols import RedisMetricsProtocol

class MetricsProvider(Provider):
    scope = Scope.APP
    
    @provide
    def get_redis_metrics(self) -> RedisMetricsProtocol | None:
        return PrometheusRedisMetrics()

container = make_async_container(
    AsyncRedisProvider(),
    SettingsProvider(),
    MetricsProvider(),
)
```

### Automatic Lifecycle Management

`AsyncRedisProvider` handles:
- Connection retry with exponential backoff
- Health checks on startup
- Graceful shutdown with timeout protection
- Error logging

```python
# Provider automatically:
# 1. Creates client
# 2. Retries connection (max 3 attempts)
# 3. Checks health
# 4. Yields client
# 5. Closes safely on exit

async with container() as ctx:
    client = await ctx.get(AsyncRedisClient)
    # Client is ready and healthy
```

## Redis Cluster

### Cluster Configuration

```python
from redis_client_kit.settings import BaseRedisSettings

settings = BaseRedisSettings(
    cluster_mode=True,
    cluster_nodes=[
        "node1.example.com:6379",
        "node2.example.com:6379",
        "node3.example.com:6379",
    ],
    require_full_coverage=True,    # Fail if not all slots covered
    read_from_replicas=False,      # Read from replicas for better perf
)

client = create_async_redis_client(settings)
```

### Cluster Health Checks

```python
from redis_client_kit import check_async_redis_health

# For cluster, checks all nodes
is_healthy = await check_async_redis_health(client)

# Returns True only if all nodes respond
```

### Read from Replicas

Enable reading from replicas for read-heavy workloads:

```python
settings = BaseRedisSettings(
    cluster_mode=True,
    cluster_nodes=["..."],
    read_from_replicas=True,  # Distribute reads across replicas
)
```

## SSL/TLS in Production

### Full TLS Setup

```python
from pathlib import Path

settings = BaseRedisSettings(
    host="redis.prod.example.com",
    port=6380,  # Secure port
    
    # TLS configuration
    ssl=True,
    ssl_cert_reqs="required",
    ssl_ca_certs=str(Path("/certs/ca.pem")),
    ssl_certfile=str(Path("/certs/client-cert.pem")),
    ssl_keyfile=str(Path("/certs/client-key.pem")),
    
    # Password authentication
    password="secret-password",
)

client = create_async_redis_client(settings)
```

### Certificate Validation

redis-client-kit validates PEM files on startup:

```python
# Validates PEM format and base64 content
settings = BaseRedisSettings(
    ssl=True,
    ssl_ca_certs="/path/to/ca.pem",  # Must be valid PEM
)

# Raises ValueError if invalid:
# - Invalid PEM format
# - Invalid base64 content
# - File not found
```

## Connection Resilience

### Retry Logic

```python
settings = BaseRedisSettings(
    retry_enabled=True,
    retry_max_attempts=5,
    retry_backoff_base=0.2,
    retry_backoff_cap=2.0,
)

# Retries with exponential backoff:
# Attempt 1: 0.2s delay
# Attempt 2: 0.4s delay
# Attempt 3: 0.8s delay
# Attempt 4: 1.6s delay
# Attempt 5: 2.0s delay (capped)
```

### Connection Pool Tuning

```python
settings = BaseRedisSettings(
    max_connections=50,              # Pool size
    socket_timeout=5.0,               # Command timeout
    socket_connect_timeout=2.0,       # Connection timeout
    socket_keepalive=True,            # TCP keepalive
    socket_keepalive_options={        # TCP settings
        socket.TCP_KEEPIDLE: 1,
        socket.TCP_KEEPINTVL: 1,
        socket.TCP_KEEPCNT: 3,
    },
)
```

### Health Check Interval

```python
settings = BaseRedisSettings(
    health_check_interval=30,  # Ping every 30 seconds
)

# Set to 0 to disable:
settings = BaseRedisSettings(
    health_check_interval=0,  # No health checks
)
```

## Error Handling

### UVLoop RuntimeError Translation

redis-client-kit automatically translates UVLoop `RuntimeError` to `RedisConnectionError`:

```python
from redis.exceptions import ConnectionError as RedisConnectionError

try:
    await client.get("key")
except RedisConnectionError as e:
    # Handles both:
    # - Standard connection errors
    # - UVLoop "handler is closed" errors
    print(f"Connection failed: {e}")
```

### Graceful Degradation

```python
from redis.exceptions import (
    ConnectionError,
    TimeoutError,
    BusyLoadingError,
    ClusterDownError,
)

async def get_user(user_id: str) -> User | None:
    try:
        data = await redis_client.get(f"user:{user_id}")
        if data:
            return User.parse_raw(data)
    except BusyLoadingError:
        # Redis is loading data, retry later
        logger.warning("Redis is loading")
        return None
    except ClusterDownError:
        # Cluster is down during failover
        logger.error("Cluster is down")
        return None
    except (ConnectionError, TimeoutError):
        # Fallback to database
        logger.error("Redis unavailable, falling back to DB")
        return await db.get_user(user_id)
    
    return None
```

## Performance Optimization

### Connection Pooling

```python
# Bad: Creates new connection every time
for i in range(1000):
    client = create_async_redis_client(settings)
    await client.set(f"key:{i}", "value")
    await client.aclose()

# Good: Reuse connection pool
client = create_async_redis_client(settings)
for i in range(1000):
    await client.set(f"key:{i}", "value")
await client.aclose()
```

### Pipeline Batching

```python
# Batch commands for better performance
async with client.pipeline() as pipe:
    for i in range(1000):
        pipe.set(f"key:{i}", f"value:{i}")
    await pipe.execute()
```

### Response Decoding

```python
# Decode responses only when needed
settings = BaseRedisSettings(
    decode_responses=False,  # Return bytes (faster)
)

# Manual decoding when needed
data = await client.get("key")
if data:
    value = data.decode("utf-8")
```

## Monitoring

### Prometheus Metrics Example

```python
from prometheus_client import start_http_server

# Start metrics server
start_http_server(8000)

# Create client with metrics
metrics = PrometheusRedisMetrics()
client = create_async_redis_client(settings, metrics=metrics)

# Metrics available at http://localhost:8000/metrics
# - redis_command_duration_seconds
# - redis_commands_total
# - redis_errors_total
# - redis_pool_size
# - redis_pool_checked_out
```

### Logging

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("redis_client_kit").setLevel(logging.DEBUG)

# Logs connection attempts, errors, and lifecycle events
```

## Testing

### Test Configuration

```python
class TestSettings(BaseRedisSettings):
    host: str = "localhost"
    port: int = 6380  # Different port
    db: int = 15       # High DB number
    
    socket_timeout: float = 1.0
    retry_enabled: bool = False  # Fail fast in tests
    
    decode_responses: bool = True

# Use in tests
@pytest.fixture
async def redis_client():
    settings = TestSettings()
    client = create_async_redis_client(settings)
    yield client
    await client.flushdb()  # Clean up
    await client.aclose()
```

### Test Containers

```python
from testcontainers.redis import RedisContainer

@pytest.fixture(scope="module")
def redis_container():
    with RedisContainer("redis:7-alpine") as redis:
        yield redis

@pytest.fixture
async def redis_client(redis_container):
    settings = BaseRedisSettings(
        host=redis_container.get_container_host_ip(),
        port=int(redis_container.get_exposed_port(6379)),
    )
    client = create_async_redis_client(settings)
    yield client
    await client.aclose()
```

## Next Steps

- [Configuration Guide](configuration.md) — Complete settings reference
- [API Reference](../reference/) — Full API documentation
- [GitHub Repository](https://github.com/bedrock-python/redis-client-kit) — Source code and issues
